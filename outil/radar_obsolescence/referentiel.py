"""Référentiel PPC des familles de causes d'obsolescence et des règles d'évaluation.

Les familles reprennent la taxonomie de l'état de l'art PPC
(causes-obsolescence-etat-de-l-art.md, section 2).
"""

FAMILLES = {
    "A": "Défaillance physique (usure, casse, panne, maturité)",
    "B": "Disponibilité / approvisionnement (DMSMS, fournisseurs, pièces)",
    "C": "Compatibilité / interopérabilité",
    "D": "Sécurité et support logiciel (fin de vie, dépendances, cloud)",
    "E": "Réglementaire",
    "F": "Technologique / performance",
    "G": "Économique (coût de réparation, d'usage)",
    "H": "Psychologique / usage",
    "I": "Intentionnelle (verrous, appairage, limitations artificielles)",
}

DOMAINES = {"M": "Mécanique", "E": "Électronique", "L": "Logiciel"}

# Criticité = exposition (0-3) x gravité (1-3) -> 0 à 9
SEUILS = [
    (6, "CRITIQUE"),
    (3, "A SURVEILLER"),
    (1, "FAIBLE"),
    (0, "MAITRISE"),
]


def niveau(criticite: int) -> str:
    for seuil, libelle in SEUILS:
        if criticite >= seuil:
            return libelle
    return "MAITRISE"


# Catalogue des règles : code -> (famille, intitulé, recommandation de conception)
REGLES = {
    "A1": ("A", "Pièce d'usure non remplaçable par l'utilisateur",
           "Rendre la pièce d'usure accessible et remplaçable sans outil spécifique "
           "(connecteur, support, fixation réversible) ; privilégier une référence standard "
           "et surdimensionner (déclassement thermique/électrique, cycles)."),
    "A2": ("A", "Pièce d'usure difficile d'accès (nombre d'étapes de démontage élevé)",
           "Réduire le nombre d'étapes d'accès (Disassembly Map) : placer les pièces d'usure "
           "en périphérie, fixations réversibles."),
    "A3": ("A", "Point faible connu de la catégorie de produit (données de réparation)",
           "Surdimensionner ou rendre remplaçable ce sous-ensemble ; prévoir le diagnostic."),
    "B1": ("B", "Composant en fin de vie ou statut de cycle de vie défavorable",
           "Rechercher une référence de remplacement compatible broche à broche, planifier un "
           "dernier achat (LTB) ou une refonte ; surveiller les avis J-STD-048."),
    "B2": ("B", "Source unique ou nombre de sources insuffisant",
           "Qualifier une seconde source ; concevoir l'empreinte pour accepter plusieurs références."),
    "B3": ("B", "Pièce spécifique (outillage, moule, composant sur mesure)",
           "Publier ou conserver les plans (STEP, schémas), sécuriser la propriété des outillages, "
           "prévoir une alternative standard ou imprimable."),
    "B4": ("B", "Disponibilité des pièces détachées inférieure à la durée de vie cible",
           "Allonger l'engagement de disponibilité ou ouvrir les fichiers de fabrication."),
    "B5": ("B", "Statut de cycle de vie inconnu (donnée manquante)",
           "Renseigner la référence fabricant et vérifier le statut (Mouser, DigiKey, Nexar ou site du fabricant)."),
    "C1": ("C", "Interface ou connectique non standard",
           "Utiliser des interfaces normalisées et documentées (USB-C, protocoles ouverts)."),
    "C2": ("C", "Technologie de réseau en cours d'arrêt (2G, 3G...)",
           "Passer à une technologie pérenne (LTE-M, NB-IoT, 4G/5G) ou rendre le module radio "
           "remplaçable sur connecteur standard (M.2, mini-PCIe)."),
    "D1": ("D", "Logiciel dont la fin de vie survient avant l'horizon du produit",
           "Choisir une version LTS couvrant la durée de support, prévoir la montée de version "
           "et la marge mémoire nécessaire."),
    "D2": ("D", "Paquet logiciel déprécié ou avec vulnérabilités connues",
           "Remplacer la dépendance ; suivre les avis de sécurité via une SBOM (Dependency-Track)."),
    "D3": ("D", "Projet open source peu ou pas maintenu",
           "Évaluer un fork, une alternative maintenue, ou internaliser la maintenance."),
    "D4": ("D", "Fonction dépendante d'un service distant (cloud)",
           "Garantir un mode de fonctionnement local et un plan de sortie (API ouverte, "
           "firmware alternatif, transfert des clés)."),
    "D5": ("D", "Date de fin de support déclarée avant l'horizon du produit",
           "Négocier un support étendu, choisir une alternative, ou documenter la sortie de support."),
    "D6": ("D", "Paquet sans publication récente",
           "Vérifier l'activité du projet ; prévoir une alternative si l'abandon se confirme."),
}

STATUTS_CYCLE_VIE = {
    # statut normalisé -> exposition
    "ACTIF": 0,
    "ACTIVE": 0,
    "PRODUCTION": 0,
    "NOUVEAU": 1,          # produit jeune : risque de maturité / d'arrêt précoce
    "NEW": 1,
    "NRND": 2,             # Not Recommended for New Design
    "LTB": 3,              # Last Time Buy annoncé
    "EOL": 3,
    "OBSOLETE": 3,
    "DISCONTINUED": 3,
    "ARRET_DISTRIBUTEUR": 1,  # retiré du catalogue d'un distributeur, pas forcément du fabricant
    "INCONNU": None,       # traité par la règle B5
    "": None,
}


# Technologies de réseau dont l'arrêt est engagé en Europe (cf. observatoire Arcep 2G/3G)
RESEAUX_EN_ARRET = {
    "2g": "2G", "gsm": "2G (GSM)", "gprs": "2G (GPRS)",
    "3g": "3G", "umts": "3G (UMTS)", "hspa": "3G (HSPA)", "wcdma": "3G (WCDMA)",
}
