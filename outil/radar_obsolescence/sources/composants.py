"""Outils communs aux sources de composants électroniques (Mouser, DigiKey, Nexar)."""

from __future__ import annotations


def normaliser_mpn(mpn: str | None) -> str:
    """Référence sans espaces, tirets ni ponctuation, en majuscules (EEU-FR1E471 = EEUFR1E471)."""
    return "".join(c for c in (mpn or "").upper() if c.isalnum())


def normaliser_statut(brut: str | None) -> str:
    """Ramène un libellé de distributeur au référentiel du radar.

    Exemples de libellés : « Production (Last Updated: 1 month ago) » (Nexar),
    « Not For New Designs », « Last Time Buy », « Discontinued at Digi-Key » (DigiKey),
    « End of Life », « New Product » (Mouser).
    Résultat : PRODUCTION, NEW, NRND, LTB, EOL, OBSOLETE, ARRET_DISTRIBUTEUR ou INCONNU.
    """
    if not brut:
        return "INCONNU"
    t = brut.split("(")[0].strip().upper()
    if "NOT RECOMMENDED" in t or "NOT FOR NEW" in t or t.startswith("NRND"):
        return "NRND"
    if "LAST TIME" in t or t.startswith("LTB"):
        return "LTB"
    if "DISCONTINUED AT" in t:
        # arrêt chez ce distributeur seulement, pas forcément chez le fabricant
        return "ARRET_DISTRIBUTEUR"
    if t.startswith("OBSOLETE") or "DISCONTINUED" in t:
        return "OBSOLETE"
    if t.startswith("EOL") or "END OF LIFE" in t:
        return "EOL"
    if "NEW AT" in t:
        # « New at Mouser » : nouveau au catalogue du distributeur, pas un statut de cycle de vie
        return "INCONNU"
    if ("PRE-PRODUCTION" in t or "PRELIMINARY" in t or "PREVIEW" in t
            or t.startswith("NEW") or "INTRODUCTION" in t):
        return "NEW"
    if t.startswith("PRODUCTION") or t.startswith("ACTIVE"):
        return "PRODUCTION"
    return t or "INCONNU"
