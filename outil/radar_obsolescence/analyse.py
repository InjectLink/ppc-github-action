"""Moteur d'analyse : applique les règles du référentiel à chaque ligne de nomenclature."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .nomenclature import Ligne, Produit, date_iso, entier, oui
import re

from .referentiel import REGLES, RESEAUX_EN_ARRET, STATUTS_CYCLE_VIE, niveau
from .sources import Cache, ErreurSource
from .sources import depsdev, digikey, endoflife, mouser, nexar, scorecard

ETAPES_DEMONTAGE_SEUIL = 5  # au-delà, l'accès à une pièce d'usure est jugé difficile


@dataclass
class Constat:
    ligne: Ligne
    code: str
    exposition: int           # 0-3
    detail: str
    preuve: str = ""          # URL ou source de la donnée
    automatique: bool = False  # True si la donnée vient d'une source externe

    @property
    def famille(self) -> str:
        return REGLES[self.code][0]

    @property
    def intitule(self) -> str:
        return REGLES[self.code][1]

    @property
    def recommandation(self) -> str:
        return REGLES[self.code][2]

    @property
    def gravite(self) -> int:
        return self.ligne.gravite

    @property
    def criticite(self) -> int:
        return self.exposition * self.gravite

    @property
    def niveau(self) -> str:
        return niveau(self.criticite)


@dataclass
class Resultat:
    produit: Produit
    lignes: list[Ligne]
    constats: list[Constat] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    ords: dict | None = None
    cycles_vie: list[dict] = field(default_factory=list)  # statut retenu par composant électronique
    echeances: list[dict] = field(default_factory=list)   # dates de fin connues (frise du visualiseur)



# Sources de cycle de vie des composants, dans l'ordre d'interrogation.
# Mouser et DigiKey sont gratuites (1 000 appels par jour) ; Nexar a un quota très faible en évaluation.
SOURCES_COMPOSANTS = (("Mouser", mouser), ("DigiKey", digikey), ("Nexar/Octopart", nexar))
VARIABLES_SOURCES = {"Mouser": "MOUSER_API_KEY", "DigiKey": "DIGIKEY_CLIENT_ID + DIGIKEY_CLIENT_SECRET",
                     "Nexar/Octopart": "NEXAR_TOKEN ou NEXAR_CLIENT_ID + NEXAR_CLIENT_SECRET"}


def etat_sources_composants() -> list[tuple[str, bool, str]]:
    """(nom, configurée, variables attendues) pour chaque source de cycle de vie des composants."""
    return [(nom, source.disponible(), VARIABLES_SOURCES[nom]) for nom, source in SOURCES_COMPOSANTS]


def _cycle_vie_composant(l, res, statut: str, preuve: str):
    """Interroge les sources configurées ; la première qui donne un statut connu l'emporte.
    Le statut saisi à la main est conservé si aucune source ne donne de statut."""
    mpn = str(l.get("reference_fabricant")).strip()
    for nom, source in SOURCES_COMPOSANTS:
        if not source.disponible():
            continue
        try:
            n = source.analyser(mpn, res._cache)
        except ErreurSource as e:
            res.avertissements.append(f"{l.libelle} : {nom} indisponible ({e})")
            continue
        if n.get("trouve") and n.get("statut") not in (None, "", "INCONNU"):
            detail = []
            if n.get("statut_brut"):
                detail.append(f"libellé : {n['statut_brut']}")
            if n.get("date_derniere_commande"):
                detail.append(f"dernière commande : {n['date_derniere_commande']}")
                _echeance(res, l, "Dernière commande", date_iso(n["date_derniere_commande"]), nom)
            if n.get("remplacement"):
                detail.append(f"remplacement suggéré : {n['remplacement']}")
            l.data["_detail_cycle_vie"] = " ; ".join(detail)
            if n.get("nb_distributeurs_agrees") is not None and entier(l.get("nb_sources")) is None:
                # nombre de distributeurs agréés : indicateur de disponibilité, pas de seconde source
                l.data["_distributeurs"] = n["nb_distributeurs_agrees"]
            return n["statut"], nom, True
        if n.get("trouve"):
            res.avertissements.append(f"{l.libelle} : trouvé sur {nom} sans statut de cycle de vie.")
        elif n.get("proches"):
            res.avertissements.append(f"{l.libelle} : référence exacte absente de {nom} ; références proches : "
                                      + ", ".join(p for p in n["proches"] if p) + ". Vérifier la référence complète.")
        elif not n.get("erreur"):
            res.avertissements.append(f"{l.libelle} : {mpn} introuvable sur {nom}"
                                      + (f" ({n['motif']})" if n.get("motif") else "") + ".")
    return statut, preuve, False

def _echeance(res: Resultat, l: Ligne, nature: str, quand: date | None, source: str = ""):
    """Mémorise une date de fin (logiciel, support, pièces, dernière commande) pour la frise."""
    if quand:
        res.echeances.append({"ligne": l.libelle, "id": str(l.get("id", l.numero)), "domaine": l.domaine,
                              "nature": nature, "date": quand.isoformat(), "source": source})


def _ajouter(res: Resultat, ligne, code, expo, detail, preuve="", auto=False):
    if expo is None or expo <= 0:
        return
    res.constats.append(Constat(ligne, code, min(int(expo), 3), detail, preuve, auto))


def _expo_date(echeance: date | None, produit: Produit) -> int:
    """Exposition selon la position d'une date de fin par rapport au calendrier du produit."""
    if echeance is None:
        return 0
    if echeance <= date.today():
        return 3
    if produit.fin_support and echeance < produit.fin_support:
        return 3
    if echeance < produit.horizon:
        return 2
    return 0


