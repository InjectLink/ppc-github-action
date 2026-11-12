"""Génère un modèle de nomenclature XLSX documenté (python -m radar_obsolescence --modele)."""

from __future__ import annotations

from pathlib import Path

# colonne -> (domaines concernés, description, valeurs attendues)
DESCRIPTION = {
    "id": ("M E L", "Repère unique de la ligne", "texte, ex. M1, E12, L3"),
    "designation": ("M E L", "Désignation lisible (sert aussi à repérer 2G/3G et les pannes fréquentes Open Repair)", "texte"),
    "domaine": ("M E L", "Domaine technique", "M (mécanique), E (électronique), L (logiciel)"),
    "quantite": ("M E L", "Quantité par produit", "entier"),
    "fonction_critique": ("M E L", "Gravité si la pièce devient indisponible ou défaillante", "1 confort, 2 fonction importante, 3 fonction essentielle (défaut : 2)"),
    "fabricant": ("M E", "Fabricant", "texte"),
    "reference_fabricant": ("M E", "Référence fabricant (MPN) ; interrogée sur Mouser, DigiKey ou Nexar si configuré (référence exacte)", "texte"),
    "fournisseur": ("M E", "Fournisseur ou distributeur actuel", "texte"),
    "nb_sources": ("M E", "Nombre de sources qualifiées (fabricants équivalents)", "entier"),
    "statut_cycle_vie": ("E (M)", "Statut de cycle de vie", "ACTIF, NOUVEAU, NRND, LTB, EOL, OBSOLETE, INCONNU"),
    "piece_specifique": ("M E", "Pièce spécifique au produit (moule, outillage, composant sur mesure)", "oui / non"),
    "plans_ouverts": ("M E", "Plans ou fichiers de fabrication disponibles (STEP, schémas, gerbers)", "oui / non"),
    "piece_usure": ("M E", "Pièce d'usure ou à durée de vie limitée (joint, roulement, batterie, condensateur, relais...)", "oui / non"),
    "remplacable_utilisateur": ("M E", "Remplaçable par l'utilisateur sans outil spécifique", "oui / non"),
    "ref_demontage": ("M E", "Repère du composant dans la cartographie de démontage (colonne « Réf. » du classeur GT1) ; sert à importer le nombre d'étapes avec --carte", "texte ou entier"),
    "etapes_demontage": ("M E", "Nombre d'étapes de démontage pour atteindre la pièce (issu de la Disassembly Map)", "entier"),
    "disponibilite_pieces_ans": ("M E", "Durée de disponibilité garantie des pièces détachées", "années"),
    "interface_standard": ("M E", "Interface ou connectique normalisée", "oui / non"),
    "logiciel_produit": ("L", "Identifiant du produit sur endoflife.date (ex. debian, python, nodejs, openssl, linux)", "texte (voir https://endoflife.date)"),
    "logiciel_version": ("L", "Version ou cycle utilisé", "ex. 11, 3.8, 20"),
    "mise_a_jour_prevue": ("L", "Une montée de version est organisée avant la fin de vie (mise à jour à distance, marge mémoire, procédure documentée)", "oui / non"),
    "ecosysteme": ("L", "Gestionnaire de paquets (interrogé sur deps.dev)", "npm, pypi, cargo, maven, go, nuget"),
    "paquet": ("L", "Nom du paquet", "texte"),
    "paquet_version": ("L", "Version du paquet (vide = version par défaut)", "texte"),
    "depot": ("L", "Dépôt source (évalué par OpenSSF Scorecard)", "URL GitHub ou GitLab"),
    "dependance_cloud": ("L E", "La fonction dépend d'un service distant", "oui / non"),
    "mode_local": ("L E", "Un mode de fonctionnement local existe sans le service distant", "oui / non"),
    "date_fin_support": ("L E", "Date de fin de support connue (fournisseur, service, licence)", "AAAA-MM-JJ"),
    "remarques": ("M E L", "Remarques libres", "texte"),
}


def generer(chemin: str | Path):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    from .nomenclature import COLONNES

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Nomenclature"
    ws.append(COLONNES)
    remplissage = PatternFill("solid", start_color="1F4E5A")
    for i, cell in enumerate(ws[1], start=1):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = remplissage
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = max(12, min(28, len(cell.value) + 4))
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "C2"
    lettre = {c: openpyxl.utils.get_column_letter(i) for i, c in enumerate(COLONNES, start=1)}

    def liste(col, valeurs):
        dv = DataValidation(type="list", formula1='"' + ",".join(valeurs) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{lettre[col]}2:{lettre[col]}1000")

    liste("domaine", ["M", "E", "L"])
    liste("fonction_critique", ["1", "2", "3"])
    liste("statut_cycle_vie", ["ACTIF", "NOUVEAU", "NRND", "LTB", "EOL", "OBSOLETE", "INCONNU"])
    for col in ("piece_specifique", "plans_ouverts", "piece_usure", "remplacable_utilisateur",
                "interface_standard", "dependance_cloud", "mode_local"):
        liste(col, ["oui", "non"])
    liste("ecosysteme", ["npm", "pypi", "cargo", "maven", "go", "nuget"])

    doc = wb.create_sheet("Colonnes")
    doc.append(["Colonne", "Domaines", "Description", "Valeurs attendues"])
    for cell in doc[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = remplissage
    for col in COLONNES:
        d = DESCRIPTION.get(col, ("", "", ""))
        doc.append([col, *d])
    for col, w in zip("ABCD", (26, 10, 80, 50)):
        doc.column_dimensions[col].width = w
    for row in doc.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    wb.save(chemin)
