"""Lecture de la nomenclature (CSV ou XLSX) et de la fiche produit (JSON)."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

COLONNES = [
    "id", "designation", "domaine", "quantite", "fonction_critique",
    "fabricant", "reference_fabricant", "fournisseur", "nb_sources",
    "statut_cycle_vie", "piece_specifique", "plans_ouverts", "piece_usure",
    "remplacable_utilisateur", "ref_demontage", "etapes_demontage", "disponibilite_pieces_ans",
    "interface_standard", "logiciel_produit", "logiciel_version",
    "mise_a_jour_prevue", "ecosysteme", "paquet", "paquet_version", "depot",
    "dependance_cloud", "mode_local", "date_fin_support", "remarques",
]

ALIAS = {
    "ref": "id", "repere": "id", "item": "id",
    "description": "designation", "nom": "designation",
    "domain": "domaine", "type": "domaine",
    "qty": "quantite", "qte": "quantite",
    "criticite_fonction": "fonction_critique", "gravite": "fonction_critique",
    "manufacturer": "fabricant", "mpn": "reference_fabricant",
    "supplier": "fournisseur", "sources": "nb_sources",
    "lifecycle": "statut_cycle_vie", "cycle_de_vie": "statut_cycle_vie",
    "specifique": "piece_specifique", "usure": "piece_usure",
    "endoflife": "logiciel_produit", "eol_produit": "logiciel_produit",
    "package": "paquet", "version_paquet": "paquet_version",
    "repo": "depot", "github": "depot", "cloud": "dependance_cloud",
    "fin_support": "date_fin_support",
    "nb_etapes_demontage": "etapes_demontage",
    "ref_carte": "ref_demontage", "ref_carto": "ref_demontage", "ref_disassembly_map": "ref_demontage",
}

CLES_PRODUIT = ("nom", "date_mise_marche", "duree_vie_cible_ans", "duree_support_annoncee_ans", "categorie_ords")


def _cle(texte) -> str:
    t = unicodedata.normalize("NFKD", str(texte or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


# en-têtes lisibles du classeur du kit (voir classeur.LIBELLES), normalisés par _cle
LIBELLES_LUS = {
    "domaine_m_e_l": "domaine", "gravite_de_la_fonction_1_a_3": "fonction_critique",
    "reference_fabricant_mpn": "reference_fabricant", "nombre_de_sources": "nb_sources",
    "statut_de_cycle_de_vie": "statut_cycle_vie", "piece_d_usure": "piece_usure",
    "remplacable_par_l_utilisateur": "remplacable_utilisateur",
    "ref_dans_la_carte_de_demontage": "ref_demontage", "etapes_de_demontage": "etapes_demontage",
    "disponibilite_des_pieces_ans": "disponibilite_pieces_ans", "logiciel_endoflife_date": "logiciel_produit",
    "version_du_logiciel": "logiciel_version", "montee_de_version_prevue": "mise_a_jour_prevue",
    "ecosysteme_de_paquets": "ecosysteme", "version_du_paquet": "paquet_version", "depot_source": "depot",
    "depend_d_un_service_distant": "dependance_cloud", "mode_local_disponible": "mode_local",
    "date_de_fin_de_support": "date_fin_support",
}


def _normaliser_entete(texte: str) -> str:
    t = _cle(texte)
    return LIBELLES_LUS.get(t) or ALIAS.get(t, t)


def oui(valeur) -> bool | None:
    """Interprète oui/non ; None si non renseigné."""
    if valeur is None:
        return None
    v = str(valeur).strip().lower()
    if v in {"oui", "o", "yes", "y", "true", "vrai", "1", "x"}:
        return True
    if v in {"non", "n", "no", "false", "faux", "0"}:
        return False
    return None


def entier(valeur, defaut=None):
    try:
        return int(float(str(valeur).replace(",", ".")))
    except (TypeError, ValueError):
        return defaut


def date_iso(valeur) -> date | None:
    if valeur in (None, ""):
        return None
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    texte = str(valeur).strip()[:10]
    for sep in ("-", "/"):
        parties = texte.split(sep)
        if len(parties) == 3:
            try:
                if len(parties[0]) == 4:
                    return date(int(parties[0]), int(parties[1]), int(parties[2]))
                return date(int(parties[2]), int(parties[1]), int(parties[0]))
            except ValueError:
                return None
    if len(texte) == 4 and texte.isdigit():
        return date(int(texte), 12, 31)
    return None


def ajouter_annees(d: date, annees: int) -> date:
    try:
        return d.replace(year=d.year + annees)
    except ValueError:  # 29 février
        return d.replace(year=d.year + annees, day=28)


@dataclass
class Ligne:
    numero: int
    data: dict

    def get(self, cle, defaut=""):
        v = self.data.get(cle)
        return defaut if v in (None, "") else v

    @property
    def domaine(self) -> str:
        d = str(self.get("domaine", "?")).strip().upper()[:1]
        return d if d in {"M", "E", "L"} else "?"

    @property
    def gravite(self) -> int:
        g = entier(self.get("fonction_critique"), 2)
        return min(max(g, 1), 3)

    @property
    def libelle(self) -> str:
        return f"{self.get('id', self.numero)} : {self.get('designation', '(sans désignation)')}"


@dataclass
class Produit:
    nom: str = "Produit"
    date_mise_marche: date = field(default_factory=date.today)
    duree_vie_cible_ans: int = 10
    duree_support_annoncee_ans: int | None = None
    categorie_ords: str | None = None

    @property
    def horizon(self) -> date:
        """Date de fin de vie visée du produit."""
        return ajouter_annees(self.date_mise_marche, self.duree_vie_cible_ans)

    @property
    def fin_support(self) -> date | None:
        if not self.duree_support_annoncee_ans:
            return None
        return ajouter_annees(self.date_mise_marche, int(self.duree_support_annoncee_ans))


def charger_produit(chemin: str | Path | None) -> Produit:
    """Fiche produit : fichier JSON, ou onglet « Produit » d'un classeur XLSX (clé en colonne A, valeur en B)."""
    if not chemin:
        return Produit()
    chemin = Path(chemin)
    if chemin.suffix.lower() in {".xlsx", ".xlsm"}:
        donnees = lire_produit_xlsx(chemin) or {}
    else:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    return Produit(
        nom=donnees.get("nom") or "Produit",
        date_mise_marche=date_iso(donnees.get("date_mise_marche")) or date.today(),
        duree_vie_cible_ans=entier(donnees.get("duree_vie_cible_ans"), 10),
        duree_support_annoncee_ans=entier(donnees.get("duree_support_annoncee_ans")),
        categorie_ords=donnees.get("categorie_ords") or None,
    )