# ---------------------------------------------------------------- règles physiques (M, E)

def regles_physiques(res: Resultat, l: Ligne):
    usure = oui(l.get("piece_usure"))
    remplacable = oui(l.get("remplacable_utilisateur"))
    if usure and remplacable is False:
        _ajouter(res, l, "A1", 3, "Pièce d'usure déclarée non remplaçable par l'utilisateur.")
    elif usure and remplacable is None:
        _ajouter(res, l, "A1", 1, "Pièce d'usure : remplaçabilité non renseignée.")
    etapes = entier(l.get("etapes_demontage"))
    if usure and etapes is not None and etapes > ETAPES_DEMONTAGE_SEUIL:
        expo = 3 if etapes > 2 * ETAPES_DEMONTAGE_SEUIL else 2
        _ajouter(res, l, "A2", expo, f"{etapes} étapes de démontage pour atteindre la pièce "
                                     f"(seuil {ETAPES_DEMONTAGE_SEUIL}).", l.data.get("_etapes_source", "Disassembly Map"))

    # Cycle de vie (manuel ou Nexar)
    statut = str(l.get("statut_cycle_vie", "")).strip().upper()
    preuve, auto = "saisie nomenclature", False
    nb_sources = entier(l.get("nb_sources"))
    if l.domaine == "E" and l.get("reference_fabricant"):
        statut, preuve, auto = _cycle_vie_composant(l, res, statut, preuve)
        res.cycles_vie.append({"ligne": l.libelle, "mpn": str(l.get("reference_fabricant")).strip(),
                               "statut": statut or "INCONNU", "source": preuve if (auto or statut) else "",
                               "detail": l.data.get("_detail_cycle_vie", "")})
    expo = STATUTS_CYCLE_VIE.get(statut, None if statut in ("", "INCONNU") else 1)
    if expo:
        detail = l.data.get("_detail_cycle_vie")
        _ajouter(res, l, "B1", expo, f"Statut de cycle de vie : {statut}" + (f" ({detail})." if detail else "."),
                 preuve, auto)
    elif expo is None and l.domaine == "E":
        _ajouter(res, l, "B5", 1, "Statut de cycle de vie non renseigné.")

    specifique = oui(l.get("piece_specifique"))
    if nb_sources is not None:
        if nb_sources <= 1:
            _ajouter(res, l, "B2", 3 if specifique else 2, "Source unique.")
        elif nb_sources == 2:
            _ajouter(res, l, "B2", 1, "Deux sources seulement.")
    if specifique:
        plans = oui(l.get("plans_ouverts"))
        _ajouter(res, l, "B3", 1 if plans else 2,
                 "Pièce spécifique" + (" (plans ouverts disponibles)." if plans else
                                       " sans plans ouverts ni alternative standard."))
    dispo = entier(l.get("disponibilite_pieces_ans"))
    if dispo is not None:
        from .nomenclature import ajouter_annees
        _echeance(res, l, "Fin de disponibilité des pièces", ajouter_annees(res.produit.date_mise_marche, dispo),
                  "saisie nomenclature")
    if dispo is not None and dispo < res.produit.duree_vie_cible_ans:
        _ajouter(res, l, "B4", 3 if usure else 2,
                 f"Pièces détachées garanties {dispo} ans pour une durée de vie cible de "
                 f"{res.produit.duree_vie_cible_ans} ans.")
    if oui(l.get("interface_standard")) is False:
        _ajouter(res, l, "C1", 2, "Interface ou connectique propriétaire.")
    if l.domaine == "E":
        texte = f"{l.get('designation')} {l.get('remarques')}".lower()
        for mot, techno in RESEAUX_EN_ARRET.items():
            if re.search(rf"\b{mot}\b", texte):
                _ajouter(res, l, "C2", 3, f"Technologie {techno} : arrêt des réseaux engagé en Europe.",
                         "https://en.arcep.fr/fileadmin/user_upload/38-26-english-version.pdf")
                break


