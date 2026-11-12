"""DigiKey Product Information V4 (optionnel, gratuit) : statut de cycle de vie.

Accès gratuit : compte My DigiKey, puis sur https://developer.digikey.com créer une
organisation, une « Production App » abonnée à « Product Information V4 »
(une application « sandbox » ne renvoie pas les vraies données).
Variables : DIGIKEY_CLIENT_ID et DIGIKEY_CLIENT_SECRET ; DIGIKEY_ACCOUNT_ID si l'API
le demande (numéro de compte client, exigé par la documentation en OAuth « 2-legged »).
Quota : 120 requêtes par minute et 1 000 par jour.
DigiKey ne fait pas de prévision : il indique le statut actuel et la date de dernière commande.
"""

from __future__ import annotations

import os
import urllib.parse

from . import Cache, ErreurSource, get_json, post_json
from .composants import normaliser_mpn, normaliser_statut

URL_JETON = "https://api.digikey.com/v1/oauth2/token"
URL_MOT_CLE = "https://api.digikey.com/products/v4/search/keyword"
URL_DETAILS = "https://api.digikey.com/products/v4/search/{}/productdetails"
_jeton = None


def disponible() -> bool:
    return bool(os.environ.get("DIGIKEY_AUTH_EXTERNE")
                or (os.environ.get("DIGIKEY_CLIENT_ID") and os.environ.get("DIGIKEY_CLIENT_SECRET")))


def _obtenir_jeton() -> str:
    global _jeton
    if not _jeton:
        rep = post_json(URL_JETON, {
            "client_id": os.environ["DIGIKEY_CLIENT_ID"],
            "client_secret": os.environ["DIGIKEY_CLIENT_SECRET"],
            "grant_type": "client_credentials",
        }, formulaire=True)
        _jeton = rep["access_token"]
    return _jeton


def analyser(mpn: str, cache: Cache) -> dict:
    cle = f"digikey-v2:{mpn}"  # v2 : les résultats des versions <= 0.3.1 (sans recherche de secours) sont ignorés
    en_cache = cache.lire(cle)
    if en_cache is not None and en_cache["data"].get("trouve"):
        return en_cache["data"]  # un résultat négatif n'est pas réutilisé : on réinterroge DigiKey
    if cache.hors_ligne or not disponible():
        return {"trouve": False, "erreur": "DigiKey non configuré"}
    en_tetes = {} if os.environ.get("DIGIKEY_AUTH_EXTERNE") else {
        # DIGIKEY_AUTH_EXTERNE=1 : un proxy ajoute lui-même Authorization et X-DIGIKEY-Client-Id
        "Authorization": f"Bearer {_obtenir_jeton()}",
        "X-DIGIKEY-Client-Id": os.environ["DIGIKEY_CLIENT_ID"],
    }
    en_tetes.update({
        "X-DIGIKEY-Locale-Site": os.environ.get("DIGIKEY_SITE", "FR"),
        "X-DIGIKEY-Locale-Language": os.environ.get("DIGIKEY_LANGUE", "en"),
        "X-DIGIKEY-Locale-Currency": os.environ.get("DIGIKEY_DEVISE", "EUR"),
    })
    if os.environ.get("DIGIKEY_ACCOUNT_ID"):
        en_tetes["X-DIGIKEY-Account-Id"] = os.environ["DIGIKEY_ACCOUNT_ID"]
    # la réponse brute n'est pas conservée, seul le résultat l'est
    rep = get_json(URL_DETAILS.format(urllib.parse.quote(mpn, safe="")), None, en_tetes=en_tetes)
    produit = rep.get("Product") if isinstance(rep, dict) else None
    origine = "productdetails"
    proches = []
    if not produit or normaliser_mpn(produit.get("ManufacturerProductNumber")) != normaliser_mpn(mpn):
        # 404, réponse sans produit ou référence différente : recherche par mot-clé en secours
        if produit:
            proches.append(produit.get("ManufacturerProductNumber"))
        produit, autres = _recherche_mot_cle(mpn, en_tetes)
        proches += autres
        origine = "keyword"
    if not produit:
        resultat = {"trouve": False, "proches": [p for p in dict.fromkeys(proches) if p],
                    "motif": "absente du catalogue" + (", HTTP 404" if rep is None else "")}
    else:
        brut = _statut_brut(produit.get("ProductStatus"))
        statut = normaliser_statut(brut)
        if statut == "INCONNU" and produit.get("EndOfLife"):
            statut = "EOL"
        if statut == "INCONNU" and produit.get("Discontinued"):
            statut = "ARRET_DISTRIBUTEUR"
        resultat = {
            "trouve": True, "mpn": produit.get("ManufacturerProductNumber"),
            "fabricant": (produit.get("Manufacturer") or {}).get("Name"),
            "statut": statut, "statut_brut": brut, "origine": origine,
            "date_derniere_commande": produit.get("DateLastBuyChance"),
            "stock_total": produit.get("QuantityAvailable"),
        }
    cache.ecrire(cle, {"data": resultat})
    return resultat




def _statut_brut(valeur) -> str | None:
    """ProductStatus est un objet {"Id", "Status"} (parfois {"Id", "Text"}) ou une simple chaîne."""
    if isinstance(valeur, dict):
        return valeur.get("Status") or valeur.get("Text") or valeur.get("Value")
    return valeur or None


def _recherche_mot_cle(mpn: str, en_tetes: dict):
    """KeywordSearch : renvoie (produit à référence exacte ou None, références proches)."""
    rep = post_json(URL_MOT_CLE, {"Keywords": mpn, "Limit": 10, "Offset": 0}, en_tetes=en_tetes) or {}
    candidats = list(rep.get("ExactMatches") or []) + list(rep.get("Products") or [])
    for p in candidats:
        if normaliser_mpn(p.get("ManufacturerProductNumber")) == normaliser_mpn(mpn):
            return p, []
    return None, [p.get("ManufacturerProductNumber") for p in candidats[:3]]
