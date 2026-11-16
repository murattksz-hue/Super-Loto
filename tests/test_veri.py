"""Siteden çekilen verinin doğrulanması (güvenilmeyen veri)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import superloto as sl  # noqa: E402


def sayfa(*cekilisler):
    """Sitedeki çekiliş tablosunu taklit eden küçük bir HTML parçası."""
    parcalar = []
    for no, tarih, toplar in cekilisler:
        toplar_html = "".join(f'<img src="/v8/images/balls/2/b{t}.gif">' for t in toplar)
        parcalar.append(f"<b>{no}.Çekiliş[{no}] - {tarih} Süper Loto Çekiliş Sonuçları</b>{toplar_html}")
    return "<html>" + "".join(parcalar) + "</html>"


class SayfaCozTest(unittest.TestCase):
    def test_gecerli_cekilis_okunur(self):
        sonuc = sl.sayfayi_coz(sayfa((984, "12 Kasım 2026", [56, 16, 25, 27, 29, 52])))
        self.assertEqual(sonuc, [{"no": 984, "tarih": "2026-11-12", "toplar": [16, 25, 27, 29, 52, 56]}])

    def test_tekrarlanan_numara_reddedilir(self):
        with self.assertRaises(ValueError):
            sl.sayfayi_coz(sayfa((500, "29 Ekim 2023", [7, 12, 20, 25, 48, 48])))

    def test_aralik_disi_numara_reddedilir(self):
        with self.assertRaises(ValueError):
            sl.sayfayi_coz(sayfa((501, "1 Kasım 2023", [0, 12, 20, 25, 48, 61])))

    def test_gecersiz_tarih_reddedilir(self):
        with self.assertRaises(ValueError):
            sl.sayfayi_coz(sayfa((502, "31 Şubat 2024", [1, 2, 3, 4, 5, 6])))


if __name__ == "__main__":
    unittest.main()
