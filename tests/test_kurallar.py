"""Kolon kuralları, gezegen saatleri ve Jüpiter saatinde üretim."""
import datetime
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import superloto as sl  # noqa: E402

VERI = sl.csv_oku()
# Sabit bir geçmiş: testler yeni çekilişler eklense de aynı sonucu versin.
CEKILISLER = [VERI[k] for k in sorted(VERI) if k <= 984]


class DizilimTest(unittest.TestCase):
    def test_dizilim(self):
        d = sl.dizilim([16, 25, 27, 29, 52, 56], [19, 22, 35, 43, 46, 59])
        self.assertEqual(d["onlu"], (0, 1, 3, 0, 0, 2))
        self.assertEqual((d["tek"], d["ardisik"], d["toplam"], d["asal"]), (3, 0, 205, 1))
        self.assertEqual((d["ilk"], d["son"], d["araliklar"]), (16, 56, (9, 2, 2, 23, 4)))
        self.assertEqual(d["tekrar"], 0)

    def test_kemik_yapi(self):
        self.assertEqual(sl.kemik_ceza([4, 13, 26, 37, 42, 51], set()), 0)
        self.assertGreater(sl.kemik_ceza([1, 3, 5, 7, 9, 11], set()), 0)   # 6 tek, aynı onlukta 5
        self.assertGreater(sl.kemik_ceza([1, 2, 30, 40, 50, 60], {1, 2, 30}), 0)  # son çekilişten 3

    def test_gevsek_kemik_yapi(self):
        # Geçmiş karşılaştırmasından sonra gevşetilen sınırlar.
        self.assertEqual(sl.kemik_ceza([16, 25, 27, 29, 52, 56], set()), 0)   # aynı onlukta 3
        self.assertEqual(sl.kemik_ceza([7, 24, 38, 40, 53, 54], set()), 0)    # toplam 216
        self.assertEqual(sl.kemik_ceza([3, 4, 15, 16, 40, 52], set()), 0)     # 2 ardışık ikili, toplam 130
        self.assertGreater(sl.kemik_ceza([12, 14, 16, 18, 20, 22], set()), 0)  # 6 çift
        self.assertGreater(sl.kemik_ceza([33, 41, 45, 50, 55, 59], set()), 0)  # toplam 283
        self.assertGreater(sl.kemik_ceza([21, 22, 23, 24, 50, 59], set()), 0)  # aynı onlukta 4

    def test_kural_karnesi(self):
        satirlar = sl.kural_karnesi(CEKILISLER, ornek=5000)
        adlar = [s["kural"] for s in satirlar]
        self.assertIn("Kemik yapının tamamı", adlar)
        for s in satirlar:
            self.assertTrue(0 <= s["gercek"] <= 1 and 0 <= s["rastgele"] <= 1)
        kemik = satirlar[adlar.index("Kemik yapının tamamı")]
        self.assertGreater(kemik["gercek"], 0.6)                      # gevşek kemik ~%67
        self.assertLess(abs(kemik["gercek"] - kemik["rastgele"]), 0.06)


