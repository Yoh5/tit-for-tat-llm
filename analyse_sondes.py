"""Analyse de `sondes_etats.jsonl` : P(coopérer) par état, palier et variante.

Une réponse coupée (`finish_reason = length`) ou illisible n'est pas comptée
comme un coup : elle est rapportée à part, dans la colonne `ill.`. Les
intervalles sont de Wilson à 95 %, parce qu'à 30 tirages un taux de 0 ou de
1 est courant et que l'intervalle normal y rend une largeur nulle, ce qui est
faux.

    python analyse_sondes.py
"""
from __future__ import annotations

import collections
import json
from math import sqrt
from pathlib import Path

SOURCE = Path(__file__).with_name("sondes_etats.jsonl")
PALIERS = ["nano", "super", "ultra"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - demi), min(1.0, centre + demi))


def charger() -> list[dict]:
    return [json.loads(l) for l in SOURCE.read_text(encoding="utf-8").splitlines() if l.strip()]


def valide(d: dict) -> bool:
    return d["coup"] is not None and d.get("finish_reason") != "length"


def tableau(donnees: list[dict], variante: str, etats: list[str], cible: str = "C") -> None:
    print(f"\n### variante `{variante}` — P({'coopérer' if cible == 'C' else cible}), IC 95 % de Wilson\n")
    print("| état | " + " | ".join(PALIERS) + " |")
    print("|---|" + "---|" * len(PALIERS))
    groupe = collections.defaultdict(list)
    for d in donnees:
        if d["variante"] == variante:
            groupe[(d["etat"], d["palier"])].append(d)
    for e in etats:
        cases = []
        for p in PALIERS:
            g = groupe.get((e, p), [])
            ok = [d for d in g if valide(d)]
            if not g:
                cases.append("—")
                continue
            if d_att := (ok[0].get("attendu") if ok else None):
                k = sum(1 for d in ok if d["coup"] == d["attendu"])
            else:
                k = sum(1 for d in ok if d["coup"] == cible)
            lo, hi = wilson(k, len(ok))
            ill = len(g) - len(ok)
            cases.append(f"{k}/{len(ok)} = **{k / len(ok):.2f}** [{lo:.2f}–{hi:.2f}]"
                         + (f" (ill. {ill})" if ill else ""))
        print(f"| {e} | " + " | ".join(cases) + " |")


def main() -> None:
    D = charger()
    variantes = sorted({d["variante"] for d in D}, key=lambda v: (v != "base", v))
    ordre = ["ouverture", "paix", "victime", "puni", "piege_1", "piege_3", "piege_8", "tentative"]
    for v in variantes:
        etats = [e for e in ordre if any(d["etat"] == e and d["variante"] == v for d in D)]
        if v.startswith("q_"):
            print(f"\n(question de compréhension : la case donne le taux de BONNES réponses)")
        tableau(D, v, etats)
    cout = collections.defaultdict(float)
    jet = collections.defaultdict(list)
    for d in D:
        cout[d["palier"]] += d["cout_usd"]
        if d.get("completion_tokens"):
            jet[d["palier"]].append(d["completion_tokens"])
    print("\n| palier | appels | coût total | jetons de sortie médians |\n|---|---|---|---|")
    for p in PALIERS:
        j = sorted(jet[p])
        print(f"| {p} | {sum(1 for d in D if d['palier'] == p)} | {cout[p]:.3f} $ | "
              f"{j[len(j) // 2] if j else '—'} |")
    print(f"\ntotal : {sum(cout.values()):.3f} $")


if __name__ == "__main__":
    main()