def lire_produit_xlsx(chemin: Path) -> dict | None:
    """Lit l'onglet « Produit » d'un classeur ; None s'il n'existe pas."""
    import openpyxl
    wb = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    try:
        if "Produit" not in wb.sheetnames:
            return None
        donnees = {}
        for ligne in wb["Produit"].iter_rows(values_only=True):
            if not ligne or len(ligne) < 2:
                continue
            # clé technique en colonne A (format simple) ou dans une colonne « Clé » (classeur du kit)
            cle = next((c for c in ligne if isinstance(c, str) and c.strip() in CLES_PRODUIT), None)
            if cle and ligne[1] not in (None, ""):
                donnees[cle.strip()] = ligne[1]
        return donnees
    finally:
        wb.close()


def charger_nomenclature(chemin: str | Path, onglet: str | None = None) -> list[Ligne]:
    chemin = Path(chemin)
    if chemin.suffix.lower() in {".xlsx", ".xlsm"}:
        lignes_brutes = _lire_xlsx(chemin, onglet)
    else:
        lignes_brutes = _lire_csv(chemin)
    if not lignes_brutes:
        return []
    entetes = [_normaliser_entete(h) for h in lignes_brutes[0]]
    resultat = []
    for i, brut in enumerate(lignes_brutes[1:], start=2):
        if not any(str(c or "").strip() for c in brut):
            continue
        data = {entetes[j]: (brut[j].strip() if isinstance(brut[j], str) else brut[j])
                for j in range(min(len(entetes), len(brut)))}
        resultat.append(Ligne(numero=i, data=data))
    return resultat


