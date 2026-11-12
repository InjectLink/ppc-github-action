"""Génération des sorties : rapport Markdown, CSV des constats, classeur XLSX."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from . import __version__
from .analyse import Resultat, etat_sources_composants, synthese
from .referentiel import DOMAINES, FAMILLES

ENTETES = ["ligne", "id", "designation", "domaine", "famille", "code", "constat",
           "exposition_0_3", "gravite_1_3", "criticite_0_9", "niveau", "detail",
           "recommandation", "preuve", "automatique"]


def _e(texte) -> str:
    """Échappe les barres verticales dans une cellule de tableau Markdown."""
    return str(texte).replace("|", "\\|")


def _md(texte: str) -> str:
    return texte


def _rangs(res: Resultat):
    return sorted(res.constats, key=lambda c: (-c.criticite, c.ligne.numero, c.code))


def _ligne_csv(c):
    return [c.ligne.numero, c.ligne.get("id"), c.ligne.get("designation"), c.ligne.domaine,
            c.famille, c.code, c.intitule, c.exposition, c.gravite, c.criticite, c.niveau,
            c.detail, c.recommandation, c.preuve, "oui" if c.automatique else "non"]


def ecrire_csv(res: Resultat, chemin: Path):
    with chemin.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(ENTETES)
        for c in _rangs(res):
            w.writerow(_ligne_csv(c))


def ecrire_markdown(res: Resultat, chemin: Path):
    s = synthese(res)
    p = res.produit
    o = []
    o.append(f"# Radar d'obsolescence : {p.nom}\n")
    o.append(f"Généré le {date.today():%d/%m/%Y} par l'outil libre PPC « radar-obsolescence » version {__version__}.\n")
    o.append("## Synthèse\n")
    o.append(f"- **Indice de pérennité : {s['indice']} / 100** (100 = aucun risque détecté)")
    o.append(f"- Lignes de nomenclature analysées : {len(res.lignes)}")
    o.append(f"- Lignes **critiques** (criticité ≥ 6) : {s['lignes_critiques']} ; "
             f"**à surveiller** (3 à 5) : {s['lignes_a_surveiller']}")
    o.append(f"- Mise sur le marché : {p.date_mise_marche:%d/%m/%Y} ; durée de vie cible : "
             f"{p.duree_vie_cible_ans} ans (horizon {p.horizon:%d/%m/%Y})"
             + (f" ; support annoncé jusqu'au {p.fin_support:%d/%m/%Y}" if p.fin_support else ""))
    o.append("")
    o.append("### Par famille de causes\n")
    o.append("| Famille | Constats | Criticité max | Critiques |")
    o.append("|---|---:|---:|---:|")
    for k, lib in FAMILLES.items():
        e = s["par_famille"].get(k)
        if e:
            o.append(f"| {k}. {lib} | {e['nb']} | {e['max']} | {e['critiques']} |")
    o.append("")
    o.append("### Par domaine\n")
    o.append("| Domaine | Constats | Criticité max | Critiques |")
    o.append("|---|---:|---:|---:|")
    for k, lib in DOMAINES.items():
        e = s["par_domaine"].get(k)
        if e:
            o.append(f"| {lib} | {e['nb']} | {e['max']} | {e['critiques']} |")
    o.append("")
    o.append("## Constats classés par criticité\n")
    o.append("Criticité = exposition (0-3) × gravité de la fonction (1-3).\n")
    o.append("| Criticité | Niveau | Ligne | Domaine | Constat | Détail | Preuve |")
    o.append("|---:|---|---|---|---|---|---|")
    for c in _rangs(res):
        preuve = f"[source]({c.preuve})" if c.preuve.startswith("http") else c.preuve
        o.append(_md(f"| {c.criticite} | {c.niveau} | {_e(c.ligne.libelle)} | {c.ligne.domaine} | "
                     f"{c.code} : {c.intitule} | {_e(c.detail)} | {preuve} |"))
    o.append("")
    if res.cycles_vie:
        o.append("## Statuts de cycle de vie des composants\n")
        o.append("Statut retenu pour chaque composant électronique, y compris quand il ne pose pas de problème. "
                 "La source indique d'où vient le statut (distributeur interrogé ou saisie dans la nomenclature).\n")
        o.append("| Ligne | Référence | Statut | Source | Détail |")
        o.append("|---|---|---|---|---|")
        for c in res.cycles_vie:
            o.append(_md(f"| {_e(c['ligne'])} | {_e(c['mpn'])} | {c['statut']} | {c['source']} | {_e(c['detail'])} |"))
        o.append("")
    o.append("## Recommandations de conception (criticité ≥ 3)\n")
    par_ligne: dict = {}
    for c in _rangs(res):
        if c.criticite >= 3:
            par_ligne.setdefault(c.ligne.numero, (c.ligne, c.criticite, []))[2].append(c)
    if not par_ligne:
        o.append("- Aucun constat à criticité ≥ 3.")
    for ligne, crit_max, constats in sorted(par_ligne.values(), key=lambda t: (-t[1], t[0].numero)):
        o.append(f"**{ligne.libelle}** (criticité max {crit_max})\n")
        deja = set()
        for c in constats:
            if c.code not in deja:
                deja.add(c.code)
                o.append(f"- {c.code} : {c.recommandation}")
        o.append("")
    if res.ords:
        o.append("## Pannes fréquentes de la catégorie (Open Repair Alliance)\n")
        if res.ords.get("trouve"):
            r = res.ords
            o.append(f"Catégorie « {r['categorie']} » : {r['nb_reparations']} tentatives de réparation"
                     + (f", âge médian {r['age_median_ans']} ans." if r.get("age_median_ans") else "."))
            o.append("")
            o.append("| Sous-ensemble cité | Occurrences | Part |")
            o.append("|---|---:|---:|")
            for nom, n, pct in r["sous_ensembles"]:
                o.append(f"| {nom} | {n} | {pct} % |")
            o.append("")
            o.append("Statuts de réparation : " + ", ".join(f"{k} ({v})" for k, v in r["statuts"]))
            if r["obstacles"]:
                o.append("\nObstacles principaux : " + ", ".join(f"{k} ({v})" for k, v in r["obstacles"]))
            o.append("\nDonnées : Open Repair Alliance, CC BY-SA 4.0, https://openrepair.org/open-data/downloads/")
        else:
            o.append(f"Catégorie « {res.ords.get('categorie')} » introuvable dans le fichier fourni.")
        o.append("")
    if not any(actif for _, actif, _ in etat_sources_composants()):
        o.append("> Aucune source de cycle de vie des composants n'était configurée : les statuts "
                 "électroniques proviennent uniquement de la nomenclature (voir le README, "
                 "« Configurer les sources de composants »).\n")
    if res.avertissements:
        o.append("## Avertissements (données manquantes ou sources indisponibles)\n")
        o.extend(f"- {a}" for a in res.avertissements)
        o.append("")
    o.append("## Sources de données\n")
    o.append("- endoflife.date : https://endoflife.date (fin de vie des logiciels)")
    o.append("- deps.dev (Open Source Insights) : https://deps.dev (dépréciation, avis de sécurité)")
    o.append("- OpenSSF Scorecard : https://scorecard.dev (maintenance des dépôts)")
    etat = {nom: actif for nom, actif, _ in etat_sources_composants()}
    def _etat(nom):
        return "configurée pour ce rapport" if etat.get(nom) else "non configurée pour ce rapport"
    o.append(f"- Mouser Search API : https://www.mouser.com/en/api-search/ (cycle de vie des composants, {_etat('Mouser')})")
    o.append(f"- DigiKey Product Information V4 : https://developer.digikey.com/ (cycle de vie des composants, {_etat('DigiKey')})")
    o.append(f"- Nexar / Octopart : https://nexar.com/api (cycle de vie des composants, {_etat('Nexar/Octopart')})")
    o.append("- Open Repair Alliance : https://openrepair.org/open-data/ (pannes observées, si fourni)")
    chemin.write_text("\n".join(o), encoding="utf-8")


def ecrire_xlsx(res: Resultat, chemin: Path) -> bool:
    try:
        import openpyxl
        from openpyxl.formatting.rule import CellIsRule
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        return False
    s = synthese(res)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Constats"
    ws.append(ENTETES)
    for c in _rangs(res):
        ws.append(_ligne_csv(c))
    entete = PatternFill("solid", start_color="1F4E5A")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = entete
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    largeurs = [7, 10, 30, 9, 9, 7, 40, 11, 10, 11, 14, 60, 60, 35, 12]
    for i, w in enumerate(largeurs, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column in (3, 7, 12, 13, 14))
    plage = f"J2:J{max(ws.max_row, 2)}"
    ws.conditional_formatting.add(plage, CellIsRule(operator="greaterThanOrEqual", formula=["6"],
                                                    fill=PatternFill("solid", start_color="F4B6B6")))
    ws.conditional_formatting.add(plage, CellIsRule(operator="between", formula=["3", "5"],
                                                    fill=PatternFill("solid", start_color="FCE4B6")))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:O{ws.max_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "1:1"

    ws2 = wb.create_sheet("Synthese")
    ws2.append(["Indice de pérennité (0-100)", s["indice"]])
    ws2.append(["Lignes analysées", len(res.lignes)])
    ws2.append(["Lignes critiques", s["lignes_critiques"]])
    ws2.append(["Lignes à surveiller", s["lignes_a_surveiller"]])
    ws2.append([])
    ws2.append(["Famille", "Constats", "Criticité max", "Critiques"])
    for k, lib in FAMILLES.items():
        e = s["par_famille"].get(k)
        if e:
            ws2.append([f"{k}. {lib}", e["nb"], e["max"], e["critiques"]])
    ws2.column_dimensions["A"].width = 62
    for col in "BCD":
        ws2.column_dimensions[col].width = 14
    for r in (1, 6):
        for cell in ws2[r]:
            cell.font = Font(bold=True)
    wb.save(chemin)
    return True


def resume(res: Resultat) -> dict:
    """Chiffres clés de l'analyse, lus par les générateurs de documents (guide, page d'accueil)."""
    s = synthese(res)
    p = res.produit
    max_ligne = {l.numero: 0 for l in res.lignes}
    for c in res.constats:
        max_ligne[c.ligne.numero] = max(max_ligne[c.ligne.numero], c.criticite)
    rangs = _rangs(res)
    return {
        "version_outil": __version__,
        "genere": date.today().isoformat(),
        "produit": {"nom": p.nom, "mise_marche": p.date_mise_marche.isoformat(),
                    "duree_vie": p.duree_vie_cible_ans, "horizon": p.horizon.isoformat(),
                    "fin_support": p.fin_support.isoformat() if p.fin_support else None},
        "indice": s["indice"],
        "nb_lignes": len(res.lignes),
        "lignes_par_domaine": {d: sum(l.domaine == d for l in res.lignes) for d in DOMAINES},
        "nb_constats": len(res.constats),
        "lignes": {"critiques": sum(v >= 6 for v in max_ligne.values()),
                   "a_surveiller": sum(3 <= v < 6 for v in max_ligne.values()),
                   "faibles": sum(1 <= v < 3 for v in max_ligne.values()),
                   "sans_constat": sum(v == 0 for v in max_ligne.values())},
        "par_famille": s["par_famille"],
        "par_domaine": s["par_domaine"],
        "constats": [{"id": str(c.ligne.get("id", c.ligne.numero)), "ligne": c.ligne.libelle,
                      "designation": str(c.ligne.get("designation", "")), "domaine": c.ligne.domaine,
                      "famille": c.famille, "code": c.code, "intitule": c.intitule,
                      "criticite": c.criticite, "niveau": c.niveau, "detail": c.detail}
                     for c in rangs],
        "echeances": sorted(res.echeances, key=lambda e: e["date"]),
        "avertissements": res.avertissements,
    }


def ecrire_json(res: Resultat, chemin: Path) -> Path:
    Path(chemin).write_text(json.dumps(resume(res), ensure_ascii=False, indent=1), encoding="utf-8")
    return Path(chemin)
