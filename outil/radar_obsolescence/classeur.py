"""Classeur de saisie du radar, au format du classeur de la cartographie de démontage PPC (GT1).

    python -m radar_obsolescence --modele Classeur.xlsx             (classeur vide)
    python -m radar_obsolescence --modele Classeur.xlsx --exemple   (classeur avec l'exemple du thermostat)

Onglets : Lisez-moi, Produit, Nomenclature, [Nomenclature améliorée], Colonnes, Référentiel.
Convention de couleurs reprise du GT1 : fond crème = cellule à saisir, fond gris = calculé.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .modele import DESCRIPTION
from .nomenclature import COLONNES
from .referentiel import FAMILLES, REGLES

MARINE, SARCELLE, CORAIL, GRIS_TXT = "1F3A5F", "1A8C8C", "E8735A", "6B7785"
CREME, GRIS_FOND = "FFF8E7", "EEF1F4"
POLICE = "Arial"

# en-têtes lisibles du classeur (relus grâce à nomenclature.LIBELLES)
LIBELLES = {
    "id": "Repère", "designation": "Désignation", "domaine": "Domaine\n(M, E, L)", "quantite": "Quantité",
    "fonction_critique": "Gravité de la fonction\n(1 à 3)", "fabricant": "Fabricant",
    "reference_fabricant": "Référence fabricant\n(MPN)", "fournisseur": "Fournisseur",
    "nb_sources": "Nombre de sources", "statut_cycle_vie": "Statut de cycle de vie",
    "piece_specifique": "Pièce spécifique ?", "plans_ouverts": "Plans ouverts ?", "piece_usure": "Pièce d'usure ?",
    "remplacable_utilisateur": "Remplaçable par l'utilisateur ?",
    "ref_demontage": "Réf. dans la carte de démontage", "etapes_demontage": "Étapes de démontage",
    "disponibilite_pieces_ans": "Disponibilité des pièces (ans)", "interface_standard": "Interface standard ?",
    "logiciel_produit": "Logiciel\n(endoflife.date)", "logiciel_version": "Version du logiciel",
    "mise_a_jour_prevue": "Montée de version prévue ?", "ecosysteme": "Écosystème de paquets",
    "paquet": "Paquet", "paquet_version": "Version du paquet", "depot": "Dépôt source",
    "dependance_cloud": "Dépend d'un service distant ?", "mode_local": "Mode local disponible ?",
    "date_fin_support": "Date de fin de support", "remarques": "Remarques",
}

GROUPES = [  # (titre, première colonne, dernière colonne, couleur)
    ("Identification", "id", "fonction_critique", MARINE),
    ("Approvisionnement", "fabricant", "plans_ouverts", SARCELLE),
    ("Réparabilité", "piece_usure", "interface_standard", CORAIL),
    ("Logiciel et services", "logiciel_produit", "date_fin_support", MARINE),
    ("", "remarques", "remarques", GRIS_TXT),
]

LARGEURS = {"id": 8, "designation": 34, "domaine": 9, "quantite": 9, "fonction_critique": 11,
            "fabricant": 16, "reference_fabricant": 20, "fournisseur": 14, "depot": 30, "remarques": 34,
            "date_fin_support": 13, "logiciel_produit": 13}

PRODUIT = [  # clé, libellé, explication
    ("nom", "Nom du produit", "Nom affiché dans le rapport et le visualiseur"),
    ("date_mise_marche", "Date de mise sur le marché", "Date réelle ou prévue (AAAA-MM-JJ)"),
    ("duree_vie_cible_ans", "Durée de vie cible (ans)", "Durée d'usage visée : sert d'horizon pour toutes les échéances"),
    ("duree_support_annoncee_ans", "Durée de support annoncée (ans)", "Mises à jour et pièces promises au client ; vide si non annoncée"),
    ("categorie_ords", "Catégorie Open Repair (facultatif)", "Catégorie ORDS pour rapprocher les pannes fréquentes (option --ords)"),
]


def generer(chemin: str | Path, exemple: bool = False, dossier_exemples: Path | None = None):
    import openpyxl
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    dossier_exemples = dossier_exemples or Path(__file__).resolve().parent.parent / "exemples"
    fin = Side(style="thin", color="D5DDE5")
    bord = Border(left=fin, right=fin, top=fin, bottom=fin)
    rempl = lambda c: PatternFill("solid", start_color=c)
    f = lambda **k: Font(name=POLICE, size=k.pop("size", 9), **k)

    def entete_onglet(ws, titre, note, legende=True):
        ws["A1"] = titre
        ws["A1"].font = f(size=16, bold=True, color=MARINE)
        ws["A2"] = note
        ws["A2"].font = f(color=GRIS_TXT)
        if legende:
            ws["A3"] = "Fond crème : cellules à saisir    Fond gris : calculé    Survoler un en-tête pour son aide"
            ws["A3"].font = f(color=SARCELLE)
        ws.sheet_view.showGridLines = False

    wb = openpyxl.Workbook()

    # ------------------------------------------------------------ Lisez-moi
    ws = wb.active
    ws.title = "Lisez-moi"
    ws.sheet_properties.tabColor = MARINE
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 100
    ws["B2"] = "Radar d'obsolescence : classeur de saisie"
    ws["B2"].font = f(size=18, bold=True, color=MARINE)
    ws["B3"] = "Association pour la Pérennité Programmée Circulaire (PPC), licence CC BY-SA 4.0"
    ws["B3"].font = f(size=10, color=GRIS_TXT)
    lignes = [
        ("Objet", "Repérer tôt, dès la conception, les causes d'obsolescence d'un produit : pièces d'usure inaccessibles, "
                  "sources uniques, composants en fin de vie, logiciels et services dont le support s'arrête avant la "
                  "durée de vie visée."),
        ("Méthode", "Une ligne par pièce, composant ou brique logicielle. L'outil libre radar_obsolescence lit ce classeur, "
                    "interroge des bases ouvertes (endoflife.date, deps.dev, OpenSSF Scorecard, et Mouser, DigiKey ou Nexar "
                    "si une clé est configurée) et cote chaque risque : criticité = exposition (0 à 3) × gravité (1 à 3)."),
        ("Étape 1 : Produit", "Onglet Produit : date de mise sur le marché, durée de vie cible et durée de support annoncée. "
                              "Ces dates servent d'horizon à toutes les échéances."),
        ("Étape 2 : Nomenclature", "Onglet Nomenclature : remplir au moins Repère, Désignation, Domaine et Gravité, puis les "
                                   "colonnes utiles au domaine (aide au survol de chaque en-tête, détail dans l'onglet Colonnes)."),
        ("Étape 3 : Démontage", "Reprendre le nombre d'étapes de démontage de la cartographie de démontage (kit GT1) : à la main "
                                "dans la colonne Étapes de démontage, ou automatiquement avec l'option --carte "
                                "etapes_par_composant.csv et la colonne Réf. dans la carte de démontage."),
        ("Étape 4 : Générer", "Double-cliquer sur lancer_radar_windows.bat, ou : python radar.py ce_classeur.xlsx. "
                              "Le dossier resultats contient visualiseur.html, le rapport et les constats."),
        ("Étape 5 : Analyser", "Ouvrir visualiseur.html : synthèse, radar par famille de causes, frise des échéances, "
                               "constats filtrables avec leurs recommandations de conception."),
        ("Étape 6 : Améliorer", "Copier l'onglet Nomenclature, modifier la conception (pièce standard, seconde source, module "
                                "remplaçable, mode local...) et relancer avec --onglet pour comparer l'indice de pérennité."),
        ("Données personnelles", "Le classeur ne contient aucune clé d'accès. Les clés Mouser ou DigiKey se déclarent dans "
                                 "Windows avec configurer_cles_windows.bat et ne doivent jamais être partagées."),
        ("Référence", "État de l'art PPC sur les causes d'obsolescence ; De Fazio F. et al. (2021), The Disassembly Map, "
                      "Journal of Cleaner Production 320, doi:10.1016/j.jclepro.2021.128552 ; norme IEC 62402 (gestion de "
                      "l'obsolescence)."),
    ]
    for i, (k, v) in enumerate(lignes, start=5):
        ws.cell(i, 2, k).font = f(size=10, bold=True, color=MARINE)
        c = ws.cell(i, 3, v)
        c.font = f(size=10)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(i, 2).alignment = Alignment(vertical="top")
        ws.row_dimensions[i].height = 15 * max(1, len(v) // 95 + 1)

    # ------------------------------------------------------------ Produit
    wp = wb.create_sheet("Produit")
    wp.sheet_properties.tabColor = SARCELLE
    entete_onglet(wp, "Fiche produit", "Calendrier du produit : il sert d'horizon à toutes les échéances du radar.")
    for col, w in zip("ABCD", (34, 26, 70, 26)):
        wp.column_dimensions[col].width = w
    for j, t in enumerate(("Paramètre", "Valeur", "Explication", "Clé lue par l'outil"), start=1):
        c = wp.cell(4, j, t)
        c.font = f(bold=True, color="FFFFFF")
        c.fill = rempl(MARINE)
        c.border = bord
    valeurs = {}
    if exemple:
        valeurs = json.loads((dossier_exemples / "produit_exemple.json").read_text(encoding="utf-8"))
    for i, (cle, lib, aide) in enumerate(PRODUIT, start=5):
        wp.cell(i, 1, lib).font = f()
        v = valeurs.get(cle, "")
        if cle == "date_mise_marche" and v:
            from .nomenclature import date_iso
            v = date_iso(v)
        c = wp.cell(i, 2, v if v != "" else None)
        c.fill = rempl(CREME)
        c.font = f(bold=True)
        if cle == "date_mise_marche":
            c.number_format = "DD/MM/YYYY"
        wp.cell(i, 3, aide).font = f(color=GRIS_TXT)
        wp.cell(i, 4, cle).font = f(color=GRIS_TXT, italic=False)
        for j in range(1, 5):
            wp.cell(i, j).border = bord
    r = 5 + len(PRODUIT)
    calc = [("Horizon du produit", "=IF(B6=\"\",\"\",EDATE(B6,12*B7))", "Mise sur le marché + durée de vie cible"),
            ("Fin du support annoncé", "=IF(OR(B6=\"\",B8=\"\"),\"\",EDATE(B6,12*B8))", "Mise sur le marché + durée de support")]
    for i, (lib, formule, aide) in enumerate(calc, start=r):
        wp.cell(i, 1, lib).font = f()
        c = wp.cell(i, 2, formule)
        c.fill = rempl(GRIS_FOND)
        c.number_format = "DD/MM/YYYY"
        c.font = f(bold=True)
        wp.cell(i, 3, aide).font = f(color=GRIS_TXT)
        for j in range(1, 5):
            wp.cell(i, j).border = bord
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="50", allow_blank=True)
    wp.add_data_validation(dv)
    dv.add("B7:B8")

    # ------------------------------------------------------------ Nomenclature(s)
    scenarios = [("Nomenclature", "nomenclature_exemple.csv",
                  "Étapes 1 à 3 : une ligne par pièce mécanique, composant électronique ou brique logicielle.")]
    if exemple:
        scenarios.append(("Nomenclature améliorée", "nomenclature_ameliore.csv",
                          "Étape 6 : même produit après reconception (pièces standard, modules remplaçables, mode local)."))
    lettre = {c: get_column_letter(i) for i, c in enumerate(COLONNES, start=1)}
    for titre, fichier, note in scenarios:
        wn = wb.create_sheet(titre)
        wn.sheet_properties.tabColor = SARCELLE if titre == "Nomenclature" else CORAIL
        entete_onglet(wn, "Nomenclature : " + ("scénario actuel" if titre == "Nomenclature" else "scénario amélioré")
                      if exemple else "Nomenclature", note)
        # bandeau de groupes (ligne 4) puis en-têtes (ligne 5)
        for nom, de, a, coul in GROUPES:
            i0, i1 = COLONNES.index(de) + 1, COLONNES.index(a) + 1
            if nom:
                wn.merge_cells(start_row=4, start_column=i0, end_row=4, end_column=i1)
            c = wn.cell(4, i0, nom or None)
            c.font = f(bold=True, color="FFFFFF")
            c.alignment = Alignment(horizontal="center")
            for j in range(i0, i1 + 1):
                wn.cell(4, j).fill = rempl(coul)
        for j, col in enumerate(COLONNES, start=1):
            c = wn.cell(5, j, LIBELLES[col])
            c.font = f(bold=True, color="FFFFFF")
            c.fill = rempl(MARINE)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = bord
            dom, desc, val = DESCRIPTION[col]
            c.comment = Comment(f"{desc}\nValeurs : {val}\nDomaines : {dom}\nColonne : {col}", "PPC", width=320, height=130)
            wn.column_dimensions[get_column_letter(j)].width = LARGEURS.get(col, 12)
        wn.row_dimensions[5].height = 42
        donnees = []
        if exemple:
            with (dossier_exemples / fichier).open(encoding="utf-8") as fh:
                donnees = list(csv.DictReader(fh, delimiter=";"))
        nb = max(len(donnees) + 30, 60)
        for i in range(nb):
            ligne = donnees[i] if i < len(donnees) else {}
            for j, col in enumerate(COLONNES, start=1):
                v = ligne.get(col, "")
                if v != "" and col in ("quantite", "fonction_critique", "nb_sources", "etapes_demontage",
                                       "disponibilite_pieces_ans"):
                    try:
                        v = int(v)
                    except ValueError:
                        pass
                c = wn.cell(6 + i, j, v if v != "" else None)
                c.fill = rempl(CREME)
                c.font = f()
                c.border = bord
                c.alignment = Alignment(vertical="top", wrap_text=col in ("designation", "remarques"))
        wn.freeze_panes = "C6"
        wn.auto_filter.ref = f"A5:{get_column_letter(len(COLONNES))}{5 + nb}"

        def liste(col, valeurs):
            dv = DataValidation(type="list", formula1='"' + ",".join(valeurs) + '"', allow_blank=True)
            wn.add_data_validation(dv)
            dv.add(f"{lettre[col]}6:{lettre[col]}{5 + nb}")

        liste("domaine", ["M", "E", "L"])
        liste("fonction_critique", ["1", "2", "3"])
        liste("statut_cycle_vie", ["ACTIF", "NOUVEAU", "NRND", "LTB", "EOL", "OBSOLETE", "INCONNU"])
        for col in ("piece_specifique", "plans_ouverts", "piece_usure", "remplacable_utilisateur",
                    "interface_standard", "mise_a_jour_prevue", "dependance_cloud", "mode_local"):
            liste(col, ["oui", "non"])
        liste("ecosysteme", ["npm", "pypi", "cargo", "maven", "go", "nuget"])

    # ------------------------------------------------------------ Colonnes
    wc = wb.create_sheet("Colonnes")
    wc.sheet_properties.tabColor = GRIS_TXT
    entete_onglet(wc, "Colonnes de la nomenclature", "Aide détaillée de chaque colonne. Les en-têtes peuvent aussi être "
                  "saisis sous leur nom technique (fichier CSV).", legende=False)
    for j, (t, w) in enumerate((("En-tête du classeur", 30), ("Nom technique (CSV)", 24), ("Domaines", 10),
                                ("Description", 80), ("Valeurs attendues", 44)), start=1):
        c = wc.cell(4, j, t)
        c.font = f(bold=True, color="FFFFFF")
        c.fill = rempl(MARINE)
        wc.column_dimensions[get_column_letter(j)].width = w
    for i, col in enumerate(COLONNES, start=5):
        dom, desc, val = DESCRIPTION[col]
        for j, v in enumerate((LIBELLES[col].replace("\n", " "), col, dom, desc, val), start=1):
            c = wc.cell(i, j, v)
            c.font = f()
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = bord

    # ------------------------------------------------------------ Référentiel
    wr = wb.create_sheet("Référentiel")
    wr.sheet_properties.tabColor = GRIS_TXT
    entete_onglet(wr, "Référentiel des règles", "Familles de causes (état de l'art PPC) et règles appliquées par le radar. "
                  "Criticité = exposition (0 à 3) × gravité (1 à 3) : critique ≥ 6, à surveiller 3 à 5, faible 1 à 2.",
                  legende=False)
    for j, (t, w) in enumerate((("Code", 8), ("Famille", 40), ("Constat", 56), ("Recommandation de conception", 90)), start=1):
        c = wr.cell(4, j, t)
        c.font = f(bold=True, color="FFFFFF")
        c.fill = rempl(MARINE)
        wr.column_dimensions[get_column_letter(j)].width = w
    for i, (code, (fam, intitule, reco)) in enumerate(REGLES.items(), start=5):
        for j, v in enumerate((code, f"{fam} : {FAMILLES[fam]}", intitule, reco), start=1):
            c = wr.cell(i, j, v)
            c.font = f(bold=(j == 1))
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = bord

    for feuille in wb.worksheets:  # impression : paysage, ajusté à la largeur
        feuille.page_setup.orientation = "landscape"
        feuille.sheet_properties.pageSetUpPr.fitToPage = True
        feuille.page_setup.fitToWidth = 1
        feuille.page_setup.fitToHeight = 0
    wb.active = 1 if exemple else 0
    wb.save(chemin)
    return Path(chemin)
