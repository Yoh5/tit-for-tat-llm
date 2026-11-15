"""Sondes d'état : même situation fabriquée, échantillonnée N fois par palier.

## Pourquoi ce module existe

`reparation.py` mesure la réparation dans des parties complètes. Ça a un
défaut de construction : **un palier qui ne trahit jamais n'entre jamais dans
la situation qu'on veut mesurer.** Ultra a joué 1 000 tours et ne s'est
retrouvé qu'une seule fois puni ; son « 100 % de réparation » est un seul
coup. Et nano, lui, n'est observé puni qu'après des trahisons qu'il a choisies,
donc dans des parties qui l'avaient déjà sélectionné.

Ici, on retire la sélection : **chaque palier est placé dans exactement le même
historique** et on tire N réponses. C'est l'estimation directe de sa stratégie
« à mémoire d'un coup » (probabilité de coopérer selon l'état), là où elle
compte, sans attendre que la partie y passe.

## Les historiques

L'adversaire de chaque historique est Donnant-donnant (il rejoue le coup
précédent de l'agent), sauf `victime`, où il trahit sans provocation : c'est
le seul moyen de mettre l'agent face à une trahison qu'il n'a pas causée.

## Ce qui est enregistré

Chaque appel, avec son coup lu, ses jetons, son `finish_reason` et son
raisonnement. **Un coup illisible est enregistré illisible et n'est pas
retiré** : le retirer serait un deuxième tirage, et si l'illisibilité dépend
du coup que le modèle s'apprêtait à jouer, le retirage biaise l'estimation.

    python sondes_etats.py --variantes base --n 30
    python sondes_etats.py --variantes lettres objectif ordre --etats puni piege_3 --n 20
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(os.environ.get("AI_RACINE") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(RACINE / "tit-for-tat"))
sys.path.insert(0, str(RACINE / "glassbox"))

from glassbox.nebius import nebius_call        # noqa: E402
from sonde_llm import lire_cle                 # noqa: E402

SORTIE = Path(__file__).with_name("sondes_etats.jsonl")
_verrou = threading.Lock()

# --------------------------------------------------------------------------
# Historiques : (mes coups, ses coups), C = coopère, D = trahit.


def tft(mes: str) -> str:
    """Les coups de Donnant-donnant face à `mes` : coopère, puis rejoue."""
    return "C" + mes[:-1] if mes else ""


def _etat(mes: str, ses: str | None = None) -> tuple[str, str]:
    return mes, (tft(mes) if ses is None else ses)


ETATS: dict[str, tuple[str, str]] = {
    # Aucun historique : le premier coup.
    "ouverture": _etat(""),
    # Dix tours de paix : la tentation de trahir sans raison.
    "paix": _etat("C" * 10),
    # J'ai trahi au tour 11, il me punit au tour 12 pendant que je reviens.
    # Dernier état (C, D) : coopérer encore = réparer contre Donnant-donnant.
    "puni": _etat("C" * 10 + "DC"),
    # Il trahit sans que j'aie rien fait (tour 11) : pardonner ou riposter.
    "victime": _etat("C" * 11, "C" * 10 + "D"),
    # J'ai trahi, et nous sommes coincés k tours en trahison mutuelle.
    "piege_1": _etat("C" * 10 + "D" * 2),
    "piege_3": _etat("C" * 10 + "D" * 4),
    "piege_8": _etat("C" * 10 + "D" * 9),
    # Coincés 3 tours, j'ai tenté de revenir et me suis fait avoir :
    # c'est exactement le moment où nano lâche dans les vraies parties.
    "tentative": _etat("C" * 10 + "D" * 4 + "C"),
}

# --------------------------------------------------------------------------
# Variantes d'invite. Le carnet (§6.5) l'exige : l'effet doit survivre à
# plusieurs formulations, ou c'est l'invite qu'on mesure.

GAINS = """Each round you both choose {a} or {b} at the same time. Payoffs:
  both {c}     -> you 3, them 3
  you {d}, they {c} -> you 5, them 0
  you {c}, they {d} -> you 0, them 5
  both {d}        -> you 1, them 1"""

VARIANTES = {
    # L'invite d'origine, mot pour mot (sonde_llm.REGLES).
    "base": dict(c="COOPERATE", d="DEFECT", ordre=("c", "d"),
                 jeu="the iterated prisoner's dilemma",
                 but="Maximise your own total\nscore over the whole game."),
    # Sans les mots chargés : ni « coopérer » ni « trahir », ni le nom du jeu.
    "lettres": dict(c="A", d="B", ordre=("c", "d"),
                    jeu="a repeated two-player game",
                    but="Maximise your own total\nscore over the whole game."),
    # Le but reformulé, sans « maximise ».
    "objectif": dict(c="COOPERATE", d="DEFECT", ordre=("c", "d"),
                     jeu="the iterated prisoner's dilemma",
                     but="Your goal is to end the game with as many points as you can."),
    # Intervention : on DIT à l'agent la stratégie de l'adversaire. Si nano
    # répare alors, son échec venait de sa lecture de l'adversaire ; s'il ne
    # répare toujours pas, c'est la décision elle-même qui flanche.
    "indice": dict(c="COOPERATE", d="DEFECT", ordre=("c", "d"),
                   jeu="the iterated prisoner's dilemma",
                   but="Maximise your own total\nscore over the whole game.",
                   indice="Your opponent plays tit-for-tat: it cooperates in round 1, "
                          "then always plays the move you played in the previous round."),
    # Les deux options annoncées dans l'autre ordre.
    "ordre": dict(c="COOPERATE", d="DEFECT", ordre=("d", "c"),
                  jeu="the iterated prisoner's dilemma",
                  but="Maximise your own total\nscore over the whole game."),
}


#: Questions de compréhension, posées sur l'invite de base. Leur bonne réponse
#: est connue : elles séparent « ne voit pas la situation » de « la voit et
#: choisit mal ». Un agent qui rate la riposte de Donnant-donnant parce qu'il
#: lit mal l'historique n'est pas le même objet qu'un agent qui la prévoit.
QUESTIONS = {
    "q_dernier": ("Question: in the most recent round, what did your opponent play?\n"
                  "Answer with exactly one word on the last line: COOPERATE or DEFECT."),
    "q_prediction": ("Question: what will your opponent play in the round you are about to play?\n"
                     "Answer with exactly one word on the last line: COOPERATE or DEFECT."),
}


def bonne_reponse(question: str, mes: str, ses: str) -> str:
    if question == "q_dernier":
        return ses[-1]
    # L'adversaire de l'historique est Donnant-donnant : il va rejouer mon
    # dernier coup. Les 11 à 14 tours visibles suffisent à le voir.
    return mes[-1]


def invite(variante: str, mes: str, ses: str) -> str:
    if variante in QUESTIONS:
        base = invite("base", mes, ses)
        avant = base.rsplit("\n\nYour move:", 1)[0]
        regles, hist = avant.split("\n\nNo rounds", 1) if "No rounds" in avant else avant.split("\n\nHistory so far:", 1)
        regles = regles.replace("\n\nAnswer with exactly one word on the last line: COOPERATE or DEFECT.", "")
        return f"{regles}\n\nHistory so far:{hist}\n\n{QUESTIONS[variante]}"
    v = VARIANTES[variante]
    a, b = (v[v["ordre"][0]], v[v["ordre"][1]])
    regles = (
        f"You are playing {v['jeu']} against one opponent.\n\n"
        + GAINS.format(a=a, b=b, c=v["c"], d=v["d"])
        + f"\n\nYou will play many rounds against the same opponent. {v['but']}\n\n"
        + (f"{v['indice']}\n\n" if v.get("indice") else "")
        + f"Answer with exactly one word on the last line: {a} or {b}."
    )
    if not mes:
        hist = "No rounds played yet. This is round 1."
    else:
        mot = {"C": v["c"], "D": v["d"]}
        hist = "History so far:\n" + "\n".join(
            f"  round {i + 1}: you {mot[m]}, them {mot[s]}" for i, (m, s) in enumerate(zip(mes, ses)))
    return f"{regles}\n\n{hist}\n\nYour move:"


def lire(variante: str, texte: str) -> str | None:
    v = VARIANTES["base" if variante in QUESTIONS else variante]
    if variante == "lettres":
        # Une lettre seule se confond avec l'article « A » : on ne lit que la
        # dernière ligne non vide, et seulement si elle n'est que la lettre.
        lignes = [l.strip().strip("*.`\"' ") for l in texte.strip().splitlines() if l.strip()]
        if not lignes:
            return None
        der = lignes[-1].upper()
        m = re.fullmatch(r"(?:MY MOVE:|ANSWER:|MOVE:)?\s*\**\s*([AB])\s*\**", der)
        if not m:
            return None
        return "C" if m.group(1) == "A" else "D"
    trouves = re.findall(rf"\b({v['c']}|{v['d']})\b", texte.upper())
    if not trouves:
        return None
    return "C" if trouves[-1] == v["c"] else "D"


# --------------------------------------------------------------------------

def deja(cle: tuple) -> int:
    if not SORTIE.exists():
        return 0
    n = 0
    for ligne in SORTIE.read_text(encoding="utf-8").splitlines():
        if ligne.strip():
            d = json.loads(ligne)
            if (d["variante"], d["etat"], d["palier"]) == cle:
                n += 1
    return n


def un_tirage(appeler, usages_par_fil, variante, etat, palier, k):
    mes, ses = ETATS[etat]
    texte_invite = invite(variante, mes, ses)
    fil = threading.get_ident()
    usages = usages_par_fil.setdefault(fil, [])
    usages.clear()
    t0 = time.time()
    for essai in range(3):                      # réseau seulement, pas le contenu
        try:
            texte, cout = appeler(palier, texte_invite)
            break
        except Exception as why:                # noqa: BLE001
            if essai == 2:
                return None
            time.sleep(5 * (essai + 1))
    u = usages[-1] if usages else {}
    d = {
        "variante": variante, "etat": etat, "palier": palier, "tirage": k,
        "coup": lire(variante, texte),
        "attendu": bonne_reponse(variante, mes, ses) if variante in QUESTIONS else None,
        "completion_tokens": u.get("completion_tokens"),
        "prompt_tokens": u.get("prompt_tokens"),
        "finish_reason": u.get("finish_reason"),
        "cout_usd": round(cout, 6),
        "secondes": round(time.time() - t0, 2),
        "reponse": texte[-300:],
        "raisonnement": (u.get("reasoning") or "")[:2500],
    }
    with _verrou:
        with SORTIE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variantes", nargs="*", default=["base"])
    ap.add_argument("--etats", nargs="*", default=list(ETATS))
    ap.add_argument("--paliers", nargs="*", default=["nano", "super", "ultra"])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--jetons", type=int, default=6000)
    ap.add_argument("--fils", type=int, default=8)
    ap.add_argument("--budget", type=float, default=3.0, help="arrêt au-delà de ce coût ($)")
    args = ap.parse_args()

    cle_api = lire_cle(RACINE / "glassbox" / ".env", "NEBIUS_API_KEY")
    usages_par_fil: dict = {}

    def puits(u):
        usages_par_fil.setdefault(threading.get_ident(), []).append(u)

    appeler = nebius_call(api_key=cle_api, temperature=0.7, max_tokens=args.jetons,
                          on_usage=puits)
    taches = []
    for v in args.variantes:
        for e in args.etats:
            for p in args.paliers:
                fait = deja((v, e, p))
                taches += [(v, e, p, k) for k in range(fait, args.n)]
    print(f"{len(taches)} tirages a faire")
    depense = [0.0]
    arret = threading.Event()

    def travail(t):
        if arret.is_set():
            return
        d = un_tirage(appeler, usages_par_fil, *t)
        if d:
            with _verrou:
                depense[0] += d["cout_usd"]
                if depense[0] > args.budget:
                    arret.set()

    # Les paliers sont entremêlés pour que les trois avancent ensemble.
    taches.sort(key=lambda t: (t[3], t[0], t[1], t[2]))
    with ThreadPoolExecutor(args.fils) as ex:
        list(ex.map(travail, taches))
    print(f"depense de cette execution : {depense[0]:.4f} $"
          + ("  (BUDGET ATTEINT, arret)" if arret.is_set() else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
