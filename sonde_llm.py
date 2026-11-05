"""SONDE JETABLE — un agent LLM contre Donnant-donnant, longueur fixe.

But : savoir ce que coûte un duel et si l'agent tient la coopération. Rien
d'autre. Pas de tournoi, pas de bruit, pas de prétention au déterminisme.

Choix assumés pour borner la dépense :
  - longueur FIXE (pas le tirage aléatoire de `tournoi.longueur`, dont
    l'espérance de 200 tours peut sortir bien plus et faire exploser la note) ;
  - palier `nano`, le moins cher des trois ;
  - les gains viennent de `strategies.GAINS`, pas d'une copie — si la matrice
    du dépôt change, la sonde change avec elle.

Nemotron réfléchit avant de répondre : avec un `max_tokens` serré, la
réflexion consomme tout et l'API rend `content: null`. D'où les 600 jetons.

    python sonde_llm.py --tours 50
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

#: Les deux depots voisins (Yoh5/tit-for-tat et Yoh5/glassbox) sont attendus
#: a cote de celui-ci. AI_RACINE sert a les ranger ailleurs.
RACINE = Path(os.environ.get("AI_RACINE") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(RACINE / "tit-for-tat"))
sys.path.insert(0, str(RACINE / "glassbox"))

import strategies as S                      # noqa: E402
from glassbox.nebius import nebius_call      # noqa: E402

COOP, TRAHIR = S.COOP, S.TRAHIR
MOT = {COOP: "COOPERATE", TRAHIR: "DEFECT"}


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


REGLES = """You are playing the iterated prisoner's dilemma against one opponent.

Each round you both choose COOPERATE or DEFECT at the same time. Payoffs:
  both COOPERATE     -> you 3, them 3
  you DEFECT, they COOPERATE -> you 5, them 0
  you COOPERATE, they DEFECT -> you 0, them 5
  both DEFECT        -> you 1, them 1

You will play many rounds against the same opponent. Maximise your own total
score over the whole game.

Answer with exactly one word on the last line: COOPERATE or DEFECT."""


def historique(mes_coups, ses_coups, garder=20) -> str:
    if not mes_coups:
        return "No rounds played yet. This is round 1."
    lignes = []
    debut = max(0, len(mes_coups) - garder)
    for i in range(debut, len(mes_coups)):
        lignes.append(f"  round {i + 1}: you {MOT[mes_coups[i]]}, "
                      f"them {MOT[ses_coups[i]]}")
    tete = "" if debut == 0 else f"(showing the last {garder} of {len(mes_coups)} rounds)\n"
    return f"{tete}History so far:\n" + "\n".join(lignes)


def lire_coup(texte: str) -> int | None:
    """Le DERNIER mot de décision du texte, parce que le modèle raisonne avant."""
    trouves = re.findall(r"\b(COOPERATE|DEFECT)\b", texte.upper())
    if not trouves:
        return None
    return COOP if trouves[-1] == "COOPERATE" else TRAHIR


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tours", type=int, default=50)
    ap.add_argument("--palier", default="nano")
    ap.add_argument("--jetons", type=int, default=600)
    args = ap.parse_args()

    cle = lire_cle(RACINE / "glassbox" / ".env", "NEBIUS_API_KEY")
    appeler = nebius_call(api_key=cle, temperature=0.7, max_tokens=args.jetons)

    adverse = S.donnant_donnant()
    adverse.nouvelle_partie()
    alea = random.Random(1)

    mes_coups: list[int] = []   # ceux du LLM
    ses_coups: list[int] = []   # ceux de Donnant-donnant
    gain_llm = gain_dd = 0
    cout_total = 0.0
    illisibles = 0
    journal = []

    debut = time.time()
    for tour in range(args.tours):
        invite = f"{REGLES}\n\n{historique(mes_coups, ses_coups)}\n\nYour move:"
        t0 = time.time()
        try:
            texte, cout = appeler(args.palier, invite)
        except Exception as why:                      # noqa: BLE001 - sonde
            print(f"  tour {tour + 1}: appel échoué ({why}); on arrête ici.")
            break
        latence = time.time() - t0
        cout_total += cout

        lu = lire_coup(texte)
        if lu is None:
            # Un coup non lu ne se devine PAS. La première version repliait sur
            # COOPERATE et comptait le repli : à 600 jetons, 23 tours sur 50
            # partaient ainsi, et la sonde annonçait 96 % de coopération au lieu
            # de 16 %. Le défaut penchait du côté flatteur, ce qui est pire
            # qu'un défaut neutre. On réessaie une fois, puis on s'arrête.
            illisibles += 1
            texte, cout2 = appeler(args.palier, invite)
            cout_total += cout2
            lu = lire_coup(texte)
        if lu is None:
            raise SystemExit(
                f"tour {tour + 1} : coup illisible deux fois de suite sur le palier "
                f"'{args.palier}' avec max_tokens={args.jetons}.\n"
                f"Réponse : {texte[:120]}\n"
                f"Augmente --jetons : le budget doit couvrir le RAISONNEMENT, "
                f"pas la réponse, qui fait un mot."
            )
        illisible = False
        coup = lu
        # Donnant-donnant joue contre l'historique qu'il observe.
        coup_dd = adverse.jouer(ses_coups, mes_coups, alea)

        g_llm, g_dd = S.GAINS[(coup, coup_dd)]
        gain_llm += g_llm
        gain_dd += g_dd
        mes_coups.append(coup)
        ses_coups.append(coup_dd)

        journal.append({
            "tour": tour + 1, "llm": MOT[coup], "dd": MOT[coup_dd],
            "gain_llm": g_llm, "cout_usd": round(cout, 6),
            "latence_s": round(latence, 2),
            "illisible": illisible,
            "reponse": texte[-200:],
        })
        print(f"  {tour + 1:>3}  LLM {MOT[coup]:<9}  DD {MOT[coup_dd]:<9} "
              f"({g_llm}/{g_dd})  {latence:.1f}s  {cout * 1000:.3f} m$")

    n = len(mes_coups)
    if not n:
        raise SystemExit("aucun tour joué")
    coop_llm = sum(mes_coups) / n
    mutuelle = sum(1 for a, b in zip(mes_coups, ses_coups) if a == b == COOP) / n

    resume = {
        "palier": args.palier, "max_tokens": args.jetons, "tours": n,
        "gain_llm_par_tour": round(gain_llm / n, 3),
        "gain_dd_par_tour": round(gain_dd / n, 3),
        "taux_coop_llm": round(coop_llm, 3),
        "coop_mutuelle": round(mutuelle, 3),
        "reponses_illisibles": illisibles,
        "cout_total_usd": round(cout_total, 5),
        "cout_par_tour_usd": round(cout_total / n, 6),
        "secondes": round(time.time() - debut, 1),
    }
    print("\n" + json.dumps(resume, indent=2))
    sortie = Path(__file__).with_name("sonde_llm_resultat.json")
    sortie.write_text(json.dumps({"resume": resume, "journal": journal},
                                 indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"journal complet -> {sortie}")


if __name__ == "__main__":
    main()
