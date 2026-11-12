"""OpenSSF Scorecard : santé et maintenance d'un dépôt open source.

API publique : https://api.securityscorecards.dev/
"""

from __future__ import annotations

import re

from . import Cache, get_json

BASE = "https://api.securityscorecards.dev/projects"


def normaliser_depot(depot: str) -> str | None:
    """Accepte https://github.com/org/repo, github.com/org/repo(.git), git+https://..."""
    if not depot:
        return None
    m = re.search(r"(github\.com|gitlab\.com)[/:]([^/\s]+)/([^/\s#?]+)", str(depot))
    if not m:
        return None
    repo = m.group(3)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{m.group(1)}/{m.group(2)}/{repo}"


def analyser(depot: str, cache: Cache) -> dict:
    cle = normaliser_depot(depot)
    if not cle:
        return {"trouve": False, "erreur": "dépôt non reconnu (GitHub/GitLab attendu)"}
    data = get_json(f"{BASE}/{cle}", cache)
    if not data:
        return {"trouve": False, "depot": cle}
    checks = {c.get("name"): c for c in data.get("checks", [])}
    maint = checks.get("Maintained", {})
    return {
        "trouve": True, "depot": cle, "score_global": data.get("score"),
        "date": data.get("date"), "maintenu_score": maint.get("score"),
        "maintenu_raison": maint.get("reason", ""),
        "url": f"https://scorecard.dev/viewer/?uri={cle}",
    }
