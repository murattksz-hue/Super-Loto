# Çekiliş değerlendirmesi: #990 (2026-11-26)

Çıkan numaralar: **10 - 17 - 28 - 32 - 33 - 42** (toplam 162, 2 tek / 4 çift, 1 ardışık ikili, önceki çekilişten 0 tekrar)

## Bu çekiliş normal mi?

- Dikkat çekici: 33 numara 30 çekiliş aradan sonra geldi

Bu durumlar seyrek ama rastgele bir çekilişte de beklenir: her çekilişte bakılan birkaç özellikten birinin %5'lik dilime düşmesi olağandır.

Aynı dizilimde (onluk dağılımı, tek sayısı, ardışıklar) geçmiş çekiliş sayısı: 0.
Güç dengesi: 1 güçlü / 2 orta / 3 zayıf numara.

## Kurallarımıza uyuyor muydu?

Evet, kemik yapıya uyuyor. Tüm kurallar modu bu dizilimde bir kolon üretebilirdi.

## Kupon

10 kolondan en iyisi **1 bildi**. Dağılım: 1 bilen 5 kolon, 0 bilen 5 kolon.
Rastgele 10 kolonla beklenen: en az bir kolonda 3 bilme yaklaşık %10, 4 bilme %0,45.

## Karne

Değerlendirilen çekiliş: 6
- Kemik yapıya uyan çekiliş: 4/6 (geçmişin tamamında %67)
- Dikkat çekici durumu olan çekiliş: 2/6
- Kupon oynanan çekiliş: 5; en az bir kolonda 3+ bilen: 0 (rastgele beklenen ~0.5)
- En iyi kolon dağılımı: 2 bilen 4 kez, 1 bilen 1 kez

## Kural karnesi

Her kural tüm geçmiş çekilişlerle karşılaştırılır (güç dengesi ve gecikme son 300 çekilişte, her biri kendinden önceki veriyle).

| Kural | Gerçek çekilişlerde uyan | Rastgele numaralarda uyan | Fark |
|---|---|---|---|
| Tek sayı adedi | %97,1 | %97,5 | yok |
| 1–30 arasından adet | %97,4 | %97,5 | yok |
| Aynı onluk | %95,6 | %96,7 | yok |
| Aynı son hane | %89,6 | %89,8 | yok |
| Toplam | %80,1 | %80,0 | yok |
| Ardışık ikili | %99,1 | %99,4 | yok |
| Son çekilişten tekrar | %98,7 | %98,9 | yok |
| Kemik yapının tamamı | %66,9 | %67,9 | yok |
| Güç dengesi 2/2/2 | %14,3 | %15,3 | yok |
| Uzun süredir çıkmayanlardan en fazla 1 | %73,3 | %74,7 | yok |

## Analizler: 60 numara penceresi

Son çekilişten geriye 60 numaranın hepsinin geldiği çekilişler: #950–#990 (2026-08-25 – 2026-11-26, 41 çekiliş). Bütün analizler bu pencere üzerinden yapılır; tüm geçmiş ve rastgele beklenen karşılaştırma içindir. Kural değildir.

### 1–30 / 31–60

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 6–0 | 0 | %0,0 | %1,2 | %1,2 |  |
| 5–1 | 4 | %9,8 | %8,1 | %8,5 |  |
| 4–2 | 5 | %12,2 | %24,5 | %23,8 |  |
| 3–3 | 11 | %26,8 | %31,2 | %32,9 |  |
| 2–4 | 19 | %46,3 | %25,6 | %23,8 | belirgin |
| 1–5 | 1 | %2,4 | %8,0 | %8,5 |  |
| 0–6 | 1 | %2,4 | %1,4 | %1,2 |  |

### Tek / çift

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 6–0 | 0 | %0,0 | %1,4 | %1,2 |  |
| 5–1 | 4 | %9,8 | %8,8 | %8,5 |  |
| 4–2 | 8 | %19,5 | %24,6 | %23,8 |  |
| 3–3 | 11 | %26,8 | %30,6 | %32,9 |  |
| 2–4 | 14 | %34,1 | %24,7 | %23,8 |  |
| 1–5 | 4 | %9,8 | %8,4 | %8,5 |  |
| 0–6 | 0 | %0,0 | %1,5 | %1,2 |  |

### Asal sayısı

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 0 | 5 | %12,2 | %10,1 | %12,2 |  |
| 1 | 15 | %36,6 | %37,3 | %32,7 |  |
| 2 | 11 | %26,8 | %31,2 | %33,5 |  |
| 3 | 7 | %17,1 | %16,4 | %16,8 |  |
| 4+ | 3 | %7,3 | %5,0 | %4,8 |  |