class KolonUretTest(unittest.TestCase):
    def kontrol_60(self, kolonlar):
        self.assertEqual(len(kolonlar), 10)
        self.assertEqual(sorted(t for k in kolonlar for t in k), list(range(1, 61)))

    def test_kolon_kurallari(self):
        an = sl.numara_analizi(CEKILISLER)
        kolonlar = sl.kolon_uret(an, tohum=1)
        self.kontrol_60(kolonlar)
        self.assertTrue(all(sl.kolon_ceza(k, an) == 0 for k in kolonlar))

    def test_farkli_duzen(self):
        an = sl.numara_analizi(CEKILISLER)
        ilk = sl.kolon_uret(an, tohum=2)
        ikinci = sl.kolon_uret(an, tohum=3, onceki=ilk)
        self.kontrol_60(ikinci)
        self.assertTrue(all(len(set(a) & set(b)) <= 2 for a in ikinci for b in ilk))

    def test_tum_kurallar(self):
        an = sl.numara_analizi(CEKILISLER)
        sonuc = sl.taklit_uret(CEKILISLER, 4, an=an, adim=50000, deneme=2)
        self.kontrol_60(sonuc["kolonlar"])
        son = CEKILISLER[-1]["toplar"]
        for k, h in zip(sonuc["kolonlar"], sonuc["hedefler"]):
            self.assertEqual(sl.taklit_kontrol(k, h, son)[0], 0)      # taklidin zorunlu kuralları
            self.assertEqual(sl.kemik_ceza(k, set(son)), 0)            # kemik yapı
            self.assertEqual(sl.dizilim(k)["onlu"], h["onlu"])
        out = io.StringIO()
        with redirect_stdout(out):
            sl.taklit_yazdir(sonuc, "Set 1", an)
        self.assertNotIn("G/O/Z", out.getvalue())                     # sadeleştirilen hedefler

    def test_dongu_kurali_eksikleri_toplar(self):
        an = sl.numara_analizi(CEKILISLER)
        # #965'ten beri süren bir döngü: 20 çekiliş, bir kısmı henüz gelmemiş numaralar.
        an["dongu_eksik"] = set(sl.donguler(CEKILISLER, capa=965)[-1]["eksik"])
        self.assertTrue(0 < len(an["dongu_eksik"]) < 60)

        def toplanma(kolonlar):
            return sum(sl.dongu_toplanma(k, an["dongu_eksik"]) for k in kolonlar)

        kurallı = sl.taklit_uret(CEKILISLER, 4, an=an, adim=50000, deneme=2)
        kuralsiz = sl.taklit_uret(CEKILISLER, 4, an=an, adim=50000, deneme=2, dongu_agirlik=0)
        self.kontrol_60(kurallı["kolonlar"])
        son = CEKILISLER[-1]["toplar"]
        for k, h in zip(kurallı["kolonlar"], kurallı["hedefler"]):
            self.assertEqual(sl.taklit_kontrol(k, h, son)[0], 0)      # zorunlu kurallar korunur
            self.assertEqual(sl.kemik_ceza(k, set(son)), 0)
        self.assertGreater(toplanma(kurallı["kolonlar"]), toplanma(kuralsiz["kolonlar"]))
        out = io.StringIO()
        with redirect_stdout(out):
            sl.taklit_yazdir(kurallı, "Set 1", an)
        self.assertIn("Dng", out.getvalue())
        self.assertIn("Döngü kuralı", out.getvalue())

    def esnek_kontrol(self, an, eksik, en_cok_ayrilan=1):
        an["dongu_eksik"] = set(eksik)
        sonuc = sl.taklit_uret(CEKILISLER, 4, an=an, adim=50000, deneme=2)
        self.kontrol_60(sonuc["kolonlar"])
        d = sonuc["dongu_kolonu"]
        self.assertIsNotNone(d)
        self.assertTrue(set(eksik) <= set(sonuc["kolonlar"][d]))     # hepsi tek kolonda
        son = CEKILISLER[-1]["toplar"]
        for i, (k, h) in enumerate(zip(sonuc["kolonlar"], sonuc["hedefler"])):
            if i == d:
                continue                                            # döngü kolonu esnetildi
            # Gerekirse kademeli esnetilen taklit; kemik yapı her zaman zorunlu.
            self.assertEqual(sl.taklit_zorunlu(k, h, son, 6, sonuc["esneklik"]), 0)
            self.assertEqual(sl.kemik_ceza(k, set(son)), 0)
        # Onluk dağılımı şablondan ayrılan, döngü kolonu dışında en fazla bir kolon olabilir.
        ayrilan = [i for i, (k, h) in enumerate(zip(sonuc["kolonlar"], sonuc["hedefler"]))
                   if i != d and sl.dizilim(k)["onlu"] != h["onlu"]]
        self.assertLessEqual(len(ayrilan), en_cok_ayrilan, ayrilan)
        out = io.StringIO()
        with redirect_stdout(out):
            sl.taklit_yazdir(sonuc, "Set 1", an)
        self.assertIn("döngü kolonu", out.getvalue())
        return sonuc

    def test_az_kalinca_dongu_kolonu(self):
        an = sl.numara_analizi(CEKILISLER)
        sonuc = self.esnek_kontrol(an, sl.donguler(CEKILISLER, capa=960)[-1]["eksik"])   # 4 numara
        self.assertEqual(sonuc["esneklik"], 0)            # olağan durumda diğer kolonlar esnemez

    def test_dongu_kolonu_zor_durum(self):
        # Aynı onluktan 4 ardışık numara: kemik yapıyı da bozar, yine tek kolonda toplanmalı.
        an = sl.numara_analizi(CEKILISLER)
        self.esnek_kontrol(an, [21, 22, 23, 24])
        self.esnek_kontrol(an, [3, 13, 23, 33, 43, 53])                       # aynı son hane
        # Altısı da aynı onlukta: hiçbir kolon bir onluktan 4 numara veremediği için
        # birden fazla ortak kolon gerekir.
        self.esnek_kontrol(an, [1, 2, 3, 4, 5, 6], en_cok_ayrilan=3)

    def test_cok_eksikte_dongu_kolonu_yok(self):
        an = sl.numara_analizi(CEKILISLER)
        an["dongu_eksik"] = set(sl.donguler(CEKILISLER, capa=975)[-1]["eksik"])
        self.assertGreater(len(an["dongu_eksik"]), 6)
        self.assertIsNone(sl.taklit_uret(CEKILISLER, 4, an=an, adim=50000, deneme=2)["dongu_kolonu"])

    def test_dongu_eksik_analizde(self):
        an = sl.numara_analizi(CEKILISLER)
        self.assertEqual(an["dongu_eksik"], set(sl.donguler(CEKILISLER)[-1]["eksik"]))

    def test_tohum_tekrarlanabilir(self):
        a = sl.taklit_uret(CEKILISLER, 7)["kolonlar"]
        b = sl.taklit_uret(CEKILISLER, 7)["kolonlar"]
        self.assertEqual(a, b)


