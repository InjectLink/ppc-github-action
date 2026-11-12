"""Open Repair Alliance (ORDS) : pannes fréquentes observées dans les Repair Cafés.

Jeu de données téléchargeable (CC BY-SA 4.0) : https://openrepair.org/open-data/downloads/
Téléchargez le CSV depuis la page de téléchargement, puis passez son chemin
avec l'option --ords.

L'analyse filtre la catégorie de produit (champ product_category) puis compte :
- les statuts de réparation (repair_status),
- les obstacles à la réparation (repair_barrier...),
- les sous-ensembles cités dans la description de la panne (problem), par mots-clés multilingues.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

# sous-ensemble -> mots-clés (fr, en, nl, de, es...)
SOUS_ENSEMBLES = {
    "batterie / accumulateur": ["batter", "accu", "akku", "pile"],
    "alimentation / chargeur": ["power supply", "alimentation", "charger", "chargeur", "adapter",
                                "voeding", "netzteil", "psu"],
    "câble / cordon": ["cable", "câble", "cord", "cordon", "snoer", "kabel", "wire", "fil "],
    "interrupteur / bouton": ["switch", "interrupteur", "button", "bouton", "schakelaar", "knop",
                              "schalter", "taste"],
    "moteur": ["motor", "moteur"],
    "écran / affichage": ["screen", "écran", "ecran", "display", "lcd", "scherm"],
    "connecteur / prise": ["connector", "connecteur", "socket", "prise", "plug", "jack", "usb", "port"],
    "fusible": ["fuse", "fusible", "zekering", "sicherung"],
    "condensateur": ["capacitor", "condensateur", "condensator", "kondensator", "cap "],
    "carte électronique": ["pcb", "board", "carte", "printplaat", "platine", "electronic"],
    "résistance chauffante / thermostat": ["heating", "chauff", "element", "thermostat", "verwarm"],
    "courroie / engrenage": ["belt", "courroie", "gear", "engrenage", "riem", "tandwiel"],
    "roulement / axe": ["bearing", "roulement", "lager", "axle", "shaft", "axe"],
    "charbons (moteur)": ["brush", "charbon", "koolborstel", "kohle"],
    "charnière / fixation / boîtier": ["hinge", "charnière", "charniere", "clip", "housing", "boîtier",
                                       "case", "scharnier", "gehäuse"],
    "logiciel / firmware": ["software", "firmware", "logiciel", "update", "mise à jour"],
    "eau / oxydation": ["water", "liquid", "corrosion", "oxyd", "rust", "rouille"],
}

COLONNES_CANDIDATES = {
    "categorie": ["product_category", "category"],
    "statut": ["repair_status"],
    "obstacle": ["repair_barrier_if_end_of_life", "repair_barrier"],
    "probleme": ["problem", "fault"],
    "age": ["product_age"],
}


def _sans_accent(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _trouver(entetes: list[str], cles: list[str]) -> str | None:
    bas = {h.lower(): h for h in entetes}
    for c in cles:
        if c in bas:
            return bas[c]
    return None


def analyser(chemin: str | Path, categorie: str, limite_lignes: int | None = None) -> dict:
    chemin = Path(chemin)
    motif = re.compile(re.escape(_sans_accent(categorie)))
    statuts, obstacles, sous_ens, ages = Counter(), Counter(), Counter(), []
    total = 0
    with chemin.open(encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f)
        entetes = lecteur.fieldnames or []
        col = {k: _trouver(entetes, v) for k, v in COLONNES_CANDIDATES.items()}
        if not col["categorie"]:
            return {"trouve": False, "erreur": "colonne product_category introuvable"}
        cles_norm = {k: [_sans_accent(m) for m in mots] for k, mots in SOUS_ENSEMBLES.items()}
        for i, ligne in enumerate(lecteur):
            if limite_lignes and i >= limite_lignes:
                break
            if not motif.search(_sans_accent(ligne.get(col["categorie"]) or "")):
                continue
            total += 1
            if col["statut"]:
                statuts[(ligne.get(col["statut"]) or "inconnu").strip() or "inconnu"] += 1
            if col["obstacle"] and (ligne.get(col["obstacle"]) or "").strip():
                obstacles[ligne[col["obstacle"]].strip()] += 1
            if col["probleme"]:
                texte = " " + _sans_accent(ligne.get(col["probleme"]) or "") + " "
                for nom, mots in cles_norm.items():
                    if any(m in texte for m in mots):
                        sous_ens[nom] += 1
            if col["age"]:
                try:
                    ages.append(float(ligne.get(col["age"]) or ""))
                except ValueError:
                    pass
    if not total:
        return {"trouve": False, "categorie": categorie}
    ages.sort()
    return {
        "trouve": True, "categorie": categorie, "nb_reparations": total,
        "statuts": statuts.most_common(),
        "obstacles": obstacles.most_common(5),
        "sous_ensembles": [(k, v, round(100 * v / total, 1)) for k, v in sous_ens.most_common(8)],
        "age_median_ans": ages[len(ages) // 2] if ages else None,
    }


def categories(chemin: str | Path, n: int = 40) -> list[tuple[str, int]]:
    """Liste des catégories présentes (aide au choix de categorie_ords)."""
    compte = Counter()
    with Path(chemin).open(encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f)
        col = _trouver(lecteur.fieldnames or [], COLONNES_CANDIDATES["categorie"])
        for ligne in lecteur:
            compte[ligne.get(col) or ""] += 1
    return compte.most_common(n)
