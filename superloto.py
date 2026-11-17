#!/usr/bin/env python3
"""Süper Loto (6/60) sonuçlarını çeker ve analiz eder.

Kullanım:
    python3 superloto.py            # yeni çekilişleri indir + analiz raporu yazdır
    python3 superloto.py --analiz   # indirmeden, mevcut CSV ile analiz
    python3 superloto.py --son 100  # analizi sadece son 100 çekilişle yap
    python3 superloto.py --yil 2026 # analizi sadece 2026 çekilişleriyle yap
    python3 superloto.py --yillik   # yıllara göre özet tablo
    python3 superloto.py --kolon    # 60 numaranın hepsini kullanan 10 kolon öner
    python3 superloto.py --taklitci # geçmiş çekilişleri (son yıl ağırlıklı) taklit eden 10 kolon
    python3 superloto.py --hepsi    # tüm kurallar birlikte (oynarken önerilen)
    python3 superloto.py --gezegen  # sonraki çekiliş günü Ankara gezegen saatleri
    python3 superloto.py --degerlendir  # son çekilişin değerlendirmesi ve karne

Sonuçlar superloto.csv dosyasına kaydedilir; sonraki çalıştırmalarda sadece
yeni çekilişler indirilir. Sadece Python standart kütüphanesi kullanılır.

Not: Her çekiliş bağımsızdır; bu istatistikler geçmişi özetler, geleceği
tahmin etmez.
"""

import argparse
import contextlib
import csv
import datetime
import functools
import io
import json
import math
import random
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from itertools import combinations
from pathlib import Path

BASE = "https://www.lototurkiye.com/SUPER-LOTO-SISAL/CEKILIS-TABLOLARI/12"
CSV_PATH = Path(__file__).with_name("superloto.csv")
GECMIS_PATH = Path(__file__).with_name("kolon_gecmisi.json")
SAYI_ARALIGI = range(1, 61)
AYLAR = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
    "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
}
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
BASLIK_RE = re.compile(r"\d+\.Çekiliş\[(\d+)\]\s*-\s*(\d{1,2})\s+(\S+)\s+(\d{4})")


def sayfa_getir(url: str, deneme: int = 4) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for i in range(deneme):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("cp1254", errors="ignore")
        except OSError as e:
            if i == deneme - 1:
                raise
            bekle = 2 ** (i + 1)
            print(f"\nBağlantı hatası ({e}); {bekle} sn sonra tekrar...", file=sys.stderr)
            time.sleep(bekle)


def sayfayi_coz(html: str) -> list[dict]:
    """Bir sayfadaki çekilişleri (no, tarih, 6 numara) döndürür.

    Siteden gelen veri güvenilmez kabul edilir: aynı numara iki kez, 1–60
    dışında bir numara ya da geçersiz bir tarih gelirse ValueError verilir
    ve hiçbir şey kaydedilmez. Yanlış veri sessizce CSV'ye girmesin diye.
    """
    parcalar = BASLIK_RE.split(html)
    cekilisler = []
    # split sonucu: [önce, no, gün, ay, yıl, içerik, no, gün, ...]
    for i in range(1, len(parcalar) - 4, 5):
        no, gun, ay, yil, icerik = parcalar[i:i + 5]
        toplar = [int(x) for x in re.findall(r"b(\d+)\.gif", icerik)][:6]
        if len(toplar) != 6 or ay not in AYLAR:
            continue
        if len(set(toplar)) != 6 or not all(1 <= t <= 60 for t in toplar):
            raise ValueError(f"{no} nolu çekilişte geçersiz numaralar: {toplar}")
        try:
            tarih = datetime.date(int(yil), AYLAR[ay], int(gun))
        except ValueError as e:
            raise ValueError(f"{no} nolu çekilişte geçersiz tarih: {gun} {ay} {yil}") from e
        cekilisler.append({"no": int(no), "tarih": tarih.isoformat(), "toplar": sorted(toplar)})
    return cekilisler


def csv_oku() -> dict[int, dict]:
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(encoding="utf-8") as f:
        return {
            int(r["no"]): {
                "no": int(r["no"]),
                "tarih": r["tarih"],
                "toplar": [int(r[f"t{i}"]) for i in range(1, 7)],
            }
            for r in csv.DictReader(f)
        }


def csv_yaz(cekilisler: dict[int, dict]) -> None:
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["no", "tarih", "t1", "t2", "t3", "t4", "t5", "t6"])
        for no in sorted(cekilisler):
            c = cekilisler[no]
            w.writerow([c["no"], c["tarih"], *c["toplar"]])


def guncelle(bekleme: float = 0.5) -> dict[int, dict]:
    """Eksik çekilişleri sondan başa doğru indirir."""
    mevcut = csv_oku()
    son_kayit = max(mevcut, default=0)

    ilk = sayfayi_coz(sayfa_getir(BASE))
    if not ilk:
        sys.exit("Sayfa çözümlenemedi; site yapısı değişmiş olabilir.")
    en_son = max(c["no"] for c in ilk)
    for c in ilk:
        mevcut[c["no"]] = c

    eksik = [n for n in range(1, en_son + 1) if n not in mevcut]
    print(f"Sitedeki son çekiliş: {en_son}, CSV'deki son: {son_kayit}, "
          f"indirilecek: {len(eksik)}", file=sys.stderr)

    while eksik:
        hedef = eksik[-1]  # bu numarayla biten 10'lu sayfa
        for c in sayfayi_coz(sayfa_getir(f"{BASE}/2/{hedef}")):
            mevcut[c["no"]] = c
        if hedef not in mevcut:
            print(f"Uyarı: {hedef} nolu çekiliş bulunamadı, atlanıyor.", file=sys.stderr)
        eksik = [n for n in eksik if n not in mevcut and n != hedef]
        csv_yaz(mevcut)  # yarıda kesilirse kaldığı yerden devam edebilsin
        print(f"  kalan: {len(eksik)}", file=sys.stderr, end="\r")
        time.sleep(bekleme)
    print(file=sys.stderr)

    csv_yaz(mevcut)
    return mevcut


def analiz(cekilisler: list[dict]) -> None:
    n = len(cekilisler)
    if not n:
        sys.exit("Analiz için veri yok.")
    son = cekilisler[-1]
    print(f"Süper Loto analizi: {n} çekiliş "
          f"({cekilisler[0]['tarih']} – {son['tarih']})")
    print(f"Son çekiliş #{son['no']} ({son['tarih']}): "
          + " - ".join(map(str, son["toplar"])))

    frekans = Counter(t for c in cekilisler for t in c["toplar"])
    beklenen = n * 6 / 60
    son_gorulme = {}
    for i, c in enumerate(cekilisler):
        for t in c["toplar"]:
            son_gorulme[t] = i
    gecikme = {t: n - 1 - son_gorulme.get(t, -1) for t in SAYI_ARALIGI}

    print(f"\nOrtalama (beklenen) çıkış sayısı: {beklenen:.1f}")
    print("\nEn çok çıkan 10 numara:")
    for t, k in sorted(frekans.items(), key=lambda x: (-x[1], x[0]))[:10]:
        print(f"  {t:2d}: {k} kez")
    print("\nEn az çıkan 10 numara:")
    for t in sorted(SAYI_ARALIGI, key=lambda t: (frekans[t], t))[:10]:
        print(f"  {t:2d}: {frekans[t]} kez")

    print("\nEn uzun süredir çıkmayan 10 numara:")
    for t in sorted(SAYI_ARALIGI, key=lambda t: (-gecikme[t], t))[:10]:
        print(f"  {t:2d}: {gecikme[t]} çekiliştir çıkmıyor")

    gruplar = [(2, "ikili", 10), (3, "üçlü", 10), (4, "dörtlü", 5), (5, "beşli", 5)]
    for boyut, ad, adet in gruplar:
        sayac = Counter(p for c in cekilisler for p in combinations(c["toplar"], boyut))
        print(f"\nBirlikte en çok çıkan {adet} {ad}:")
        for grup, k in sorted(sayac.items(), key=lambda x: (-x[1], x[0]))[:adet]:
            print(f"  {'-'.join(f'{t:2d}' for t in grup)}: {k} kez")
    tekrar_6 = sum(1 for k in Counter(tuple(c["toplar"]) for c in cekilisler).values() if k > 1)
    print(f"\nAynı 6 numaranın tekrar çıktığı kombinasyon sayısı: {tekrar_6}")

    tek = Counter(sum(t % 2 for t in c["toplar"]) for c in cekilisler)
    print("\nTek/çift dağılımı (tek sayı adedi):")
    for k in range(7):
        print(f"  {k} tek / {6 - k} çift: {tek[k]:4d} (%{100 * tek[k] / n:.1f})")

    def ardisik_ikili(toplar):
        return sum(1 for a, b in zip(toplar, toplar[1:]) if b - a == 1)
    ardisik = Counter(ardisik_ikili(c["toplar"]) for c in cekilisler)
    print("\nArdışık ikili sayısı:")
    for k in sorted(ardisik):
        print(f"  {k}: {ardisik[k]:4d} (%{100 * ardisik[k] / n:.1f})")

    print("\nOnlu gruplara göre çıkış adedi:")
    for bas in range(1, 61, 10):
        k = sum(frekans[t] for t in range(bas, bas + 10))
        print(f"  {bas:2d}-{bas + 9:2d}: {k:5d} (%{100 * k / (6 * n):.1f})")

    print("\nSon haneye göre çıkış adedi:")
    for h in range(10):
        k = sum(frekans[t] for t in SAYI_ARALIGI if t % 10 == h)
        print(f"  ...{h}: {k:5d}")

    tekrar = Counter(len(set(a["toplar"]) & set(b["toplar"]))
                     for a, b in zip(cekilisler, cekilisler[1:]))
    print("\nBir önceki çekilişten tekrar eden numara sayısı:")
    for k in sorted(tekrar):
        print(f"  {k}: {tekrar[k]:4d} (%{100 * tekrar[k] / (n - 1):.1f})")

    print("\nTakip listesi: son çekilişteki numaralar çıktıktan sonraki "
          "çekilişte en çok / en az gelenler:")
    for x in son["toplar"]:
        takip = Counter()
        adet = 0
        for a, b in zip(cekilisler, cekilisler[1:]):
            if x in a["toplar"]:
                adet += 1
                takip.update(b["toplar"])
        if not adet:
            print(f"  {x:2d}: daha önce çıkmamış")
            continue
        sirali = sorted(SAYI_ARALIGI, key=lambda t: (-takip[t], t))
        cok = ", ".join(f"{t} ({takip[t]})" for t in sirali[:5])
        az = ", ".join(f"{t} ({takip[t]})" for t in sirali[-3:])
        print(f"  {x:2d} ({adet} kez, beklenen ~{adet / 10:.1f}): en çok {cok} | en az {az}")

    haftanin_gunu(cekilisler)

    toplamlar = sorted(sum(c["toplar"]) for c in cekilisler)
    ort = sum(toplamlar) / n
    print(f"\nNumara toplamları: en düşük {toplamlar[0]}, en yüksek {toplamlar[-1]}, "
          f"ortalama {ort:.1f}, ortanca {toplamlar[n // 2]}")
    print(f"  Çekilişlerin %50'si {toplamlar[n // 4]}–{toplamlar[3 * n // 4]} aralığında")

    # Ki-kare: numaralar eşit olasılıkla mı çıkıyor?
    ki2 = sum((frekans[t] - beklenen) ** 2 / beklenen for t in SAYI_ARALIGI)
    print(f"\nKi-kare istatistiği (sd=59): {ki2:.1f}  "
          f"(~%95 eşiği 77.9; altındaysa dağılım rastgelelikle uyumlu)")


def ki_kare_esik(sd: int) -> float:
    """Ki-kare dağılımının ~%95 eşiği (Wilson-Hilferty yaklaşımı)."""
    return sd * (1 - 2 / (9 * sd) + 1.645 * (2 / (9 * sd)) ** 0.5) ** 3


def haftanin_gunu(cekilisler: list[dict], en_az_cekilis: int = 30) -> None:
    """Haftanın her çekiliş günü için en çok/en az çıkan numaralar."""
    gunler: dict[int, list[dict]] = {}
    for c in cekilisler:
        gun = datetime.date.fromisoformat(c["tarih"]).weekday()
        gunler.setdefault(gun, []).append(c)

    print("\nHaftanın gününe göre en çok / en az çıkanlar:")
    yeterli = {g: l for g, l in gunler.items() if len(l) >= en_az_cekilis}
    for gun in sorted(gunler):
        liste = gunler[gun]
        if gun not in yeterli:
            print(f"  {GUNLER[gun]}: {len(liste)} çekiliş (analiz için az, atlandı)")
            continue
        f = Counter(t for c in liste for t in c["toplar"])
        sirali = sorted(SAYI_ARALIGI, key=lambda t: (-f[t], t))
        cok = ", ".join(f"{t} ({f[t]})" for t in sirali[:5])
        az = ", ".join(f"{t} ({f[t]})" for t in sirali[-3:])
        print(f"  {GUNLER[gun]} ({len(liste)} çekiliş, beklenen ~{len(liste) * 6 / 60:.1f}): "
              f"en çok {cok} | en az {az}")

    # Bağımsızlık testi: numaraların dağılımı güne göre değişiyor mu?
    if len(yeterli) < 2:
        return
    toplam = Counter(t for l in yeterli.values() for c in l for t in c["toplar"])
    n_toplam = sum(len(l) for l in yeterli.values())
    ki2 = 0.0
    for liste in yeterli.values():
        f = Counter(t for c in liste for t in c["toplar"])
        for t in SAYI_ARALIGI:
            beklenen = toplam[t] * len(liste) / n_toplam
            if beklenen:
                ki2 += (f[t] - beklenen) ** 2 / beklenen
    sd = 59 * (len(yeterli) - 1)
    print(f"  Ki-kare (sd={sd}): {ki2:.1f}  (~%95 eşiği {ki_kare_esik(sd):.1f}; "
          f"altındaysa numaralar günden bağımsız)")


def yillik_ozet(cekilisler: list[dict]) -> None:
    """Her yıl için çekiliş sayısı, en çok/en az çıkanlar ve ortalama toplam."""
    yillar: dict[str, list[dict]] = {}
    for c in cekilisler:
        yillar.setdefault(c["tarih"][:4], []).append(c)

    print("Süper Loto yıllara göre özet")
    print(f"{'Yıl':<6}{'Çekiliş':>8}  {'En çok çıkanlar':<26}"
          f"{'En az çıkanlar':<26}{'Ort. toplam':>11}")
    for yil, liste in sorted(yillar.items()):
        f = Counter(t for c in liste for t in c["toplar"])
        en_cok = max(f[t] for t in SAYI_ARALIGI)
        en_az = min(f[t] for t in SAYI_ARALIGI)
        cok = ",".join(str(t) for t in SAYI_ARALIGI if f[t] == en_cok)
        az = ",".join(str(t) for t in SAYI_ARALIGI if f[t] == en_az)
        ort = sum(sum(c["toplar"]) for c in liste) / len(liste)
        kismi = " (kısmi yıl)" if len(liste) < 150 else ""
        print(f"{yil:<6}{len(liste):>8}  {f'{cok} ({en_cok} kez)':<26}"
              f"{f'{az} ({en_az} kez)':<26}{ort:>11.1f}{kismi}")


CEKILIS_GUNLERI = (1, 3, 6)  # Salı, Perşembe, Pazar


def sonraki_cekilis(tarih: str) -> datetime.date:
    gun = datetime.date.fromisoformat(tarih)
    while True:
        gun += datetime.timedelta(days=1)
        if gun.weekday() in CEKILIS_GUNLERI:
            return gun


