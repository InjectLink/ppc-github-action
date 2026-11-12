"""Interface en ligne de commande.

Exemples :
    python -m radar_obsolescence exemples/nomenclature_exemple.csv -p exemples/produit_exemple.json
    python -m radar_obsolescence ma_bom.xlsx -p produit.json --ords OpenRepairData.csv -o resultats/
    python -m radar_obsolescence --categories-ords OpenRepairData.csv
    python radar.py Classeur.xlsx --carte etapes_par_composant.csv
    python radar.py Classeur.xlsx --onglet "Nomenclature améliorée" -o resultats_ameliore
    python -m radar_obsolescence --modele Classeur.xlsx [--exemple]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyse import analyser, etat_sources_composants, synthese
from .nomenclature import charger_nomenclature, charger_produit, importer_carte_demontage
from .rapport import ecrire_csv, ecrire_json, ecrire_markdown, ecrire_xlsx
from .visualiseur import ecrire_visualiseur
from .sources import Cache


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="radar_obsolescence",
                                 description="Radar d'obsolescence PPC : croise une nomenclature "
                                             "mécanique / électronique / logicielle avec des sources "
                                             "ouvertes de signaux d'obsolescence.")
    ap.add_argument("nomenclature", nargs="?",
                    help="Classeur XLSX du kit (onglets Produit et Nomenclature) ou nomenclature CSV/XLSX")
    ap.add_argument("-p", "--produit", help="Fiche produit JSON ; inutile si le classeur contient l'onglet Produit")
    ap.add_argument("--carte", metavar="CSV",
                    help="etapes_par_composant.csv du générateur de cartographie de démontage (GT1) : "
                         "complète le nombre d'étapes de démontage")
    ap.add_argument("--scenario", help="Colonne d'étapes à reprendre de la carte (ex. Actuel, Amélioré ; défaut : la première)")
    ap.add_argument("-o", "--sortie", default="resultats", help="Dossier de sortie (défaut : resultats)")
    ap.add_argument("--ords", help="CSV Open Repair Alliance (optionnel)")
    ap.add_argument("--categories-ords", metavar="CSV", help="Lister les catégories d'un CSV ORDS et quitter")
    ap.add_argument("--onglet", help="Onglet de nomenclature à analyser dans le classeur (défaut : Nomenclature)")
    ap.add_argument("--modele", metavar="XLSX", help="Générer le classeur de saisie du kit (vide) et quitter")
    ap.add_argument("--exemple", action="store_true", help="Avec --modele : remplir le classeur avec l'exemple du thermostat")
    ap.add_argument("--hors-ligne", action="store_true", help="N'utiliser que le cache local")
    ap.add_argument("--cache", default=".cache_radar", help="Dossier du cache (défaut : .cache_radar)")
    ap.add_argument("--verifier-sources", action="store_true",
                    help="Vérifier la configuration des sources de composants (un appel de test par source) et quitter")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    if args.modele:
        from .classeur import generer
        generer(args.modele, exemple=args.exemple)
        print(f"Classeur de saisie créé : {args.modele}" + (" (exemple du thermostat)" if args.exemple else ""))
        return 0
    if args.categories_ords:
        from .sources import ords
        for nom, n in ords.categories(args.categories_ords):
            print(f"{n:>8}  {nom}")
        return 0
    if args.verifier_sources:
        return verifier_sources()
    if not args.nomenclature:
        ap.error("indiquez un fichier de nomenclature")

    print(f"Radar d'obsolescence PPC {__version__}")
    for nom, actif, variables in etat_sources_composants():
        print(f"Source {nom} : " + ("configurée" if actif else f"non configurée (variables : {variables})"))
    lignes = charger_nomenclature(args.nomenclature, args.onglet)
    if not lignes:
        print("Aucune ligne de nomenclature trouvée : remplissez l'onglet Nomenclature (au moins Repère et Désignation).")
        return 1
    source_produit = args.produit
    if not source_produit and str(args.nomenclature).lower().endswith((".xlsx", ".xlsm")):
        source_produit = args.nomenclature  # onglet « Produit » du classeur, s'il existe
    produit = charger_produit(source_produit)
    avertissements_carte = []
    if args.carte:
        n, avertissements_carte = importer_carte_demontage(lignes, args.carte, args.scenario)
        print(f"Carte de démontage : {n} ligne(s) complétée(s) avec le nombre d'étapes.")
    cache = Cache(args.cache, hors_ligne=args.hors_ligne)
    res = analyser(lignes, produit, cache, ords_csv=args.ords)
    res.avertissements[:0] = avertissements_carte

    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    ecrire_markdown(res, sortie / "rapport_obsolescence.md")
    ecrire_csv(res, sortie / "constats.csv")
    ecrire_json(res, sortie / "resume.json")
    xlsx = ecrire_xlsx(res, sortie / "constats.xlsx")
    ecrire_visualiseur(res, sortie / "visualiseur.html", Path(args.nomenclature).name
                       + (f" : onglet {nom_onglet(args.nomenclature, args.onglet)}" if args.onglet else ""))

    s = synthese(res)
    print(f"{produit.nom} : indice de pérennité {s['indice']}/100 : "
          f"{s['lignes_critiques']} ligne(s) critique(s), {s['lignes_a_surveiller']} à surveiller, "
          f"{len(res.avertissements)} avertissement(s).")
    print(f"Résultats : {sortie}/visualiseur.html, rapport_obsolescence.md, constats.csv, resume.json"
          + (", constats.xlsx" if xlsx else ""))
    return 0


def nom_onglet(chemin, onglet: str) -> str:
    """Nom exact de l'onglet (l'option --onglet tolère casse et accents)."""
    from .nomenclature import _cle, onglets_xlsx
    try:
        return next((n for n in onglets_xlsx(chemin) if _cle(n) == _cle(onglet)), onglet)
    except Exception:
        return onglet


def verifier_sources(mpn: str = "STM32F103C8T6") -> int:
    """Un appel de test par source configurée, sans cache. Nexar n'est pas appelé (quota de 10 pièces)."""
    from .sources import ErreurSource, digikey, mouser
    from .sources import _SansCache
    ok = True
    for nom, actif, variables in etat_sources_composants():
        if not actif:
            print(f"{nom} : non configurée (variables : {variables})")
            continue
        if nom == "Nexar/Octopart":
            print(f"{nom} : configurée (non testée pour préserver le quota)")
            continue
        module = digikey if nom == "DigiKey" else mouser
        try:
            r = module.analyser(mpn, _SansCache())
        except ErreurSource as e:
            ok = False
            print(f"{nom} : ERREUR {e}")
            continue
        except KeyError as e:
            ok = False
            print(f"{nom} : ERREUR réponse inattendue (champ {e} absent)")
            continue
        if r.get("trouve"):
            print(f"{nom} : OK : {r.get('mpn')} : {r.get('statut')} (libellé : {r.get('statut_brut')}"
                  + (f", via {r['origine']}" if r.get("origine") else "") + ")")
        else:
            print(f"{nom} : connectée, mais {mpn} introuvable"
                  + (f" : {r['motif']}" if r.get("motif") else "")
                  + (f" ; références proches : {', '.join(r['proches'])}" if r.get("proches") else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
