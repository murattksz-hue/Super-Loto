![520 – Süper Loto](520.png)

# Süper Loto

Süper Loto (6/60) çekiliş sonuçlarını indiren, analiz eden ve 60 numaranın hepsini kullanan 10 kolon öneren bir Python scripti. Sadece Python standart kütüphanesini kullanır; kurulum gerektirmez.

> **Not:** Her çekiliş bağımsızdır. Bu analizler geçmişi özetler, geleceği tahmin etmez. Geriye dönük testlerde hiçbir analiz rastgele oynamaktan daha iyi sonuç vermedi. Oynayacaksanız, kaybetmeyi göze alabileceğiniz bir bütçeyle oynayın.

## Kullanım

```bash
python3 superloto.py                    # yeni çekilişleri indir + analiz raporu
python3 superloto.py --analiz           # indirmeden analiz
python3 superloto.py --son 100          # son 100 çekilişin analizi
python3 superloto.py --yil 2026         # sadece 2026 çekilişlerinin analizi
python3 superloto.py --yillik           # yıllara göre özet tablo
python3 superloto.py --kolon            # 60 numaranın hepsini kullanan 10 kolon
python3 superloto.py --kolon --set 3    # tek seferde birbirinden farklı 3 set (30 kolon)
python3 superloto.py --kolon --sifirla  # bu çekiliş için verilen kolonları unut
python3 superloto.py --kolon --tohum 5  # aynı tohum her seferinde aynı kolonları verir
python3 superloto.py --taklitci         # geçmiş çekilişleri (son yıl ağırlıklı) taklit eden 10 kolon
python3 superloto.py --taklitci --set 3 # taklitçi kuralla birbirinden farklı 3 set
```

## Analiz raporu

- En çok ve en az çıkan numaralar, uzun süredir çıkmayanlar
- Birlikte en çok çıkan ikili, üçlü, dörtlü ve beşli gruplar; aynı 6 numaranın tekrarı
- Tek/çift ve ardışık sayı dağılımları
- Onlu gruplar ve son haneler
- Bir önceki çekilişten tekrar eden numaralar
- Takip listesi: son çekilişteki numaralardan sonra en çok/en az gelenler
- Haftanın gününe göre en çok/en az çıkanlar
- Numara toplamları ve ki-kare rastgelelik testi
- Yıllık özet tablosu (`--yillik`)

## Kolon üretici (`--kolon`)

60 numaranın her birini tam bir kez kullanarak 10 kolon üretir. Numaralar önce rastgele dağıtılır, sonra her kolon şu kurallara uydurulur:

- **Güç dengesi:** Her numaraya altı sıralamanın ortalamasından puan verilir: tüm zamanlar, son 1 yıl, son 4 ay, bu yıl, sonraki çekilişin haftanın günü ve takip listesi. Her kolonda 2 güçlü, 2 orta ve 2 zayıf numara olur.
- **Uzun süredir çıkmayanlar:** En uzun süredir çıkmayan 10 numaradan her kolonda en fazla 1 olur.
- **Kemik yapı:** 2–4 tek sayı, 1–30 arasından 2–4 sayı, aynı onluda ve aynı son haneden en fazla 2 sayı, toplam 150–215, en fazla 1 ardışık ikili, son çekilişten en fazla 2 numara.
- **Birlikte çıkanlar:** Kurallar bozulmadan, geçmişte birlikte çok çıkan numaralar aynı kolona toplanır.
- **Farklı düzen:** Script, aynı çekiliş için verdiği kolonları `kolon_gecmisi.json` dosyasında hatırlar. Yeni istenen her set, daha önce verilen kolonların her biriyle en fazla 2 numara paylaşır. Bir sonraki çekilişe geçildiğinde bu hafıza kendiliğinden sıfırlanır. `--tohum` verilirse hafıza kullanılmaz.

Bu kurallar kazanma ihtimalini değiştirmez; seçimi düzenli hale getirir.

## Taklitçi kural (`--taklitci`)

Geleceği göremeyiz ama geçmişte çıkan sayıların geliş biçimini taklit edebiliriz. Her kolon, geçmişte gerçekten çıkmış bir çekilişi şablon alır ve onun dizilimini taklit eder. Şablonlar tüm geçmişten seçilir ama son yıl ağırlıklıdır: 10 şablonun 7'si son 1 yıldan (156 çekiliş), 3'ü önceki yıllardan gelir.

- **Birebir aynı:** hangi onluktan kaç sayı geldiği, tek sayı adedi, ardışık ikili adedi ve aynı son haneli sayı adedi.
- **Yakın:** 6 numaranın toplamı, şablonunkinden en fazla ±6 farklı.
- 60 numaranın hepsi yine tam bir kez kullanılır. Bunun için 10 şablon çekiliş, onluk dağılımları ve tek sayıları 60 numarayı tam dolduracak şekilde seçilir.
- Çıktıda her kolonun yanında taklit ettiği çekilişin tarihi ve numaraları yazar.
- Farklı düzen kuralı burada da geçerlidir: aynı çekiliş için verilen her yeni kolon, öncekilerin her biriyle en fazla 2 numara paylaşır.

Geriye dönük testte (828 çekiliş) taklitçi kolonlar rastgele kolonlarla şans payı içinde aynı sonucu verdi.

## Dosyalar

- `superloto.py`: script
- `superloto.csv`: 2 Ağustos 2020'den bu yana bütün Süper Loto çekilişleri (çekiliş no, tarih, 6 numara)
- `superloto_rapor.txt`: en son analiz raporu ve yıllık özet

## Otomatik güncelleme

`.github/workflows/superloto.yml`, her Süper Loto çekilişinin ertesi sabahı (Pazartesi, Çarşamba, Cuma 08:23 TR) scripti çalıştırır. Yeni çekiliş varsa `superloto.csv` ve `superloto_rapor.txt` dosyalarını günceller. Actions sekmesinden "Run workflow" ile elle de çalıştırılabilir.