# ---------------------------------------------------------------- règles logicielles (L, et firmware E)

def regles_logicielles(res: Resultat, l: Ligne):
    p = res.produit
    if l.get("logiciel_produit"):
        try:
            r = endoflife.analyser(str(l.get("logiciel_produit")), str(l.get("logiciel_version", "")), res._cache)
            if r.get("trouve") and r.get("eol"):
                _echeance(res, l, f"Fin de vie {l.get('logiciel_produit')} {r['cycle']}", r["eol"], "endoflife.date")
            if not r["trouve"]:
                res.avertissements.append(
                    f"{l.libelle} : '{l.get('logiciel_produit')}' version '{l.get('logiciel_version')}' "
                    f"introuvable sur endoflife.date ({r.get('url')}).")
            elif r["deja_eol"]:
                _ajouter(res, l, "D1", 3, f"Cycle {r['cycle']} déjà en fin de vie"
                         + (f" depuis le {r['eol']:%d/%m/%Y}" if r.get("eol") else "")
                         + f" (dernier cycle : {r['dernier_cycle']}).", r["url"], True)
            elif r.get("eol"):
                expo = _expo_date(r["eol"], p)
                prevue = oui(l.get("mise_a_jour_prevue"))
                if expo and prevue:
                    expo = 1  # chemin de mise à jour organisé : le risque devient un suivi
                if expo:
                    _ajouter(res, l, "D1", expo, f"Fin de vie du cycle {r['cycle']} le {r['eol']:%d/%m/%Y}, "
                             f"avant l'horizon produit ({p.horizon:%d/%m/%Y})"
                             + (" ; montée de version prévue." if prevue else "."), r["url"], True)
        except ErreurSource as e:
            res.avertissements.append(f"{l.libelle} : endoflife.date indisponible ({e})")

    depot = l.get("depot")
    if l.get("ecosysteme") and l.get("paquet"):
        try:
            r = depsdev.analyser(str(l.get("ecosysteme")), str(l.get("paquet")),
                                 str(l.get("paquet_version")) or None, res._cache)
            if not r.get("trouve"):
                res.avertissements.append(f"{l.libelle} : paquet introuvable sur deps.dev "
                                          f"({r.get('erreur') or r.get('url')}).")
            else:
                if r.get("deprecie"):
                    _ajouter(res, l, "D2", 3, f"Paquet déprécié : {r.get('raison_depreciation') or 'sans motif'}.",
                             r["url"], True)
                if r.get("nb_avis_securite"):
                    _ajouter(res, l, "D2", 2, f"{r['nb_avis_securite']} avis de sécurité sur la version "
                             f"{r['version']} ({', '.join(r['avis_securite'])}).", r["url"], True)
                jours = r.get("jours_depuis_publication")
                if jours is not None and jours > 730:
                    _ajouter(res, l, "D6", 2 if jours > 1460 else 1,
                             f"Dernière publication le {r['derniere_publication']} ({jours // 365} ans).",
                             r["url"], True)
                depot = depot or r.get("depot")
        except ErreurSource as e:
            res.avertissements.append(f"{l.libelle} : deps.dev indisponible ({e})")

    if depot:
        try:
            s = scorecard.analyser(str(depot), res._cache)
            if s.get("trouve") and s.get("maintenu_score") is not None:
                m = s["maintenu_score"]
                expo = 3 if m <= 0 else 2 if m < 5 else 1 if m < 8 else 0
                _ajouter(res, l, "D3", expo, f"OpenSSF Scorecard « Maintained » = {m}/10 "
                         f"({s['maintenu_raison']}) ; score global {s['score_global']}/10.", s["url"], True)
            elif s.get("erreur"):
                res.avertissements.append(f"{l.libelle} : {s['erreur']}")
        except ErreurSource as e:
            res.avertissements.append(f"{l.libelle} : OpenSSF Scorecard indisponible ({e})")

    if oui(l.get("dependance_cloud")):
        local = oui(l.get("mode_local"))
        _ajouter(res, l, "D4", 1 if local else 3,
                 "Dépend d'un service distant" + (" ; un mode local existe." if local else
                                                  " sans mode de fonctionnement local."))
    fin = date_iso(l.get("date_fin_support"))
    _echeance(res, l, "Fin de support déclarée", fin, "saisie nomenclature")
    if fin:
        expo = _expo_date(fin, p)
        if expo:
            _ajouter(res, l, "D5", expo, f"Fin de support déclarée le {fin:%d/%m/%Y} "
                     f"(horizon produit {p.horizon:%d/%m/%Y}).", "saisie nomenclature")


