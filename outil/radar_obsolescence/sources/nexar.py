"""Nexar / Octopart (optionnel) : statut de cycle de vie et nombre de distributeurs d'un composant.

Nécessite un compte développeur Nexar (https://portal.nexar.com) et, au choix :
- les variables NEXAR_CLIENT_ID et NEXAR_CLIENT_SECRET (onglet « Authorization »
  de l'application) : l'outil obtient lui-même un jeton valable 24 h ;
- ou la variable NEXAR_TOKEN : un jeton d'accès déjà généré dans le portail
  (valable 24 h) ;
- ou NEXAR_AUTH_EXTERNE=1 si un proxy ajoute lui-même l'en-tête d'autorisation.
Le plan gratuit « Evaluation » est limité à 100 pièces renvoyées : chaque
pièce renvoyée est décomptée (jusqu'à 3 par référence, pour retrouver la
référence exacte parmi les résultats approchés), d'où le cache local.
Sans ces identifiants, l'outil utilise les colonnes renseignées à la main
(statut_cycle_vie, nb_sources).

"""

from __future__ import annotations

import os

from . import Cache, ErreurSource, post_json
from .composants import normaliser_mpn, normaliser_statut  # noqa: F401 (réexportés)

URL_JETON = "https://identity.nexar.com/connect/token"
URL_API = "https://api.nexar.com/graphql"

REQUETE = """
query Recherche($mpn: String!) {
  supSearchMpn(q: $mpn, limit: 3) {
    results {
      part {
        mpn
        manufacturer { name }
        totalAvail
        sellers(authorizedOnly: true) { company { name } }
        specs { attribute { shortname } displayValue }
      }
    }
  }
}
"""

_jeton = None


def disponible() -> bool:
    return bool(os.environ.get("NEXAR_TOKEN") or os.environ.get("NEXAR_AUTH_EXTERNE")
                or (os.environ.get("NEXAR_CLIENT_ID") and os.environ.get("NEXAR_CLIENT_SECRET")))


def _en_tetes() -> dict:
    if os.environ.get("NEXAR_AUTH_EXTERNE"):
        return {}
    return {"Authorization": f"Bearer {_obtenir_jeton()}"}


def _obtenir_jeton() -> str:
    global _jeton
    if _jeton:
        return _jeton
    if os.environ.get("NEXAR_TOKEN"):
        _jeton = os.environ["NEXAR_TOKEN"].strip()
        return _jeton
    rep = post_json(URL_JETON, {
        "grant_type": "client_credentials",
        "client_id": os.environ["NEXAR_CLIENT_ID"],
        "client_secret": os.environ["NEXAR_CLIENT_SECRET"],
        "scope": "supply.domain",
    }, formulaire=True)
    _jeton = rep["access_token"]
    return _jeton


def analyser(mpn: str, cache: Cache) -> dict:
    cle = f"nexar:{mpn}"
    en_cache = cache.lire(cle)
    if en_cache is not None:
        return en_cache["data"]
    if cache.hors_ligne or not disponible():
        return {"trouve": False, "erreur": "Nexar non configuré"}
    rep = post_json(URL_API, {"query": REQUETE, "variables": {"mpn": mpn}},
                    en_tetes=_en_tetes())
    if rep.get("errors"):
        raise ErreurSource(f"Nexar : {rep['errors'][0].get('message')}")
    resultats = (rep.get("data", {}).get("supSearchMpn") or {}).get("results") or []
    # La recherche Nexar est approchée : on n'accepte que la référence exacte
    # (à la ponctuation près), sinon on signale la correspondance la plus proche.
    cible = normaliser_mpn(mpn)
    exacts = [r["part"] for r in resultats if normaliser_mpn(r["part"].get("mpn")) == cible]
    if not exacts:
        resultat = {"trouve": False,
                    "proches": [r["part"].get("mpn") for r in resultats if r["part"].get("mpn")]}
    else:
        part = exacts[0]
        specs = {s["attribute"]["shortname"]: s.get("displayValue") for s in part.get("specs", [])}
        vendeurs = {s["company"]["name"] for s in part.get("sellers", [])}
        resultat = {
            "trouve": True, "mpn": part.get("mpn"),
            "fabricant": (part.get("manufacturer") or {}).get("name"),
            "statut": normaliser_statut(specs.get("lifecyclestatus")),
            "statut_brut": specs.get("lifecyclestatus"),
            "stock_total": part.get("totalAvail"),
            "nb_distributeurs_agrees": len(vendeurs),
        }
    cache.ecrire(cle, {"data": resultat})
    return resultat
