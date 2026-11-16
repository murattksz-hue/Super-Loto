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
            eski = sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH
            sl.KARNE_PATH = Path(t) / "karne.csv"
            sl.DEGERLENDIRME_PATH = Path(t) / "son.md"
            sl.KURAL_KARNESI_PATH = Path(t) / "kural.csv"
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
            finally:
                sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH = eski

    def test_karne_ilk_satiri_dogru_sayar(self):
        uygun = dict(CEKILISLER[-1], no=985, tarih="2026-11-15", toplar=[3, 14, 22, 38, 47, 59])
        with tempfile.TemporaryDirectory() as t:
            eski = sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH
            sl.KARNE_PATH = Path(t) / "karne.csv"
            sl.DEGERLENDIRME_PATH = Path(t) / "son.md"
            sl.KURAL_KARNESI_PATH = Path(t) / "kural.csv"
            try:
                with redirect_stdout(io.StringIO()):
                    sl.degerlendir_ve_kaydet(CEKILISLER + [uygun], "")
                self.assertIn("Kemik yapıya uyan çekiliş: 1/1",
                              sl.DEGERLENDIRME_PATH.read_text(encoding="utf-8"))
            finally:
                sl.KARNE_PATH, sl.DEGERLENDIRME_PATH, sl.KURAL_KARNESI_PATH = eski


if __name__ == "__main__":
    unittest.main()
