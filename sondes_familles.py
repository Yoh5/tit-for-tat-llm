"""Sondes d'état sur D'AUTRES FAMILLES de modèles (§8.7 : « une seule famille »).

La limite principale du résultat publié est qu'il porte sur trois tailles de
Nemotron 3. Ce module rejoue EXACTEMENT les mêmes historiques fabriqués et la
même invite (`sondes_etats.invite`, `sondes_etats.lire`) sur d'autres familles,
par paires petite/grande quand le fournisseur en propose une.

Question testée : l'écart de réparation (P(coopérer) une fois puni) est-il un
effet de TAILLE en général, ou une particularité de Nemotron ?

Fournisseurs compatibles OpenAI : Nebius (clé de ../glassbox/.env) et, si la
variable OPENROUTER_API_KEY est définie, OpenRouter. Le prix vient de l'API
`/models` du fournisseur au moment de l'exécution, jamais d'une table recopiée.

Règles héritées de sondes_etats : un coup illisible est enregistré illisible et
n'est PAS retiré ; seul une erreur réseau est réessayée.

    python sondes_familles.py --modeles qwen-s qwen-l --etats puni --n 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from sondes_etats import ETATS, invite, lire, RACINE   # noqa: E402
from sonde_llm import lire_cle                         # noqa: E402

SORTIE = ICI / "sondes_familles.jsonl"
_verrou = threading.Lock()

FOURNISSEURS = {
    "nebius": "https://api.tokenfactory.nebius.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

#: alias -> (fournisseur, identifiant). Paires petite (-s) / grande (-l).
MODELES = {
    "qwen-s": ("nebius", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
    "qwen-l": ("nebius", "Qwen/Qwen3-235B-A22B-Instruct-2507"),
    "ds-s": ("nebius", "deepseek-ai/DeepSeek-V4.1-Flash-1017"),
    "ds-l": ("nebius", "deepseek-ai/DeepSeek-V4-Pro-0813"),
    "mm-s": ("nebius", "MiniMaxAI/MiniMax-M3.1-Flash"),
    "mm-l": ("nebius", "MiniMaxAI/MiniMax-M3"),
    "gemma": ("nebius", "google/gemma-3-27b-it"),
    "gptoss": ("nebius", "openai/gpt-oss-120b"),
    # OpenRouter : modèles fermés, échelles d'UNE même génération.
    "gpt-s": ("openrouter", "openai/gpt-5-nano"),
    "gpt-m": ("openrouter", "openai/gpt-5-mini"),
    "gpt-l": ("openrouter", "openai/gpt-5"),
    "claude-s": ("openrouter", "anthropic/claude-haiku-4.5"),
    "claude-m": ("openrouter", "anthropic/claude-sonnet-4.5"),
    "claude-l": ("openrouter", "anthropic/claude-opus-4.5"),
    "gemini-s": ("openrouter", "google/gemini-2.5-flash-lite"),
    "gemini-m": ("openrouter", "google/gemini-2.5-flash"),
    "gemini-l": ("openrouter", "google/gemini-2.5-pro"),
    "llama-s": ("openrouter", "meta-llama/llama-4-scout"),
    "llama-l": ("openrouter", "meta-llama/llama-4-maverick"),
}


def cle(fournisseur: str) -> str:
    if fournisseur == "nebius":
        return lire_cle(RACINE / "glassbox" / ".env", "NEBIUS_API_KEY")
    # Variable d'environnement d'abord ; sinon la clé déjà rangée dans le
    # projet voisin agent-sql-oracle (accord donné le 23/11/2026). Jamais affichée.
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        try:
            k = lire_cle(RACINE / "agent-sql-oracle" / ".env", "OPENROUTER_API_KEY")
        except Exception:                      # noqa: BLE001
            k = None
    if not k:
        raise SystemExit("OPENROUTER_API_KEY absente de l'environnement")
    return k


def _get(url: str, k: str):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {k}"})
    with urllib.request.urlopen(req, timeout=60) as r:   # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def prix(fournisseur: str, k: str) -> dict[str, tuple[float, float]]:
    """$ par jeton (entrée, sortie), lus sur l'API du fournisseur."""
    suffixe = "/models?verbose=true" if fournisseur == "nebius" else "/models"
    out = {}
    for m in _get(FOURNISSEURS[fournisseur] + suffixe, k)["data"]:
        p = m.get("pricing") or {}
        try:
            out[m["id"]] = (float(p["prompt"]), float(p["completion"]))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def appeler(fournisseur, k, modele, texte, jetons):
    corps = {"model": modele, "messages": [{"role": "user", "content": texte}],
             "temperature": 0.7, "max_tokens": jetons}
    req = urllib.request.Request(
        FOURNISSEURS[fournisseur] + "/chat/completions",
        data=json.dumps(corps).encode("utf-8"),
        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:   # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def deja(cle_: tuple) -> int:
    if not SORTIE.exists():
        return 0
    return sum(1 for l in SORTIE.read_text(encoding="utf-8").splitlines()
               if l.strip() and tuple(json.loads(l)[c] for c in ("variante", "etat", "palier")) == cle_)


def un_tirage(ctx, variante, etat, alias, k_):
    fournisseur, modele = MODELES[alias]
    mes, ses = ETATS[etat]
    texte = invite(variante, mes, ses)
    t0 = time.time()
    for essai in range(3):                       # réseau seulement
        try:
            corps = appeler(fournisseur, ctx["cles"][fournisseur], modele, texte, ctx["jetons"])
            break
        except Exception as why:                 # noqa: BLE001
            if essai == 2:
                print(f"  réseau : {alias} {etat} : {why}")
                return None
            time.sleep(5 * (essai + 1))
    choix = corps["choices"][0]
    msg = choix.get("message") or {}
    contenu = (msg.get("content") or "").strip()
    raisonnement = msg.get("reasoning") or msg.get("reasoning_content") or ""
    u = corps.get("usage") or {}
    pe, ps = ctx["prix"].get(modele, (0.0, 0.0))
    cout = u.get("prompt_tokens", 0) * pe + u.get("completion_tokens", 0) * ps
    d = {
        "variante": variante, "etat": etat, "palier": alias, "modele": modele,
        "fournisseur": fournisseur, "tirage": k_,
        "coup": lire(variante, contenu) if contenu else None,
        "completion_tokens": u.get("completion_tokens"), "prompt_tokens": u.get("prompt_tokens"),
        "finish_reason": choix.get("finish_reason"),
        "cout_usd": round(cout, 7), "prix_connu": modele in ctx["prix"],
        "secondes": round(time.time() - t0, 2),
        "reponse": contenu[-300:], "raisonnement": raisonnement[:2500],
    }
    with _verrou:
        with SORTIE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modeles", nargs="*", default=list(MODELES))
    ap.add_argument("--etats", nargs="*", default=["ouverture", "paix", "victime", "puni", "piege_3", "tentative"])
    ap.add_argument("--variantes", nargs="*", default=["base"])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--jetons", type=int, default=6000)
    ap.add_argument("--fils", type=int, default=8)
    ap.add_argument("--budget", type=float, default=1.0)
    ap.add_argument("--sortie", default=None, help="fichier jsonl (défaut : sondes_familles.jsonl)")
    a = ap.parse_args()
    if a.sortie:
        global SORTIE
        SORTIE = ICI / a.sortie

    fournisseurs = {MODELES[m][0] for m in a.modeles}
    ctx = {"jetons": a.jetons, "cles": {}, "prix": {}}
    for f in fournisseurs:
        ctx["cles"][f] = cle(f)
        ctx["prix"].update(prix(f, ctx["cles"][f]))
    for m in a.modeles:
        if MODELES[m][1] not in ctx["prix"]:
            raise SystemExit(f"prix inconnu pour {MODELES[m][1]} : le budget ne pourrait pas s'arrêter")

    taches = [(v, e, m, k) for v in a.variantes for e in a.etats for m in a.modeles
              for k in range(deja((v, e, m)), a.n)]
    taches.sort(key=lambda t: (t[3], t[0], t[1], t[2]))
    print(f"{len(taches)} tirages a faire")
    depense, arret = [0.0], threading.Event()

    def travail(t):
        if arret.is_set():
            return
        d = un_tirage(ctx, *t)
        if d:
            with _verrou:
                depense[0] += d["cout_usd"]
                if depense[0] > a.budget:
                    arret.set()

    with ThreadPoolExecutor(a.fils) as ex:
        list(ex.map(travail, taches))
    print(f"depense : {depense[0]:.4f} $" + ("  (BUDGET ATTEINT)" if arret.is_set() else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
