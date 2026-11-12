"""endoflife.date : dates de fin de vie des OS, langages, frameworks, bases de données...

API publique : https://endoflife.date/docs/api/  (données sous licence MIT)
"""

from __future__ import annotations

from datetime import date

from . import Cache, get_json
from ..nomenclature import date_iso

BASE = "https://endoflife.date/api"


def cycles(produit: str, cache: Cache) -> list[dict] | None:
    return get_json(f"{BASE}/{produit.strip().lower()}.json", cache)


def _date_ou_bool(valeur) -> tuple[date | None, bool | None]:
    """Le champ eol vaut une date, true (déjà en fin de vie) ou false (pas de date)."""
    if isinstance(valeur, bool):
        return None, valeur
    return date_iso(valeur), None


def trouver_cycle(liste: list[dict], version: str) -> dict | None:
    if not version:
        return liste[0] if liste else None
    v = str(version).strip()
    # correspondance exacte, puis par préfixe le plus long (ex. 3.11.4 -> 3.11)
    exact = [c for c in liste if str(c.get("cycle")) == v]
    if exact:
        return exact[0]
    candidats = [c for c in liste if v.startswith(str(c.get("cycle")) + ".")]
    if candidats:
        return max(candidats, key=lambda c: len(str(c.get("cycle"))))
    return None


def analyser(produit: str, version: str, cache: Cache) -> dict:
    """Retourne {trouve, cycle, eol (date|None), deja_eol (bool), support, latest, url}."""
    liste = cycles(produit, cache)
    url = f"https://endoflife.date/{produit.strip().lower()}"
    if not liste:
        return {"trouve": False, "url": url}
    c = trouver_cycle(liste, version)
    if c is None:
        return {"trouve": False, "url": url, "cycles_connus": [x.get("cycle") for x in liste[:8]]}
    eol, eol_bool = _date_ou_bool(c.get("eol"))
    deja = bool(eol_bool) or (eol is not None and eol <= date.today())
    support, _ = _date_ou_bool(c.get("support"))
    return {
        "trouve": True, "cycle": c.get("cycle"), "eol": eol, "deja_eol": deja,
        "pas_de_date_eol": eol is None and not eol_bool,
        "support": support, "lts": c.get("lts"), "latest": c.get("latest"),
        "dernier_cycle": liste[0].get("cycle"), "url": url,
    }
