"""§6.1 — Le temps de réparation en fonction du palier.

La sonde avait montré, en **une partie par palier**, que ce qui sépare les
modèles n'est pas de trahir moins mais de savoir rentrer : nano s'enferme dans
41 tours de trahison mutuelle, super se fait punir et revient deux fois, ultra
ne trahit jamais. L'écart de gain — 1,40 contre 2,96 — venait entièrement de
là.

Un effet énorme sur une seule exécution est encourageant **et** suspect. Ce
module le répète.

## Ce qui est mesuré

**Le temps de réparation** : le nombre de tours entre la riposte de l'adversaire
et le retour à la coopération mutuelle. Donnant-donnant riposte au tour qui suit
une trahison ; on compte à partir de là, jusqu'au premier tour où les deux
coopèrent de nouveau.

Une partie qui ne répare jamais n'a pas un temps infini : elle est **censurée**,
et comptée comme telle. Mélanger « réparé en 2 tours » et « jamais réparé » dans
une moyenne fabriquerait un nombre qui ne décrit aucune des deux.

## Ce qui n'est pas mesuré, et pourquoi

Aucun classement « quel modèle est le plus coopératif ». Le dépôt voisin a
établi que les classements dépendent du plateau ; un palmarès de modèles
reproduirait exactement l'erreur que ce travail dénonce.

## Protocole

Trois paliers x 20 répétitions x 50 tours. L'adversaire est déterministe, donc
la variation ne vient pas d'une graine : elle vient de l'échantillonnage du
modèle à température 0,7. Répéter, ici, c'est tirer vingt fois la même
expérience, pas vingt expériences différentes.

Le budget de jetons est **par palier** (§4 du carnet) : il couvre le
raisonnement, pas la réponse, qui fait un mot. Un coup illisible ne se devine
pas — on réessaie une fois, puis la partie est abandonnée et dite abandonnée.

## Reprise

Chaque partie finie est écrite immédiatement dans `reparation.jsonl`. Relancer
reprend où l'exécution s'est arrêtée au lieu de repayer ce qui est déjà mesuré :
trois heures et deux dollars ne se redépensent pas pour une coupure réseau.

    python reparation.py                      # les trois paliers
    python reparation.py --paliers nano       # un seul
    python reparation.py --repetitions 3      # un essai court d'abord
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

#: Les deux depots voisins (Yoh5/tit-for-tat et Yoh5/glassbox) sont attendus
#: a cote de celui-ci. AI_RACINE sert a les ranger ailleurs.
RACINE = Path(os.environ.get("AI_RACINE") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(RACINE / "tit-for-tat"))
sys.path.insert(0, str(RACINE / "glassbox"))

import strategies as S                        # noqa: E402
from glassbox.nebius import nebius_call        # noqa: E402

from sonde_llm import REGLES, historique, lire_coup, lire_cle, MOT  # noqa: E402

COOP, TRAHIR = S.COOP, S.TRAHIR

#: Mesuré au carnet, §4 : le budget couvre le raisonnement. À 600 jetons, nano
#: rendait 23 réponses vides sur 50 et la sonde annonçait l'inverse du vrai.
JETONS = {"nano": 2000, "super": 2000, "ultra": 2500}

SORTIE = Path(__file__).with_name("reparation.jsonl")
_ecriture = threading.Lock()


def temps_de_reparation(mes_coups: list[int], ses_coups: list[int]) -> list[dict]:
    """Chaque riposte subie, et le nombre de tours mis à en revenir.

    Donnant-donnant riposte au tour suivant une trahison. On part de cette
    riposte et on cherche le premier tour où les deux coopèrent.
    `tours` vaut None quand la partie se termine sans retour : c'est une
    observation censurée, pas une valeur manquante.
    """
    episodes = []
    i = 0
    n = len(mes_coups)
    while i < n:
        if ses_coups[i] == TRAHIR:              # une riposte commence ici
            debut = i
            j = i
            retour = None
            while j < n:
                if mes_coups[j] == COOP and ses_coups[j] == COOP:
                    retour = j
                    break
                j += 1
            episodes.append({
                "riposte_au_tour": debut + 1,
                "tours": None if retour is None else retour - debut,
                "censure": retour is None,
            })
            if retour is None:
                break
            i = retour + 1
        else:
            i += 1
    return episodes


def premiere_trahison(mes_coups: list[int]) -> int | None:
    for i, c in enumerate(mes_coups):
        if c == TRAHIR:
            return i + 1
    return None


def une_partie(palier: str, repetition: int, tours: int, appeler, usages: list) -> dict:
    adverse = S.donnant_donnant()
    adverse.nouvelle_partie()
    import random
    alea = random.Random(1)                     # l'adversaire est déterministe

    mes_coups: list[int] = []
    ses_coups: list[int] = []
    gain = 0
    cout = 0.0
    illisibles = 0
    raisonnement_t1 = ""
    debut = time.time()

    for tour in range(tours):
        invite = f"{REGLES}\n\n{historique(mes_coups, ses_coups)}\n\nYour move:"
        usages.clear()
        try:
            texte, c = appeler(palier, invite)
        except Exception as why:                # noqa: BLE001
            return {"palier": palier, "repetition": repetition, "abandonnee": True,
                    "pourquoi": f"{type(why).__name__}: {str(why)[:120]}",
                    "tours_joues": len(mes_coups)}
        cout += c
        if tour == 0 and usages:
            raisonnement_t1 = usages[-1].get("reasoning", "")[:1500]

        lu = lire_coup(texte)
        if lu is None:
            illisibles += 1
            usages.clear()
            try:
                texte, c2 = appeler(palier, invite)
            except Exception as why:            # noqa: BLE001
                return {"palier": palier, "repetition": repetition, "abandonnee": True,
                        "pourquoi": f"{type(why).__name__}: {str(why)[:120]}",
                        "tours_joues": len(mes_coups)}
            cout += c2
            lu = lire_coup(texte)
        if lu is None:
            # Un coup non lu ne se devine pas, et une partie tronquée ne se
            # complète pas : elle est dite tronquée et exclue des moyennes.
            return {"palier": palier, "repetition": repetition, "abandonnee": True,
                    "pourquoi": "coup illisible deux fois",
                    "tours_joues": len(mes_coups)}

        coup_dd = adverse.jouer(ses_coups, mes_coups, alea)
        g, _ = S.GAINS[(lu, coup_dd)]
        gain += g
        mes_coups.append(lu)
        ses_coups.append(coup_dd)

    n = len(mes_coups)
    episodes = temps_de_reparation(mes_coups, ses_coups)
    reparations = [e["tours"] for e in episodes if not e["censure"]]
    return {
        "palier": palier,
        "repetition": repetition,
        "abandonnee": False,
        "tours": n,
        "premiere_trahison": premiere_trahison(mes_coups),
        "gain_par_tour": round(gain / n, 3),
        "taux_coop": round(sum(mes_coups) / n, 3),
        "episodes": episodes,
        "reparations": reparations,
        "censures": sum(1 for e in episodes if e["censure"]),
        "reponses_illisibles": illisibles,
        "cout_usd": round(cout, 5),
        "secondes": round(time.time() - debut, 1),
        "suite": "".join("C" if c == COOP else "D" for c in mes_coups),
        "raisonnement_tour_1": raisonnement_t1,
    }


def deja_faites(palier: str) -> set[int]:
    if not SORTIE.exists():
        return set()
    faites = set()
    for ligne in SORTIE.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        d = json.loads(ligne)
        if d.get("palier") == palier and not d.get("abandonnee"):
            faites.add(d["repetition"])
    return faites


def jouer_palier(palier: str, repetitions: int, tours: int, cle: str) -> None:
    usages: list[dict] = []
    appeler = nebius_call(api_key=cle, temperature=0.7, max_tokens=JETONS[palier],
                          on_usage=usages.append)
    faites = deja_faites(palier)
    if faites:
        print(f"[{palier}] {len(faites)} partie(s) deja mesuree(s), on reprend")
    for r in range(1, repetitions + 1):
        if r in faites:
            continue
        d = une_partie(palier, r, tours, appeler, usages)
        with _ecriture:
            with SORTIE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        if d["abandonnee"]:
            print(f"[{palier}] {r:>2}/{repetitions}  ABANDONNEE — {d['pourquoi']}")
        else:
            rep = d["reparations"]
            print(f"[{palier}] {r:>2}/{repetitions}  1re trahison "
                  f"{str(d['premiere_trahison'] or 'jamais'):>6}  "
                  f"gain {d['gain_par_tour']:.2f}  "
                  f"reparations {rep if rep else '—'}  "
                  f"censures {d['censures']}  "
                  f"{d['cout_usd']:.4f} $  {d['secondes']:.0f}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paliers", nargs="*", default=["nano", "super", "ultra"])
    ap.add_argument("--repetitions", type=int, default=20)
    ap.add_argument("--tours", type=int, default=50)
    args = ap.parse_args()

    cle = lire_cle(RACINE / "glassbox" / ".env", "NEBIUS_API_KEY")

    # Les trois paliers en parallele : l'adversaire est deterministe et chaque
    # partie est independante, donc rien ne se partage. Super est dix fois plus
    # lent que les autres ; en serie, c'est lui qui fixerait la duree totale
    # apres avoir attendu les deux autres.
    fils = [threading.Thread(target=jouer_palier,
                             args=(p, args.repetitions, args.tours, cle),
                             name=p, daemon=False)
            for p in args.paliers]
    debut = time.time()
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    print(f"\ntermine en {(time.time() - debut) / 60:.1f} min -> {SORTIE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
