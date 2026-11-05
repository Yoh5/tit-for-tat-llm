"""Expérience : un agent LLM contre Donnant-donnant SOUS BRUIT D'EXÉCUTION.

Prédiction testée (la plus falsifiable du run 3 paliers) : un modèle qui sait
réparer sans bruit devrait survivre AU bruit, là où Donnant-donnant se suicide
(section 2 du dépôt voisin). Si c'est vrai, la part de trahison mutuelle reste
basse et le temps de récupération court ; si c'est faux, le palier qui
réparait spontanément s'effondre comme les autres.

Bruit d'exécution, exactement celui du dépôt voisin : chaque coup VOULU est
inversé avec probabilité p au moment de l'exécution, et les DEUX joueurs
n'observent que les coups EXÉCUTÉS — personne ne voit son propre dérapage, donc
une stratégie qui raisonne sur ses intentions ne peut pas le réparer. Le LLM
reçoit l'historique exécuté, comme n'importe quelle stratégie.

Métriques, toutes sur les coups exécutés :
  - gain par tour (matrice du dépôt voisin, jamais recopiée)
  - part de tours en trahison mutuelle (DD) : l'état dont il faut sortir
  - temps de récupération : longueur moyenne des séries de DD consécutives
    (combien de tours avant de revenir à autre chose que (D,D))

Témoins du dépôt voisin, pour situer : sous bruit, Donnant-donnant s'effondre ;
Pavlov revient en 2 tours (exécution) / 3 (perception).

Un coup illisible n'est JAMAIS deviné : réessai une fois, puis échec explicite.

    python experience_bruit.py --palier nano --bruit 0.1 --graines 1,2 --tours 40
"""
from __future__ import annotations

import argparse
import json
import random
import re
import os
import sys
import time
from pathlib import Path

#: Les deux depots voisins (Yoh5/tit-for-tat et Yoh5/glassbox) sont attendus
#: a cote de celui-ci. AI_RACINE sert a les ranger ailleurs.
RACINE = Path(os.environ.get("AI_RACINE") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(RACINE / "tit-for-tat"))
sys.path.insert(0, str(RACINE / "glassbox"))

import strategies as S                        # noqa: E402
from glassbox.nebius import nebius_call        # noqa: E402

COOP, TRAHIR = S.COOP, S.TRAHIR
MOT = {COOP: "COOPERATE", TRAHIR: "DEFECT"}
SORTIE = Path(__file__).with_name("resultats_bruit.json")

REGLES = """You are playing the iterated prisoner's dilemma against one opponent.

Each round you both choose COOPERATE or DEFECT at the same time. Payoffs:
  both COOPERATE             -> you 3, them 3
  you DEFECT, they COOPERATE -> you 5, them 0
  you COOPERATE, they DEFECT -> you 0, them 5
  both DEFECT                -> you 1, them 1

You will play many rounds against the same opponent. Note: moves sometimes get
flipped by noise when executed, so the history may contain accidents that were
not intended. Maximise your own total score over the whole game.

Answer with exactly one word on the last line: COOPERATE or DEFECT."""


def lire_cle(chemin: Path, nom: str) -> str:
    """Lit une clé dans l'environnement, sinon dans un .env, sans l'afficher.

    L'environnement d'abord : un clone de ce dépôt n'a pas de .env voisin,
    et une clé ne se met pas dans un fichier suivi par git.
    """
    depuis_env = os.environ.get(nom)
    if depuis_env:
        return depuis_env.strip()
    if not chemin.exists():
        raise SystemExit(
            f"{nom} absente de l'environnement et {chemin} introuvable. "
            f"Posez la clé dans l'environnement : set {nom}=... (Windows) "
            f"ou export {nom}=... (POSIX)."
        )
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.startswith(f"{nom}="):
            return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{nom} introuvable dans {chemin}")


def historique(mes, ses, garder=20) -> str:
    if not mes:
        return "No rounds played yet. This is round 1."
    deb = max(0, len(mes) - garder)
    lignes = [f"  round {i + 1}: you {MOT[mes[i]]}, them {MOT[ses[i]]}"
              for i in range(deb, len(mes))]
    tete = "" if deb == 0 else f"(showing the last {garder} of {len(mes)} rounds)\n"
    return tete + "History so far:\n" + "\n".join(lignes)


def lire_coup(texte: str) -> int | None:
    t = re.findall(r"\b(COOPERATE|DEFECT)\b", texte.upper())
    return None if not t else (COOP if t[-1] == "COOPERATE" else TRAHIR)


def appeler_resilient(appeler, palier, invite, essais=4):
    """Rejoue l'appel sur panne RÉSEAU (DNS, timeout), avec recul.

    Une coupure réseau n'est pas un résultat de l'expérience — la deviner ou
    laisser la matrice entière tomber dessus serait aussi faux l'un que
    l'autre. On réessaie l'appel, pas le coup.
    """
    import urllib.error
    dernier = None
    for i in range(essais):
        try:
            return appeler(palier, invite)
        except (urllib.error.URLError, OSError) as why:  # réseau, pas logique
            dernier = why
            time.sleep(2 ** i)
    raise SystemExit(f"réseau indisponible après {essais} essais : {dernier}")


