"""La figure du README, recalculée depuis `sondes_etats.jsonl` (rien n'est recopié).

Gauche : P(coopérer) dans chaque état fabriqué, invite de base, trois paliers.
Droite : l'intervention — les mêmes états avec l'indice « tit-for-tat ».
Points = taux, barres = IC 95 % de Wilson. Une seule échelle (0 à 1) partout.

Couleurs : emplacements 1-3 de la palette catégorielle de référence, validée
(`validate_palette.js`, mode clair : PASS, avec un avertissement de contraste sur
l'aqua, et le magenta du panneau de droite, validé à part avec le bleu). D'où le relief exigé : chaque palier a aussi sa FORME de marqueur, une
légende, et les chiffres sont dans le tableau du README.

    python figure_reparation.py   ->  figures/reparation.png
"""
from __future__ import annotations

import collections
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                 # noqa: E402

from analyse_sondes import charger, valide, wilson  # noqa: E402

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "figures" / "reparation.png"

SURFACE, ENCRE, ENCRE_2, GRILLE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
PALIERS = [("nano", "#2a78d6", "o"), ("super", "#eb6834", "s"), ("ultra", "#1baf7a", "D")]

ETATS = [
    ("ouverture", "Round 1, no history"),
    ("paix", "After 10 rounds of peace"),
    ("victime", "Betrayed for no reason"),
    ("puni", "Punished after my defection"),
    ("piege_1", "Mutual defection, 1 round"),
    ("piege_3", "Mutual defection, 3 rounds"),
    ("piege_8", "Mutual defection, 8 rounds"),
    ("tentative", "My attempt to come back\nwas just exploited"),
]
ETATS_INDICE = ["puni", "piege_3", "tentative"]


def taux(donnees, variante, etat, palier):
    g = [d for d in donnees if (d["variante"], d["etat"], d["palier"]) == (variante, etat, palier)]
    ok = [d for d in g if valide(d)]
    if not ok:
        return None
    k = sum(1 for d in ok if d["coup"] == "C")
    lo, hi = wilson(k, len(ok))
    return k / len(ok), lo, hi, len(ok)


def panneau(ax, donnees, lignes, series, titre, marge_titre=34):
    """lignes : [(cle_etat, libelle)] ; series : [(variante, palier, couleur, marqueur, nom)]."""
    n = len(series)
    for i, (cle, _) in enumerate(lignes):
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color="#f3f2ee", zorder=0, lw=0)
    for j, (variante, palier, couleur, marq, nom) in enumerate(series):
        decal = (j - (n - 1) / 2) * 0.22
        for i, (cle, _) in enumerate(lignes):
            t = taux(donnees, variante, cle, palier)
            if t is None:
                continue
            p, lo, hi, _ = t
            y = i + decal
            ax.plot([lo, hi], [y, y], color=couleur, lw=2, solid_capstyle="round", zorder=2)
            ax.plot(p, y, marker=marq, ms=8, color=couleur, mec=SURFACE, mew=2, zorder=3,
                    ls="none", label=nom if i == 0 else None)
    ax.set_yticks(range(len(lignes)), [l for _, l in lignes], color=ENCRE, fontsize=10)
    ax.set_ylim(len(lignes) - 0.5, -0.5)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "0.25", "0.5", "0.75", "1"], color=ENCRE_2, fontsize=9)
    ax.set_xlabel("probability of cooperating next round", color=ENCRE_2, fontsize=9)
    ax.grid(axis="x", color=GRILLE, lw=1, zorder=1)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(titre, loc="left", color=ENCRE, fontsize=11.5, fontweight="bold", pad=marge_titre)


def main() -> None:
    D = charger()
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, (g, d) = plt.subplots(1, 2, figsize=(12.5, 5.6), facecolor=SURFACE,
                               gridspec_kw={"width_ratios": [1.35, 1], "wspace": 0.62})
    for ax in (g, d):
        ax.set_facecolor(SURFACE)

    panneau(g, D, ETATS,
            [("base", p, c, m, p) for p, c, m in PALIERS],
            "What separates the sizes: coming back, not retaliating")
    g.legend(loc="lower left", frameon=False, fontsize=9.5, labelcolor=ENCRE,
             bbox_to_anchor=(0.0, 1.02), ncol=3, handletextpad=0.3, columnspacing=1.2,
             borderaxespad=0)

    lignes = [(e, l) for e, l in ETATS if e in ETATS_INDICE]
    panneau(d, D, lignes,
            [("base", "nano", "#2a78d6", "o", "nano, base prompt"),
             ("indice", "nano", "#e87ba4", "^", 'nano, + "your opponent plays tit-for-tat"')],
            "Nano comes back when told the rule", marge_titre=56)
    d.legend(loc="lower left", frameon=False, fontsize=9.5, labelcolor=ENCRE,
             bbox_to_anchor=(0.0, 1.02), ncol=1, handletextpad=0.3, borderaxespad=0)

    fig.text(0.012, -0.04,
             "Nemotron 3 (nano 30B, super 120B, ultra 550B) against tit-for-tat, temperature 0.7. "
             "Each point: 20 to 30 draws in the same fabricated history; bars = Wilson 95% CI.",
             color=ENCRE_2, fontsize=8.5)
    SORTIE.parent.mkdir(exist_ok=True)
    fig.savefig(SORTIE, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    print(f"-> {SORTIE}")


if __name__ == "__main__":
    main()