def numara_analizi(cekilisler: list[dict]) -> dict:
    """Kolon üretimi için bütün analizlerden numara bilgilerini toplar.

    Güç puanı, şu sıralamaların yüzdelik ortalamasıdır: tüm zamanlar, son 1 yıl
    (156 çekiliş), son 4 ay (52 çekiliş), bu yıl, sonraki çekilişin haftanın
    gününde çıkış adedi ve takip listesi (son çekilişteki numaralardan sonra
    gelme adedi). En güçlü 20 numara "G", en zayıf 20 numara "Z", kalanlar "O".
    """
    son = cekilisler[-1]
    yil = son["tarih"][:4]
    sonraki = sonraki_cekilis(son["tarih"])
    sonraki_gun = sonraki.weekday()

    def sayac(liste):
        return Counter(t for c in liste for t in c["toplar"])

    takip = Counter()
    for a, b in zip(cekilisler, cekilisler[1:]):
        ortak = len(set(a["toplar"]) & set(son["toplar"]))
        for t in b["toplar"]:
            takip[t] += ortak
    olcutler = {
        "tüm zamanlar": sayac(cekilisler),
        "son 1 yıl": sayac(cekilisler[-156:]),
        "son 4 ay": sayac(cekilisler[-52:]),
        f"{yil} yılı": sayac([c for c in cekilisler if c["tarih"].startswith(yil)]),
        f"{GUNLER[sonraki_gun]} günleri": sayac(
            [c for c in cekilisler
             if datetime.date.fromisoformat(c["tarih"]).weekday() == sonraki_gun]),
        "takip listesi": takip,
    }
    puan = {t: 0.0 for t in SAYI_ARALIGI}
    for f in olcutler.values():
        for sira, t in enumerate(sorted(SAYI_ARALIGI, key=lambda t: (f[t], t))):
            puan[t] += sira / 59 / len(olcutler)
    sirali = sorted(SAYI_ARALIGI, key=lambda t: (-puan[t], t))
    seviye = {t: "G" if i < 20 else "O" if i < 40 else "Z" for i, t in enumerate(sirali)}

    son_gorulme = {}
    for i, c in enumerate(cekilisler):
        for t in c["toplar"]:
            son_gorulme[t] = i
    gecikme = sorted(SAYI_ARALIGI, key=lambda t: (son_gorulme.get(t, -1), t))[:10]
    ikili = Counter(p for c in cekilisler for p in combinations(c["toplar"], 2))
    return {"son": set(son["toplar"]), "dongu_eksik": set(donguler(cekilisler)[-1]["eksik"]),
            "seviye": seviye, "puan": puan,
            "gecikme": set(gecikme), "ikili": ikili, "olcutler": list(olcutler),
            "sonraki_gun": GUNLER[sonraki_gun], "sonraki_tarih": sonraki.isoformat()}


# Kemik yapı sınırları. Geçmiş karşılaştırmasında (985 çekiliş) eski sınırlar
# gerçek çekilişlerin yalnızca %30'una uyuyordu; bunlar ~%67'sine uyar.
KEMIK = {"tek": (1, 5), "dusuk": (1, 5), "onlu": 3, "son_hane": 2,
         "toplam": (130, 235), "ardisik": 2, "tekrar": 2}
KEMIK_METNI = ("1–5 tek, 1–30 arasından 1–5, aynı onluda en fazla 3, aynı son haneden en fazla 2, "
               "toplam 130–235, en fazla 2 ardışık ikili, son çekilişten en fazla 2 numara")


def kemik_olcu(kolon: list[int], son_cekilis: set[int]) -> dict:
    k = sorted(kolon)
    return {"tek": sum(t % 2 for t in k), "dusuk": sum(t <= 30 for t in k),
            "onlu": max(Counter((t - 1) // 10 for t in k).values()),
            "son_hane": max(Counter(t % 10 for t in k).values()), "toplam": sum(k),
            "ardisik": sum(1 for a, b in zip(k, k[1:]) if b - a == 1),
            "tekrar": len(son_cekilis & set(k))}


def kemik_ceza(kolon: list[int], son_cekilis: set[int]) -> int:
    """Kemik yapıdan sapma (0 = uyuyor); sınırlar KEMIK sözlüğünde."""
    o = kemik_olcu(kolon, son_cekilis)
    ceza = 0
    for ad in ("tek", "dusuk"):
        alt, ust = KEMIK[ad]
        ceza += max(0, alt - o[ad], o[ad] - ust)
    alt, ust = KEMIK["toplam"]
    ceza += (max(0, alt - o["toplam"], o["toplam"] - ust) + 4) // 5
    for ad in ("onlu", "son_hane", "ardisik", "tekrar"):
        ceza += max(0, o[ad] - KEMIK[ad])
    return ceza


def dagilim_ceza(kolon: list[int], an: dict) -> int:
    """Güç dengesi (güçlü/orta/zayıf ikişer) ve uzun süredir çıkmayanlardan
    en fazla 1 kuralından sapma."""
    seviye = Counter(an["seviye"][t] for t in kolon)
    return (sum(abs(seviye[s] - 2) for s in "GOZ")
            + max(0, len(an["gecikme"] & set(kolon)) - 1))


def kolon_ceza(kolon: list[int], an: dict) -> int:
    """Kolonun kurallardan ne kadar saptığı (0 = bütün kurallara uyuyor):
    kemik yapı + güç dengesi + uzun süredir çıkmayanların dağılımı."""
    return kemik_ceza(kolon, an["son"]) + dagilim_ceza(kolon, an)


# Döngü kuralı: şu anki döngüde henüz gelmeyen numaralar tüm kurallar modunda
# mümkün olduğunca aynı kolonlarda toplanır (hedef; zorunlu kurallar bozulmaz).
DONGU_AGIRLIK = 60.0  # tam toplanmanın toplam ödülü (hedef puanı cinsinden)


def dongu_toplanma(kolon: list[int], eksik: set[int]) -> int:
    """Kolondaki gelmeyen numaraların oluşturduğu ikili sayısı (toplanma puanı)."""
    e = len(eksik & set(kolon))
    return e * (e - 1) // 2


def ikili_puani(kolon: list[int], an: dict) -> int:
    """Kolondaki numaraların geçmişte birlikte çıkma sayılarının toplamı."""
    return sum(an["ikili"][p] for p in combinations(sorted(kolon), 2))


def kolon_uret(an: dict, tohum: int | None = None,
               onceki: list[list[int]] | None = None, adim: int = 40000,
               iyilestirme: int = 20000, deneme: int = 50) -> list[list[int]]:
    """60 numaranın her birini tam bir kez kullanan 10 kolon üretir.

    1. Numaralar rastgele dağıtılır (şans faktörü).
    2. Kolonlar arasında takas yapılarak bütün kurallar sağlanır. `onceki`
       verilirse, yeni kolonların her biri önceki kolonların her biriyle en
       fazla 2 numara paylaşabilir (farklı düzen kuralı).
    3. Kurallar bozulmadan, geçmişte birlikte çok çıkan numaralar aynı
       kolona toplanır; önceki kolonlarda yan yana gelmiş numara çiftlerinden
       kaçınılır.
    """
    rng = random.Random(tohum)
    numaralar = list(SAYI_ARALIGI)
    onceki_kumeler = [set(k) for k in onceki or []]
    onceki_ciftler = {p for k in onceki or [] for p in combinations(sorted(k), 2)}

    def ceza(k):
        return kolon_ceza(k, an) + sum(max(0, len(set(k) & o) - 2) for o in onceki_kumeler)

    def puan(k):
        ciftler = list(combinations(sorted(k), 2))
        return (sum(an["ikili"][p] for p in ciftler)
                - 1000 * sum(p in onceki_ciftler for p in ciftler))

    def takas(kolonlar):
        a, b = rng.sample(range(10), 2)
        i, j = rng.randrange(6), rng.randrange(6)
        kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]
        return a, b, i, j

    for _ in range(deneme):
        rng.shuffle(numaralar)
        kolonlar = [numaralar[i:i + 6] for i in range(0, 60, 6)]
        cezalar = [ceza(k) for k in kolonlar]
        for _ in range(adim):
            if not any(cezalar):
                break
            a, b, i, j = takas(kolonlar)
            ya, yb = ceza(kolonlar[a]), ceza(kolonlar[b])
            if ya + yb <= cezalar[a] + cezalar[b]:
                cezalar[a], cezalar[b] = ya, yb
            else:
                kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]
        if not any(cezalar):
            break
    else:
        raise RuntimeError("Kurallara uyan ve öncekilerden farklı bir düzen bulunamadı. "
                           "Bu çekiliş için kolon geçmişini --sifirla ile temizleyebilirsiniz.")

    puanlar = [puan(k) for k in kolonlar]
    for _ in range(iyilestirme):
        a, b, i, j = takas(kolonlar)
        if ceza(kolonlar[a]) == 0 and ceza(kolonlar[b]) == 0:
            pa, pb = puan(kolonlar[a]), puan(kolonlar[b])
            if pa + pb >= puanlar[a] + puanlar[b]:
                puanlar[a], puanlar[b] = pa, pb
                continue
        kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]
    return sorted((sorted(k) for k in kolonlar), key=lambda k: -ikili_puani(k, an))


def gecmis_oku(tarih: str) -> dict:
    """Bu çekiliş için daha önce verilen kolonlar ve kullanılan taklit şablonları
    (eski çekilişlerin kayıtları dikkate alınmaz)."""
    try:
        kayit = json.loads(GECMIS_PATH.read_text(encoding="utf-8")).get(tarih, {})
    except (OSError, ValueError):
        kayit = {}
    if isinstance(kayit, list):  # eski biçim: yalnızca kolon listesi
        kayit = {"kolonlar": kayit}
    return {"kolonlar": kayit.get("kolonlar", []), "sablonlar": kayit.get("sablonlar", [])}


def gecmis_yaz(tarih: str, kayit: dict) -> None:
    GECMIS_PATH.write_text(json.dumps({tarih: kayit}), encoding="utf-8")


def kolon_yazdir(kolonlar: list[list[int]], an: dict, baslik: str) -> None:
    print(baslik)
    print(f"  {'#':>2}  {'Kolon':<29}{'G/O/Z':>7}{'Tek':>5}{'1-30':>6}"
          f"{'Toplam':>8}{'İkili puanı':>13}")
    for i, k in enumerate(kolonlar, 1):
        sev = Counter(an["seviye"][t] for t in k)
        karisim = f"{sev['G']}/{sev['O']}/{sev['Z']}"
        print(f"  {i:>2}  {' - '.join(f'{t:2d}' for t in k):<29}{karisim:>7}"
              f"{sum(t % 2 for t in k):>5}{sum(t <= 30 for t in k):>6}{sum(k):>8}"
              f"{ikili_puani(k, an):>13}")
    kullanilan = sorted(t for k in kolonlar for t in k)
    assert kullanilan == list(SAYI_ARALIGI), "her numara tam bir kez kullanılmalı"
    assert all(kolon_ceza(k, an) == 0 for k in kolonlar), "bütün kolonlar kurallara uymalı"


def kolon_aciklama(an: dict) -> None:
    def liste(s):
        return ", ".join(str(t) for t in sorted(t for t in SAYI_ARALIGI if an["seviye"][t] == s))
    print(f"  Güçlü (G): {liste('G')}")
    print(f"  Orta  (O): {liste('O')}")
    print(f"  Zayıf (Z): {liste('Z')}")
    print(f"  En uzun süredir çıkmayan 10: {', '.join(map(str, sorted(an['gecikme'])))}")
    print("\n  Kullanılan analizler:")
    print(f"  - Güç puanı: {', '.join(an['olcutler'])} sıralamalarının ortalaması.")
    print("    Her kolonda 2 güçlü, 2 orta, 2 zayıf numara var.")
    print("  - Uzun süredir çıkmayanlar kolonlara dağıtıldı (her kolonda en fazla 1).")
    print(f"  - Kemik yapı: {KEMIK_METNI}.")
    print("  - Birlikte çıkanlar: kurallar bozulmadan, geçmişte birlikte çok çıkan")
    print("    numaralar aynı kolona toplandı (İkili puanı = bu birlikteliklerin toplamı).")
    print("  - Farklı düzen: aynı çekiliş için verilen her yeni kolon, daha önce verilen")
    print("    kolonların her biriyle en fazla 2 numara paylaşır.")
    print("  Not: Bu ayarlar kazanma ihtimalini değiştirmez; geriye dönük testlerde")
    print("  kurallı ve rastgele kolonlar aynı sonucu verdi.")


