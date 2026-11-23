"""Tableau P(coopérer) par modèle et par état, toutes familles, avec IC de Wilson 95 %.

Lit sondes_etats.jsonl (Nemotron, variante base : la référence publiée),
sondes_familles.jsonl (Nebius) et sondes_openrouter.jsonl (OpenRouter).
Les illisibles ne sont jamais comptés comme un coup : ils sont rapportés à part.

    python analyse_familles.py
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent
FICHIERS = ["sondes_etats.jsonl", "sondes_familles.jsonl", "sondes_openrouter.jsonl"]
ETATS = ["ouverture", "paix", "victime", "puni", "piege_3", "tentative"]
ORDRE = ["nano", "super", "ultra", "qwen-s", "qwen-l", "ds-s", "ds-l", "mm-s", "mm-l",
         "gemma", "gptoss", "llama-s", "llama-l", "gemini-s", "gemini-m", "gemini-l",
         "gpt-s", "gpt-m", "gpt-l", "claude-s", "claude-m", "claude-l"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (max(0.0, m - c), min(1.0, m + c))


def charger():
    cases = defaultdict(lambda: {"C": 0, "D": 0, "?": 0, "cout": 0.0, "tok": []})
    for nom in FICHIERS:
        f = ICI / nom
        if not f.exists():
            continue
        for l in f.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            d = json.loads(l)
            if d.get("variante") != "base":
                continue
            c = cases[(d["palier"], d["etat"])]
            c[d["coup"] or "?"] += 1
            c["cout"] += d.get("cout_usd") or 0
            if d.get("completion_tokens") is not None:
                c["tok"].append(d["completion_tokens"])
    return cases


def main() -> None:
    cases = charger()
    modeles = [m for m in ORDRE if any((m, e) in cases for e in ETATS)]
    etats = [e for e in ETATS if any((m, e) in cases for m in modeles)]
    print("P(coopérer) [IC 95 %] (n lus, illisibles)")
    print(f"{'modèle':9}" + "".join(f"{e:>24}" for e in etats))
    for m in modeles:
        ligne = f"{m:9}"
        for e in etats:
            c = cases.get((m, e))
            if not c:
                ligne += f"{'—':>24}"
                continue
            n = c["C"] + c["D"]
            lo, hi = wilson(c["C"], n)
            ligne += f"{c['C'] / n if n else float('nan'):>6.2f} [{lo:.2f}-{hi:.2f}] ({n},{c['?']})".rjust(24)
        print(ligne)
    total = sum(c["cout"] for (m, e), c in cases.items() if m not in ("nano", "super", "ultra"))
    print(f"\ncoût des nouvelles familles : {total:.3f} $")


if __name__ == "__main__":
    main()
