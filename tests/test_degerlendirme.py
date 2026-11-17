"""Her çekiliş sonrası değerlendirme ve karne."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import superloto as sl  # noqa: E402

VERI = sl.csv_oku()
CEKILISLER = [VERI[k] for k in sorted(VERI) if k <= 984]

KUPON = """Gezegen saatleri — 2026-11-12 Perşembe, Ankara (gün yöneticisi: Jüpiter)

KOLONLAR: 2026-11-12 Jüpiter saati 07:30–08:20 içinde üretildi, üretim saati 07:40.

   #  Kolon                          G/O/Z  Tek  1-30  Toplam  İkili puanı
   1  16 - 22 - 28 - 30 - 44 - 47    2/2/2    1     4     187          160
   2   1 - 13 - 20 - 25 - 27 - 46    2/2/2    3     4     132          159
   3   2 - 10 - 21 - 29 - 52 - 56    2/2/2    3     3     170          157
"""


class KuponCozTest(unittest.TestCase):
    def test_kupon_okunur(self):
        tarih, kolonlar = sl.kupon_coz(KUPON)
        self.assertEqual(tarih, "2026-11-12")
        self.assertEqual(kolonlar[0], [16, 22, 28, 30, 44, 47])
        self.assertEqual(len(kolonlar), 3)

    def test_uretilmemis_kupon_bos(self):
        self.assertEqual(sl.kupon_coz("KOLONLAR: 2026-11-17 çekiliş günü ilk Jüpiter saatinde üretilecek.\n"),
                         ("2026-11-17", []))


class DegerlendirmeTest(unittest.TestCase):
    def test_son_cekilis_984(self):
        d = sl.cekilis_degerlendir(CEKILISLER, KUPON)
        self.assertEqual(d["no"], 984)
        self.assertEqual(d["toplam"], 205)
        self.assertTrue(d["kemik_uygun"])                # aynı onlukta 3 numaraya artık izin var
        self.assertEqual(d["kupon_bilen"], [1, 2, 3])     # 16 / 25,27 / 29,52,56
        self.assertEqual(d["en_iyi"], 3)
        self.assertIn("Kupon", d["rapor"])

    def test_dikkat_cekici_cekilis(self):
        gecmis = CEKILISLER[:-1]
        uc = dict(CEKILISLER[-1], no=985, tarih="2026-11-15", toplar=[1, 2, 3, 4, 5, 6])
        d = sl.cekilis_degerlendir(gecmis + [uc], "")
        self.assertFalse(d["kemik_uygun"])
        self.assertTrue(any("toplam" in x for x in d["dikkat"]))
        self.assertTrue(any("ardışık" in x for x in d["dikkat"]))
        self.assertIsNone(d["en_iyi"])                   # bu çekiliş için kupon yok

    def test_karne_birikir_ve_tekrarlamaz(self):
        with tempfile.TemporaryDirectory() as t:
            eski = (sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH, sl.PENCERE_ANALIZI_PATH,
                    sl.PENCERE_LISTELERI_PATH, sl.DONGU_KARNESI_PATH)
            sl.DONGU_KARNESI_PATH = Path(t) / "dongu.csv"
            sl.PENCERE_LISTELERI_PATH = Path(t) / "listeler.csv"
            sl.KARNE_PATH = Path(t) / "karne.csv"
            sl.DEGERLENDIRME_PATH = Path(t) / "son.md"
            sl.KURAL_KARNESI_PATH = Path(t) / "kural.csv"
            sl.PENCERE_ANALIZI_PATH = Path(t) / "pencere.csv"
            try:
                with redirect_stdout(io.StringIO()):
                    sl.degerlendir_ve_kaydet(CEKILISLER, KUPON)
                    sl.degerlendir_ve_kaydet(CEKILISLER, KUPON)   # aynı çekiliş ikinci kez yazılmaz
                satirlar = sl.KARNE_PATH.read_text(encoding="utf-8").strip().splitlines()
                self.assertEqual(len(satirlar), 2)                # başlık + 1 satır
                metin = sl.DEGERLENDIRME_PATH.read_text(encoding="utf-8")
                self.assertIn("Karne", metin)
                self.assertIn("Kural karnesi", metin)
                kural = sl.KURAL_KARNESI_PATH.read_text(encoding="utf-8").splitlines()
                self.assertEqual(kural[0], "kural,sinir,gercek,rastgele,fark,cekilis")
                self.assertIn("Kemik yapının tamamı", "".join(kural))
                self.assertIn("Analizler: 60 numara penceresi", metin)
                pencere = sl.PENCERE_ANALIZI_PATH.read_text(encoding="utf-8").splitlines()
                self.assertEqual(pencere[0], "bolum,deger,pencere,pencere_yuzde,tum_yuzde,rastgele_yuzde,"
                                             "bas_no,son_no,cekilis")
                listeler = sl.PENCERE_LISTELERI_PATH.read_text(encoding="utf-8").splitlines()
                self.assertEqual(listeler[0], "bolum,deger,adet,bas_no,son_no,cekilis")
                self.assertIn("Döngü kuralı", metin)
                dongu = sl.DONGU_KARNESI_PATH.read_text(encoding="utf-8").splitlines()
                self.assertTrue(dongu[0].startswith("sira,bas_no,bas_tarih"))
            finally:
                (sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH, sl.PENCERE_ANALIZI_PATH,
                 sl.PENCERE_LISTELERI_PATH, sl.DONGU_KARNESI_PATH) = eski

    def test_karne_ilk_satiri_dogru_sayar(self):
        uygun = dict(CEKILISLER[-1], no=985, tarih="2026-11-15", toplar=[3, 14, 22, 38, 47, 59])
        with tempfile.TemporaryDirectory() as t:
            eski = (sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH, sl.PENCERE_ANALIZI_PATH,
                    sl.PENCERE_LISTELERI_PATH, sl.DONGU_KARNESI_PATH)
            sl.DONGU_KARNESI_PATH = Path(t) / "dongu.csv"
            sl.PENCERE_LISTELERI_PATH = Path(t) / "listeler.csv"
            sl.KARNE_PATH = Path(t) / "karne.csv"
            sl.DEGERLENDIRME_PATH = Path(t) / "son.md"
            sl.KURAL_KARNESI_PATH = Path(t) / "kural.csv"
            sl.PENCERE_ANALIZI_PATH = Path(t) / "pencere.csv"
            try:
                with redirect_stdout(io.StringIO()):
                    sl.degerlendir_ve_kaydet(CEKILISLER + [uygun], "")
                self.assertIn("Kemik yapıya uyan çekiliş: 1/1",
                              sl.DEGERLENDIRME_PATH.read_text(encoding="utf-8"))
            finally:
                (sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH, sl.PENCERE_ANALIZI_PATH,
                 sl.PENCERE_LISTELERI_PATH, sl.DONGU_KARNESI_PATH) = eski


class PencereAnaliziTest(unittest.TestCase):
    """Analizler, son çekilişten geriye 60 numaranın tamamlandığı pencere üzerinden yapılır."""
    C985 = [VERI[k] for k in sorted(VERI) if k <= 985]

    def test_pencere(self):
        p = sl.pencere(self.C985)
        self.assertEqual((p[0]["no"], p[-1]["no"], len(p)), (950, 985, 36))
        self.assertEqual(len({t for c in p for t in c["toplar"]}), 60)
        self.assertLess(len({t for c in p[1:] for t in c["toplar"]}), 60)   # en kısa pencere
        p984 = sl.pencere(CEKILISLER)
        self.assertEqual(p984[-1]["no"], 984)

    def test_dagilimlar(self):
        a = sl.pencere_analizi(self.C985)
        self.assertEqual((a["bas_no"], a["son_no"], a["cekilis"]), (950, 985, 36))
        satir = {(r["bolum"], r["deger"]): r for r in a["dagilimlar"]}
        self.assertEqual(satir[("1–30 / 31–60", "2–4")]["pencere"], 19)
        self.assertAlmostEqual(satir[("1–30 / 31–60", "2–4")]["rastgele"], 0.2378, places=3)
        self.assertEqual(satir[("Tek / çift", "2–4")]["pencere"], 13)
        self.assertEqual(satir[("Ardışık ikili", "0")]["pencere"], 21)
        self.assertEqual(satir[("Üst üste (önceki çekilişten)", "3+")]["pencere"], 1)
        for bolum in {r["bolum"] for r in a["dagilimlar"]}:
            satirlar = [r for r in a["dagilimlar"] if r["bolum"] == bolum]
            self.assertEqual(sum(r["pencere"] for r in satirlar), 36, bolum)
            self.assertAlmostEqual(sum(r["rastgele"] for r in satirlar), 1.0, places=2)

    def test_listeler(self):
        a = sl.pencere_analizi(self.C985)
        liste = {}
        for r in a["listeler"]:
            liste.setdefault(r["bolum"], []).append((r["deger"], r["adet"]))
        self.assertEqual(liste["Numara sıklığı"][0], ("16", 9))
        self.assertEqual(set(liste["Birlikte gelen (2+ kez)"][:3]), {("40-42", 3), ("14-56", 3), ("45-54", 3)})
        self.assertEqual(liste["Üst üste gelen"][0], ("30", 3))
        self.assertIn(("53-54", 2), liste["Ardışık ikili"])
        self.assertEqual(liste["En uzun süredir gelmeyen"][0], ("13", 35))
        ozet = dict(liste["Özet"])
        self.assertEqual(ozet["Toplam ortalaması"], 200.2)


class DonguTest(unittest.TestCase):
    def test_geriye_dogru_donguler(self):
        d = sl.donguler(CEKILISLER, capa=985)          # 984'e kadar veri: hepsi geçmiş döngü
        tam = [x for x in d if x["durum"] == "tamam"]
        self.assertEqual(tam[-1]["son_no"], 984)
        for x in tam:
            numaralar = {t for c in CEKILISLER if x["bas_no"] <= c["no"] <= x["son_no"] for t in c["toplar"]}
            self.assertEqual(len(numaralar), 60)
            self.assertEqual(x["uzunluk"], x["son_no"] - x["bas_no"] + 1)
        self.assertGreater(len(tam), 15)

    def test_ileriye_dogru_yeni_dongu(self):
        d = sl.donguler(CEKILISLER, capa=980)
        self.assertEqual(d[-2]["son_no"], 979)            # geçmiş döngüler 979'da biter
        yeni = d[-1]
        self.assertEqual((yeni["durum"], yeni["bas_no"], yeni["son_no"]), ("devam", 980, 984))
        gelen = {t for c in CEKILISLER if c["no"] >= 980 for t in c["toplar"]}
        self.assertEqual(yeni["eksik"], sorted(set(range(1, 61)) - gelen))

    def test_tahmin_skoru(self):
        s = sl.dongu_tahmin_skoru(CEKILISLER, capa=980)
        self.assertEqual(len(s), 5)                       # 980..984
        self.assertEqual((s[0]["isabet"], s[0]["beklenen"]), (6, 6.0))  # ilk çekilişte hepsi eksik
        c980 = set(CEKILISLER[-5]["toplar"])
        c981 = set(CEKILISLER[-4]["toplar"])
        self.assertEqual(s[1]["isabet"], 6 - len(c980 & c981))
        self.assertAlmostEqual(s[1]["beklenen"], 6 * (60 - 6) / 60)


class DonguTamamlanmaTest(unittest.TestCase):
    """Bir döngü tamamlanınca yenisi sıradaki çekilişle 60 numarayla baştan başlar."""

    def setUp(self):
        self.gecmis = [VERI[k] for k in sorted(VERI) if k <= 985]
        # #986–#995: 1–6, 7–12, ..., 55–60 → 10 çekilişte 60 numara tamamlanır.
        self.tamamlayan = [{"no": 986 + i, "tarih": f"2026-12-{i + 1:02d}",
                            "toplar": list(range(6 * i + 1, 6 * i + 7))} for i in range(10)]

    def test_tamamlaninca_yeni_dongu(self):
        d = sl.donguler(self.gecmis + self.tamamlayan, capa=986)
        tamam = d[-2]
        self.assertEqual((tamam["durum"], tamam["bas_no"], tamam["son_no"], tamam["uzunluk"]),
                         ("tamam", 986, 995, 10))
        self.assertEqual(tamam["tamamlayan"], [55, 56, 57, 58, 59, 60])
        yeni = d[-1]
        self.assertEqual((yeni["durum"], yeni["bas_no"], yeni["uzunluk"]), ("devam", 996, 0))
        self.assertEqual(yeni["eksik"], list(range(1, 61)))

    def test_yeni_dongu_ilerler(self):
        sonraki = {"no": 996, "tarih": "2026-12-11", "toplar": [5, 18, 27, 33, 41, 56]}
        cekilisler = self.gecmis + self.tamamlayan + [sonraki]
        yeni = sl.donguler(cekilisler, capa=986)[-1]
        self.assertEqual((yeni["bas_no"], yeni["uzunluk"], yeni["gelen"]), (996, 1, 6))
        self.assertEqual(len(yeni["eksik"]), 54)
        skor = sl.dongu_tahmin_skoru(cekilisler, capa=986)
        self.assertEqual(skor[-1]["eksik_sayisi"], 60)        # yeni döngüde sayaç sıfırlandı
        self.assertEqual(sl.numara_analizi(cekilisler)["dongu_eksik"], set(yeni["eksik"]))

    def test_tamamlanma_degerlendirmede_yazar(self):
        cekilisler = self.gecmis + self.tamamlayan
        metin = sl.dongu_karnesi_metni(cekilisler, sl.donguler(cekilisler, capa=986))
        self.assertIn("Döngü tamamlandı", metin)
        self.assertIn("#986–#995", metin)


if __name__ == "__main__":
    unittest.main()
