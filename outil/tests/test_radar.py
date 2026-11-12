"""Tests hors ligne (aucun appel réseau) : python -m unittest discover -s tests"""

import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from radar_obsolescence import analyse
from radar_obsolescence.nomenclature import Ligne, Produit, charger_nomenclature
from radar_obsolescence.referentiel import niveau
from radar_obsolescence.sources import Cache, ErreurSource, depsdev, digikey, endoflife, mouser, nexar, scorecard


def ligne(**kw):
    return Ligne(numero=2, data=kw)


def codes(res):
    return {(c.code, c.exposition) for c in res.constats}


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Cache(self.tmp.name)
        self.produit = Produit(nom="T", date_mise_marche=date.today(), duree_vie_cible_ans=10,
                               duree_support_annoncee_ans=5)

    def tearDown(self):
        self.tmp.cleanup()

    def run_(self, *lignes):
        return analyse.analyser(list(lignes), self.produit, self.cache)


class TestRegles(BaseTest):
    def test_niveaux(self):
        self.assertEqual(niveau(9), "CRITIQUE")
        self.assertEqual(niveau(4), "A SURVEILLER")
        self.assertEqual(niveau(1), "FAIBLE")
        self.assertEqual(niveau(0), "MAITRISE")

    def test_piece_usure_non_remplacable(self):
        res = self.run_(ligne(id="M1", domaine="M", piece_usure="oui", remplacable_utilisateur="non",
                              etapes_demontage="12", fonction_critique="3"))
        self.assertIn(("A1", 3), codes(res))
        self.assertIn(("A2", 3), codes(res))
        self.assertEqual(max(c.criticite for c in res.constats), 9)

    def test_source_unique_specifique(self):
        res = self.run_(ligne(domaine="M", nb_sources="1", piece_specifique="oui", plans_ouverts="oui"))
        self.assertIn(("B2", 3), codes(res))
        self.assertIn(("B3", 1), codes(res))

    def test_statut_cycle_vie(self):
        res = self.run_(ligne(domaine="E", statut_cycle_vie="NRND"), ligne(domaine="E"))
        self.assertIn(("B1", 2), codes(res))
        self.assertIn(("B5", 1), codes(res))

    def test_reseau_2g(self):
        res = self.run_(ligne(domaine="E", designation="Module GSM quadribande", statut_cycle_vie="ACTIF"))
        self.assertIn(("C2", 3), codes(res))
        res = self.run_(ligne(domaine="E", designation="Module LTE-M", statut_cycle_vie="ACTIF"))
        self.assertNotIn("C2", {c.code for c in res.constats})

    def test_pieces_detachees(self):
        res = self.run_(ligne(domaine="M", disponibilite_pieces_ans="5", piece_usure="oui",
                              remplacable_utilisateur="oui"))
        self.assertIn(("B4", 3), codes(res))

    def test_cloud(self):
        res = self.run_(ligne(domaine="L", dependance_cloud="oui", mode_local="non"),
                        ligne(domaine="L", dependance_cloud="oui", mode_local="oui"))
        self.assertIn(("D4", 3), codes(res))
        self.assertIn(("D4", 1), codes(res))

    def test_endoflife(self):
        futur = (date.today() + timedelta(days=365 * 7)).isoformat()
        cycles = [{"cycle": "3.12", "eol": futur}, {"cycle": "3.8", "eol": "2024-10-07"}]
        with mock.patch.object(endoflife, "cycles", return_value=cycles):
            res = self.run_(ligne(domaine="L", logiciel_produit="python", logiciel_version="3.8.10"),
                            ligne(domaine="L", logiciel_produit="python", logiciel_version="3.12"))
        par_version = {c.ligne.data["logiciel_version"]: c.exposition for c in res.constats}
        self.assertEqual(par_version["3.8.10"], 3)       # déjà en fin de vie
        self.assertEqual(par_version["3.12"], 2)         # avant l'horizon (10 ans)

    def test_depsdev_et_scorecard(self):
        faux_deps = {"trouve": True, "url": "u", "version": "1.0", "deprecie": True,
                     "raison_depreciation": "abandonné", "nb_avis_securite": 0,
                     "jours_depuis_publication": 2000, "derniere_publication": "2020-01-01",
                     "depot": "github.com/a/b"}
        faux_score = {"trouve": True, "maintenu_score": 0, "maintenu_raison": "archived",
                      "score_global": 3, "url": "s"}
        with mock.patch.object(depsdev, "analyser", return_value=faux_deps), \
                mock.patch.object(scorecard, "analyser", return_value=faux_score):
            res = self.run_(ligne(domaine="L", ecosysteme="npm", paquet="x"))
        self.assertTrue({("D2", 3), ("D3", 3), ("D6", 2)} <= codes(res))

    def test_indice(self):
        res = self.run_(ligne(domaine="M", nb_sources="5"))
        self.assertEqual(analyse.synthese(res)["indice"], 100)