### Ardışık ikili

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 0 | 25 | %61,0 | %58,1 | %57,9 |  |
| 1 | 14 | %34,1 | %33,7 | %34,7 |  |
| 2 | 2 | %4,9 | %7,3 | %6,8 |  |
| 3+ | 0 | %0,0 | %0,9 | %0,5 |  |

### Üst üste (önceki çekilişten)

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 0 | 22 | %53,7 | %50,4 | %51,6 |  |
| 1 | 13 | %31,7 | %37,3 | %37,9 |  |
| 2 | 5 | %12,2 | %11,0 | %9,5 |  |
| 3+ | 1 | %2,4 | %1,3 | %1,0 |  |

### Aynı onluktan en çok

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 1 | 1 | %2,4 | %1,9 | %2,0 |  |
| 2 | 29 | %70,7 | %65,6 | %67,0 |  |
| 3 | 10 | %24,4 | %28,0 | %27,7 |  |
| 4+ | 1 | %2,4 | %4,4 | %3,3 |  |

### Aynı son haneden en çok

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 1 | 6 | %14,6 | %20,1 | %19,6 |  |
| 2 | 28 | %68,3 | %69,5 | %70,3 |  |
| 3 | 7 | %17,1 | %10,0 | %9,8 |  |
| 4+ | 0 | %0,0 | %0,4 | %0,4 |  |

### Toplam

| Değer | Pencere (41) | Oran | Tüm geçmiş | Rastgele | Fark |
|---|---|---|---|---|---|
| 150'den az | 5 | %12,2 | %20,7 | %21,1 |  |
| 150–179 | 7 | %17,1 | %24,9 | %25,7 |  |
| 180–209 | 10 | %24,4 | %29,3 | %27,1 |  |
| 210–239 | 15 | %36,6 | %17,2 | %17,6 | belirgin |
| 240 ve üstü | 4 | %9,8 | %7,9 | %8,4 |  |

### Numara sıklığı

- 9 kez: 16
- 8 kez: 30 59
- 7 kez: 42 43 52
- 6 kez: 14 17 31 46 54 56
- 5 kez: 3 7 12 18 19 27 28 32 38 39 51 53
- 4 kez: 2 10 15 23 25 40 45 47 50 57 60
- 3 kez: 9 20 22 33 34 35 37 41 44 48 49 55 58
- 2 kez: 1 5 6 8 21 24 26 29 36
- 1 kez: 4 11 13

**Birlikte gelen (2+ kez):** 14-56 (3), 17-39 (3), 28-42 (3), 28-59 (3), 30-42 (3), 30-59 (3), 40-42 (3), 42-59 (3), 45-54 (3), 2-12 (2), 2-47 (2), 3-15 (2), 3-18 (2), 3-20 (2), 7-14 (2), 7-40 (2), 7-42 (2), 9-17 (2), 10-38 (2), 12-19 (2), 12-52 (2), 14-40 (2), 14-42 (2), 14-43 (2), 14-52 (2), 15-50 (2), 15-52 (2), 16-22 (2), 16-25 (2), 16-30 (2), 16-38 (2), 16-43 (2), 16-46 (2), 16-52 (2), 16-55 (2), 16-56 (2), 16-58 (2), 16-59 (2), 17-28 (2), 17-31 (2), 17-32 (2), 18-28 (2), 18-59 (2), 19-46 (2), 19-51 (2), 22-43 (2), 23-47 (2), 25-46 (2), 27-41 (2), 27-52 (2), 28-30 (2), 30-40 (2), 30-41 (2), 30-50 (2), 31-34 (2), 31-53 (2), 31-55 (2), 32-39 (2), 32-49 (2), 32-51 (2), 32-54 (2), 38-50 (2), 39-54 (2), 42-45 (2), 42-47 (2), 43-46 (2), 43-56 (2), 46-59 (2), 47-59 (2), 50-59 (2), 51-52 (2), 53-54 (2), 54-56 (2), 54-60 (2)
**Üst üste gelen:** 30 (3), 16 (2), 34 (2), 51 (2), 3 (1), 12 (1), 13 (1), 14 (1), 18 (1), 19 (1), 23 (1), 24 (1), 27 (1), 32 (1), 40 (1), 42 (1), 43 (1), 45 (1), 47 (1), 52 (1), 54 (1)
**Ardışık ikili:** 51-52 (2), 53-54 (2), 7-8 (1), 8-9 (1), 9-10 (1), 14-15 (1), 17-18 (1), 26-27 (1), 30-31 (1), 31-32 (1), 32-33 (1), 43-44 (1), 54-55 (1), 55-56 (1), 56-57 (1), 59-60 (1)
**En uzun süredir gelmeyen:** 13 (40 çekiliş), 6 (27 çekiliş), 26 (26 çekiliş), 44 (26 çekiliş), 15 (24 çekiliş), 34 (23 çekiliş), 20 (22 çekiliş), 11 (21 çekiliş), 55 (20 çekiliş), 31 (18 çekiliş)
**Özet:** Toplam ortalaması: 196,3, En düşük toplam: 103, En yüksek toplam: 290, Ortalama tek sayı: 2,85, Ortalama asal sayı: 1,73, Kemik yapıya uyan: 27

