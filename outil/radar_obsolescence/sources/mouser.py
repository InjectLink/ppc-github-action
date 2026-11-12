"""Mouser Search API (optionnel, gratuit) : statut de cycle de vie et remplacement suggéré.

Clé gratuite et immédiate : https://www.mouser.com/en/api-search/ (compte My Mouser
puis formulaire « Search API »). Variable d'environnement : MOUSER_API_KEY.
Quota annoncé : 30 appels par minute et 1 000 par jour ; une référence = un appel.
La clé passe dans l'URL : elle est masquée dans les messages d'erreur.
"""

from __future__ import annotations

import os
import time

from . import Cache, ErreurSource, post_json
from .composants import normaliser_mpn, normaliser_statut

URL_API = "https://api.mouser.com/api/v1/search/partnumber"
_dernier_appel = 0.0


def disponible() -> bool:
    return bool(os.environ.get("MOUSER_API_KEY"))


def analyser(mpn: str, cache: Cache) -> dict:
    global _dernier_appel
    cle = f"mouser:{mpn}"
    en_cache = cache.lire(cle)
    if en_cache is not None:
        return en_cache["data"]
    if cache.hors_ligne or not disponible():
        return {"trouve": False, "erreur": "Mouser non configuré"}
    api_key = os.environ["MOUSER_API_KEY"].strip()
    attente = 2.1 - (time.time() - _dernier_appel)  # 30 appels par minute au plus
    if attente > 0:
        time.sleep(attente)
    _dernier_appel = time.time()
    try:
        rep = post_json(f"{URL_API}?apiKey={api_key}",
                        {"SearchByPartRequest": {"mouserPartNumber": mpn, "partSearchOptions": "Exact"}})
    except ErreurSource as e:
        raise ErreurSource(str(e).replace(api_key, "***")) from None
    erreurs = rep.get("Errors") or []
    if erreurs:
        raise ErreurSource(f"Mouser : {erreurs[0].get('Message')}")
    parts = (rep.get("SearchResults") or {}).get("Parts") or []
    cible = normaliser_mpn(mpn)
    exacts = [p for p in parts if normaliser_mpn(p.get("ManufacturerPartNumber")) == cible]
    if not exacts:
        resultat = {"trouve": False,
                    "proches": [p.get("ManufacturerPartNumber") for p in parts[:3] if p.get("ManufacturerPartNumber")]}
    else:
        p = exacts[0]
        brut = p.get("LifecycleStatus")
        statut = normaliser_statut(brut)
        if statut == "INCONNU" and str(p.get("IsDiscontinued", "")).lower() == "true":
            statut, brut = "OBSOLETE", brut or "IsDiscontinued"
        resultat = {
            "trouve": True, "mpn": p.get("ManufacturerPartNumber"),
            "fabricant": p.get("Manufacturer"),
            "statut": statut, "statut_brut": brut,
            "remplacement": p.get("SuggestedReplacement") or None,
            "stock_total": p.get("AvailabilityInStock"),
        }
    cache.ecrire(cle, {"data": resultat})
    return resultat
