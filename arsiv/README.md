# Kupon analizi arşivi

Tüm analizlerin özeti: `analizler.md`.

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

Kupon bazında sıralama yapılmadı; kolonlar esas alındı (aşağıya bakın).

## kolon_analizi.csv

Aynı 10.000 kuponun 100.000 kolonu, kolon bazında (41.546 farklı kolon; aynı kolon birden çok kuponda çıkabiliyor). 3'ü geçemeyen (986 çekilişte hiç 4 bilmemiş) 27.254 kolon silindi; 14.292 kolon kaldı. Her kolon için 986 çekilişte 2–6 bilme sayıları, son 200 çekiliş, 4+ isabetler (`#çekiliş/bilen`) ve hangi kuponlarda geçtiği (`kupon/kolon no`). 5, 4, 3 bilmeye göre sıralı.

En iyi kolonlar: `../en_iyi_kolonlar.md`.