## Lastik sayılar

Uzun süredir gelmeyen numaralar (izleme, kural değil). Gergin: 22+ çekiliş (bu kadar uzun ara ~%10), çok gergin: 29+ (~%5), kopma sınırında: 44+ (~%1). Tarihteki en uzun ara 71.

| Numara | Kaç çekiliştir yok | Seviye | Kendi rekoru | Bu kadar uzun ara olasılığı |
|---|---|---|---|---|
| 13 | 40 | çok gergin | 56 | %1,48 |
| 6 | 27 | gergin | 39 | %5,81 |
| 26 | 26 | gergin | 56 | %6,46 |
| 44 | 26 | gergin | 29 | %6,46 |
| 15 | 24 | gergin | 60 | %7,98 |
| 34 | 23 | gergin | 48 | %8,86 |
| 20 | 22 | gergin | 46 | %9,85 |

**Lastikler kopuyor mu?** Geçmişte bir numara lastikken sonraki çekilişte gelme oranı (rastgele beklenen %10):
- gergin: 5504 durumda 555 kez geldi, %10,1
- çok gergin: 2617 durumda 268 kez geldi, %10,2
- kopma sınırında: 505 durumda 57 kez geldi, %11,3

## Döngü kuralı

Döngü: 60 numaranın hepsinin geldiği ardışık çekilişler. Döngü kuralı: tüm kurallar modunda bu döngüde henüz gelmeyen numaralar mümkün olduğunca aynı kolonlarda toplanır.

**Şu anki döngü:** #986'dan beri 5 çekiliş, 60 numaranın 24 tanesi geldi.
**Sıradaki tahmin (bu döngüde henüz gelmeyen 36 numara):** 1 4 5 6 7 8 11 13 14 15 16 20 22 23 26 27 29 31 34 36 37 38 40 41 43 44 45 48 49 52 53 54 55 56 57 60
Son 1,5 yılın döngü ortalaması 37,0 çekiliş (tüm geçmiş 44,0); buna göre döngünün tamamlanmasına yaklaşık 32 çekiliş kaldı.

**Tahmin isabeti:** her çekilişte, o döngüde henüz gelmeyen numaralardan kaçı geldi.
- Takip başladığından beri (4 çekiliş): 18 isabet, rastgele beklenen 18,4.
- Geriye dönük test (967 çekiliş): 1228 isabet, rastgele beklenen 1207,7. Fark yoksa tahmin rastgeleden iyi değildir.

| Döngü | Çekilişler | Başlangıç | Kaç çekilişte | Son tamamlayan |
|---|---|---|---|---|
| 22 | #950–#985 | 2026-08-25 | 36 | 24 |
| 21 | #911–#949 | 2026-05-26 | 39 | 42 |
| 20 | #870–#910 | 2026-02-19 | 41 | 4 24 |
| 19 | #833–#869 | 2025-11-25 | 37 | 14 60 |
| 18 | #803–#832 | 2025-09-16 | 30 | 27 |
| 17 | #764–#802 | 2025-06-17 | 39 | 48 |
| 16 | #725–#763 | 2025-03-18 | 39 | 8 |
| 15 | #680–#724 | 2024-12-03 | 45 | 27 |
| 14 | #634–#679 | 2024-08-18 | 46 | 23 |
| 13 | #601–#633 | 2024-06-02 | 33 | 59 |

## Öneriler

- Hiçbir kural gerçek çekilişlerde rastgele numaralardan belirgin farklı davranmıyor. Kurallar kazanma ihtimalini değiştirmez, yalnızca düzen sağlar.
- Kendi kuponlarımızın sonucu için 5 çekiliş var; rastgele beklentiyle anlamlı karşılaştırma için en az 30 kuponlu çekiliş gerekiyor.

Not: Her çekiliş bağımsızdır; bu değerlendirme geçmişi özetler, sonraki çekilişi tahmin etmez.
