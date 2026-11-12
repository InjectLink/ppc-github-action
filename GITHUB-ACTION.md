# Action GitHub — Radar d'obsolescence PPC

Cette action analyse une nomenclature depuis un workflow GitHub et produit le visualiseur, le rapport Markdown, les tableaux CSV/XLSX et le résumé JSON.

## Utiliser l'action depuis un autre dépôt

Après publication de ce dépôt sur GitHub et création d'un tag stable (par exemple `v1`), ajouter ce workflow dans le dépôt qui contient la nomenclature :

```yaml
name: Radar d'obsolescence

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  radar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Analyser la nomenclature
        id: radar
        uses: VOTRE-ORGANISATION/radar-obsolescence@v1
        with:
          nomenclature: "documents/ma-nomenclature.xlsx"
          sortie: "resultats-radar"
          # Paramètres facultatifs :
          produit: "documents/produit.json"
          carte: "documents/etapes_par_composant.csv"
          scenario: "Actuel"
          onglet: "Nomenclature"

          # Les valeurs sensibles viennent des secrets du dépôt appelant.
          mouser-api-key: ${{ secrets.MOUSER_API_KEY }}
          digikey-client-id: ${{ secrets.DIGIKEY_CLIENT_ID }}
          digikey-client-secret: ${{ secrets.DIGIKEY_CLIENT_SECRET }}
          digikey-account-id: ${{ secrets.DIGIKEY_ACCOUNT_ID }}

      - name: Télécharger les résultats depuis GitHub
        uses: actions/upload-artifact@v7
        with:
          name: radar-obsolescence
          path: ${{ steps.radar.outputs.result-directory }}
```

Remplacer `VOTRE-ORGANISATION/radar-obsolescence@v1` par le nom et le tag réels du dépôt qui héberge l'action. Le dépôt de la nomenclature peut être public ou privé.

## Configurer les secrets

Dans le dépôt qui exécute le radar, ouvrir **Settings → Secrets and variables → Actions → New repository secret**, puis créer seulement les secrets utilisés :

- `MOUSER_API_KEY` ;
- `DIGIKEY_CLIENT_ID` et `DIGIKEY_CLIENT_SECRET` ;
- éventuellement `DIGIKEY_ACCOUNT_ID` ;
- éventuellement `NEXAR_TOKEN`, ou `NEXAR_CLIENT_ID` et `NEXAR_CLIENT_SECRET`.

Les API fournisseurs sont facultatives. Sans secret, le radar fonctionne tout de même avec les informations de la nomenclature et les sources publiques sans clé. Ne jamais écrire une clé directement dans le fichier YAML : les entrées de l'action ne sont masquées que lorsque leur valeur provient d'un secret GitHub.

Les paramètres non sensibles (`nomenclature`, `sortie`, `onglet`, `scenario`, etc.) se renseignent directement sous `with:`. Les réglages DigiKey `digikey-site`, `digikey-langue` et `digikey-devise` valent respectivement `FR`, `en` et `EUR` par défaut.

## Exécuter depuis ce dépôt

Le workflow [`.github/workflows/radar.yml`](.github/workflows/radar.yml) ajoute un bouton **Run workflow** dans l'onglet **Actions → Radar d'obsolescence**. Les fichiers indiqués doivent être versionnés dans le dépôt. Les résultats sont disponibles à la fin de l'exécution sous forme d'artefact `radar-obsolescence`.

Les secrets configurés dans le dépôt sont automatiquement transmis au workflow manuel. Une personne autorisée à lancer des workflows choisit les chemins et options, mais n'a pas besoin de connaître les valeurs des secrets.

## Entrées principales

| Entrée | Obligatoire | Défaut | Description |
|---|---:|---|---|
| `nomenclature` | oui | — | Classeur XLSX ou fichier CSV |
| `produit` | non | vide | Fiche produit JSON |
| `carte` | non | vide | Carte de démontage CSV |
| `scenario` | non | vide | Scénario de la carte |
| `sortie` | non | `resultats` | Dossier de sortie |
| `ords` | non | vide | CSV Open Repair Alliance |
| `onglet` | non | vide | Onglet du classeur |
| `hors-ligne` | non | `false` | N'utiliser que le cache local |
| `cache` | non | `.cache_radar` | Dossier du cache |

L'action expose `result-directory` et `summary-file` comme sorties. Elle accepte aussi les identifiants Mouser, DigiKey et Nexar détaillés dans [`action.yml`](action.yml).

