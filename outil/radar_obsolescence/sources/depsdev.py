"""deps.dev (Open Source Insights, Google) : dépréciation, vulnérabilités, dépôt source, Scorecard.

API publique : https://docs.deps.dev/api/v3/
Écosystèmes : npm, pypi, go, maven, cargo, nuget.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

from . import Cache, get_json

BASE = "https://api.deps.dev/v3"
SYSTEMES = {"npm": "npm", "pypi": "pypi", "python": "pypi", "pip": "pypi", "go": "go",
            "maven": "maven", "cargo": "cargo", "rust": "cargo", "nuget": "nuget"}


def _q(texte: str) -> str:
    return urllib.parse.quote(texte, safe="")


def analyser(ecosysteme: str, paquet: str, version: str | None, cache: Cache) -> dict:
    systeme = SYSTEMES.get(str(ecosysteme).strip().lower())
    if not systeme:
        return {"trouve": False, "erreur": f"écosystème non géré : {ecosysteme}"}
    info = get_json(f"{BASE}/systems/{systeme}/packages/{_q(paquet)}", cache)
    url = f"https://deps.dev/{systeme}/{_q(paquet)}"
    if not info:
        return {"trouve": False, "url": url}
    versions = info.get("versions", [])
    defaut = next((v for v in versions if v.get("isDefault")), versions[-1] if versions else None)
    cible_nom = version or (defaut or {}).get("versionKey", {}).get("version")
    resultat = {"trouve": True, "url": url, "version": cible_nom,
                "derniere_version": (defaut or {}).get("versionKey", {}).get("version")}
    # date de la dernière publication
    dates = [v.get("publishedAt") for v in versions if v.get("publishedAt")]
    if dates:
        derniere = max(dates)
        resultat["derniere_publication"] = derniere[:10]
        age = datetime.now(timezone.utc) - datetime.fromisoformat(derniere.replace("Z", "+00:00"))
        resultat["jours_depuis_publication"] = age.days
    detail = get_json(f"{BASE}/systems/{systeme}/packages/{_q(paquet)}/versions/{_q(cible_nom)}", cache) \
        if cible_nom else None
    if detail:
        resultat["deprecie"] = bool(detail.get("isDeprecated"))
        resultat["raison_depreciation"] = detail.get("deprecatedReason", "")
        resultat["nb_avis_securite"] = len(detail.get("advisoryKeys", []))
        resultat["avis_securite"] = [a.get("id") for a in detail.get("advisoryKeys", [])][:5]
        projets = [p.get("projectKey", {}).get("id") for p in detail.get("relatedProjects", [])]
        resultat["depot"] = next((p for p in projets if p), None)
    return resultat
