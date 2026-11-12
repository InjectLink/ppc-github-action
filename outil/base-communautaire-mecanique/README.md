# Base communautaire d'obsolescence mécanique (amorce)

L'état de l'art PPC a relevé un manque : il existe des bases ouvertes pour l'arrêt des composants électroniques (statuts de cycle de vie des distributeurs) et des logiciels (endoflife.date, deps.dev), mais aucune base ouverte ne recense l'arrêt des **pièces mécaniques** (pièces injectées, moulées, usinées sur mesure, ressorts, engrenages, charnières, joints...).

Ce fichier CSV est une amorce. Chacun peut y signaler une pièce devenue introuvable et, si possible, un moyen de la contourner.

## Fichier

`obsolescence_mecanique.csv` : séparateur `;`, encodage UTF-8. Les deux lignes `EXEMPLE-*` sont fictives et servent seulement à montrer le format.

| Colonne | Contenu |
|---|---|
| id_fiche | Identifiant unique (ex. PPC-M-0001) |
| date_signalement | AAAA-MM-JJ |
| categorie_produit | Catégorie, si possible celle d'Open Repair (ORDS) |
| produit_marque_modele | Produit concerné |
| piece_designation, reference_piece | Pièce concernée |
| type_piece | `specifique` (propre au produit) ou `standard` (normalisée, catalogue) |
| fabricant_piece | Fabricant d'origine |
| procede_fabrication | Injection, fonderie, emboutissage, usinage, frittage... |
| outillage_specifique | `moule`, `matrice`, `gabarit`, `non` |
| nb_sources_connues | Nombre de fournisseurs connus |
| statut_disponibilite | `disponible`, `rare`, `indisponible` |
| date_arret_constatee | AAAA-MM si connue |
| preuve_url | Lien public : catalogue, réponse du service après-vente, forum de réparation |
| cause_arret | Fin de gamme, faillite, moule détruit, changement de fournisseur... |
| contournement | Impression 3D, pièce d'un autre modèle, usinage, pièce standard équivalente |
| fichier_contournement_url, licence_fichier | Fichier STL/STEP et sa licence (CC BY-SA 4.0, CC0...) |
| norme_equivalente | Norme ISO/DIN/EN de la pièce standard équivalente |
| remarques, contributeur | Texte libre, pseudonyme |

## Règles de contribution

1. Ne signaler que des faits vérifiables, avec un lien public quand c'est possible.
2. Ne déposer que des fichiers de contournement dont vous avez les droits, sous licence libre.
3. Pas de données personnelles.

## Usage avec le radar

Les fiches `specifique` + `moule` + `nb_sources_connues = 1` correspondent aux règles B2 et B3 du radar d'obsolescence. Elles servent à repérer, dès la conception, les pièces qui ont déjà posé problème dans des produits comparables.

## Pistes d'évolution

- Passer du CSV à un formulaire de contribution et à une base partagée (Wikidata, ou une instance libre comme NocoDB ou Baserow).
- Faire le lien avec les plateformes de pièces à imprimer (Printables, Thingiverse) et les données d'Open Repair.
