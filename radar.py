"""Lanceur du radar d'obsolescence PPC depuis le dossier du kit.

    python radar.py MonClasseur.xlsx                     analyse l'onglet Nomenclature
    python radar.py MonClasseur.xlsx --onglet "Nomenclature améliorée" -o resultats_ameliore
    python radar.py MonClasseur.xlsx --carte etapes_par_composant.csv --scenario Actuel
    python radar.py --modele MonClasseur.xlsx            crée un classeur vide
    python radar.py --verifier-sources                   teste les clés Mouser / DigiKey
    python radar.py --help                               toutes les options
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "outil"))

from radar_obsolescence.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