class TestScorecard(unittest.TestCase):
    def test_normaliser_depot(self):
        f = scorecard.normaliser_depot
        self.assertEqual(f("git+https://github.com/request/request.git"), "github.com/request/request")
        self.assertEqual(f("https://github.com/a/b#readme"), "github.com/a/b")
        self.assertIsNone(f("https://example.org/x"))


class TestFichiers(BaseTest):
    def test_csv_point_virgule_et_alias(self):
        p = Path(self.tmp.name) / "bom.csv"
        p.write_text("Ref;Description;Domaine;MPN\nE1;Module;E;ABC\n", encoding="utf-8")
        lignes = charger_nomenclature(p)
        self.assertEqual(lignes[0].data["id"], "E1")
        self.assertEqual(lignes[0].data["reference_fabricant"], "ABC")

    def test_ords(self):
        from radar_obsolescence.sources import ords
        p = Path(self.tmp.name) / "ords.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "product_category", "repair_status", "problem", "product_age"])
            w.writerow([1, "Kettle", "Fixed", "switch broken", 4])
            w.writerow([2, "Kettle", "End of life", "heating element dead", 8])
            w.writerow([3, "Kettle", "Repairable", "interrupteur HS", 6])
            w.writerow([4, "Toaster", "Fixed", "cord", 3])
        r = ords.analyser(p, "kettle")
        self.assertEqual(r["nb_reparations"], 3)
        self.assertEqual(r["sous_ensembles"][0][0], "interrupteur / bouton")
        self.assertEqual(r["age_median_ans"], 6.0)


class TestNexar(unittest.TestCase):
    def test_normalisation_statut(self):
        # libellé réel renvoyé par l'API Nexar le 6 novembre 2026
        self.assertEqual(nexar.normaliser_statut("Production (Last Updated: 1 month ago)"), "PRODUCTION")
        self.assertEqual(nexar.normaliser_statut("Obsolete (Last Updated: 2 years ago)"), "OBSOLETE")
        self.assertEqual(nexar.normaliser_statut("Not Recommended for New Designs"), "NRND")
        self.assertEqual(nexar.normaliser_statut("EOL"), "EOL")
        self.assertEqual(nexar.normaliser_statut(None), "INCONNU")

    def test_correspondance_exacte(self):
        # cas réels du 6 novembre 2026 : la recherche approchée renvoyait une autre pièce
        rep = {"data": {"supSearchMpn": {"results": [{"part": {"mpn": "ESP32-WROOM-32E-N4", "specs": [], "sellers": []}}]}}}
        with tempfile.TemporaryDirectory() as d, mock.patch.dict("os.environ", {"NEXAR_AUTH_EXTERNE": "1"}), \
                mock.patch.object(nexar, "post_json", return_value=rep):
            r = nexar.analyser("ESP32-WROOM-32", Cache(d))
        self.assertFalse(r["trouve"])
        self.assertEqual(r["proches"], ["ESP32-WROOM-32E-N4"])
        self.assertEqual(nexar.normaliser_mpn("EEU-FR1E471"), nexar.normaliser_mpn("EEUFR1E471"))



