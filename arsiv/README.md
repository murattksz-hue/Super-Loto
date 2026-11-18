# Kupon analizi arşivi

## kupon_analizi_10000.csv

10.000 kuponluk büyük analiz (18 Kasım 2026). Her kupon 60 sayının hepsini 10 kolonda içerir ve sistemin tüm kurallarıyla (taklitçi, kemik, farklı düzen, döngü) #1–#986 verisiyle üretildi (`taklit_uret`, tohum = kupon no).

Her kupon geçmiş 986 çekilişin hepsiyle test edildi. Kolonun taklit ettiği şablon çekiliş sayılmadı.

| Sütun | Anlamı |
|---|---|
| kupon | Kupon no (üretim tohumu) |
| kolon1–kolon10 | Kolonlar |
| sablonlar | Her kolonun taklit ettiği çekiliş no |
| bilen2–bilen6 | 986 çekilişte o kadar bilen kolon sayısı |
| son200_bilen3–5 | Son 200 çekilişte (#787–#986) aynı sayılar |
| isabet_4plus | 4+ bilen her isabet: çekiliş / kolon / bilen |

Özet: ortalama kupon 932 kez 2, 96,6 kez 3, 4,3 kez 4 bildi. 9.410 kupon hiç 5 bilmedi, 564 kupon 1 kez, 24 kupon 2 kez, 2 kupon 3 kez 5 bildi. 1 kupon (#8690) #985'te 6 bildi.

En iyi 100 kupon: `../en_iyi_100_kupon.md`.