class GezegenTest(unittest.TestCase):
    def test_ankara_15_kasim(self):
        s = sl.gezegen_saatleri(datetime.date(2026, 11, 15))
        self.assertEqual(len(s), 24)
        self.assertEqual(s[0]["gezegen"], "Güneş")              # Pazar
        self.assertEqual(f"{s[0]['bas']:%H:%M}", "07:32")
        self.assertEqual(f"{s[12]['bas']:%H:%M}", "17:32")
        j = sl.jupiter_saatleri(datetime.date(2026, 11, 15))
        self.assertEqual([f"{x['bas']:%H:%M}" for x in j], ["11:42", "17:32"])

    def test_gun_yoneticisi(self):
        self.assertEqual(sl.gezegen_saatleri(datetime.date(2026, 11, 17))[0]["gezegen"], "Mars")
        self.assertEqual(sl.gezegen_saatleri(datetime.date(2026, 11, 19))[0]["gezegen"], "Jüpiter")

    def test_kalde_sirasi(self):
        s = sl.gezegen_saatleri(datetime.date(2026, 11, 19))
        sira = sl.KALDE_SIRASI
        for a, b in zip(s, s[1:]):
            self.assertEqual(sira.index(b["gezegen"]), (sira.index(a["gezegen"]) + 1) % 7)


class JupiterUretimTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.eski = sl.OYUN_PATH
        sl.OYUN_PATH = Path(self.tmp.name) / "oyun.txt"

    def tearDown(self):
        sl.OYUN_PATH = self.eski
        self.tmp.cleanup()

    def calistir(self, zaman):
        with redirect_stdout(io.StringIO()) as cikti:
            sl.oyun_jupiter(CEKILISLER, datetime.datetime.fromisoformat(zaman))
        return cikti.getvalue()

    def test_akis(self):
        with redirect_stdout(io.StringIO()):
            sl.oyun_planla(CEKILISLER)
        self.assertIn("üretilecek", sl.OYUN_PATH.read_text(encoding="utf-8"))
        self.assertIn("bekleniyor", self.calistir("2026-11-15T09:00"))
        self.assertIn("üretildi", self.calistir("2026-11-15T11:50"))
        metin = sl.OYUN_PATH.read_text(encoding="utf-8")
        self.assertIn("Jüpiter saati 11:42–12:32 içinde", metin)
        self.assertIn("zaten üretilmiş", self.calistir("2026-11-15T12:00"))
        with redirect_stdout(io.StringIO()):
            sl.oyun_planla(CEKILISLER)   # üretilmiş kolonlara dokunmamalı
        self.assertEqual(sl.OYUN_PATH.read_text(encoding="utf-8"), metin)

    def test_kacirilan_jupiter(self):
        self.assertIn("bekleniyor (17:32", self.calistir("2026-11-15T13:00"))
        self.assertIn("kaçırıldı", self.calistir("2026-11-15T17:40"))

    def test_cekilis_olmayan_gun(self):
        self.assertIn("çekiliş günü değil", self.calistir("2026-11-16T12:00"))
        self.assertFalse(sl.OYUN_PATH.exists())


class AnalizTest(unittest.TestCase):
    def test_bilinen_degerler(self):
        with redirect_stdout(io.StringIO()) as cikti:
            sl.analiz(CEKILISLER)
        rapor = cikti.getvalue()
        self.assertIn("984 çekiliş", rapor)
        self.assertIn("6: 118 kez", rapor)
        self.assertIn("24: 39 çekiliştir çıkmıyor", rapor)
        self.assertIn("Ki-kare istatistiği (sd=59): 51.7", rapor)

    def test_ikililer_sitedeki_degerlerle(self):
        ikili = {}
        for c in CEKILISLER:
            for p in combinations(c["toplar"], 2):
                ikili[p] = ikili.get(p, 0) + 1
        self.assertEqual(ikili[(6, 43)], 19)


if __name__ == "__main__":
    unittest.main()