class TestDistributeurs(BaseTest):
    """Réponses simulées d'après la documentation publique de Mouser et DigiKey (non testées en réel)."""

    def test_mouser_statut_et_remplacement(self):
        rep = {"Errors": [], "SearchResults": {"NumberOfResult": 1, "Parts": [
            {"ManufacturerPartNumber": "ESP32-WROOM-32", "Manufacturer": "Espressif",
             "LifecycleStatus": "Not Recommended for New Designs", "SuggestedReplacement": "ESP32-WROOM-32E-N4"}]}}
        with mock.patch.dict("os.environ", {"MOUSER_API_KEY": "cle-test"}, clear=False), \
                mock.patch.object(mouser, "post_json", return_value=rep), mock.patch.object(mouser, "_dernier_appel", 0.0), \
                mock.patch("time.sleep"):
            res = self.run_(ligne(domaine="E", reference_fabricant="ESP32-WROOM-32"))
        b1 = [c for c in res.constats if c.code == "B1"][0]
        self.assertEqual((b1.exposition, b1.preuve, b1.automatique), (2, "Mouser", True))
        self.assertIn("ESP32-WROOM-32E-N4", b1.detail)

    def test_mouser_cle_masquee(self):
        with mock.patch.dict("os.environ", {"MOUSER_API_KEY": "secret123"}), mock.patch("time.sleep"), \
                mock.patch.object(mouser, "post_json", side_effect=ErreurSource("HTTP 403 sur https://x?apiKey=secret123")):
            with self.assertRaises(ErreurSource) as ctx:
                mouser.analyser("ABC", self.cache)
        self.assertNotIn("secret123", str(ctx.exception))

    def test_digikey_statut_et_date(self):
        rep = {"Product": {"ManufacturerProductNumber": "STM32F103C8T6", "Manufacturer": {"Name": "ST"},
                           "ProductStatus": {"Id": 0, "Status": "Last Time Buy"},
                           "DateLastBuyChance": "2027-03-31T00:00:00Z", "QuantityAvailable": 10}}
        env = {"DIGIKEY_CLIENT_ID": "id", "DIGIKEY_CLIENT_SECRET": "s"}
        with mock.patch.dict("os.environ", env), mock.patch.object(digikey, "_jeton", "jeton"), \
                mock.patch.object(digikey, "get_json", return_value=rep):
            r = digikey.analyser("STM32F103C8T6", self.cache)
        self.assertEqual((r["statut"], r["date_derniere_commande"]), ("LTB", "2027-03-31T00:00:00Z"))

    def test_statut_production_visible(self):
        rep = {"Product": {"ManufacturerProductNumber": "STM32F103C8T6", "ProductStatus": {"Id": 0, "Status": "Active"}}}
        env = {"DIGIKEY_CLIENT_ID": "id", "DIGIKEY_CLIENT_SECRET": "s"}
        with mock.patch.dict("os.environ", env), mock.patch.object(digikey, "_jeton", "jeton"), \
                mock.patch.object(digikey, "get_json", return_value=rep):
            res = self.run_(ligne(domaine="E", reference_fabricant="STM32F103C8T6"))
        self.assertFalse([c for c in res.constats if c.code == "B1"])
        self.assertEqual((res.cycles_vie[0]["statut"], res.cycles_vie[0]["source"]), ("PRODUCTION", "DigiKey"))

    def test_digikey_404_puis_mot_cle(self):
        mot_cle = {"Products": [{"ManufacturerProductNumber": "G5LE-14 DC24"}],
                   "ExactMatches": [{"ManufacturerProductNumber": "G5LE-1", "ProductStatus": {"Id": 0, "Text": "Active"}}]}
        env = {"DIGIKEY_CLIENT_ID": "id", "DIGIKEY_CLIENT_SECRET": "s"}
        with mock.patch.dict("os.environ", env), mock.patch.object(digikey, "_jeton", "jeton"), \
                mock.patch.object(digikey, "get_json", return_value=None), \
                mock.patch.object(digikey, "post_json", return_value=mot_cle):
            r = digikey.analyser("G5LE-1", self.cache)
        self.assertEqual((r["trouve"], r["statut"], r["origine"]), (True, "PRODUCTION", "keyword"))

    def test_digikey_introuvable_signale(self):
        env = {"DIGIKEY_CLIENT_ID": "id", "DIGIKEY_CLIENT_SECRET": "s"}
        with mock.patch.dict("os.environ", env), mock.patch.object(digikey, "_jeton", "jeton"), \
                mock.patch.object(digikey, "get_json", return_value=None), \
                mock.patch.object(digikey, "post_json", return_value={"Products": [], "ExactMatches": []}):
            res = self.run_(ligne(domaine="E", reference_fabricant="LCD-PPC-01"))
        self.assertTrue(any("introuvable sur DigiKey" in a for a in res.avertissements))

    def test_statut_saisi_conserve(self):
        rep = {"Errors": [], "SearchResults": {"Parts": [
            {"ManufacturerPartNumber": "ESP32-WROOM-32", "LifecycleStatus": None}]}}
        with mock.patch.dict("os.environ", {"MOUSER_API_KEY": "k"}), mock.patch("time.sleep"), \
                mock.patch.object(mouser, "post_json", return_value=rep):
            res = self.run_(ligne(domaine="E", reference_fabricant="ESP32-WROOM-32", statut_cycle_vie="NRND"))
        b1 = [c for c in res.constats if c.code == "B1"][0]
        self.assertEqual((b1.exposition, b1.automatique), (2, False))

    def test_libelles_distributeurs(self):
        from radar_obsolescence.sources.composants import normaliser_statut as n
        self.assertEqual(n("Not For New Designs"), "NRND")
        self.assertEqual(n("Discontinued at Digi-Key"), "ARRET_DISTRIBUTEUR")
        self.assertEqual(n("End of Life"), "EOL")
        self.assertEqual(n("New at Mouser"), "INCONNU")
        self.assertEqual(n("Preliminary"), "NEW")