def analyser(lignes: list[Ligne], produit: Produit, cache: Cache, ords_csv: str | None = None) -> Resultat:
    res = Resultat(produit=produit, lignes=lignes)
    res._cache = cache  # type: ignore[attr-defined]
    for l in lignes:
        if l.domaine in ("M", "E"):
            regles_physiques(res, l)
        if l.domaine == "L" or l.get("logiciel_produit") or l.get("paquet") or l.get("depot") \
                or l.get("dependance_cloud") or l.get("date_fin_support"):
            regles_logicielles(res, l)
        if l.domaine == "?":
            res.avertissements.append(f"{l.libelle} : domaine non reconnu (M, E ou L attendu).")
    if ords_csv and produit.categorie_ords:
        from .sources import ords
        res.ords = ords.analyser(ords_csv, produit.categorie_ords)
        _rapprocher_ords(res)
    return res


def _rapprocher_ords(res: Resultat):
    """Signale les lignes de nomenclature qui correspondent aux pannes les plus fréquentes."""
    if not res.ords or not res.ords.get("trouve"):
        return
    from .sources.ords import SOUS_ENSEMBLES, _sans_accent
    frequents = {nom: pct for nom, _, pct in res.ords["sous_ensembles"] if pct >= 5}
    for l in res.lignes:
        texte = " " + _sans_accent(str(l.get("designation"))) + " "
        for nom, pct in frequents.items():
            if any(_sans_accent(m) in texte for m in SOUS_ENSEMBLES[nom]):
                expo = 3 if pct >= 20 else 2 if pct >= 10 else 1
                _ajouter(res, l, "A3", expo,
                         f"« {nom} » cité dans {pct} % des réparations de la catégorie "
                         f"« {res.ords['categorie']} » (Open Repair, {res.ords['nb_reparations']} cas).",
                         "https://openrepair.org/open-data/downloads/", True)
                break


def synthese(res: Resultat) -> dict:
    """Agrégats par famille et domaine + indice de pérennité (100 = aucun risque détecté)."""
    par_famille, par_domaine = {}, {}
    for c in res.constats:
        for d, cle in ((par_famille, c.famille), (par_domaine, c.ligne.domaine)):
            e = d.setdefault(cle, {"nb": 0, "somme": 0, "max": 0, "critiques": 0})
            e["nb"] += 1
            e["somme"] += c.criticite
            e["max"] = max(e["max"], c.criticite)
            e["critiques"] += c.criticite >= 6
    # indice par ligne : on retient la criticité maximale de chaque ligne
    max_par_ligne = {}
    for c in res.constats:
        max_par_ligne[c.ligne.numero] = max(max_par_ligne.get(c.ligne.numero, 0), c.criticite)
    n = len(res.lignes) or 1
    indice = round(100 * (1 - sum(max_par_ligne.values()) / (9 * n)))
    return {"par_famille": par_famille, "par_domaine": par_domaine, "indice": indice,
            "lignes_critiques": sum(v >= 6 for v in max_par_ligne.values()),
            "lignes_a_surveiller": sum(3 <= v < 6 for v in max_par_ligne.values())}
