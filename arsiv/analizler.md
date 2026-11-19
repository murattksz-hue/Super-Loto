# Analiz arşivi (17–18 Kasım 2026)

Bu oturumda yapılan bütün kupon ve kolon analizleri. Aksi yazılmadıkça testler `superloto.csv`'deki gerçek çekilişlerle (#1–#986) yapıldı. Bazı erken testler rastgele (kurgu) çekiliş de kullanmıştı; bunlar **[kurgu]** diye işaretli ve `CLAUDE.md` kuralına göre artık kullanılmıyor.

Kolon kuralları (aksi yazılmadıkça): kemik yapı, kolonda 2–4 tek, 1–3 asal, kolonlar arası tekrar eden ikili yok. Taklitçi kurallı kuponlarda kolonun şablon çekilişi sayılmadı.

## 1. 60 sayı mı, 50 sayı mı?

- **[kurgu]** 300.000 rastgele çekiliş: 60 sayı en az bir 3+ %10,35, 50 sayı (10 rastgele dışarıda) %10,22.
- Gerçek çekilişler #101–#986 (886): 60 sayı %10,33; 50 rastgele %10,67; 50 lastik dışarıda %10,05; 50 pencerede en çok çıkan dışarıda %10,23.
- Tüm kurallarla 50 sayılık kupon taklitçi üreticiyle çoğu çekilişte üretilemedi.

## 2. 40 ve 30 sayılık kuponlar (her çekiliş için o güne kadarki verilerle yeniden kuruldu)

| Test | Aralık | En az bir kolonda 3+ | 4+ |
|---|---|---|---|
| En iyi 40 (pencerede en sık 40) | son 150 | 19 (%12,7) | 2 |
| Rastgele 40 | son 150 | 14 (%9,3) | 0 |
| Kurallı 40 (döngü eksikleri, tek/çift, asal, 1–30/31–60, sık/az) | son 150 | 13 (%8,7) | 1 |
| Rastgele 40 | son 150 | 10 (%6,7) | 1 |
| Kurallı 30 | son 100 | 9 (%9) | 1 |
| Rastgele 30 | son 100 | 7 (%7) | 0 |

## 3. 50 sayılık yöntemler (#101–#986, 886 çekiliş, en az bir kolonda)

| Yöntem | 3+ | 4+ | 5+ |
|---|---|---|---|
| A: kurallı 50 | 90 (%10,2) | 5 | 0 |
| B: sıcak 50 (en az çıkan 10 dışarıda) | 73 (%8,2) | 2 | 0 |
| C: soğuk 50 (en çok çıkan 10 dışarıda) | 86 (%9,7) | 5 | 0 |
| D: son 2 çekilişin sayılarından 10 dışarıda | 87 (%9,8) | 4 | 0 |
| E: en uzun süredir çıkmayan 10 dışarıda | 86 (%9,7) | 3 | 0 |
| F: son 10 çekilişte en çok çıkan 10 dışarıda | 110 (%12,4) | 2 | 0 |
| F, farklı tohumla | 95 (%10,7) | 7 | 0 |
| G: rastgele 10 dışarıda | 79 (%8,9) | 1 | 0 |

## 4. Sabit kuponlar 986 çekilişin hepsiyle (kolon bazında)

| Kupon | 3 | 4 | 5 |
|---|---|---|---|
| 50 sayı A | 93 | 4 | 0 |
| 50 sayı C | 104 | 2 | 0 |
| 50 sayı F | 95 | 4 | 0 |
| Kurallı 40 | 105 | 6 | 0 |
| En iyi 40 | 93 | 7 | 0 |
| Yeni kurallı 40 | 104 | 2 | 0 |
| 60 sayı, tüm kurallar (tek kupon) | 98 | 5 | 0 |

## 5. 100, 1.000 ve 10.000 kupon (60 sayı, 10 kolon, tüm kurallar)

- 100 kupon: ortalama 96,6 kez 3, 4,4 kez 4; toplam 7 kez 5. En iyi #84 (2 kez 5).
- 1.000 kupon: ortalama 96,2 kez 3, 4,3 kez 4; 945 kupon hiç 5 bilmedi, 53 kupon 1, 2 kupon 2 kez. En iyi #84 ve #441.
- 10.000 kupon: ortalama 932 kez 2, 96,6 kez 3, 4,3 kez 4; 9.410 kupon hiç 5 bilmedi, 564 kupon 1, 24 kupon 2, 2 kupon 3 kez 5 bildi; 1 kupon (#8690) #985'te 6 bildi. Tüm sonuçlar: `kupon_analizi_10000.csv`.

## 6. Aktif kupon

- 1.000 kupon, geçmiş ikiye bölündü (#1–#493 / #494–#986): iki yarının aktifliği (3+ sayısı) arasındaki korelasyon −0,016. İlk yarıda en aktif 100 kupon ikinci yarıda ortalama 49,6, en soğuk 100 kupon 50,6, tüm kuponlar 50,1 kez 3+ bildi.
- Her çekilişten önce son N çekilişte en aktif kuponu seçip oynama (#201–#986, 786 çekiliş; ortalama kupon 80,4 kez 3+):

| Seçim | 3+ | 4+ | 5+ |
|---|---|---|---|
| Son 5 | 81 | 5 | 0 |
| Son 10 | 78 | 3 | 0 |
| Son 20 | 66 | 0 | 0 |
| Son 50 | 83 | 2 | 0 |
| Son 100 | 88 | 2 | 0 |
| Son 200 | 68 | 1 | 0 |

## 7. 3 bildikten sonra 4–5 gelir mi? (1.000 kuponun 10.000 kolonu)

| 3 bildikten sonraki | 4+ oranı | Diğer zamanlar |
|---|---|---|
| 1 çekiliş | %0,046 | %0,044 |
| 5 çekiliş | %0,043 | %0,044 |
| 10 çekiliş | %0,039 | %0,045 |
| 20 çekiliş | %0,041 | %0,045 |

57 kez 5 bilmenin 14'ünde aynı kolon son 20 çekiliş içinde 3 bilmişti (13 farklı kolon).

## 8. Kolon analizi (10.000 kuponun 100.000 kolonu, 41.546 farklı kolon)

- Toplam: 3.891.624 kez 2, 405.431 kez 3, 17.408 kez 4, 255 kez 5, 1 kez 6.
- Ortalama kolon 9,8 kez 3, 0,42 kez 4 bildi; her kolon en az 1 kez 3 ve en az 57 kez 2 bildi.
- 3'ü geçemeyen (hiç 4 bilmemiş) 27.254 kolon silindi; 14.292 kolon kaldı (`kolon_analizi.csv`). En iyiler: `../en_iyi_kolonlar.md`.
- En iyi kolonlardan 60 sayılık kupon: her listenin ilk 100 ve ilk 300 kolonundan kurulamadı; ilk 1.000'den 1, ilk 3.000'den 4 kupon bulundu (aramalar 20 sn ile sınırlı). İlk 3.000'den kurulan kupon 19 Kasım (#987) için oynandı (`../oyun_kolonlari.txt`).
- Kupon arşivinde 10 kolonunun hepsi kalan kolonlardan olan tek kupon #5859 (99 kez 3, 11 kez 4).