class TestEtatSources(unittest.TestCase):
    def test_sources_detectees_selon_variables(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(any(a for _, a, _ in analyse.etat_sources_composants()))
        with mock.patch.dict("os.environ", {"DIGIKEY_CLIENT_ID": "x", "DIGIKEY_CLIENT_SECRET": "y"}, clear=True):
            etat = {n: a for n, a, _ in analyse.etat_sources_composants()}
            self.assertTrue(etat["DigiKey"])
            self.assertFalse(etat["Mouser"])


class TestKit(BaseTest):
    """Classeur du kit, carte de démontage GT1 et visualiseur."""

    def test_montee_de_version_prevue_modere_D1(self):
        fin = (date.today() + timedelta(days=365 * 3)).isoformat()
        cycles = [{"cycle": "1", "eol": fin}]
        with mock.patch.object(endoflife, "cycles", return_value=cycles):
            sans = self.run_(ligne(id="L1", designation="OS", domaine="L", fonction_critique="3",
                                   logiciel_produit="debian", logiciel_version="1"))
            avec = self.run_(ligne(id="L1", designation="OS", domaine="L", fonction_critique="3",
                                   logiciel_produit="debian", logiciel_version="1", mise_a_jour_prevue="oui"))
        d1 = lambda r: [c.exposition for c in r.constats if c.code == "D1"]
        self.assertTrue(d1(sans) and d1(sans)[0] >= 2)
        self.assertEqual(d1(avec), [1])

    def test_carte_demontage_par_ref_et_scenario(self):
        from radar_obsolescence.nomenclature import importer_carte_demontage
        carte = Path(self.tmp.name) / "etapes_par_composant.csv"
        carte.write_text("\ufeffRéf.;Composant;Cible;Étapes (Actuel);Étapes (Amélioré)\r\n"
                         "3;Joint;Oui;7;2\r\n9;Module Wi-Fi;Non;5;3\r\n", encoding="utf-8")
        lignes = [ligne(id="M3", designation="Joint façade", ref_demontage="3"),
                  Ligne(numero=3, data={"id": "E1", "designation": "Module Wi-Fi"}),
                  Ligne(numero=4, data={"id": "E2", "designation": "Autre", "etapes_demontage": "4"})]
        n, avert = importer_carte_demontage(lignes, carte, "Amélioré")
        self.assertEqual((n, avert), (2, []))
        self.assertEqual([l.data.get("etapes_demontage") for l in lignes], [2, 3, "4"])
        n, avert = importer_carte_demontage(lignes, carte, "Variante")
        self.assertEqual(n, 0)
        self.assertTrue(avert)

    def test_classeur_aller_retour(self):
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            self.skipTest("openpyxl absent")
        from radar_obsolescence.classeur import generer
        from radar_obsolescence.nomenclature import charger_produit
        chemin = Path(self.tmp.name) / "classeur.xlsx"
        generer(chemin, exemple=True)
        actuel = charger_nomenclature(chemin)
        ameliore = charger_nomenclature(chemin, "Nomenclature améliorée")
        self.assertEqual(len(actuel), 20)
        self.assertEqual(actuel[0].get("id"), "M1")
        self.assertEqual(actuel[0].domaine, "M")
        self.assertIn("mise_a_jour_prevue", ameliore[12].data)
        p = charger_produit(chemin)
        self.assertEqual((p.duree_vie_cible_ans, p.date_mise_marche.year), (15, 2026))
        vide = Path(self.tmp.name) / "vide.xlsx"
        generer(vide)
        self.assertEqual(charger_nomenclature(vide), [])

    def test_visualiseur_autonome(self):
        from radar_obsolescence.visualiseur import ecrire_visualiseur
        res = self.run_(ligne(id="M1", designation="Joint", domaine="M", piece_usure="oui",
                              remplacable_utilisateur="non", etapes_demontage="7", fonction_critique="3"))
        sortie = Path(self.tmp.name) / "visualiseur.html"
        ecrire_visualiseur(res, sortie, "test.csv")
        html = sortie.read_text(encoding="utf-8")
        self.assertIn("<html", html)
        self.assertNotIn("http://cdn", html)
        self.assertIn("M1", html)

    def test_resume_json(self):
        import json
        from radar_obsolescence.rapport import ecrire_json
        res = self.run_(ligne(id="M1", designation="Joint", domaine="M", piece_usure="oui",
                              remplacable_utilisateur="non", etapes_demontage="7", fonction_critique="3"),
                        Ligne(numero=3, data=dict(id="M2", designation="Vis", domaine="M")))
        d = json.loads(ecrire_json(res, Path(self.tmp.name) / "resume.json").read_text(encoding="utf-8"))
        self.assertEqual(d["nb_lignes"], 2)
        self.assertEqual(sum(d["lignes"].values()), 2)
        self.assertGreaterEqual(d["lignes"]["critiques"], 1)
        self.assertEqual(d["constats"][0]["id"], "M1")
        self.assertIn("horizon", d["produit"])

    def test_aucun_tiret_long_dans_les_sorties(self):
        from radar_obsolescence.rapport import ecrire_markdown
        from radar_obsolescence.visualiseur import ecrire_visualiseur
        res = self.run_(ligne(id="M1", designation="Joint", domaine="M", piece_usure="oui"))
        for f in (ecrire_visualiseur(res, Path(self.tmp.name) / "v.html", "t.csv"),
                  ecrire_markdown(res, Path(self.tmp.name) / "r.md") or Path(self.tmp.name) / "r.md"):
            texte = Path(f).read_text(encoding="utf-8")
            self.assertNotIn("\u2014", texte)
            self.assertNotIn("\u2013", texte)


if __name__ == "__main__":
    unittest.main()