def _lire_csv(chemin: Path) -> list[list]:
    texte = chemin.read_text(encoding="utf-8-sig")
    try:
        dialecte = csv.Sniffer().sniff(texte.splitlines()[0], delimiters=";,\t")
    except csv.Error:
        dialecte = csv.excel
    return list(csv.reader(texte.splitlines(), dialecte))


def onglets_xlsx(chemin) -> list[str]:
    import openpyxl
    wb = openpyxl.load_workbook(chemin, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def _lire_xlsx(chemin: Path, onglet: str | None = None) -> list[list]:
    """Onglet « Nomenclature » s'il existe (sinon le premier) ; l'en-tête est la première ligne
    contenant les colonnes id et designation, ce qui permet un titre ou une légende au-dessus."""
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Lecture XLSX : installez openpyxl (pip install openpyxl)") from exc
    wb = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    if onglet:
        trouve = next((n for n in wb.sheetnames if _cle(n) == _cle(onglet)), None)
        if not trouve:
            noms = ", ".join(wb.sheetnames)
            wb.close()
            raise SystemExit(f"Onglet « {onglet} » introuvable (onglets : {noms})")
        ws = wb[trouve]
    else:
        ws = wb["Nomenclature"] if "Nomenclature" in wb.sheetnames else wb.worksheets[0]
    lignes = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    for i, r in enumerate(lignes[:15]):
        entetes = {_normaliser_entete(c) for c in r if c is not None}
        if {"id", "designation"} <= entetes:
            return lignes[i:]
    return lignes


def importer_carte_demontage(lignes: list[Ligne], chemin: str | Path, scenario: str | None = None) -> tuple[int, list[str]]:
    """Reprend le nombre d'étapes de démontage du fichier etapes_par_composant.csv produit par
    le générateur de cartographie de démontage PPC (GT1, carto_demontage.py).

    Rapprochement par la colonne ref_demontage (repère « Réf. » de la carte), sinon par la désignation.
    Une valeur déjà saisie dans la nomenclature est conservée. Renvoie (nombre de lignes complétées, avertissements).
    """
    brut = _lire_csv(Path(chemin))
    if not brut:
        return 0, [f"Carte de démontage vide : {chemin}"]
    entetes = [str(h).strip() for h in brut[0]]
    colonnes_etapes = [i for i, h in enumerate(entetes) if h.lower().startswith("étapes") or h.lower().startswith("etapes")]
    if not colonnes_etapes:
        return 0, [f"Carte de démontage : aucune colonne « Étapes (...) » dans {chemin}"]
    col = colonnes_etapes[0]
    if scenario:
        choix = [i for i in colonnes_etapes if _cle(scenario) in _cle(entetes[i])]
        if not choix:
            return 0, [f"Carte de démontage : scénario « {scenario} » absent (colonnes : "
                       + ", ".join(entetes[i] for i in colonnes_etapes) + ")"]
        col = choix[0]
    i_ref = next((i for i, h in enumerate(entetes) if _normaliser_entete(h).rstrip(".") in ("ref", "id")), 0)
    i_nom = next((i for i, h in enumerate(entetes) if _normaliser_entete(h) in ("composant", "designation")), 1)
    par_ref, par_nom = {}, {}
    for r in brut[1:]:
        if len(r) <= col or entier(r[col]) is None:
            continue
        par_ref[str(r[i_ref]).strip().upper()] = entier(r[col])
        par_nom[_cle_texte(r[i_nom])] = entier(r[col])
    n = 0
    for l in lignes:
        if l.get("etapes_demontage") != "":
            continue
        ref = str(l.get("ref_demontage")).strip().upper()
        valeur = par_ref.get(ref) if ref else None
        if valeur is None:
            valeur = par_nom.get(_cle_texte(l.get("designation")))
        if valeur is not None:
            l.data["etapes_demontage"] = valeur
            l.data["_etapes_source"] = f"carte de démontage ({entetes[col]})"
            n += 1
    return n, []


def _cle_texte(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())