ASALLAR = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}
AYLAR_AD = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
            "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def dizilim(toplar: list[int], onceki: list[int] | None = None) -> dict:
    """Bir çekilişin "oynanış biçimi"."""
    k = sorted(toplar)
    onlu = Counter((t - 1) // 10 for t in k)
    return {
        "onlu": tuple(onlu[d] for d in range(6)),
        "tek": sum(t % 2 for t in k),
        "ardisik": sum(1 for a, b in zip(k, k[1:]) if b - a == 1),
        "son_hane": 6 - len({t % 10 for t in k}),
        "asal": sum(t in ASALLAR for t in k),
        "toplam": sum(k),
        "ilk": k[0],
        "son": k[-1],
        "araliklar": tuple(b - a for a, b in zip(k, k[1:])),
        "tekrar": len(set(k) & set(onceki)) if onceki else 0,
    }


def taklit_sablonlari(cekilisler: list[dict], rng: random.Random, gun: int, ay: int,
                      son_yil_adet: int = 7, donem: int = 156,
                      haric: set[int] = frozenset(), adim: int = 20000,
                      deneme: int = 6, kemik: bool = False) -> tuple[list[dict], str]:
    """10 şablon çekiliş seçer; hangi seçim seviyesinin kullanıldığını da döndürür.

    `son_yil_adet` şablon son `donem` çekilişten (son 1 yıl), kalanı önceki
    yıllardan gelir. Önce sonraki çekilişle aynı gün (eski yıllar için aynı gün
    ve aynı ay) denenir; olmazsa koşullar adım adım gevşetilir. `haric`
    içindeki çekilişler (aynı çekiliş için önceki setlerde kullanılanlar)
    seçilmez. `kemik` True ise yalnızca kemik yapıya uyan çekilişler şablon olur.

    Zorunlu: onlu dağılımlar toplamı her onlukta 10 ve tek sayılar toplamı 30
    (60 numara tam dolsun diye). Tercih edilen: asal sayılar toplamı 17 (1–60
    arasındaki asal sayısı) ve önceki çekilişten tekrar sayıları toplamı 6;
    son çekilişin numaraları da şablonlara onluk bazında sığmalı.
    """
    son_yil_adet = max(0, min(10, son_yil_adet))
    son_toplar = cekilisler[-1]["toplar"]
    son_onlu = Counter((t - 1) // 10 for t in son_toplar)
    adaylar = []
    for i in range(1, len(cekilisler)):
        c = cekilisler[i]
        if c["no"] in haric:
            continue
        if kemik and kemik_ceza(c["toplar"], set(cekilisler[i - 1]["toplar"])):
            continue
        tarih = datetime.date.fromisoformat(c["tarih"])
        adaylar.append({"cekilis": c, "yeni": i >= len(cekilisler) - donem,
                        "gun": tarih.weekday(), "ay": tarih.month,
                        "d": dizilim(c["toplar"], cekilisler[i - 1]["toplar"])})
    seviyeler = [
        ("aynı gün; eski yıllardan aynı gün ve aynı ay",
         lambda a: a["gun"] == gun, lambda a: a["gun"] == gun and a["ay"] == ay),
        ("aynı gün; eski yıllardan aynı ay",
         lambda a: a["gun"] == gun, lambda a: a["ay"] == ay),
        ("aynı gün", lambda a: a["gun"] == gun, lambda a: a["gun"] == gun),
        ("bütün günler", lambda a: True, lambda a: True),
    ]

    def zorunlu(secim):
        onlu = [sum(a["d"]["onlu"][d] for a in secim) for d in range(6)]
        return sum(abs(o - 10) for o in onlu) + abs(sum(a["d"]["tek"] for a in secim) - 30)

    def tercih(secim):
        ceza = (abs(sum(a["d"]["asal"] for a in secim) - 17)
                + abs(sum(a["d"]["tekrar"] for a in secim) - 6))
        if ceza:
            return ceza
        # Son çekilişin numaraları tekrar kotası olan şablonlara onluk bazında sığıyor mu?
        kota = [a["d"]["tekrar"] for a in secim]
        yuva = [list(a["d"]["onlu"]) for a in secim]
        ogeler = [d for d, n in son_onlu.items() for _ in range(n)]

        def yerlestir(k):
            if k == len(ogeler):
                return True
            for i in range(10):
                if kota[i] and yuva[i][ogeler[k]]:
                    kota[i] -= 1
                    yuva[i][ogeler[k]] -= 1
                    if yerlestir(k + 1):
                        return True
                    kota[i] += 1
                    yuva[i][ogeler[k]] += 1
            return False
        return 0 if yerlestir(0) else 1

    for ad, yeni_kosul, eski_kosul in seviyeler:
        yeni = [a for a in adaylar if a["yeni"] and yeni_kosul(a)]
        eski = [a for a in adaylar if not a["yeni"] and eski_kosul(a)]
        y_adet = son_yil_adet if len(eski) >= 10 - son_yil_adet else 10 - len(eski)
        if len(yeni) < y_adet or len(eski) < 10 - y_adet:
            continue
        gruplar = [yeni] * y_adet + [eski] * (10 - y_adet)
        yedek = None
        for _ in range(deneme):
            secim = rng.sample(yeni, y_adet) + rng.sample(eski, 10 - y_adet)
            c = 100 * zorunlu(secim) + tercih(secim)
            for _ in range(adim):
                if c == 0:
                    return [a["cekilis"] for a in secim], ad
                if c < 100 and yedek is None:
                    yedek = [a["cekilis"] for a in secim]
                j = rng.randrange(10)
                aday = rng.choice(gruplar[j])
                if any(aday is x for x in secim):
                    continue
                eski_secim, secim[j] = secim[j], aday
                yeni_c = 100 * zorunlu(secim) + tercih(secim)
                if yeni_c <= c or rng.random() < 0.02:
                    c = yeni_c
                else:
                    secim[j] = eski_secim
        if yedek is not None:
            return yedek, ad
    if haric:
        # Kullanılmamış uygun şablon kalmadıysa, önceki setlerin şablonlarına da izin ver.
        # (Kolonlar yine farklı olur: farklı düzen kuralı ayrıca uygulanır.)
        sablonlar, ad = taklit_sablonlari(cekilisler, rng, gun, ay, son_yil_adet, donem,
                                          frozenset(), adim, deneme, kemik)
        return sablonlar, ad + "; şablonlar önceki setlerle ortak olabilir"
    raise RuntimeError("Uygun şablon çekilişler bulunamadı.")


def taklit_kontrol(kolon: list[int], h: dict, son_toplar: list[int],
                   tolerans: int = 6, aralik_tolerans: int = 2,
                   uc_tolerans: int = 3) -> tuple[int, int, int]:
    """(zorunlu kural sapması, hedef sapması, tutan hedef sayısı / 5)."""
    d = dizilim(kolon, son_toplar)
    zorunlu = (abs(d["tek"] - h["tek"]) + abs(d["ardisik"] - h["ardisik"])
               + abs(d["son_hane"] - h["son_hane"])
               + (max(0, abs(d["toplam"] - h["toplam"]) - tolerans) + 4) // 5)
    asal = abs(d["asal"] - h["asal"])
    tekrar = abs(d["tekrar"] - h["tekrar"])
    ilk = max(0, abs(d["ilk"] - h["ilk"]) - uc_tolerans)
    son = max(0, abs(d["son"] - h["son"]) - uc_tolerans)
    aralik = sum(max(0, abs(x - y) - aralik_tolerans)
                 for x, y in zip(d["araliklar"], h["araliklar"]))
    hedef = asal + 2 * tekrar + ilk + son + aralik
    tutan = sum(x == 0 for x in (asal, tekrar, ilk, son, aralik))
    return zorunlu, hedef, tutan


# Döngü kolonu için diğer kolonlarda kademeli esnetme: (tek, son hane, ardışık
# toleransı, toplam toleransı çarpanı). Son kademede taklitçi kural bırakılır.
ESNEKLIK = [(0, 0, 0, 1), (1, 1, 0, 1), (1, 1, 1, 2), None]
ESNEKLIK_METNI = ["", "tek ve son hane ±1", "tek, son hane ve ardışık ±1, toplam aralığı iki kat",
                  "taklitçi kural (kemik yapı ve farklı düzen kaldı)"]


def taklit_zorunlu(kolon: list[int], h: dict, son_toplar: list[int], tolerans: int,
                   esneklik: int = 0) -> int:
    """Taklidin zorunlu kurallarından sapma; `esneklik` kademesine göre toleranslı."""
    if ESNEKLIK[esneklik] is None:
        return 0
    tek_t, hane_t, ard_t, top_c = ESNEKLIK[esneklik]
    d = dizilim(kolon, son_toplar)
    return (max(0, abs(d["tek"] - h["tek"]) - tek_t)
            + max(0, abs(d["ardisik"] - h["ardisik"]) - ard_t)
            + max(0, abs(d["son_hane"] - h["son_hane"]) - hane_t)
            + (max(0, abs(d["toplam"] - h["toplam"]) - tolerans * top_c) + 4) // 5)


def taklit_uret(cekilisler: list[dict], tohum: int | None = None,
                onceki: list[list[int]] | None = None,
                haric_sablon: set[int] = frozenset(), son_yil_adet: int = 7,
                tolerans: int = 6, adim: int = 80000, deneme: int = 3,
                sablon_denemesi: int = 8, an: dict | None = None,
                dongu_agirlik: float = DONGU_AGIRLIK) -> dict:
    """Taklitçi kural: her kolon gerçek bir çekilişin dizilimini taklit eder.

    Zorunlu (her kolonda kesin): onlu dağılım, tek, ardışık ikili, aynı son
    hane birebir; toplam ±`tolerans`; önceki kolonların her biriyle en fazla 2
    ortak numara. Hedef (olabildiğince yakın): asal sayı adedi, son çekilişten
    gelen numara adedi (şablonun kendinden önceki çekilişten tekrar ettiği
    kadar), ilk ve son top ±3, sıralı toplar arası her aralık ±2.
    60 numara tam bir kez kullanılır. Birkaç şablon setiyle "tavlama" araması
    yapılır ve hedeflere en yakın sonuç döndürülür.

    `an` (numara_analizi sonucu) verilirse "tüm kurallar" modu çalışır:
    şablonlar yalnızca kemik yapıya uyan çekilişlerden seçilir ve kemik yapı
    zorunlu olur. Güç dengesi, uzun süredir çıkmayanlar ve ikili puanı bu
    modda kullanılmaz: geçmiş karşılaştırmasında gerçek çekilişlerde rastgele
    numaralardan farksız çıktılar.
    """
    rng = random.Random(tohum)
    son = cekilisler[-1]
    sonraki = sonraki_cekilis(son["tarih"])
    onceki_kumeler = [set(k) for k in onceki or []]
    bicim = {c["no"]: dizilim(c["toplar"], cekilisler[i - 1]["toplar"] if i else None)
             for i, c in enumerate(cekilisler)}
    en_iyi = None

    eksik_tum = an.get("dongu_eksik", set()) if an is not None else set()
    kademeler = (range(len(ESNEKLIK)) if an is not None and dongu_agirlik
                 and 1 <= len(eksik_tum) <= 6 else [0])
    for esneklik in kademeler:
        if en_iyi is not None:
            break
        for deneme_no in range(sablon_denemesi):
            if en_iyi is not None and deneme_no >= deneme:
                break
            sablonlar, seviye = taklit_sablonlari(
                cekilisler, rng, sonraki.weekday(), sonraki.month, son_yil_adet,
                haric=haric_sablon, kemik=an is not None)
            hedefler = [bicim[s["no"]] for s in sablonlar]

            dkol = None  # döngü kolonu (gelmeyen numaralar 6 ya da daha azsa)

            def zorunlu(i, kolon):
                if i == dkol:
                    # Döngü kolonunda gelmeyen numaraların hepsi kilitli durur; taklit, kemik yapı
                    # ve farklı düzen bu kolon için zorunlu değil, hedef olarak izlenir.
                    return 0
                z = taklit_zorunlu(kolon, hedefler[i], son["toplar"], tolerans, esneklik)
                z += sum(max(0, len(set(kolon) & o) - 2) for o in onceki_kumeler)
                if an is not None:
                    z += kemik_ceza(kolon, an["son"])
                return z

            eksik = an.get("dongu_eksik", set()) if an is not None else set()
            # Toplanma puanı, gelmeyen numara sayısına göre olası en yüksek değere bölünür:
            # 2 de kalsa 20 de kalsa tam toplanma aynı ödülü (dongu_agirlik) alır.
            en_cok = (len(eksik) // 6) * 15 + math.comb(len(eksik) % 6, 2) if eksik else 0
            birim = dongu_agirlik / en_cok if en_cok and len(eksik) < 60 else 0.0

            def hedef(i, kolon):
                z, h, _ = taklit_kontrol(kolon, hedefler[i], son["toplar"], tolerans)
                if i == dkol:
                    # Esnetilen kurallar döngü kolonunda olabildiğince korunmaya çalışılır.
                    h += 3 * z + 3 * kemik_ceza(kolon, an["son"])
                if birim:
                    # Döngü kuralı: gelmeyen numaralar aynı kolonda toplandıkça ceza azalır.
                    h -= birim * dongu_toplanma(kolon, eksik)
                return h

            # Döngü kuralı devredeyken çift takasa da izin verilir: gelmeyen bir numarayı
            # başka kolona taşımak çoğu zaman tek/çift dengesini bozar; ikinci takas düzeltir.
            cift_takas = bool(eksik and dongu_agirlik and len(eksik) < 60)
            # Gelmeyen numaralar 6 ya da daha azsa hepsi tek bir "döngü kolonu"nda toplanır;
            # bunu engelleyen kurallar o kolon için esnetilir.
            esnek = bool(an is not None and dongu_agirlik and 1 <= len(eksik) <= 6)

            def kilitli(k, x):
                return k == dkol and kolonlar[k][x] in eksik

            def takas_dene(kolonlar):
                a, b = rng.sample(range(10), 2)
                ciftler = []
                for _ in range(2 if cift_takas and rng.random() < 0.5 else 1):
                    kullanilan_i = {x for x, _ in ciftler}
                    kullanilan_j = {y for _, y in ciftler}
                    adaylar_i = [x for x in range(6) if x not in kullanilan_i and not kilitli(a, x)]
                    if not adaylar_i:
                        break
                    i = rng.choice(adaylar_i)
                    d = (kolonlar[a][i] - 1) // 10
                    secenek = [j for j, t in enumerate(kolonlar[b])
                               if (t - 1) // 10 == d and j not in kullanilan_j and not kilitli(b, j)]
                    if not secenek:
                        break
                    # Yalnızca aynı onluktan numaralar takas edilir: onlu dağılım korunur.
                    ciftler.append((i, rng.choice(secenek)))
                if not ciftler:
                    return None
                for i, j in ciftler:
                    kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]
                return a, b, ciftler

            def geri_al(t):
                a, b, ciftler = t
                for i, j in ciftler:
                    kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]

            kolonlar: list[list[int]] = [[] for _ in range(10)]
            havuz = []
            for d in range(6):
                numaralar = list(range(d * 10 + 1, d * 10 + 11))
                rng.shuffle(numaralar)
                havuz.append(numaralar)
            if esnek:
                # Döngü kolonu: gelmeyen numaraları onluk bazında en çok alabilen kolon.
                sayi = Counter((t - 1) // 10 for t in eksik)
                dkol = max(range(10), key=lambda i: (sum(min(hedefler[i]["onlu"][d], sayi[d])
                                                         for d in range(6)), rng.random()))
                bos = [list(h["onlu"]) for h in hedefler]
                for d in range(6):
                    for t in [t for t in havuz[d] if t in eksik]:
                        if bos[dkol][d]:
                            havuz[d].remove(t)
                            kolonlar[dkol].append(t)
                            bos[dkol][d] -= 1
                for i in range(10):
                    for d in range(6):
                        for _ in range(bos[i][d]):
                            kolonlar[i].append(havuz[d].pop())
                # Sığmayanlar tek bir ortak kolon üzerinden alınır: gelmeyen numara önce
                # aynı onluktan takasla ortak kolona getirilir, sonra döngü kolonuyla onluk
                # dışı takas edilir. Böylece döngü kolonu dışında yalnızca ortak kolonun
                # onluk dağılımı şablondan ayrılır.
                tasan = [t for t in sorted(eksik) if t not in kolonlar[dkol]]
                while tasan:
                    ihtiyac = Counter((t - 1) // 10 for t in tasan)

                    def ortak_puani(i):
                        if i == dkol:
                            return -1
                        return sum(min(n, sum(1 for x in kolonlar[i]
                                              if (x - 1) // 10 == d and x not in eksik))
                                   for d, n in ihtiyac.items())
                    # Gerekirse birden fazla ortak kolon: her seferinde en çok alabilen seçilir.
                    ortak = max(range(10), key=lambda i: (ortak_puani(i), rng.random()))
                    kalan = []
                    for t in tasan:
                        q = next(i for i in range(10) if t in kolonlar[i])
                        if q != ortak:
                            z = next((x for x in kolonlar[ortak]
                                      if (x - 1) // 10 == (t - 1) // 10 and x not in eksik), None)
                            if z is None:
                                kalan.append(t)
                                continue
                            kolonlar[q][kolonlar[q].index(t)] = z
                            kolonlar[ortak][kolonlar[ortak].index(z)] = t
                        y = next(x for x in kolonlar[dkol] if x not in eksik)
                        kolonlar[ortak][kolonlar[ortak].index(t)] = y
                        kolonlar[dkol][kolonlar[dkol].index(y)] = t
                    if len(kalan) == len(tasan):  # hiçbir kolon alamıyor: numaranın kendi kolonu
                        t = kalan.pop(0)
                        q = next(i for i in range(10) if t in kolonlar[i])
                        y = next(x for x in kolonlar[dkol] if x not in eksik)
                        kolonlar[q][kolonlar[q].index(t)] = y
                        kolonlar[dkol][kolonlar[dkol].index(y)] = t
                    tasan = kalan
            elif eksik and dongu_agirlik and len(eksik) < 60:
                # Döngü kuralı: gelmeyen numaralar baştan aynı kolonlarda toplanır. En çok
                # gelmeyen numara alabilecek kolon önce doldurulur, sonra sıradaki.
                kalan_eksik = [[t for t in havuz[d] if t in eksik] for d in range(6)]
                bos = [list(h["onlu"]) for h in hedefler]
                while any(kalan_eksik):
                    def kapasite(i):
                        return sum(min(bos[i][d], len(kalan_eksik[d])) for d in range(6))
                    en = max(range(10), key=lambda i: (kapasite(i), rng.random()))
                    if not kapasite(en):
                        break
                    for d in range(6):
                        while bos[en][d] and kalan_eksik[d]:
                            t = kalan_eksik[d].pop()
                            havuz[d].remove(t)
                            kolonlar[en].append(t)
                            bos[en][d] -= 1
                for i, h in enumerate(hedefler):
                    for d in range(6):
                        for _ in range(bos[i][d]):
                            kolonlar[i].append(havuz[d].pop())
            else:
                for d in range(6):
                    for i, h in enumerate(hedefler):
                        for _ in range(h["onlu"][d]):
                            kolonlar[i].append(havuz[d].pop())

            # 1. aşama: zorunlu kurallar. Taklitçi modunda hedefler de birlikte izlenir;
            # tüm kurallar modunda hedefler yalnızca 2. aşamada iyileştirilir.
            def ceza(i, k):
                if an is None:
                    return 100 * zorunlu(i, k) + hedef(i, k)
                # Tüm kurallar: önce zorunlular; döngü kuralının toplanması korunmaya çalışılır.
                # 1. aşamada toplanma, zorunlu kuralların hemen altında bir öncelikle korunur.
                return 100 * zorunlu(i, k) - (90 / en_cok * dongu_toplanma(k, eksik) if birim else 0)
            cezalar = [ceza(i, k) for i, k in enumerate(kolonlar)]
            zor = [zorunlu(i, k) for i, k in enumerate(kolonlar)]
            for adim_no in range(adim):
                if not any(zor) and (an is not None or not any(cezalar)):
                    break
                sicaklik = 3.0 * (1 - adim_no / adim) + 0.05
                t = takas_dene(kolonlar)
                if t is None:
                    continue
                a, b = t[0], t[1]
                ya, yb = ceza(a, kolonlar[a]), ceza(b, kolonlar[b])
                fark = ya + yb - cezalar[a] - cezalar[b]
                if fark <= 0 or rng.random() < math.exp(-fark / sicaklik):
                    cezalar[a], cezalar[b] = ya, yb
                    zor[a], zor[b] = zorunlu(a, kolonlar[a]), zorunlu(b, kolonlar[b])
                else:
                    geri_al(t)
            if any(zorunlu(i, k) for i, k in enumerate(kolonlar)):
                continue

            # 2. aşama (tüm kurallar modu): zorunlu kurallar hiç bozulmadan hedefler iyileştirilir.
            if an is not None:
                puan = [hedef(i, k) for i, k in enumerate(kolonlar)]
                for adim_no in range(adim):
                    sicaklik = 1.0 * (1 - adim_no / adim) + 0.02
                    t = takas_dene(kolonlar)
                    if t is None:
                        continue
                    a, b = t[0], t[1]
                    if zorunlu(a, kolonlar[a]) or zorunlu(b, kolonlar[b]):
                        geri_al(t)
                        continue
                    pa, pb = hedef(a, kolonlar[a]), hedef(b, kolonlar[b])
                    fark = pa + pb - puan[a] - puan[b]
                    if fark <= 0 or rng.random() < math.exp(-fark / sicaklik):
                        puan[a], puan[b] = pa, pb
                    else:
                        geri_al(t)

            toplam = sum(hedef(i, k) for i, k in enumerate(kolonlar))
            if en_iyi is None or toplam < en_iyi[0]:
                en_iyi = (toplam, {"kolonlar": [sorted(k) for k in kolonlar], "dongu_kolonu": dkol,
                                   "esneklik": esneklik,
                                   "sablonlar": sablonlar, "hedefler": hedefler,
                                   "seviye": seviye, "son_toplar": son["toplar"],
                                   "tolerans": tolerans})
            if an is None and toplam == 0:
                break
    if en_iyi is None:
        raise RuntimeError("Taklitçi kurala uyan ve öncekilerden farklı bir düzen bulunamadı. "
                           "Bu çekiliş için kolon geçmişini --sifirla ile temizleyebilirsiniz.")
    return en_iyi[1]


def taklit_yazdir(sonuc: dict, baslik: str, an: dict | None = None) -> None:
    print(baslik)
    print(f"  Şablon seçimi: {sonuc['seviye']}.")
    eksik = an.get("dongu_eksik", set()) if an else set()
    ek = f"{'Dng':>5}" if an else ""
    print(f"  {'#':>2}  {'Kolon':<29}{'Tek':>4}{'Asal':>5}{'Tkr':>4}{'Top':>5}{ek}{'Uyum':>6}   "
          f"Taklit edilen çekiliş")
    toplam_tutan = 0
    hedef_sayisi = 5
    for i, (k, s, h) in enumerate(zip(sonuc["kolonlar"], sonuc["sablonlar"],
                                      sonuc["hedefler"]), 1):
        d = dizilim(k, sonuc["son_toplar"])
        z, _, tutan = taklit_kontrol(k, h, sonuc["son_toplar"], sonuc["tolerans"])
        dongu_kolonu = sonuc.get("dongu_kolonu") == i - 1
        if not dongu_kolonu:
            assert taklit_zorunlu(k, h, sonuc["son_toplar"], sonuc["tolerans"],
                                  sonuc.get("esneklik", 0)) == 0, "zorunlu kurallar sağlanmalı"
            if an:
                assert kemik_ceza(k, an["son"]) == 0, "kemik yapı sağlanmalı"
        toplam_tutan += tutan
        tarih = datetime.date.fromisoformat(s["tarih"])
        sablon = " - ".join(f"{t:2d}" for t in s["toplar"])
        print(f"  {i:>2}  {' - '.join(f'{t:2d}' for t in k):<29}"
              f"{d['tek']:>4}{d['asal']:>5}{d['tekrar']:>4}{d['toplam']:>5}"
              + (f"{len(eksik & set(k)):>5}" if an else "")
              + f"{f'{tutan}/{hedef_sayisi}':>6}   "
              f"#{s['no']} {s['tarih']} {GUNLER[tarih.weekday()][:3]}: {sablon}"
              + ("  ← döngü kolonu" if dongu_kolonu else ""))
    ad = "asal, son çekilişten tekrar, ilk top, son top, aralık deseni"
    print(f"  Hedef uyumu: {toplam_tutan}/{10 * hedef_sayisi} ({ad})")
    if an:
        dk = sonuc.get("dongu_kolonu")
        if dk is not None:
            k, h = sonuc["kolonlar"][dk], sonuc["hedefler"][dk]
            esnetilen = []
            if taklit_kontrol(k, h, sonuc["son_toplar"], sonuc["tolerans"])[0]:
                esnetilen.append("taklit (tek, ardışık, son hane, toplam)")
            if kemik_ceza(k, an["son"]):
                esnetilen.append("kemik yapı")
            onlu_degisen = [i + 1 for i, (kk, hh) in enumerate(zip(sonuc["kolonlar"], sonuc["hedefler"]))
                            if dizilim(kk)["onlu"] != hh["onlu"]]
            if onlu_degisen:
                esnetilen.append("onluk dağılımı (" + ", ".join(f"{x}. kolon" for x in onlu_degisen) + ")")
            if sonuc.get("esneklik"):
                esnetilen.append("diğer kolonlarda " + ESNEKLIK_METNI[sonuc["esneklik"]])
            print(f"  Döngü kuralı: bu döngüde henüz gelmeyen {len(eksik)} numaranın hepsi "
                  f"({' '.join(map(str, sorted(eksik)))}) {dk + 1}. kolonda (döngü kolonu). "
                  + ("Bunun için esnetilen: " + "; ".join(esnetilen) + "."
                     if esnetilen else "Hiçbir kural esnetilmedi."))
        elif len(eksik) == 60:
            print("  Döngü kuralı: yeni döngünün ilk çekilişi; 60 numaranın hepsi henüz gelmemiş "
                  "sayılır, toplama yapılmaz (Dng = kolondaki gelmeyen numara).")
        elif eksik:
            dagilim = sorted((len(eksik & set(k)) for k in sonuc["kolonlar"]), reverse=True)
            if len(eksik) > 30:
                gelen = sorted(set(SAYI_ARALIGI) - eksik)
                hangi = f"bu döngüde gelen {len(gelen)} numara ({' '.join(map(str, gelen))}) dışındaki"
            else:
                hangi = f"bu döngüde henüz gelmeyen ({' '.join(map(str, sorted(eksik)))})"
            print(f"  Döngü kuralı: {hangi} {len(eksik)} numara aynı kolonlarda toplandı; "
                  f"kolonlara dağılımı {'/'.join(map(str, dagilim))} (Dng sütunu).")
    kullanilan = sorted(t for k in sonuc["kolonlar"] for t in k)
    assert kullanilan == list(SAYI_ARALIGI), "her numara tam bir kez kullanılmalı"


def hepsi_aciklama(son_yil_adet: int, tolerans: int) -> None:
    print("  Tüm kurallar modu (--hepsi): taklitçi + analizli kural birlikte.")
    print("  - Her kolon, kemik yapıya uyan gerçek bir geçmiş çekilişi taklit eder.")
    print(f"    10 şablondan {son_yil_adet} tanesi son 1 yıldan, {10 - son_yil_adet} tanesi "
          "önceki yıllardan; aynı gün, eski yıllar için aynı ay öncelikli.")
    print("  - Zorunlu (her kolonda kesin):")
    print(f"    taklit: onluk dağılımı, tek, ardışık ikili, aynı son hane birebir; toplam ±{tolerans}")
    print(f"    kemik yapı: {KEMIK_METNI[:KEMIK_METNI.index(', toplam')]},")
    print(f"    {KEMIK_METNI[KEMIK_METNI.index('toplam'):]}")
    print("    farklı düzen: önceki kolonların her biriyle en fazla 2 ortak numara")
    print("  - Hedef (olabildiğince yakın, Uyum sütununda): asal adedi, son çekilişten tekrar,")
    print("    ilk ve son top ±3, aralık deseni ±2.")
    print("  - Döngü kuralı: 60 numaranın tamamlandığı döngüde henüz gelmeyen numaralar mümkün")
    print("    olduğunca aynı kolonlarda toplanır (Dng sütunu). 6 ya da daha az kaldıysa hepsi tek")
    print("    bir döngü kolonuna konur; engel olan kurallar o kolon için, gerekirse kademeli")
    print("    olarak diğer kolonlarda da esnetilir (kemik yapı diğer kolonlarda hep zorunlu).")
    print("  - Güç dengesi, uzun süredir çıkmayanlar ve birlikte çıkanlar kullanılmaz: geçmiş")
    print("    karşılaştırmasında gerçek çekilişlerde rastgele numaralardan farksız çıktılar.")
    print("  - 60 numaranın hepsi tam bir kez kullanılır. Her yeni çekilişle kendini günceller.")
    print("  Not: Kurallar kazanma ihtimalini değiştirmez; seçimi düzenli hale getirir.")


def taklit_aciklama(son_yil_adet: int, tolerans: int) -> None:
    print("  Taklitçi kural:")
    print("  - Her kolon, geçmişte gerçekten çıkmış bir çekilişin dizilimini taklit eder.")
    print(f"    10 şablondan {son_yil_adet} tanesi son 1 yıldan (156 çekiliş), "
          f"{10 - son_yil_adet} tanesi önceki yıllardan seçilir.")
    print("    Öncelik sonraki çekilişle aynı güne, eski yıllar için aynı aya verilir.")
    print("    Aynı çekiliş için önceki setlerde kullanılan şablonlar tekrar kullanılmaz.")
    print("  - Zorunlu (her kolonda kesin): onluk dağılımı, tek sayı, ardışık ikili ve aynı")
    print(f"    son hane adedi birebir; toplam ±{tolerans}.")
    print("  - Hedef (olabildiğince yakın, Uyum sütununda): asal sayı adedi; son çekilişten")
    print("    gelen numara adedi (Tkr: şablon kendinden önceki çekilişten kaç numara tekrar")
    print("    ettiyse); ilk ve son top ±3; sıralı toplar arası her aralık ±2.")
    print("  - 60 numaranın hepsi tam bir kez kullanılır. Farklı düzen: her yeni kolon")
    print("    daha önce verilen kolonların her biriyle en fazla 2 numara paylaşır.")
    print("  - Her yeni çekilişle şablon havuzu, gün/ay ve son çekiliş kendiliğinden güncellenir.")
    print("  Not: Geçmişin dizilimini taklit etmek kazanma ihtimalini değiştirmez.")


# Gezegen saatleri (geleneksel Kalde sistemi), Ankara için.
ANKARA = (39.9334, 32.8597, 3)  # enlem, boylam, UTC farkı (Türkiye: UTC+3)
SATIS_KAPANIS = datetime.time(21, 0)
KALDE_SIRASI = ["Satürn", "Jüpiter", "Mars", "Güneş", "Venüs", "Merkür", "Ay"]
GUN_YONETICISI = {0: "Ay", 1: "Mars", 2: "Merkür", 3: "Jüpiter", 4: "Venüs",
                  5: "Satürn", 6: "Güneş"}
SANSLI_GEZEGENLER = {"Jüpiter": "büyük talih", "Venüs": "küçük talih"}


def gunes_zamani(gun: datetime.date, dogus: bool, yer=ANKARA) -> datetime.datetime:
    """Gün doğumu/batımı (NOAA yaklaşımı, birkaç dakika hassasiyet)."""
    enlem, boylam, utc = yer
    n = gun.timetuple().tm_yday
    boylam_saat = boylam / 15
    t = n + ((6 if dogus else 18) - boylam_saat) / 24
    m = 0.9856 * t - 3.289
    l = (m + 1.916 * math.sin(math.radians(m)) + 0.020 * math.sin(math.radians(2 * m))
         + 282.634) % 360
    ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(l)))) % 360
    ra = (ra + (math.floor(l / 90) * 90 - math.floor(ra / 90) * 90)) / 15
    sin_d = 0.39782 * math.sin(math.radians(l))
    cos_d = math.cos(math.asin(sin_d))
    cos_h = ((math.cos(math.radians(90.833)) - sin_d * math.sin(math.radians(enlem)))
             / (cos_d * math.cos(math.radians(enlem))))
    h = math.degrees(math.acos(cos_h))
    h = (360 - h if dogus else h) / 15
    ut = (h + ra - 0.06571 * t - 6.622 - boylam_saat) % 24
    return (datetime.datetime.combine(gun, datetime.time())
            + datetime.timedelta(hours=(ut + utc) % 24))


def gezegen_saatleri(gun: datetime.date, yer=ANKARA) -> list[dict]:
    """Günün 24 gezegen saati: gündüz 12 (gün doğumu–batımı), gece 12
    (gün batımı–ertesi gün doğumu). İlk saati günün yöneticisi yönetir."""
    dogus, batis = gunes_zamani(gun, True, yer), gunes_zamani(gun, False, yer)
    ertesi = gunes_zamani(gun + datetime.timedelta(days=1), True, yer)
    gunduz, gece = (batis - dogus) / 12, (ertesi - batis) / 12
    ilk = KALDE_SIRASI.index(GUN_YONETICISI[gun.weekday()])
    saatler = []
    for i in range(24):
        bas = dogus + gunduz * i if i < 12 else batis + gece * (i - 12)
        saatler.append({"bas": bas, "bit": bas + (gunduz if i < 12 else gece),
                        "gezegen": KALDE_SIRASI[(ilk + i) % 7], "gunduz": i < 12,
                        "sira": i % 12 + 1})
    return saatler


def gezegen_yazdir(gun: datetime.date, yer_adi: str = "Ankara") -> None:
    saatler = gezegen_saatleri(gun)
    kapanis = datetime.datetime.combine(gun, SATIS_KAPANIS)
    print(f"Gezegen saatleri — {gun.isoformat()} {GUNLER[gun.weekday()]}, {yer_adi} "
          f"(gün yöneticisi: {GUN_YONETICISI[gun.weekday()]})")
    print(f"  Gün doğumu {saatler[0]['bas']:%H:%M}, gün batımı {saatler[12]['bas']:%H:%M}. "
          f"Gündüz saati {round((saatler[0]['bit'] - saatler[0]['bas']).seconds / 60)} dk, "
          f"gece saati {round((saatler[12]['bit'] - saatler[12]['bas']).seconds / 60)} dk.")
    print(f"\n  Kupon için şanslı saatler (satış {SATIS_KAPANIS:%H:%M}'de kapanır):")
    var = False
    for s in saatler:
        if s["gezegen"] in SANSLI_GEZEGENLER and s["bas"] < kapanis:
            var = True
            bit = min(s["bit"], kapanis)
            yildiz = "★★" if s["gezegen"] == "Jüpiter" else "★ "
            not_ = " (satış kapanışına kadar)" if s["bit"] > kapanis else ""
            print(f"    {yildiz} {s['bas']:%H:%M}–{bit:%H:%M}  {s['gezegen']} "
                  f"({SANSLI_GEZEGENLER[s['gezegen']]}){not_}")
    if not var:
        print("    Satış kapanmadan önce Jüpiter ya da Venüs saati yok.")
    print("\n  Bütün saatler:")
    for s in saatler:
        isaret = {"Jüpiter": " ★★", "Venüs": " ★"}.get(s["gezegen"], "")
        print(f"    {'Gündüz' if s['gunduz'] else 'Gece  '} {s['sira']:2d}. "
              f"{s['bas']:%H:%M}–{s['bit']:%H:%M}  {s['gezegen']}{isaret}")
    print("  Not: Geleneksel bir hesaplamadır; çekiliş sonucunu etkilemez.")


OYUN_PATH = Path(__file__).with_name("oyun_kolonlari.txt")


def yakala(fonksiyon, *args, **kwargs) -> str:
    """Bir yazdırma fonksiyonunun çıktısını metin olarak döndürür."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        fonksiyon(*args, **kwargs)
    return tampon.getvalue()


def kolonlar_uretildi_mi(gun: datetime.date) -> bool:
    """Oyun dosyasında bu gün için kolonların üretildiğini gösteren satır var mı?"""
    try:
        metin = OYUN_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(satir.startswith(f"KOLONLAR: {gun.isoformat()} ") and "üretildi" in satir
               for satir in metin.splitlines())


def satis_saatleri(gun: datetime.date, gezegen: str) -> list[dict]:
    """Satış kapanmadan önce başlayan, verilen gezegenin saatleri (bitiş en geç kapanış)."""
    kapanis = datetime.datetime.combine(gun, SATIS_KAPANIS)
    return [dict(s, bit=min(s["bit"], kapanis)) for s in gezegen_saatleri(gun)
            if s["gezegen"] == gezegen and s["bas"] < kapanis]


def jupiter_saatleri(gun: datetime.date) -> list[dict]:
    """Satış kapanmadan önce başlayan Jüpiter saatleri (bitiş en geç kapanış)."""
    return satis_saatleri(gun, "Jüpiter")


def oyun_planla(cekilisler: list[dict]) -> None:
    """Sonraki çekiliş günü için oyun dosyasını hazırlar: gezegen saatleri ve
    kolonların ilk Jüpiter saatinde üretileceği notu."""
    gun = sonraki_cekilis(cekilisler[-1]["tarih"])
    if kolonlar_uretildi_mi(gun):
        print(f"{gun}: kolonlar Jüpiter saatinde zaten üretilmiş, dosyaya dokunulmadı.")
        return
    j = jupiter_saatleri(gun)
    plan = (f"KOLONLAR: {gun.isoformat()} çekiliş günü ilk Jüpiter saatinde "
            f"({j[0]['bas']:%H:%M}–{j[0]['bit']:%H:%M}) üretilecek." if j else
            f"KOLONLAR: {gun.isoformat()} günü satıştan önce Jüpiter saati yok; "
            "kolonlar sabah üretilecek.")
    OYUN_PATH.write_text(yakala(gezegen_yazdir, gun) + "\n" + plan + "\n", encoding="utf-8")
    print(plan)


UYKU = time.sleep  # testlerde değiştirilir


def oyun_jupiter(cekilisler: list[dict], simdi: datetime.datetime, bekle: int = 0) -> None:
    """Çekiliş günü Jüpiter saatinde kolonları üretir (gün içinde sık çalıştırılır).

    Kolonlar günün ilk Jüpiter saatinde üretilir. O saat kaçırıldıysa (ör.
    zamanlanmış iş gecikti) satış kapanana kadar sonraki Jüpiter saatleri
    denenir; Jüpiter saati kalmadıysa Venüs saatleri; o da kalmadıysa hemen
    üretilir. Bugün için zaten üretildiyse hiçbir şey yapılmaz.

    `bekle` saniye verilirse ve Jüpiter saati en geç o kadar sonra başlıyorsa,
    saat gelene kadar beklenir ve kolonlar Jüpiter saatinde üretilir (GitHub
    zamanlanmış işleri geciktirebildiği için iş Jüpiter saatinden önce başlar).
    """
    gun = simdi.date()
    if gun.weekday() not in CEKILIS_GUNLERI:
        print(f"{gun}: çekiliş günü değil.")
        return
    if kolonlar_uretildi_mi(gun):
        print(f"{gun}: kolonlar zaten üretilmiş.")
        return
    kapanis = datetime.datetime.combine(gun, SATIS_KAPANIS)
    if simdi >= kapanis:
        print(f"{gun}: satış kapandı, kolon üretilmedi.")
        return
    jup = jupiter_saatleri(gun)
    # Önce günün bütün Jüpiter saatleri denenir; hiçbiri kalmadıysa Venüs saatleri;
    # o da kalmadıysa satış kapanmadan hemen üretilir.
    saatler, gezegen = jup, "Jüpiter"
    if not any(s["bit"] > simdi for s in jup):
        saatler, gezegen = satis_saatleri(gun, "Venüs"), "Venüs"
    simdiki = next((s for s in saatler if s["bas"] <= simdi < s["bit"]), None)
    sonraki = next((s for s in saatler if s["bas"] > simdi), None)
    if simdiki is None and sonraki is not None:
        kalan = (sonraki["bas"] - simdi).total_seconds()
        if not bekle or kalan > bekle:
            print(f"{gun}: {gezegen} saati bekleniyor "
                  f"({sonraki['bas']:%H:%M}–{sonraki['bit']:%H:%M}).")
            return
        print(f"{gun}: {gezegen} saati {sonraki['bas']:%H:%M}'de başlıyor; {kalan / 60:.0f} dakika "
              "bekleniyor.", flush=True)
        UYKU(kalan + 5)  # saat başladıktan birkaç saniye sonra
        simdi = sonraki["bas"]
        simdiki = sonraki
    if simdiki is not None and gezegen == "Jüpiter":
        not_ = (f"Jüpiter saati {simdiki['bas']:%H:%M}–{simdiki['bit']:%H:%M} içinde üretildi, "
                f"üretim saati {simdi:%H:%M}.")
        if simdiki is not jup[0]:
            not_ += f" (İlk Jüpiter saati {jup[0]['bas']:%H:%M} kaçırıldı.)"
    elif simdiki is not None:
        not_ = (f"Jüpiter saatleri kaçırıldı; Venüs saati {simdiki['bas']:%H:%M}–"
                f"{simdiki['bit']:%H:%M} içinde üretildi, üretim saati {simdi:%H:%M}.")
    else:
        not_ = (f"satıştan önce Jüpiter ve Venüs saati kalmadığı için hemen üretildi, "
                f"üretim saati {simdi:%H:%M}.")
    an = numara_analizi(cekilisler)
    tohum = int(simdi.strftime("%Y%m%d%H%M"))
    sonuc = taklit_uret(cekilisler, tohum, an=an, adim=50000, deneme=2)
    metin = (yakala(gezegen_yazdir, gun) + "\n"
             + f"KOLONLAR: {gun.isoformat()} {not_}\n\n"
             + yakala(taklit_yazdir, sonuc, "Set 1: 60 numaranın hepsini kullanan 10 kolon "
                      "(tüm kurallar)", an)
             + "\n" + yakala(hepsi_aciklama, 7, 6))
    OYUN_PATH.write_text(metin, encoding="utf-8")
    print(f"{gun}: kolonlar üretildi — {not_}")


# Her çekiliş sonrası değerlendirme ve karne.
KARNE_PATH = Path(__file__).with_name("degerlendirme_karnesi.csv")
DEGERLENDIRME_PATH = Path(__file__).with_name("son_degerlendirme.md")
KURAL_KARNESI_PATH = Path(__file__).with_name("kural_karnesi.csv")
PENCERE_ANALIZI_PATH = Path(__file__).with_name("pencere_analizi.csv")
PENCERE_LISTELERI_PATH = Path(__file__).with_name("pencere_listeleri.csv")
DONGU_KARNESI_PATH = Path(__file__).with_name("dongu_karnesi.csv")
# 60 numaranın tamamlandığı döngüler: bu çekilişten önceki döngüler geriye doğru
# (#985'ten başlayarak) bulunur, bu çekilişten itibaren ileriye doğru izlenir.
DONGU_CAPA = 986
SON_DONEM_GUN = 548  # "son 1,5 yıl"
KARNE_ALANLARI = ["no", "tarih", "toplam", "tek", "ardisik", "tekrar", "kemik_uygun",
                  "dikkat_sayisi", "kupon_var", "en_iyi", "uc_ve_ustu"]


def kupon_coz(metin: str) -> tuple[str | None, list[list[int]]]:
    """Oyun dosyasındaki kuponun tarihini ve kolonlarını okur
    (kolonlar henüz üretilmediyse boş liste)."""
    tarih = None
    for satir in metin.splitlines():
        m = re.match(r"KOLONLAR: (\d{4}-\d\d-\d\d) ", satir)
        if m:
            tarih = m.group(1)
            break
    kolonlar = []
    for satir in metin.splitlines():
        m = re.match(r"^\s*\d{1,2}\s+((?:\d{1,2}\s*-\s*){5}\d{1,2})\s", satir)
        if m:
            kolonlar.append(sorted(int(x) for x in m.group(1).split("-")))
    return tarih, kolonlar


def gecmis_kupon_metni(tarih: str, derinlik: int = 40) -> str:
    """Oyun dosyası o çekilişin kuponunu artık içermiyorsa (sonraki gün
    planlanmışsa) git geçmişindeki son halini arar."""
    try:
        metin = OYUN_PATH.read_text(encoding="utf-8")
        if kupon_coz(metin)[0] == tarih:
            return metin
    except OSError:
        pass
    try:
        shalar = subprocess.run(
            ["git", "log", f"-{derinlik}", "--format=%H", "--", OYUN_PATH.name],
            cwd=OYUN_PATH.parent, capture_output=True, text=True, check=True).stdout.split()
        for sha in shalar:
            metin = subprocess.run(["git", "show", f"{sha}:{OYUN_PATH.name}"], cwd=OYUN_PATH.parent,
                                   capture_output=True, text=True, check=True).stdout
            t, kolonlar = kupon_coz(metin)
            if t == tarih and kolonlar:
                return metin
    except (OSError, subprocess.CalledProcessError):
        pass
    return ""


def cekilis_degerlendir(cekilisler: list[dict], kupon_metni: str) -> dict:
    """Son çekilişi geçmişin ışığında sorgular: normal mi, dikkat çekici bir
    durum var mı, kuponumuz nasıl tuttu, kurallarımıza uyuyor muydu?"""
    son, gecmis = cekilisler[-1], cekilisler[:-1]
    onceki = gecmis[-1]["toplar"] if gecmis else []
    d = dizilim(son["toplar"], onceki)
    g = [dizilim(c["toplar"], gecmis[i - 1]["toplar"] if i else None) for i, c in enumerate(gecmis)]
    n = len(g) or 1

    def oran(kosul):
        return sum(1 for x in g if kosul(x)) / n

    dikkat = []
    alt = oran(lambda x: x["toplam"] <= d["toplam"])
    ust = oran(lambda x: x["toplam"] >= d["toplam"])
    if min(alt, ust) < 0.025:
        dikkat.append(f"toplam {d['toplam']}: bu kadar {'düşük' if alt < ust else 'yüksek'} "
                      f"toplamın geçmişteki oranı %{100 * min(alt, ust):.1f}")
    tek_oran = oran(lambda x: x["tek"] == d["tek"])
    if tek_oran < 0.05:
        dikkat.append(f"{d['tek']} tek / {6 - d['tek']} çift: geçmişte %{100 * tek_oran:.1f} sıklıkta")
    ard_oran = oran(lambda x: x["ardisik"] >= d["ardisik"])
    if d["ardisik"] and ard_oran < 0.05:
        dikkat.append(f"{d['ardisik']} ardışık ikili: geçmişte %{100 * ard_oran:.1f} sıklıkta")
    tkr_oran = oran(lambda x: x["tekrar"] >= d["tekrar"])
    if d["tekrar"] and tkr_oran < 0.05:
        dikkat.append(f"önceki çekilişten {d['tekrar']} numara tekrar etti: "
                      f"geçmişte %{100 * tkr_oran:.1f} sıklıkta")
    onlu_max = max(d["onlu"])
    onlu_oran = oran(lambda x: max(x["onlu"]) >= onlu_max)
    if onlu_oran < 0.05:
        dikkat.append(f"aynı onluktan {onlu_max} numara: geçmişte %{100 * onlu_oran:.1f} sıklıkta")
    son_gorulme = {}
    for i, c in enumerate(gecmis):
        for t in c["toplar"]:
            son_gorulme[t] = i
    gecikmeler = {t: len(gecmis) - 1 - son_gorulme.get(t, -1) for t in son["toplar"]}
    for t, gk in sorted(gecikmeler.items()):
        if gk >= 30:  # bir numaranın 30 çekiliş çıkmama ihtimali ~%4
            dikkat.append(f"{t} numara {gk} çekiliş aradan sonra geldi")

    kemik_uygun = kemik_ceza(son["toplar"], set(onceki)) == 0
    kemik_oran = (sum(1 for i, c in enumerate(gecmis[1:], 1)
                      if kemik_ceza(c["toplar"], set(gecmis[i - 1]["toplar"])) == 0) / max(1, n - 1))
    benzer = sum(1 for x in g if (x["onlu"], x["tek"], x["ardisik"])
                 == (d["onlu"], d["tek"], d["ardisik"]))

    an = numara_analizi(gecmis) if len(gecmis) > 10 else None
    seviye = Counter(an["seviye"][t] for t in son["toplar"]) if an else Counter()

    kupon_tarih, kolonlar = kupon_coz(kupon_metni) if kupon_metni else (None, [])
    kupon_var = kupon_tarih == son["tarih"] and bool(kolonlar)
    cikan = set(son["toplar"])
    bilen = [len(cikan & set(k)) for k in kolonlar] if kupon_var else []

    r = [f"# Çekiliş değerlendirmesi: #{son['no']} ({son['tarih']})", "",
         f"Çıkan numaralar: **{' - '.join(map(str, son['toplar']))}** "
         f"(toplam {d['toplam']}, {d['tek']} tek / {6 - d['tek']} çift, "
         f"{d['ardisik']} ardışık ikili, önceki çekilişten {d['tekrar']} tekrar)", "",
         "## Bu çekiliş normal mi?", ""]
    if dikkat:
        r += [f"- Dikkat çekici: {x}" for x in dikkat]
        r += ["", "Bu durumlar seyrek ama rastgele bir çekilişte de beklenir: her çekilişte "
              "bakılan birkaç özellikten birinin %5'lik dilime düşmesi olağandır."]
    else:
        r.append("Dikkat çekici bir durum yok: toplam, tek/çift dengesi, ardışıklar, "
                 "tekrarlar ve onluk dağılımı geçmişteki olağan aralıkta.")
    r += ["", f"Aynı dizilimde (onluk dağılımı, tek sayısı, ardışıklar) geçmiş çekiliş sayısı: "
          f"{benzer}."]
    if an:
        r.append(f"Güç dengesi: {seviye['G']} güçlü / {seviye['O']} orta / {seviye['Z']} zayıf numara.")
    r += ["", "## Kurallarımıza uyuyor muydu?", ""]
    if kemik_uygun:
        r.append("Evet, kemik yapıya uyuyor. Tüm kurallar modu bu dizilimde bir kolon üretebilirdi.")
    else:
        r.append("Hayır, kemik yapının dışında. Tüm kurallar modu (kemik yapı zorunlu) bu dizilimde "
                 "bir kolon üretemezdi (döngü kolonunda kemik yapı esnetilebildiği için o kolon "
                 "hariç). Bu bir \"hata\" değil, kuralın doğası: geçmiş çekilişlerde "
                 f"kemik yapıya uyma oranı %{100 * kemik_oran:.0f}.")
    r += ["", "## Kupon", ""]
    if kupon_var:
        dag = Counter(bilen)
        r.append(f"10 kolondan en iyisi **{max(bilen)} bildi**. Dağılım: "
                 + ", ".join(f"{k} bilen {dag[k]} kolon" for k in sorted(dag, reverse=True)) + ".")
        if len(kolonlar) == 10 and sorted(t for k in kolonlar for t in k) == list(range(1, 61)):
            r.append("60 numara / 10 kolon düzeninde çıkan 6 numaranın hepsi kuponda olur; "
                     "kazanmak için birkaçının aynı kolonda toplanması gerekir ve bu tamamen şansa bağlıdır.")
        r.append("Rastgele 10 kolonla beklenen: en az bir kolonda 3 bilme yaklaşık %10, 4 bilme %0,45.")
    else:
        r.append("Bu çekiliş için kayıtlı kupon bulunamadı.")
    return {"no": son["no"], "tarih": son["tarih"], "toplam": d["toplam"], "tek": d["tek"],
            "ardisik": d["ardisik"], "tekrar": d["tekrar"], "kemik_uygun": kemik_uygun,
            "dikkat": dikkat, "kupon_var": kupon_var, "kupon_bilen": bilen,
            "en_iyi": max(bilen) if bilen else None,
            "uc_ve_ustu": sum(1 for b in bilen if b >= 3) if bilen else None,
            "kemik_oran": kemik_oran, "rapor": "\n".join(r)}


def karne_oku() -> list[dict]:
    try:
        with KARNE_PATH.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def kural_karnesi(cekilisler: list[dict], ornek: int = 20000, analiz_son: int = 300) -> list[dict]:
    """Her kuralın gerçek çekilişlere uyma oranını, rastgele numaralarınkiyle
    karşılaştırır. Bir kural işe yarasaydı gerçek oran rastgeleden belirgin
    biçimde farklı olurdu. Rastgele örnek sabit tohumla üretilir."""
    rng = random.Random(0)
    kurallar = [
        ("Tek sayı adedi", lambda o: KEMIK["tek"][0] <= o["tek"] <= KEMIK["tek"][1]),
        ("1–30 arasından adet", lambda o: KEMIK["dusuk"][0] <= o["dusuk"] <= KEMIK["dusuk"][1]),
        ("Aynı onluk", lambda o: o["onlu"] <= KEMIK["onlu"]),
        ("Aynı son hane", lambda o: o["son_hane"] <= KEMIK["son_hane"]),
        ("Toplam", lambda o: KEMIK["toplam"][0] <= o["toplam"] <= KEMIK["toplam"][1]),
        ("Ardışık ikili", lambda o: o["ardisik"] <= KEMIK["ardisik"]),
        ("Son çekilişten tekrar", lambda o: o["tekrar"] <= KEMIK["tekrar"]),
    ]
    gercek = [kemik_olcu(c["toplar"], set(cekilisler[i - 1]["toplar"]))
              for i, c in enumerate(cekilisler) if i]
    rastgele = [kemik_olcu(rng.sample(SAYI_ARALIGI, 6),
                           set(cekilisler[rng.randrange(1, len(cekilisler))]["toplar"]))
                for _ in range(ornek)]
    satirlar = []
    for ad, f in kurallar + [("Kemik yapının tamamı", lambda o: all(g(o) for _, g in kurallar))]:
        satirlar.append({"kural": ad, "n": len(gercek),
                         "gercek": sum(map(f, gercek)) / len(gercek),
                         "rastgele": sum(map(f, rastgele)) / ornek})
    # Analize dayalı kurallar: her çekiliş, kendinden önceki veriyle.
    say = {"denge": [0, 0], "gecikme": [0, 0]}
    n = 0
    for i in range(max(11, len(cekilisler) - analiz_son), len(cekilisler)):
        an = numara_analizi(cekilisler[:i])
        for j, k in enumerate((cekilisler[i]["toplar"], rng.sample(SAYI_ARALIGI, 6))):
            sev = Counter(an["seviye"][t] for t in k)
            say["denge"][j] += all(sev[x] == 2 for x in "GOZ")
            say["gecikme"][j] += len(an["gecikme"] & set(k)) <= 1
        n += 1
    if n:
        for ad, a in (("Güç dengesi 2/2/2", "denge"),
                      ("Uzun süredir çıkmayanlardan en fazla 1", "gecikme")):
            satirlar.append({"kural": ad, "n": n, "gercek": say[a][0] / n, "rastgele": say[a][1] / n})
    k = KEMIK
    sinir = {"Tek sayı adedi": f"{k['tek'][0]}–{k['tek'][1]}",
             "1–30 arasından adet": f"{k['dusuk'][0]}–{k['dusuk'][1]}",
             "Aynı onluk": f"en fazla {k['onlu']}", "Aynı son hane": f"en fazla {k['son_hane']}",
             "Toplam": f"{k['toplam'][0]}–{k['toplam'][1]}", "Ardışık ikili": f"en fazla {k['ardisik']}",
             "Son çekilişten tekrar": f"en fazla {k['tekrar']}", "Kemik yapının tamamı": "hepsi birlikte",
             "Güç dengesi 2/2/2": "2 güçlü / 2 orta / 2 zayıf",
             "Uzun süredir çıkmayanlardan en fazla 1": "en uzun çıkmayan 10'dan en fazla 1"}
    for x in satirlar:
        x["sinir"] = sinir.get(x["kural"], "")
        # Rastgele orandan 3 standart hatadan fazla sapma "belirgin fark" sayılır.
        p = x["rastgele"]
        x["belirgin"] = abs(x["gercek"] - p) > 3 * (p * (1 - p) / x["n"]) ** 0.5 + 1e-9
    return satirlar


def kural_karnesi_metni(satirlar: list[dict]) -> str:
    r = ["", "## Kural karnesi", "",
         "Her kural tüm geçmiş çekilişlerle karşılaştırılır (güç dengesi ve gecikme son "
         f"{satirlar[-1]['n']} çekilişte, her biri kendinden önceki veriyle).", "",
         "| Kural | Gerçek çekilişlerde uyan | Rastgele numaralarda uyan | Fark |",
         "|---|---|---|---|"]
    for x in satirlar:
        fark = "belirgin" if x["belirgin"] else "yok"
        g, rs = (f"{100 * x[a]:.1f}".replace(".", ",") for a in ("gercek", "rastgele"))
        r.append(f"| {x['kural']} | %{g} | %{rs} | {fark} |")
    return "\n".join(r)


def ardisik_ikililer(toplar: list[int]) -> list[tuple[int, int]]:
    t = sorted(toplar)
    return [(a, b) for a, b in zip(t, t[1:]) if b - a == 1]


def pencere(cekilisler: list[dict]) -> list[dict]:
    """Analiz penceresi: son çekilişten geriye doğru 60 numaranın hepsi gelene
    kadar gidilir; tamamlandığı çekilişten son çekilişe kadar (eskiden yeniye)."""
    gor = set()
    for j in range(len(cekilisler) - 1, -1, -1):
        gor |= set(cekilisler[j]["toplar"])
        if len(gor) == 60:
            return cekilisler[j:]
    return list(cekilisler)


def _hiper(k_basari: int, x: int) -> float:
    """60 numaradan 6 çekilince belirli k_basari numaradan tam x tanesinin gelme olasılığı."""
    return math.comb(k_basari, x) * math.comb(60 - k_basari, 6 - x) / math.comb(60, 6)


def _toplam_dilimi(t: int) -> str:
    if t < 150:
        return "150'den az"
    if t >= 240:
        return "240 ve üstü"
    alt = 150 + (t - 150) // 30 * 30
    return f"{alt}–{alt + 29}"


PENCERE_BOLUMLERI = [
    ("1–30 / 31–60", [f"{a}–{6 - a}" for a in range(6, -1, -1)],
     lambda t, o: (lambda a: f"{a}–{6 - a}")(sum(x <= 30 for x in t))),
    ("Tek / çift", [f"{a}–{6 - a}" for a in range(6, -1, -1)],
     lambda t, o: (lambda a: f"{a}–{6 - a}")(sum(x % 2 for x in t))),
    ("Asal sayısı", ["0", "1", "2", "3", "4+"],
     lambda t, o: (lambda a: "4+" if a >= 4 else str(a))(sum(x in ASALLAR for x in t))),
    ("Ardışık ikili", ["0", "1", "2", "3+"],
     lambda t, o: (lambda a: "3+" if a >= 3 else str(a))(len(ardisik_ikililer(t)))),
    ("Üst üste (önceki çekilişten)", ["0", "1", "2", "3+"],
     lambda t, o: (lambda a: "3+" if a >= 3 else str(a))(len(set(t) & set(o)))),
    ("Aynı onluktan en çok", ["1", "2", "3", "4+"],
     lambda t, o: (lambda a: "4+" if a >= 4 else str(a))(max(Counter((x - 1) // 10 for x in t).values()))),
    ("Aynı son haneden en çok", ["1", "2", "3", "4+"],
     lambda t, o: (lambda a: "4+" if a >= 4 else str(a))(max(Counter(x % 10 for x in t).values()))),
    ("Toplam", ["150'den az", "150–179", "180–209", "210–239", "240 ve üstü"],
     lambda t, o: _toplam_dilimi(sum(t))),
]


@functools.lru_cache(maxsize=1)
def _rastgele_oranlar(ornek: int = 100000) -> dict:
    """Rastgele beklenen oranlar: kesin formülü olanlar formülle, diğerleri sabit
    tohumlu örneklemle."""
    kesin = {
        "1–30 / 31–60": {f"{a}–{6 - a}": _hiper(30, a) for a in range(7)},
        "Tek / çift": {f"{a}–{6 - a}": _hiper(30, a) for a in range(7)},
        "Asal sayısı": {**{str(a): _hiper(len(ASALLAR), a) for a in range(4)},
                        "4+": sum(_hiper(len(ASALLAR), a) for a in range(4, 7))},
        "Ardışık ikili": {**{str(r): math.comb(5, r) * math.comb(55, 6 - r) / math.comb(60, 6)
                             for r in range(3)},
                          "3+": sum(math.comb(5, r) * math.comb(55, 6 - r) / math.comb(60, 6)
                                    for r in range(3, 6))},
        "Üst üste (önceki çekilişten)": {**{str(a): _hiper(6, a) for a in range(3)},
                                         "3+": sum(_hiper(6, a) for a in range(3, 7))},
    }
    rng = random.Random(0)
    say = {ad: Counter() for ad, _, _ in PENCERE_BOLUMLERI if ad not in kesin}
    for _ in range(ornek):
        t = sorted(rng.sample(SAYI_ARALIGI, 6))
        for ad, _, f in PENCERE_BOLUMLERI:
            if ad in say:
                say[ad][f(t, [])] += 1
    return {**kesin, **{ad: {k: n / ornek for k, n in c.items()} for ad, c in say.items()}}


def pencere_analizi(cekilisler: list[dict]) -> dict:
    """Bütün analizler, son 60 numara penceresi üzerinden; tüm geçmiş ve rastgele
    beklenen karşılaştırma için yanında. Kural değildir."""
    pen = pencere(cekilisler)
    ilk = cekilisler.index(pen[0])
    onceki = [cekilisler[ilk + i - 1]["toplar"] if ilk + i else [] for i in range(len(pen))]
    rastgele = _rastgele_oranlar()
    tum_n = len(cekilisler) - 1
    dagilimlar = []
    for ad, degerler, f in PENCERE_BOLUMLERI:
        p_say = Counter(f(sorted(c["toplar"]), o) for c, o in zip(pen, onceki))
        t_say = Counter(f(sorted(c["toplar"]), cekilisler[i - 1]["toplar"])
                        for i, c in enumerate(cekilisler) if i)
        for deger in degerler:
            dagilimlar.append({"bolum": ad, "deger": deger, "pencere": p_say[deger],
                               "pencere_oran": p_say[deger] / len(pen),
                               "tum": t_say[deger] / tum_n if tum_n else 0.0,
                               "rastgele": rastgele[ad].get(deger, 0.0)})
    sik = Counter(t for c in pen for t in c["toplar"])
    ikili = Counter(p for c in pen for p in combinations(sorted(c["toplar"]), 2))
    ustuste = Counter(t for c, o in zip(pen, onceki) for t in set(c["toplar"]) & set(o))
    ardisik = Counter(p for c in pen for p in ardisik_ikililer(c["toplar"]))
    son_gorulme = {t: i for i, c in enumerate(pen) for t in c["toplar"]}
    gecikme = sorted(((len(pen) - 1 - i, t) for t, i in son_gorulme.items()), key=lambda x: (-x[0], x[1]))
    toplamlar = [sum(c["toplar"]) for c in pen]
    listeler = []

    def ekle(bolum, deger, adet):
        listeler.append({"bolum": bolum, "deger": deger, "adet": adet})
    for n in sorted(set(sik.values()), reverse=True):
        ekle("Numara sıklığı", " ".join(str(t) for t in SAYI_ARALIGI if sik[t] == n), n)
    for (a, b), n in sorted(ikili.items(), key=lambda x: (-x[1], x[0])):
        if n >= 2:
            ekle("Birlikte gelen (2+ kez)", f"{a}-{b}", n)
    for t, n in sorted(ustuste.items(), key=lambda x: (-x[1], x[0])):
        ekle("Üst üste gelen", str(t), n)
    for (a, b), n in sorted(ardisik.items(), key=lambda x: (-x[1], x[0])):
        ekle("Ardışık ikili", f"{a}-{b}", n)
    for g, t in gecikme[:10]:
        ekle("En uzun süredir gelmeyen", str(t), g)
    ekle("Özet", "Toplam ortalaması", round(sum(toplamlar) / len(pen), 1))
    ekle("Özet", "En düşük toplam", min(toplamlar))
    ekle("Özet", "En yüksek toplam", max(toplamlar))
    ekle("Özet", "Ortalama tek sayı", round(sum(sum(t % 2 for t in c["toplar"]) for c in pen) / len(pen), 2))
    ekle("Özet", "Ortalama asal sayı",
         round(sum(sum(t in ASALLAR for t in c["toplar"]) for c in pen) / len(pen), 2))
    ekle("Özet", "Kemik yapıya uyan", sum(kemik_ceza(c["toplar"], set(o)) == 0 for c, o in zip(pen, onceki)))
    return {"bas_no": pen[0]["no"], "son_no": pen[-1]["no"], "bas_tarih": pen[0]["tarih"],
            "son_tarih": pen[-1]["tarih"], "cekilis": len(pen),
            "dagilimlar": dagilimlar, "listeler": listeler}


def pencere_analizi_yaz(cekilisler: list[dict]) -> dict:
    """Pencere analizini pano için iki CSV dosyasına yazar."""
    a = pencere_analizi(cekilisler)
    ek = [a["bas_no"], a["son_no"], a["cekilis"]]
    with PENCERE_ANALIZI_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["bolum", "deger", "pencere", "pencere_yuzde", "tum_yuzde", "rastgele_yuzde",
                    "bas_no", "son_no", "cekilis"])
        for r in a["dagilimlar"]:
            w.writerow([r["bolum"], r["deger"], r["pencere"], f"{100 * r['pencere_oran']:.1f}",
                        f"{100 * r['tum']:.1f}", f"{100 * r['rastgele']:.1f}", *ek])
    with PENCERE_LISTELERI_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["bolum", "deger", "adet", "bas_no", "son_no", "cekilis"])
        for r in a["listeler"]:
            w.writerow([r["bolum"], r["deger"], r["adet"], *ek])
    return a


def pencere_analizi_metni(a: dict) -> str:
    def y(x):
        return f"{100 * x:.1f}".replace(".", ",")
    n = a["cekilis"]
    r = ["", "## Analizler: 60 numara penceresi", "",
         f"Son çekilişten geriye 60 numaranın hepsinin geldiği çekilişler: #{a['bas_no']}–#{a['son_no']} "
         f"({a['bas_tarih']} – {a['son_tarih']}, {n} çekiliş). Bütün analizler bu pencere üzerinden "
         "yapılır; tüm geçmiş ve rastgele beklenen karşılaştırma içindir. Kural değildir.", ""]
    for ad, degerler, _ in PENCERE_BOLUMLERI:
        r += [f"### {ad}", "", f"| Değer | Pencere ({n}) | Oran | Tüm geçmiş | Rastgele | Fark |",
              "|---|---|---|---|---|---|"]
        for x in (x for x in a["dagilimlar"] if x["bolum"] == ad):
            p = x["rastgele"]
            belirgin = n and abs(x["pencere"] - n * p) > 3 * (n * p * (1 - p)) ** 0.5 + 1e-9
            r.append(f"| {x['deger']} | {x['pencere']} | %{y(x['pencere_oran'])} | %{y(x['tum'])} | "
                     f"%{y(p)} | {'belirgin' if belirgin else ''} |")
        r.append("")
    gruplar = {}
    for x in a["listeler"]:
        gruplar.setdefault(x["bolum"], []).append(x)
    yazim = {
        "Numara sıklığı": lambda x: f"{x['adet']} kez: {x['deger']}",
        "Birlikte gelen (2+ kez)": lambda x: f"{x['deger']} ({x['adet']})",
        "Üst üste gelen": lambda x: f"{x['deger']} ({x['adet']})",
        "Ardışık ikili": lambda x: f"{x['deger']} ({x['adet']})",
        "En uzun süredir gelmeyen": lambda x: f"{x['deger']} ({x['adet']} çekiliş)",
        "Özet": lambda x: f"{x['deger']}: {str(x['adet']).replace('.', ',')}",
    }
    for ad, f in yazim.items():
        if ad not in gruplar:
            continue
        if ad == "Numara sıklığı":
            r += [f"### {ad}", ""] + [f"- {f(x)}" for x in gruplar[ad]] + [""]
        else:
            r.append(f"**{ad}:** " + ", ".join(f(x) for x in gruplar[ad]))
    return "\n".join(r)


def _dongu_kaydi(parca: list[dict], tamam: bool, tamamlayan: list[int]) -> dict:
    gelen = {t for c in parca for t in c["toplar"]}
    return {"bas_no": parca[0]["no"], "bas_tarih": parca[0]["tarih"],
            "son_no": parca[-1]["no"], "son_tarih": parca[-1]["tarih"], "uzunluk": len(parca),
            "durum": "tamam" if tamam else "devam", "gelen": len(gelen),
            "tamamlayan": tamamlayan if tamam else [],
            "eksik": [] if tamam else sorted(set(SAYI_ARALIGI) - gelen)}


def _ileri_tamamlayan(parca: list[dict]) -> list[int]:
    """Bloğu eskiden yeniye tarayınca 60 numarayı tamamlayan çekilişte ilk kez gelenler."""
    gor = set()
    for c in parca:
        yeni = set(c["toplar"]) - gor
        gor |= yeni
        if len(gor) == 60:
            return sorted(yeni)
    return []


def donguler(cekilisler: list[dict], capa: int = DONGU_CAPA) -> list[dict]:
    """60 numaranın hepsinin geldiği ardışık çekiliş blokları (döngüler), eskiden
    yeniye. `capa`dan önceki çekilişler geriye doğru bölünür (son döngü capa-1'de
    biter, en eski tamamlanmayan parça atılır); capa ve sonrası ileriye doğru
    izlenir. Son döngü tamamlandıysa, sıradaki çekilişle başlayacak boş bir
    "devam" döngüsü eklenir (hiçbir numara henüz gelmemiş)."""
    gecmis = [c for c in cekilisler if c["no"] < capa]
    ileri = [c for c in cekilisler if c["no"] >= capa]
    sonuc = []
    i = len(gecmis) - 1
    while i >= 0:
        gor, j, yeni = set(), i, set()
        while j >= 0 and len(gor) < 60:
            yeni = set(gecmis[j]["toplar"]) - gor
            gor |= yeni
            j -= 1
        if len(gor) < 60:
            break
        parca = gecmis[j + 1:i + 1]
        sonuc.append(_dongu_kaydi(parca, True, _ileri_tamamlayan(parca)))
        i = j
    sonuc.reverse()
    bas = 0
    while bas < len(ileri):
        gor, k, yeni = set(), bas, set()
        while k < len(ileri) and len(gor) < 60:
            yeni = set(ileri[k]["toplar"]) - gor
            gor |= yeni
            k += 1
        sonuc.append(_dongu_kaydi(ileri[bas:k], len(gor) == 60, sorted(yeni)))
        bas = k
    if not sonuc or sonuc[-1]["durum"] == "tamam":
        son = cekilisler[-1]
        sonraki = sonraki_cekilis(son["tarih"]).isoformat()
        sonuc.append({"bas_no": son["no"] + 1, "bas_tarih": sonraki, "son_no": son["no"],
                      "son_tarih": son["tarih"], "uzunluk": 0, "durum": "devam", "gelen": 0,
                      "tamamlayan": [], "eksik": list(SAYI_ARALIGI)})
    for n, d in enumerate(sonuc, 1):
        d["sira"] = n
    return sonuc


def dongu_tahmin_skoru(cekilisler: list[dict], capa: int = DONGU_CAPA) -> list[dict]:
    """İleriye doğru izlenen döngülerde, her çekilişten önce o döngüde henüz
    gelmemiş numaralar "tahmin"dir. Her çekilişte bunlardan kaçının geldiği
    (isabet) ve rastgele beklenen (6 × eksik / 60)."""
    sonuc, gor = [], set()
    for c in (c for c in cekilisler if c["no"] >= capa):
        if len(gor) == 60:
            gor = set()
        eksik = set(SAYI_ARALIGI) - gor
        sonuc.append({"no": c["no"], "tarih": c["tarih"], "eksik_sayisi": len(eksik),
                      "isabet": len(eksik & set(c["toplar"])), "beklenen": 6 * len(eksik) / 60})
        gor |= set(c["toplar"])
    return sonuc


def dongu_tahmin_testi(cekilisler: list[dict]) -> tuple[int, float, int]:
    """Geriye dönük test: tüm geçmiş ileriye doğru döngülere bölünür ve her
    çekilişte (döngünün ilk çekilişi hariç) eksik numaralardan gelen sayısı
    rastgele beklenenle toplanır. Dönüş: (isabet, beklenen, çekiliş)."""
    s = [x for x in dongu_tahmin_skoru(cekilisler, capa=cekilisler[0]["no"]) if x["eksik_sayisi"] < 60]
    return sum(x["isabet"] for x in s), sum(x["beklenen"] for x in s), len(s)


def dongu_karnesi_yaz(cekilisler: list[dict]) -> list[dict]:
    """Döngüleri ve ileriye doğru tahmin isabetini pano için dongu_karnesi.csv'ye yazar."""
    d = donguler(cekilisler)
    skor = dongu_tahmin_skoru(cekilisler)
    with DONGU_KARNESI_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["sira", "bas_no", "bas_tarih", "son_no", "son_tarih", "uzunluk", "durum",
                    "gelen", "tamamlayan", "eksik", "isabet", "beklenen"])
        for x in d:
            ici = [s for s in skor if x["bas_no"] <= s["no"] <= x["son_no"] and s["eksik_sayisi"] < 60]
            w.writerow([x["sira"], x["bas_no"], x["bas_tarih"], x["son_no"], x["son_tarih"],
                        x["uzunluk"], x["durum"], x["gelen"], " ".join(map(str, x["tamamlayan"])),
                        " ".join(map(str, x["eksik"])),
                        sum(s["isabet"] for s in ici) if ici else "",
                        f"{sum(s['beklenen'] for s in ici):.1f}" if ici else ""])
    return d


def dongu_karnesi_metni(cekilisler: list[dict], d: list[dict]) -> str:
    def v(x, n=1):
        return f"{x:.{n}f}".replace(".", ",")
    simdi = d[-1]
    tam = [x for x in d if x["durum"] == "tamam"]
    sinir = (datetime.date.fromisoformat(cekilisler[-1]["tarih"])
             - datetime.timedelta(days=SON_DONEM_GUN)).isoformat()
    yakin = [x["uzunluk"] for x in tam if x["bas_tarih"] >= sinir]
    tum = [x["uzunluk"] for x in tam]
    ort_yakin = sum(yakin) / len(yakin) if yakin else None
    ort_tum = sum(tum) / len(tum)
    r = ["", "## Döngü kuralı", "",
         "Döngü: 60 numaranın hepsinin geldiği ardışık çekilişler. Döngü kuralı: tüm kurallar "
         "modunda bu döngüde henüz gelmeyen numaralar mümkün olduğunca aynı kolonlarda toplanır.", ""]
    biten = tam[-1] if tam and not simdi["uzunluk"] and tam[-1]["son_no"] == cekilisler[-1]["no"] else None
    if biten:
        kiyas = ""
        onceki = [x["uzunluk"] for x in tam[:-1] if x["bas_tarih"] >= sinir]
        if onceki:
            ort_onceki = sum(onceki) / len(onceki)
            fark = biten["uzunluk"] - ort_onceki
            kiyas = (f" Önceki döngülerin son 1,5 yıl ortalamasından ({v(ort_onceki)}) "
                     + (f"{v(abs(fark))} çekiliş {'kısa' if fark < 0 else 'uzun'}." if abs(fark) >= 0.05
                        else "farksız."))
        r.append(f"**Döngü tamamlandı:** #{biten['bas_no']}–#{biten['son_no']}, {biten['uzunluk']} "
                 f"çekilişte; son tamamlayan {' '.join(map(str, biten['tamamlayan']))}.{kiyas} "
                 f"Yeni döngü #{simdi['bas_no']} ile 60 numaradan baştan başlıyor.")
    if simdi["uzunluk"]:
        r.append(f"**Şu anki döngü:** #{simdi['bas_no']}'dan beri {simdi['uzunluk']} çekiliş, "
                 f"60 numaranın {simdi['gelen']} tanesi geldi.")
    else:
        r.append(f"**Şu anki döngü:** #{simdi['bas_no']} ile başlayacak; henüz hiçbir numara gelmedi.")
    r.append(f"**Sıradaki tahmin (bu döngüde henüz gelmeyen {len(simdi['eksik'])} numara):** "
             + " ".join(map(str, simdi["eksik"])))
    if ort_yakin is not None:
        kalan = max(0, round(ort_yakin) - simdi["uzunluk"])
        r.append(f"Son 1,5 yılın döngü ortalaması {v(ort_yakin)} çekiliş (tüm geçmiş {v(ort_tum)}); "
                 f"buna göre döngünün tamamlanmasına yaklaşık {kalan} çekiliş kaldı.")
    skor = [s for s in dongu_tahmin_skoru(cekilisler) if s["eksik_sayisi"] < 60]
    test_i, test_b, test_n = dongu_tahmin_testi(cekilisler)
    r += ["", "**Tahmin isabeti:** her çekilişte, o döngüde henüz gelmeyen numaralardan kaçı geldi."]
    if skor:
        r.append(f"- Takip başladığından beri ({len(skor)} çekiliş): {sum(s['isabet'] for s in skor)} "
                 f"isabet, rastgele beklenen {v(sum(s['beklenen'] for s in skor))}.")
    else:
        r.append("- Takip #986'dan sonraki çekilişlerle ölçülmeye başlayacak.")
    r.append(f"- Geriye dönük test ({test_n} çekiliş): {test_i} isabet, rastgele beklenen "
             f"{v(test_b)}. Fark yoksa tahmin rastgeleden iyi değildir.")
    r += ["", "| Döngü | Çekilişler | Başlangıç | Kaç çekilişte | Son tamamlayan |", "|---|---|---|---|---|"]
    for x in tam[-10:][::-1]:
        r.append(f"| {x['sira']} | #{x['bas_no']}–#{x['son_no']} | {x['bas_tarih']} | {x['uzunluk']} | "
                 + " ".join(map(str, x["tamamlayan"])) + " |")
    return "\n".join(r)


# Lastik sayılar: uzun süredir gelmeyen numaralar. Bir numaranın bir çekilişte
# gelme olasılığı 6/60 = %10; g çekiliş üst üste gelmeme olasılığı 0,9^g.
LASTIK_SEVIYELER = [(44, "kopma sınırında"), (29, "çok gergin"), (22, "gergin")]  # ~%1, ~%5, ~%10


def _gecikmeler(cekilisler: list[dict]) -> tuple[dict, dict]:
    """Her numaranın şu anki gecikmesi ve geçmişteki en uzun arası (rekor)."""
    son, rekor = {}, {t: 0 for t in SAYI_ARALIGI}
    for i, c in enumerate(cekilisler):
        for t in c["toplar"]:
            if t in son:
                rekor[t] = max(rekor[t], i - son[t] - 1)
            son[t] = i
    n = len(cekilisler)
    return {t: n - 1 - son.get(t, -1) for t in SAYI_ARALIGI}, rekor


def lastik_sayilar(cekilisler: list[dict]) -> list[dict]:
    """En az 22 çekiliştir gelmeyen numaralar, gecikmesi en uzun olan önce."""
    gecikme, rekor = _gecikmeler(cekilisler)
    sonuc = []
    for t, g in gecikme.items():
        seviye = next((ad for esik, ad in LASTIK_SEVIYELER if g >= esik), None)
        if seviye:
            sonuc.append({"sayi": t, "gecikme": g, "seviye": seviye, "rekor": rekor[t],
                          "olasilik": 0.9 ** g})
    return sorted(sonuc, key=lambda x: (-x["gecikme"], x["sayi"]))


def lastik_karnesi(cekilisler: list[dict], isinma: int = 60) -> list[dict]:
    """Geriye dönük: bir numara lastik olduğunda sonraki çekilişte kaç kez geldi?
    (Rastgele beklenen %10.) Her seviye kendi eşiği ve üstünü sayar."""
    say = {ad: [0, 0] for _, ad in LASTIK_SEVIYELER}
    son = {}
    for i, c in enumerate(cekilisler):
        if i >= isinma:
            cikan = set(c["toplar"])
            for t in SAYI_ARALIGI:
                g = i - son.get(t, -1) - 1
                for esik, ad in LASTIK_SEVIYELER:
                    if g >= esik:
                        say[ad][0] += 1
                        say[ad][1] += t in cikan
        for t in c["toplar"]:
            son[t] = i
    return [{"seviye": ad, "durum": say[ad][0], "geldi": say[ad][1],
             "oran": say[ad][1] / say[ad][0] if say[ad][0] else 0.0}
            for _, ad in reversed(LASTIK_SEVIYELER)]


def lastik_metni(cekilisler: list[dict]) -> str:
    def y(x, n=1):
        return f"{100 * x:.{n}f}".replace(".", ",")
    r = ["", "## Lastik sayılar", "",
         "Uzun süredir gelmeyen numaralar (izleme, kural değil). Gergin: 22+ çekiliş (bu kadar uzun "
         "ara ~%10), çok gergin: 29+ (~%5), kopma sınırında: 44+ (~%1). Tarihteki en uzun ara 71.", ""]
    l = lastik_sayilar(cekilisler)
    if l:
        r += ["| Numara | Kaç çekiliştir yok | Seviye | Kendi rekoru | Bu kadar uzun ara olasılığı |",
              "|---|---|---|---|---|"]
        for x in l:
            rekor = f"{x['rekor']}" + (" (rekor kırıyor)" if x["gecikme"] > x["rekor"] else "")
            r.append(f"| {x['sayi']} | {x['gecikme']} | {x['seviye']} | {rekor} | %{y(x['olasilik'], 2)} |")
    else:
        r.append("Şu an lastik numara yok.")
    r += ["", "**Lastikler kopuyor mu?** Geçmişte bir numara lastikken sonraki çekilişte gelme oranı "
          "(rastgele beklenen %10):"]
    for x in lastik_karnesi(cekilisler):
        r.append(f"- {x['seviye']}: {x['durum']} durumda {x['geldi']} kez geldi, %{y(x['oran'])}")
    return "\n".join(r)


def kural_karnesi_yaz(cekilisler: list[dict]) -> list[dict]:
    """Kural karnesini hesaplar ve pano için kural_karnesi.csv dosyasına yazar."""
    kurallar = kural_karnesi(cekilisler)
    with KURAL_KARNESI_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["kural", "sinir", "gercek", "rastgele", "fark", "cekilis"])
        for x in kurallar:
            w.writerow([x["kural"], x["sinir"], f"{100 * x['gercek']:.1f}", f"{100 * x['rastgele']:.1f}",
                        "belirgin" if x["belirgin"] else "yok", x["n"]])
    return kurallar


def karne_ozeti(satirlar: list[dict], kemik_oran: float,
                kurallar: list[dict] | None = None, analiz: dict | None = None,
                dongu: tuple[list[dict], list[dict]] | None = None) -> str:
    """Biriken değerlendirmelerden karne ve kanıta dayalı öneriler."""
    n = len(satirlar)
    r = ["", "## Karne", "", f"Değerlendirilen çekiliş: {n}"]
    if not n:
        return "\n".join(r)
    satirlar = [{k: str(v) for k, v in s.items()} for s in satirlar]  # CSV'den okunanla aynı biçim
    kemik = sum(s["kemik_uygun"] == "1" for s in satirlar)
    dikkat = sum(int(s["dikkat_sayisi"]) > 0 for s in satirlar)
    kuponlu = [s for s in satirlar if s["kupon_var"] == "1"]
    r.append(f"- Kemik yapıya uyan çekiliş: {kemik}/{n} (geçmişin tamamında %{100 * kemik_oran:.0f})")
    r.append(f"- Dikkat çekici durumu olan çekiliş: {dikkat}/{n}")
    if kuponlu:
        uc = sum(int(s["uc_ve_ustu"] or 0) > 0 for s in kuponlu)
        en_iyi = Counter(int(s["en_iyi"]) for s in kuponlu)
        r.append(f"- Kupon oynanan çekiliş: {len(kuponlu)}; en az bir kolonda 3+ bilen: "
                 f"{uc} (rastgele beklenen ~{0.099 * len(kuponlu):.1f})")
        r.append("- En iyi kolon dağılımı: "
                 + ", ".join(f"{k} bilen {en_iyi[k]} kez" for k in sorted(en_iyi, reverse=True)))
    if kurallar:
        r.append(kural_karnesi_metni(kurallar))
    if analiz:
        r.append(pencere_analizi_metni(analiz))
    if dongu:
        r.append(lastik_metni(dongu[0]))
    if dongu:
        r.append(dongu_karnesi_metni(*dongu))
    r += ["", "## Öneriler", ""]
    oneri = []
    if kurallar:
        belirgin = [x["kural"] for x in kurallar if x["belirgin"]]
        if belirgin:
            oneri.append("Gerçek çekilişlerde rastgeleden belirgin farklı davranan kural: "
                         + ", ".join(belirgin) + ". Bu kurala daha yakından bakmaya değer.")
        else:
            oneri.append("Hiçbir kural gerçek çekilişlerde rastgele numaralardan belirgin farklı "
                         "davranmıyor. Kurallar kazanma ihtimalini değiştirmez, yalnızca düzen sağlar.")
        tamami = next(x for x in kurallar if x["kural"] == "Kemik yapının tamamı")
        if tamami["gercek"] < 0.5:
            oneri.append(f"Kemik yapı gerçek çekilişlerin yalnızca %{100 * tamami['gercek']:.0f}'ine "
                         "uyuyor; kolonlar gerçek dizilimlere benzesin isteniyorsa sınırlar gevşetilebilir.")
    if len(kuponlu) >= 30:
        beklenen = 0.099 * len(kuponlu)
        uc = sum(int(s["uc_ve_ustu"] or 0) > 0 for s in kuponlu)
        if uc < beklenen - 2 * (beklenen * 0.9) ** 0.5:
            oneri.append("Kuponlarımız 3+ bilmede rastgele beklenenin belirgin şekilde altında "
                         "kaldı; kuralları gözden geçirmek mantıklı olabilir.")
    elif kuponlu:
        oneri.append(f"Kendi kuponlarımızın sonucu için {len(kuponlu)} çekiliş var; rastgele "
                     "beklentiyle anlamlı karşılaştırma için en az 30 kuponlu çekiliş gerekiyor.")
    r += [f"- {x}" for x in oneri] or ["Henüz öneri yok."]
    return "\n".join(r)


def degerlendir_ve_kaydet(cekilisler: list[dict], kupon_metni: str | None = None) -> None:
    """Son çekilişi değerlendirir; karneye bir satır ekler (bir kez) ve
    son_degerlendirme.md dosyasını yazar."""
    son = cekilisler[-1]
    if kupon_metni is None:
        kupon_metni = gecmis_kupon_metni(son["tarih"])
    d = cekilis_degerlendir(cekilisler, kupon_metni)
    kurallar = kural_karnesi_yaz(cekilisler)
    analiz = pencere_analizi_yaz(cekilisler)
    satirlar = karne_oku()
    if not any(s["no"] == str(son["no"]) for s in satirlar):
        satirlar.append({"no": d["no"], "tarih": d["tarih"], "toplam": d["toplam"], "tek": d["tek"],
                         "ardisik": d["ardisik"], "tekrar": d["tekrar"],
                         "kemik_uygun": int(d["kemik_uygun"]), "dikkat_sayisi": len(d["dikkat"]),
                         "kupon_var": int(d["kupon_var"]),
                         "en_iyi": "" if d["en_iyi"] is None else d["en_iyi"],
                         "uc_ve_ustu": "" if d["uc_ve_ustu"] is None else d["uc_ve_ustu"]})
        with KARNE_PATH.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=KARNE_ALANLARI)
            w.writeheader()
            w.writerows(satirlar)
    metin = (d["rapor"] + "\n" + karne_ozeti(satirlar, d["kemik_oran"], kurallar, analiz,
                          (cekilisler, dongu_karnesi_yaz(cekilisler)))
             + "\n\nNot: Her çekiliş bağımsızdır; bu değerlendirme geçmişi özetler, "
               "sonraki çekilişi tahmin etmez.\n")
    DEGERLENDIRME_PATH.write_text(metin, encoding="utf-8")
    print(metin)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--analiz", action="store_true", help="indirmeden sadece analiz yap")
    p.add_argument("--son", type=int, help="analizi son N çekilişle sınırla")
    p.add_argument("--yil", type=int, help="analizi tek bir yılın çekilişleriyle sınırla")
    p.add_argument("--yillik", action="store_true", help="yıllara göre özet tablo yazdır")
    p.add_argument("--kolon", action="store_true",
                   help="60 numaranın hepsini kullanan 10 kolon öner")
    p.add_argument("--tohum", type=int,
                   help="--kolon için tohum (aynı tohum aynı kolonları verir; geçmiş kullanılmaz)")
    p.add_argument("--taklitci", action="store_true",
                   help="taklitçi kural: her kolon gerçek bir çekilişin dizilimini taklit eder")
    p.add_argument("--gezegen", action="store_true",
                   help="sonraki çekiliş günü için Ankara gezegen saatleri ve şanslı saatler")
    p.add_argument("--tarih", help="--gezegen için tarih (YYYY-AA-GG); verilmezse sonraki çekiliş günü")
    p.add_argument("--degerlendir", action="store_true",
                   help="son çekilişi değerlendir: normal mi, kupon nasıl tuttu, kurallara uyuyor muydu; "
                        "karneye ekle")
    p.add_argument("--kural-karnesi", action="store_true",
                   help="kural karnesini, 60 numara penceresi analizlerini ve döngüleri "
                        "CSV dosyalarına yaz")
    p.add_argument("--oyun", choices=["planla", "jupiter"],
                   help="oyun_kolonlari.txt: 'planla' sonraki çekiliş gününü hazırlar, "
                        "'jupiter' çekiliş günü Jüpiter saatindeyse kolonları üretir")
    p.add_argument("--simdi", help="--oyun jupiter için zamanı belirle (YYYY-AA-GGTSS:DD), test için")
    p.add_argument("--bekle", type=int, default=0, metavar="SANIYE",
                   help="--oyun jupiter: Jüpiter saati en geç bu kadar saniye sonra başlıyorsa "
                        "bekleyip o saatte üret")
    p.add_argument("--hepsi", action="store_true",
                   help="tüm kurallar: taklitçi kural + kemik yapı + farklı düzen + döngü kuralı birlikte")
    p.add_argument("--taklit-oran", type=int, default=7,
                   help="--taklitci: 10 şablondan kaçının son 1 yıldan seçileceği (0-10, varsayılan 7)")
    p.add_argument("--tolerans", type=int, default=6,
                   help="--taklitci: toplamın şablondan en fazla ne kadar farklı olabileceği "
                        "(varsayılan 6)")
    p.add_argument("--set", type=int, default=1,
                   help="--kolon ile kaç farklı 10'lu kolon seti üretileceği")
    p.add_argument("--sifirla", action="store_true",
                   help="--kolon: bu çekiliş için daha önce verilen kolonları unut")
    a = p.parse_args()

    if a.gezegen and a.tarih:
        gezegen_yazdir(datetime.date.fromisoformat(a.tarih))
        return
    veri = csv_oku() if a.analiz else guncelle()
    cekilisler = [veri[k] for k in sorted(veri)]
    if a.gezegen:
        gezegen_yazdir(sonraki_cekilis(cekilisler[-1]["tarih"]))
        return
    if a.degerlendir:
        degerlendir_ve_kaydet(cekilisler)
        return
    if a.kural_karnesi:
        print(kural_karnesi_metni(kural_karnesi_yaz(cekilisler)).strip())
        print(pencere_analizi_metni(pencere_analizi_yaz(cekilisler)))
        print(lastik_metni(cekilisler))
        print(dongu_karnesi_metni(cekilisler, dongu_karnesi_yaz(cekilisler)))
        return
    if a.oyun == "planla":
        oyun_planla(cekilisler)
        return
    if a.oyun == "jupiter":
        simdi = (datetime.datetime.fromisoformat(a.simdi) if a.simdi else
                 datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=ANKARA[2])))
                 .replace(tzinfo=None))
        oyun_jupiter(cekilisler, simdi, a.bekle)
        return
    if a.hepsi:
        a.taklitci = True
    if a.kolon or a.taklitci:
        an = numara_analizi(cekilisler)
        son = cekilisler[-1]
        tarih = an["sonraki_tarih"]
        gecmisli = a.tohum is None
        kayit = (gecmis_oku(tarih) if gecmisli and not a.sifirla
                 else {"kolonlar": [], "sablonlar": []})
        onceki = kayit["kolonlar"]
        print(f"Son çekiliş #{son['no']} ({son['tarih']}), sonraki çekiliş: "
              f"{tarih} {an['sonraki_gun']}. Bu çekiliş için daha önce verilen kolon: "
              f"{len(onceki)}\n")
        for n in range(a.set):
            tohum = None if a.tohum is None else a.tohum + n
            baslik = f"Set {len(onceki) // 10 + 1}: 60 numaranın hepsini kullanan 10 kolon"
            try:
                if a.taklitci:
                    sonuc = taklit_uret(cekilisler, tohum, onceki, set(kayit["sablonlar"]),
                                        a.taklit_oran, a.tolerans,
                                        an=an if a.hepsi else None,
                                        **({"adim": 50000, "deneme": 2} if a.hepsi else {}))
                    kolonlar = sonuc["kolonlar"]
                    kayit["sablonlar"] += [s["no"] for s in sonuc["sablonlar"]]
                else:
                    kolonlar = kolon_uret(an, tohum, onceki)
            except RuntimeError as e:
                sys.exit(str(e))
            if a.taklitci:
                taklit_yazdir(sonuc, baslik + (" (tüm kurallar)" if a.hepsi else " (taklitçi)"),
                              an if a.hepsi else None)
            else:
                kolon_yazdir(kolonlar, an, baslik)
            print()
            onceki = onceki + kolonlar
            kayit["kolonlar"] = onceki
            if gecmisli:
                gecmis_yaz(tarih, kayit)
        if a.hepsi:
            hepsi_aciklama(a.taklit_oran, a.tolerans)
        elif a.taklitci:
            taklit_aciklama(a.taklit_oran, a.tolerans)
        else:
            kolon_aciklama(an)
        return
    if a.yillik:
        yillik_ozet(cekilisler)
        return
    if a.yil:
        cekilisler = [c for c in cekilisler if c["tarih"].startswith(str(a.yil))]
        if not cekilisler:
            sys.exit(f"{a.yil} yılına ait çekiliş yok.")
        print(f"[{a.yil} yılı analizi; gecikmeler yılın son çekilişine göre]")
    if a.son:
        cekilisler = cekilisler[-a.son:]
    analiz(cekilisler)


if __name__ == "__main__":
    main()
