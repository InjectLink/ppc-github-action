# Radar d'obsolescence PPC

Outil libre (licence MIT) de l'association [PPC (Pérennité Programmée Circulaire)](https://www.perennite-programmee-circulaire.org/). Il croise la **nomenclature mécanique, électronique et logicielle** d'un produit avec des **sources ouvertes de signaux d'obsolescence**. Il produit ensuite un rapport priorisé et des recommandations de conception.

Il complète le guide et l'outil Disassembly Map de PPC (méthode De Fazio et al., 2021) : le nombre d'étapes de démontage issu de la carte de démontage sert à juger si une pièce d'usure reste accessible. Les familles de causes reprennent la taxonomie de l'état de l'art PPC ([causes-obsolescence-etat-de-l-art.md](../causes-obsolescence-etat-de-l-art.md)).

## Ce que fait l'outil

| Domaine | Signaux vérifiés | Source |
|---|---|---|
| Mécanique | Pièce d'usure non remplaçable ou difficile d'accès, source unique, pièce spécifique (moule, outillage), pièces détachées disponibles moins longtemps que la durée de vie visée, interface propriétaire | Déclaratif (nomenclature) |
| Électronique | Statut de cycle de vie (NRND, LTB, EOL...), source unique, réseau 2G/3G en cours d'arrêt, pièce d'usure (condensateur, relais, batterie) | Déclaratif, plus les API gratuites de [Mouser](https://www.mouser.com/en/api-search/) et [DigiKey](https://developer.digikey.com/) en option (et Nexar/Octopart) |
| Logiciel | Fin de vie de l'OS, du langage ou de la bibliothèque avant l'horizon du produit | [endoflife.date](https://endoflife.date) |
| Logiciel | Paquet déprécié, avis de sécurité, absence de publication récente | [deps.dev](https://deps.dev) |
| Logiciel | Projet open source peu ou pas maintenu | [OpenSSF Scorecard](https://scorecard.dev) |
| Logiciel | Dépendance à un service distant sans mode local, fin de support déclarée trop tôt | Déclaratif |
| Tous | Sous-ensembles qui tombent souvent en panne dans la catégorie de produit | [Open Repair Alliance](https://openrepair.org/open-data/) (option) |

## Installation

Python 3.9 ou plus récent. Aucune dépendance n'est obligatoire. Le module `openpyxl` sert à lire et écrire les fichiers Excel.

```bash
pip install openpyxl          # optionnel, pour les fichiers .xlsx
pip install truststore        # conseillé sous Windows : utilise les certificats du système
pip install .                 # optionnel, installe la commande « radar-obsolescence »
```

## Utilisation

```bash
# Exemple fourni : thermostat connecté, avec le nombre d'étapes repris de sa carte de démontage
python -m radar_obsolescence exemples/nomenclature_exemple.csv -p exemples/produit_exemple.json \
       --carte exemples/etapes_par_composant.csv --scenario Actuel -o resultats

# Générer le classeur de saisie (vide, ou rempli avec l'exemple)
python -m radar_obsolescence --modele mon_classeur.xlsx
python -m radar_obsolescence --modele classeur_exemple.xlsx --exemple

# Analyser un classeur : la fiche produit est lue dans l'onglet Produit
python -m radar_obsolescence mon_classeur.xlsx -o resultats
python -m radar_obsolescence mon_classeur.xlsx --onglet "Nomenclature améliorée" -o resultats_ameliore

# Ajouter les données de réparation Open Repair
python -m radar_obsolescence --categories-ords OpenRepairData_v0.3.csv     # lister les catégories
python -m radar_obsolescence ma_nomenclature.xlsx -p produit.json --ords OpenRepairData_v0.3.csv

# Relancer sans réseau (cache local, valable 7 jours)
python -m radar_obsolescence ma_nomenclature.xlsx -p produit.json --hors-ligne
```

Résultats dans le dossier de sortie :

- `visualiseur.html` : page autonome (sans connexion internet) à six vues : Synthèse (indice, matrice famille × domaine), Radar (exposition par famille de causes), Frise des échéances, Constats filtrables, Composants (cycle de vie), Fichiers ;
- `rapport_obsolescence.md` : synthèse, indice de pérennité, constats par niveau, recommandations par pièce, sources ;
- `constats.csv` : séparateur `;`, s'ouvre directement dans Excel ou LibreOffice ;
- `constats.xlsx` : onglets Constats (filtrable, couleurs par niveau) et Synthese.

## Lien avec la cartographie de démontage (kit GT1)

Le générateur de cartographie de démontage PPC (`carto_demontage.py`, kit GT1) écrit `etapes_par_composant.csv` (`Réf.;Composant;Cible;Étapes (Actuel);Étapes (Amélioré)`). L'option `--carte` reprend ce fichier : chaque ligne de la nomenclature est rapprochée par sa colonne `ref_demontage`, sinon par une désignation identique, et `--scenario` choisit la colonne d'étapes (première par défaut). Une valeur déjà saisie dans `etapes_demontage` est conservée. Le rapport indique pour chaque constat d'accessibilité que le nombre d'étapes vient de la carte.

## Fiche produit (JSON)

```json
{
  "nom": "Thermostat connecté",
  "date_mise_marche": "2026-01-15",
  "duree_vie_cible_ans": 15,
  "duree_support_annoncee_ans": 7,
  "categorie_ords": "Small home electrical"
}
```

L'**horizon** du produit est égal à la date de mise sur le marché plus la durée de vie visée. La **fin de support annoncée** est égale à la date de mise sur le marché plus la durée de support annoncée. Une échéance (fin de vie d'un logiciel, fin d'un service) qui tombe avant la fin de support annoncée est critique. Si elle tombe seulement avant l'horizon, elle est à surveiller.

## Nomenclature

Fichier CSV (séparateur `;` ou `,`, détecté automatiquement) ou classeur XLSX, une ligne par pièce, composant ou brique logicielle. Les colonnes vides sont permises. Seules `id`, `designation` et `domaine` sont nécessaires. Dans un classeur, l'onglet lu est « Nomenclature » (ou celui indiqué par `--onglet`) ; la ligne d'en-tête est détectée automatiquement et accepte les noms techniques ci-dessous comme les libellés lisibles du classeur du kit (« Repère », « Gravité de la fonction (1 à 3) »...). L'onglet « Colonnes » du classeur décrit chaque colonne. Certains en-têtes courants sont aussi reconnus (`Ref`, `Description`, `MPN`...).

| Colonne | Domaines | Valeurs |
|---|---|---|
| id, designation, domaine | tous | domaine : `M`, `E` ou `L` |
| fonction_critique | tous | gravité 1 (confort), 2 (importante, défaut), 3 (essentielle) |
| fabricant, reference_fabricant, fournisseur, nb_sources | M, E | texte, entier |
| statut_cycle_vie | E | ACTIF, NOUVEAU, NRND, LTB, EOL, OBSOLETE, INCONNU |
| piece_specifique, plans_ouverts, piece_usure, remplacable_utilisateur, interface_standard | M, E | oui / non |
| ref_demontage | M, E | repère « Réf. » du composant dans la cartographie de démontage |
| etapes_demontage | M, E | entier, issu de la Disassembly Map (saisi, ou importé avec `--carte`) |
| disponibilite_pieces_ans | M, E | années |
| logiciel_produit, logiciel_version | L | identifiant [endoflife.date](https://endoflife.date/docs/api) (debian, python, nodejs, openssl...) et cycle |
| mise_a_jour_prevue | L | oui / non : une montée de version est organisée avant la fin de vie ; la fin de vie avant l'horizon devient alors un simple suivi |
| ecosysteme, paquet, paquet_version | L | npm, pypi, cargo, maven, go, nuget |
| depot | L | URL GitHub ou GitLab |
| dependance_cloud, mode_local | L, E | oui / non |
| date_fin_support | L, E | AAAA-MM-JJ |

## Méthode de cotation

Chaque constat a une **exposition** de 0 à 3 (probabilité ou proximité de l'obsolescence). Elle est multipliée par la **gravité** de la ligne (1 à 3) pour donner une **criticité** de 0 à 9 :

| Criticité | Niveau |
|---|---|
| 6 à 9 | CRITIQUE |
| 3 à 5 | A SURVEILLER |
| 1 à 2 | FAIBLE |
| 0 | MAITRISE |

**Indice de pérennité** = 100 × (1 − somme des criticités maximales par ligne / (9 × nombre de lignes)). 100 signifie qu'aucun signal n'a été détecté. L'indice sert à suivre les progrès d'une même conception d'une version à l'autre. Il ne sert pas à comparer des produits différents.

### Règles

| Code | Famille | Constat | Exposition |
|---|---|---|---|
| A1 | A Défaillance | Pièce d'usure non remplaçable par l'utilisateur | 3 (1 si non renseigné) |
| A2 | A Défaillance | Pièce d'usure à plus de 5 étapes de démontage | 2, ou 3 au-delà de 10 étapes |
| A3 | A Défaillance | Sous-ensemble souvent en panne dans la catégorie (Open Repair) | 1 à 3 selon la part des pannes (5 %, 10 %, 20 %) |
| B1 | B Approvisionnement | Statut de cycle de vie défavorable | NOUVEAU 1, retiré chez un distributeur 1, NRND 2, LTB/EOL/OBSOLETE 3 |
| B2 | B Approvisionnement | Source unique ou double | 1 source : 2, ou 3 si la pièce est spécifique ; 2 sources : 1 |
| B3 | B Approvisionnement | Pièce spécifique | 2, ou 1 si les plans sont ouverts |
| B4 | B Approvisionnement | Pièces détachées disponibles moins longtemps que la durée de vie visée | 2, ou 3 pour une pièce d'usure |
| B5 | B Approvisionnement | Statut de cycle de vie électronique inconnu | 1 |
| C1 | C Compatibilité | Interface propriétaire | 2 |
| C2 | C Compatibilité | Réseau 2G/3G | 3 |
| D1 | D Support logiciel | Fin de vie (endoflife.date) avant l'horizon | 3 si déjà atteinte ou avant la fin de support, sinon 2 ; 1 si une montée de version est prévue (`mise_a_jour_prevue`) et la fin de vie pas encore atteinte |
| D2 | D Support logiciel | Paquet déprécié ou avec avis de sécurité (deps.dev) | 3 / 2 |
| D3 | D Support logiciel | Score « Maintained » d'OpenSSF Scorecard | 0/10 : 3 ; moins de 5 : 2 ; moins de 8 : 1 |
| D4 | D Support logiciel | Dépendance cloud | 3 sans mode local, 1 avec |
| D5 | D Support logiciel | Fin de support déclarée avant l'horizon | même logique que D1 |
| D6 | D Support logiciel | Dernière publication du paquet | plus de 2 ans : 1 ; plus de 4 ans : 2 |

Les familles E à I de la taxonomie (réglementaire, technologique, économique, psychologique, intentionnelle) ne sont pas encore automatisées. Elles relèvent de la grille d'analyse qualitative. Contributions bienvenues.

## Sources externes et options

- **endoflife.date, deps.dev, OpenSSF Scorecard** : API publiques sans clé. Les réponses sont gardées en cache 7 jours dans `.cache_radar/`.
- **Statut de cycle de vie des composants électroniques** (option) : l'outil interroge, dans l'ordre, Mouser, DigiKey puis Nexar, selon les identifiants configurés. La première source qui donne un statut connu pour la **référence exacte** l'emporte. Sinon, le statut saisi dans la nomenclature est conservé et les références proches sont signalées. Voir la section « Configurer les sources de composants ».
- **OSV.dev** (piste d'évolution, non intégrée) : base ouverte de vulnérabilités avec API sans clé ([osv.dev](https://osv.dev/)), utile pour compléter la famille D.
- **Open Repair Alliance** (option) : le jeu de données ouvert (licence CC BY-SA 4.0, format ORDS) se télécharge depuis la [page de téléchargement d'openrepair.org](https://openrepair.org/open-data/downloads/). Il comptait 416 282 réparations d'équipements électriques et électroniques et 203 591 hors EEE lors de la vérification du 6 novembre 2026. Indiquez le chemin du fichier CSV avec `--ords` et la catégorie dans la fiche produit (`categorie_ords`). Les pannes sont rapprochées des lignes de la nomenclature par mots-clés multilingues (moteur, batterie, interrupteur, charnière...).

## Configurer les sources de composants

Les deux sources recommandées sont gratuites et offrent chacune 1 000 appels par jour. Une seule suffit ; avec les deux, la seconde complète la première quand elle ne connaît pas une référence.

### Mouser (le plus simple : une clé, délivrée immédiatement)

1. Créer un compte « My Mouser » sur [mouser.fr](https://www.mouser.fr) ou se connecter.
2. Remplir le formulaire de la [page Search API](https://www.mouser.com/en/api-search/). La clé arrive par e-mail ; l'accès est annoncé comme immédiat.
3. Déclarer la clé dans la variable `MOUSER_API_KEY`.

Ce que donne Mouser : statut de cycle de vie (`LifecycleStatus`, par exemple « End of Life », « Not Recommended for New Designs »), indicateur d'arrêt (`IsDiscontinued`), **remplacement suggéré** (`SuggestedReplacement`) et stock. Limites annoncées : 30 appels par minute (l'outil espace ses appels de 2 secondes) et 1 000 par jour.

### DigiKey (plus long à obtenir, donne la date de dernière commande)

1. Créer un compte « My DigiKey » sur [digikey.fr](https://www.digikey.fr) et noter son numéro de compte client.
2. Sur [developer.digikey.com](https://developer.digikey.com/), se connecter avec ce compte, puis ouvrir **Organizations** et créer une organisation (par exemple au nom de l'association).
3. Dans l'organisation, ouvrir **Production Apps** (sous « Operations ») puis **Create Production App** ([documentation DigiKey](https://developer.digikey.com/tutorials-and-resources/organization-and-production)). Cocher le produit **Product Information V4**. L'adresse de rappel (« callback ») n'est pas utilisée par l'outil : `https://localhost` convient.
4. Une fois l'application validée, copier le **Client ID** et le **Client Secret** affichés sur sa page.
5. Déclarer `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET` et, si l'API répond par une erreur d'authentification ou de compte, `DIGIKEY_ACCOUNT_ID` (numéro de compte client, demandé par la documentation pour ce mode d'accès).

Attention : une application « sandbox » (personnelle) ne renvoie pas les vraies données ; il faut une « Production App ». Ce que donne DigiKey : statut (`Active`, `Obsolete`, `Last Time Buy`, `Not For New Designs`, `Discontinued at Digi-Key`, `Preliminary`), **date de dernière commande** (`DateLastBuyChance`) et stock. DigiKey ne fait pas de prévision. Quota : 120 requêtes par minute et 1 000 par jour ([documentation](https://developer.digikey.com/documentation)). Variables facultatives : `DIGIKEY_SITE` (défaut `FR`), `DIGIKEY_DEVISE` (défaut `EUR`).

### Déclarer les variables

Sous Windows (PowerShell), pour la session en cours :

```powershell
$env:MOUSER_API_KEY = "votre-cle"
$env:DIGIKEY_CLIENT_ID = "votre-client-id"
$env:DIGIKEY_CLIENT_SECRET = "votre-client-secret"
python -m radar_obsolescence exemples\nomenclature_exemple.csv -p exemples\produit_exemple.json
```

Sous Linux ou macOS :

```bash
export MOUSER_API_KEY="votre-cle"
python -m radar_obsolescence exemples/nomenclature_exemple.csv -p exemples/produit_exemple.json
```

Sous l'invite de commandes classique (cmd.exe), la syntaxe `$env:` ne fonctionne pas ; utiliser `set DIGIKEY_CLIENT_ID=votre-client-id` (sans guillemets ni espaces autour du signe égal). Dans les deux cas, les variables ne valent que pour la fenêtre où elles ont été déclarées : lancer le radar dans cette même fenêtre.

### Vérifier la configuration avant l'analyse

```powershell
python -m radar_obsolescence --verifier-sources
```

La commande indique pour chaque source si elle est configurée, puis fait un appel de test sur le STM32F103C8T6 (sans cache). Exemple de réponse attendue : `DigiKey : OK : STM32F103C8T6 : PRODUCTION`. Une réponse `ERREUR HTTP 401 sur https://api.digikey.com/v1/oauth2/token` signale un Client ID ou un Client Secret refusé (secret régénéré, application « sandbox » au lieu de « Production », copie incomplète). Nexar n'est pas appelé, pour préserver son quota de 10 pièces.

Depuis la version 0.3.2, une référence que DigiKey ne trouve pas en recherche exacte (« productdetails ») est recherchée par mot-clé (« KeywordSearch »). Si elle reste introuvable, un avertissement l'indique dans le rapport.

Si le rapport signale `CERTIFICATE_VERIFY_FAILED` (fréquent sous Windows avec un antivirus qui inspecte le trafic HTTPS, ou derrière un proxy d'entreprise), installer `pip install truststore` : le radar utilisera alors le magasin de certificats de Windows.

Depuis la version 0.3.1, le radar affiche aussi les sources actives au démarrage, et le rapport le précise dans sa section « Sources de données ». Si aucune source n'est configurée, un avertissement rappelle que les statuts électroniques viennent seulement de la nomenclature.

Ne jamais enregistrer ces clés dans un fichier versionné (dépôt Git, nomenclature partagée). Les résultats sont gardés 7 jours dans le cache `.cache_radar/` pour ne pas consommer deux fois le quota ; la clé Mouser, qui passe dans l'adresse de la requête, est masquée dans les messages d'erreur.

### Fiabilité des données des distributeurs

- Un statut « retiré chez ce distributeur » (« Discontinued at Digi-Key ») ne veut pas dire que le fabricant a arrêté la pièce : l'outil le classe à part (exposition 1).
- Chez Mouser, le statut est souvent vide pour les pièces courantes ; l'outil considère alors le statut comme inconnu et conserve la saisie.
- Les connecteurs Mouser et DigiKey suivent la documentation publique et sont testés avec des réponses simulées ; ils n'ont pas encore été essayés avec de vraies clés. Merci de signaler tout écart.

## Limites

- La qualité du résultat dépend d'abord de la nomenclature déclarée. Le radar aide à prioriser, mais il ne remplace pas l'analyse d'un concepteur.
- Pour la mécanique, il n'existe pas de base ouverte sur l'arrêt des pièces. Le dossier [base-communautaire-mecanique](base-communautaire-mecanique/) propose une amorce de base contributive.
- La correspondance entre logiciels et identifiants endoflife.date est manuelle (colonne `logiciel_produit`).
- La recherche des pannes Open Repair par mots-clés est approximative.

## Tests

```bash
python -m unittest discover -s tests -v
```

Les tests fonctionnent sans réseau : les sources externes sont simulées.

## Contribuer

Nouvelles règles (familles E à I), nouvelles sources ouvertes (bases d'arrêt de composants, données de réparabilité), traductions, cas d'usage réels : toutes les propositions sont bienvenues, dans un esprit libre et communautaire. Le référentiel des règles se trouve dans `radar_obsolescence/referentiel.py` et leur logique dans `radar_obsolescence/analyse.py`.

## Licence

Code sous licence MIT (voir [LICENSE](LICENSE)). La base communautaire mécanique est proposée sous licence CC BY-SA 4.0, comme les données Open Repair qu'elle complète.


## Test réel du connecteur Nexar (6 novembre 2026)

Le connecteur a été testé avec l'application d'évaluation d'un compte Nexar gratuit, sur les 8 composants électroniques de la nomenclature d'exemple.

| Référence saisie | Réponse Nexar | Statut de cycle de vie |
|---|---|---|
| STM32F103C8T6 | Trouvée (STMicroelectronics, 8 distributeurs agréés) | Production |
| EEU-FR1E471 | Trouvée sous EEUFR1E471 (Panasonic, 19 distributeurs agréés) | Production |
| ESP32-WROOM-32 | Référence exacte absente ; propose ESP32-WROOM-32E-N4, -32E-N16, -32UE-N16 | aucun |
| G5LE-1 | Première réponse : G5LE-14 DC24, une autre pièce | aucun |
| SIM800L, INR18650-35E | Trouvées, sans statut de cycle de vie | aucun |
| LCD-PPC-01, PWR-4P | Absentes (pièces spécifiques fictives) | aucun |

Enseignements, intégrés dans la version 0.2 du connecteur :

1. **La recherche Nexar est approchée.** Elle peut renvoyer une autre pièce que celle demandée. L'outil n'accepte plus que la référence exacte (à la ponctuation près) et liste sinon les références proches dans les avertissements.
2. **Statut absent.** Quand Nexar ne donne pas de statut, le statut saisi à la main est conservé (auparavant, il était effacé).
3. **Libellé du statut.** Nexar renvoie par exemple « Production (Last Updated: 1 month ago) ». L'outil le ramène au référentiel (PRODUCTION, NEW, NRND, LTB, EOL, OBSOLETE).
4. **Quota.** L'application d'évaluation de ce compte était limitée à **10 pièces renvoyées** (message de l'API : « You have exceeded your part limit of 10 »), et non 100 comme l'indique la [page des offres](https://nexar.com/compare-plans). Chaque pièce renvoyée compte, y compris les résultats approchés. Le plan gratuit permet donc de vérifier le fonctionnement, pas d'analyser une nomenclature réelle. Le cache local évite de consommer deux fois la même référence.
5. **Proxy HTTPS.** Si votre réseau impose un proxy en HTTPS, la bibliothèque standard de Python ne sait pas l'utiliser. L'outil passe alors automatiquement par `requests` si elle est installée.

Pour un usage régulier sans frais, la version 0.3 ajoute les connecteurs Mouser et DigiKey (voir « Configurer les sources de composants »).

## Test réel du connecteur DigiKey (6 novembre 2026)

Le connecteur a été testé sous Windows (PowerShell, Python installé depuis python.org) avec une « Production App » DigiKey abonnée à Product Information V4, en OAuth « 2-legged » (Client ID et Client Secret), sur les 8 composants électroniques de la nomenclature d'exemple. Aucun numéro de compte (`DIGIKEY_ACCOUNT_ID`) n'a été nécessaire.

| Référence saisie | Réponse DigiKey | Statut retenu |
|---|---|---|
| STM32F103C8T6 | Trouvée, libellé « Active » | PRODUCTION (DigiKey) |
| EEU-FR1E471 | Trouvée, libellé « Active » | PRODUCTION (DigiKey) |
| ESP32-WROOM-32 | Référence exacte absente ; propose ESP32-WROOM-32E-N4, -32E-H4, -32UE-N8 | NRND (saisie conservée) |
| G5LE-1 | Référence exacte absente ; propose G5LE-1A4 DC12, G5LE-1 DC24, G5LE-14 DC12 | saisie conservée |
| SIM800L | Référence exacte absente ; propose M004 | inconnu |
| INR18650-35E | Absente du catalogue (HTTP 404) | saisie conservée |
| LCD-PPC-01, PWR-4P | Absentes (pièces spécifiques fictives, HTTP 404) | inconnu |

Enseignements, intégrés dans les versions 0.3.1 à 0.3.4 :

1. **Variables non vues.** Lancer le radar dans une autre fenêtre que celle où les variables ont été déclarées, ou utiliser la syntaxe PowerShell dans cmd.exe, désactive DigiKey sans erreur. Le radar affiche désormais les sources actives au démarrage et dans le rapport, et `--verifier-sources` fait un appel de test.
2. **Jeton de 10 minutes.** Le jeton « 2-legged » expire au bout de 10 minutes : le radar le redemande à chaque exécution à partir du Client ID et du Client Secret. Un jeton copié à la main expire trop vite pour être utile.
3. **Recherche de secours.** Une référence absente de « productdetails » (HTTP 404) est recherchée par mot-clé (« KeywordSearch ») ; seule une correspondance exacte est retenue, sinon les références proches sont listées dans les avertissements.
4. **Références incomplètes.** Les propositions montrent que la nomenclature doit porter la référence complète : variante du module (ESP32-WROOM-32E-N4 a remplacé ESP32-WROOM-32, absent du catalogue), tension de bobine du relais (G5LE-1 DC24).
5. **Statuts favorables visibles.** Un statut « Active » ne crée pas de constat ; le tableau « Statuts de cycle de vie des composants » du rapport l'affiche avec sa source.
6. **Certificats sous Windows.** Une erreur `CERTIFICATE_VERIFY_FAILED` (antivirus qui inspecte le trafic HTTPS) a bloqué OpenSSF Scorecard ; `pip install truststore` l'a résolue.
7. **Cache.** Les résultats négatifs ne sont plus réutilisés depuis le cache, pour qu'une correction de la nomenclature ou du connecteur soit prise en compte immédiatement.