def series_dd(mes_exec, ses_exec) -> list[int]:
    """Longueurs des séries de (D,D) consécutives — le temps de récupération."""
    series, courant = [], 0
    for a, b in zip(mes_exec, ses_exec):
        if a == TRAHIR and b == TRAHIR:
            courant += 1
        elif courant:
            series.append(courant)
            courant = 0
    if courant:
        series.append(courant)
    return series


def une_partie(appeler, palier, p, graine, tours, jetons) -> dict:
    adverse = S.donnant_donnant()
    adverse.nouvelle_partie()
    alea = random.Random(graine)         # pilote le bruit, reproductible
    mes_v, ses_v = [], []                 # voulus
    mes_e, ses_e = [], []                 # exécutés (observés)
    g_llm = g_dd = 0
    cout = 0.0
    illisibles = 0

    for tour in range(tours):
        invite = f"{REGLES}\n\n{historique(mes_e, ses_e)}\n\nYour move:"
        texte, c = appeler_resilient(appeler, palier, invite)
        cout += c
        lu = lire_coup(texte)
        if lu is None:
            illisibles += 1
            texte, c2 = appeler_resilient(appeler, palier, invite)
            cout += c2
            lu = lire_coup(texte)
        if lu is None:
            raise SystemExit(
                f"illisible 2x (palier {palier}, jetons {jetons}) : {texte[:100]}")
        voulu_llm = lu
        voulu_dd = adverse.jouer(ses_e, mes_e, alea)   # DD réagit à l'exécuté

        # bruit d'exécution : chaque coup voulu peut déraper
        exec_llm = (1 - voulu_llm) if alea.random() < p else voulu_llm
        exec_dd = (1 - voulu_dd) if alea.random() < p else voulu_dd

        gl, gd = S.GAINS[(exec_llm, exec_dd)]
        g_llm += gl
        g_dd += gd
        mes_v.append(voulu_llm); ses_v.append(voulu_dd)
        mes_e.append(exec_llm);  ses_e.append(exec_dd)

    n = tours
    dd = series_dd(mes_e, ses_e)
    return {
        "palier": palier, "bruit": p, "graine": graine, "tours": n,
        "gain_llm": round(g_llm / n, 3), "gain_dd": round(g_dd / n, 3),
        "part_trahison_mutuelle": round(sum(dd) / n, 3),
        "nb_series_dd": len(dd),
        "recuperation_moy": round(sum(dd) / len(dd), 2) if dd else None,
        "recuperation_max": max(dd) if dd else 0,
        "illisibles": illisibles,
        "cout_usd": round(cout, 5),
        "seq_llm": "".join("C" if m == COOP else "D" for m in mes_e),
        "seq_dd": "".join("C" if m == COOP else "D" for m in ses_e),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--palier", default="nano")
    ap.add_argument("--bruit", type=float, default=0.1)
    ap.add_argument("--graines", default="1,2")
    ap.add_argument("--tours", type=int, default=40)
    ap.add_argument("--jetons", type=int, default=2500)
    args = ap.parse_args()

    cle = lire_cle(RACINE / "glassbox" / ".env", "NEBIUS_API_KEY")
    appeler = nebius_call(api_key=cle, temperature=0.7, max_tokens=args.jetons)
    graines = [int(g) for g in args.graines.split(",") if g.strip()]

    acquis = []
    if SORTIE.exists():
        acquis = json.loads(SORTIE.read_text(encoding="utf-8"))

    for g in graines:
        t0 = time.time()
        try:
            r = une_partie(appeler, args.palier, args.bruit, g, args.tours, args.jetons)
        except SystemExit as why:
            # une partie illisible ne tue pas la matrice : on l'inscrit et on
            # passe. La cellule manquante est un trou honnête, pas un faux zéro.
            r = {"palier": args.palier, "bruit": args.bruit, "graine": g,
                 "erreur": str(why)[:160]}
            acquis.append(r)
            SORTIE.write_text(json.dumps(acquis, indent=2, ensure_ascii=False),
                              encoding="utf-8")
            print(f"{args.palier:<6} bruit {args.bruit} graine {g} : ÉCHEC — {r['erreur']}")
            continue
        r["secondes"] = round(time.time() - t0, 1)
        acquis.append(r)
        SORTIE.write_text(json.dumps(acquis, indent=2, ensure_ascii=False),
                          encoding="utf-8")
        print(f"{args.palier:<6} bruit {args.bruit} graine {g} : "
              f"gain {r['gain_llm']} | DD {r['part_trahison_mutuelle']*100:.0f}% | "
              f"récup {r['recuperation_moy']} | {r['secondes']:.0f}s | "
              f"{r['cout_usd']} $")


if __name__ == "__main__":
    main()
