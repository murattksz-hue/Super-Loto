#!/usr/bin/env python3
"""Süper Loto (6/60) sonuçlarını çeker ve analiz eder.

Kullanım:
    python3 superloto.py            # yeni çekilişleri indir + analiz raporu yazdır
    python3 superloto.py --analiz   # indirmeden, mevcut CSV ile analiz
    python3 superloto.py --son 100  # analizi sadece son 100 çekilişle yap
    python3 superloto.py --yil 2026 # analizi sadece 2026 çekilişleriyle yap
    python3 superloto.py --yillik   # yıllara göre özet tablo
    python3 superloto.py --kolon    # 60 numaranın hepsini kullanan 10 kolon öner
    python3 superloto.py --taklitci # son 1 yılın çekilişlerini taklit eden 10 kolon

Sonuçlar superloto.csv dosyasına kaydedilir; sonraki çalıştırmalarda sadece
yeni çekilişler indirilir. Sadece Python standart kütüphanesi kullanılır.

Not: Her çekiliş bağımsızdır; bu istatistikler geçmişi özetler, geleceği
tahmin etmez.
"""

import argparse
import csv
import datetime
import json
import random
import re
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
    """Bir sayfadaki çekilişleri (no, tarih, 6 numara) döndürür."""
    parcalar = BASLIK_RE.split(html)
    cekilisler = []
    # split sonucu: [önce, no, gün, ay, yıl, içerik, no, gün, ...]
    for i in range(1, len(parcalar) - 4, 5):
        no, gun, ay, yil, icerik = parcalar[i:i + 5]
        toplar = [int(x) for x in re.findall(r"b(\d+)\.gif", icerik)][:6]
        if len(toplar) != 6 or ay not in AYLAR:
            continue
        cekilisler.append({
            "no": int(no),
            "tarih": f"{yil}-{AYLAR[ay]:02d}-{int(gun):02d}",
            "toplar": sorted(toplar),
        })
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
    return {"son": set(son["toplar"]), "seviye": seviye, "puan": puan,
            "gecikme": set(gecikme), "ikili": ikili, "olcutler": list(olcutler),
            "sonraki_gun": GUNLER[sonraki_gun], "sonraki_tarih": sonraki.isoformat()}


def kolon_ceza(kolon: list[int], an: dict) -> int:
    """Kolonun kurallardan ne kadar saptığı (0 = bütün kurallara uyuyor).

    Kemik yapı: 2–4 tek sayı, 1–30 arasından 2–4 sayı, aynı onluda en fazla 2,
    aynı son haneden en fazla 2, toplam 150–215, en fazla 1 ardışık ikili,
    son çekilişten en fazla 2 numara.
    Dağılım: güçlü/orta/zayıf numaralardan ikişer, en uzun süredir çıkmayan
    10 numaradan en fazla 1.
    """
    k = sorted(kolon)
    tek = sum(t % 2 for t in k)
    dusuk = sum(t <= 30 for t in k)
    onlu = max(Counter((t - 1) // 10 for t in k).values())
    son_hane = max(Counter(t % 10 for t in k).values())
    toplam = sum(k)
    ardisik = sum(1 for a, b in zip(k, k[1:]) if b - a == 1)
    tekrar = len(an["son"] & set(k))
    seviye = Counter(an["seviye"][t] for t in k)
    gecikme = len(an["gecikme"] & set(k))
    return (max(0, 2 - tek, tek - 4) + max(0, 2 - dusuk, dusuk - 4)
            + max(0, onlu - 2) + max(0, son_hane - 2)
            + (max(0, 150 - toplam, toplam - 215) + 4) // 5
            + max(0, ardisik - 1) + max(0, tekrar - 2)
            + sum(abs(seviye[s] - 2) for s in "GOZ") + max(0, gecikme - 1))


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


def gecmis_oku(tarih: str) -> list[list[int]]:
    """Bu çekiliş için daha önce verilen kolonlar (eski çekilişlerinki silinir)."""
    try:
        return json.loads(GECMIS_PATH.read_text(encoding="utf-8")).get(tarih, [])
    except (OSError, ValueError):
        return []


def gecmis_yaz(tarih: str, kolonlar: list[list[int]]) -> None:
    GECMIS_PATH.write_text(json.dumps({tarih: kolonlar}), encoding="utf-8")


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
    print("  - Kemik yapı: 2–4 tek, 1–30 arasından 2–4, aynı onluda ve aynı son haneden")
    print("    en fazla 2, toplam 150–215, en fazla 1 ardışık ikili, son çekilişten en fazla 2.")
    print("  - Birlikte çıkanlar: kurallar bozulmadan, geçmişte birlikte çok çıkan")
    print("    numaralar aynı kolona toplandı (İkili puanı = bu birlikteliklerin toplamı).")
    print("  - Farklı düzen: aynı çekiliş için verilen her yeni kolon, daha önce verilen")
    print("    kolonların her biriyle en fazla 2 numara paylaşır.")
    print("  Not: Bu ayarlar kazanma ihtimalini değiştirmez; geriye dönük testlerde")
    print("  kurallı ve rastgele kolonlar aynı sonucu verdi.")


def dizilim(toplar: list[int]) -> dict:
    """Bir çekilişin "oynanış biçimi": onlu dağılımı, tek sayısı, ardışık
    ikili sayısı, aynı son haneli fazlalık ve toplam."""
    k = sorted(toplar)
    onlu = Counter((t - 1) // 10 for t in k)
    return {
        "onlu": tuple(onlu[d] for d in range(6)),
        "tek": sum(t % 2 for t in k),
        "ardisik": sum(1 for a, b in zip(k, k[1:]) if b - a == 1),
        "son_hane": 6 - len({t % 10 for t in k}),
        "toplam": sum(k),
    }


def taklit_sablonlari(cekilisler: list[dict], rng: random.Random,
                      donem: int = 156, adim: int = 20000) -> list[dict]:
    """Son `donem` çekilişten 10 şablon seçer. Seçilen 10 çekilişin onlu
    dağılımları toplamı her onlukta tam 10, tek sayıları toplamı tam 30
    olmalıdır; böylece 60 numaranın hepsi bu şablonlarla kullanılabilir."""
    havuz = cekilisler[-donem:]
    bicimler = [dizilim(c["toplar"]) for c in havuz]

    def ceza(secim):
        onlu = [sum(bicimler[i]["onlu"][d] for i in secim) for d in range(6)]
        tek = sum(bicimler[i]["tek"] for i in secim)
        return sum(abs(o - 10) for o in onlu) + abs(tek - 30)

    while True:
        secim = rng.sample(range(len(havuz)), 10)
        c = ceza(secim)
        for _ in range(adim):
            if c == 0:
                return [havuz[i] for i in secim]
            j = rng.randrange(10)
            aday = rng.randrange(len(havuz))
            if aday in secim:
                continue
            eski = secim[j]
            secim[j] = aday
            yeni = ceza(secim)
            if yeni <= c:
                c = yeni
            else:
                secim[j] = eski


def taklit_uret(cekilisler: list[dict], tohum: int | None = None,
                onceki: list[list[int]] | None = None, tolerans: int = 6,
                adim: int = 60000, deneme: int = 50) -> list[tuple[list[int], dict]]:
    """Taklitçi kural: her kolon, son 1 yılın gerçek bir çekilişinin dizilimini
    taklit eder. Onlu dağılım birebir, tek sayısı, ardışık ikili ve aynı son
    hane sayısı birebir, toplam ±`tolerans` içinde aynıdır. 60 numaranın her
    biri tam bir kez kullanılır; `onceki` verilirse her kolon önceki
    kolonların her biriyle en fazla 2 numara paylaşır."""
    rng = random.Random(tohum)
    onceki_kumeler = [set(k) for k in onceki or []]
    for _ in range(deneme):
        sablonlar = taklit_sablonlari(cekilisler, rng)
        hedef = [dizilim(s["toplar"]) for s in sablonlar]

        def ceza(i, kolon):
            d, h = dizilim(kolon), hedef[i]
            return (abs(d["tek"] - h["tek"]) + abs(d["ardisik"] - h["ardisik"])
                    + abs(d["son_hane"] - h["son_hane"])
                    + (max(0, abs(d["toplam"] - h["toplam"]) - tolerans) + 4) // 5
                    + sum(max(0, len(set(kolon) & o) - 2) for o in onceki_kumeler))

        # Her onluğun 10 numarası, şablonların o onluktaki adedine göre dağıtılır.
        kolonlar: list[list[int]] = [[] for _ in range(10)]
        for d in range(6):
            numaralar = list(range(d * 10 + 1, d * 10 + 11))
            rng.shuffle(numaralar)
            for i, h in enumerate(hedef):
                for _ in range(h["onlu"][d]):
                    kolonlar[i].append(numaralar.pop())
        cezalar = [ceza(i, k) for i, k in enumerate(kolonlar)]
        for _ in range(adim):
            if not any(cezalar):
                break
            # Aynı onluktan iki numarayı takas et: onlu dağılım bozulmaz.
            a, b = rng.sample(range(10), 2)
            i = rng.randrange(6)
            d = (kolonlar[a][i] - 1) // 10
            secenek = [j for j, t in enumerate(kolonlar[b]) if (t - 1) // 10 == d]
            if not secenek:
                continue
            j = rng.choice(secenek)
            kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]
            ya, yb = ceza(a, kolonlar[a]), ceza(b, kolonlar[b])
            if ya + yb <= cezalar[a] + cezalar[b]:
                cezalar[a], cezalar[b] = ya, yb
            else:
                kolonlar[a][i], kolonlar[b][j] = kolonlar[b][j], kolonlar[a][i]
        if not any(cezalar):
            return [(sorted(k), s) for k, s in zip(kolonlar, sablonlar)]
    raise RuntimeError("Taklitçi kurala uyan ve öncekilerden farklı bir düzen bulunamadı. "
                       "Bu çekiliş için kolon geçmişini --sifirla ile temizleyebilirsiniz.")


def taklit_yazdir(sonuc: list[tuple[list[int], dict]], baslik: str) -> None:
    print(baslik)
    print(f"  {'#':>2}  {'Kolon':<29}{'Tek':>4}{'Ard':>4}{'Top':>5}   "
          f"Taklit edilen çekiliş")
    for i, (k, s) in enumerate(sonuc, 1):
        d = dizilim(k)
        sablon = " - ".join(f"{t:2d}" for t in s["toplar"])
        print(f"  {i:>2}  {' - '.join(f'{t:2d}' for t in k):<29}"
              f"{d['tek']:>4}{d['ardisik']:>4}{d['toplam']:>5}   "
              f"#{s['no']} {s['tarih']}: {sablon} (toplam {sum(s['toplar'])})")
    kullanilan = sorted(t for k, _ in sonuc for t in k)
    assert kullanilan == list(SAYI_ARALIGI), "her numara tam bir kez kullanılmalı"


def taklit_aciklama() -> None:
    print("  Taklitçi kural:")
    print("  - Her kolon, son 1 yılın (156 çekiliş) gerçek bir çekilişinin dizilimini taklit eder.")
    print("  - Birebir aynı: hangi onluktan kaç sayı geldiği, tek sayı adedi, ardışık ikili")
    print("    adedi ve aynı son haneli sayı adedi. Toplam en fazla ±6 farklı.")
    print("  - 60 numaranın hepsi tam bir kez kullanılır; şablon çekilişler buna uygun seçilir.")
    print("  - Farklı düzen: aynı çekiliş için verilen her yeni kolon, daha önce verilen")
    print("    kolonların her biriyle en fazla 2 numara paylaşır.")
    print("  Not: Geçmişin dizilimini taklit etmek kazanma ihtimalini değiştirmez.")


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
                   help="taklitçi kural: her kolon son 1 yılın gerçek bir çekilişinin dizilimini taklit eder")
    p.add_argument("--set", type=int, default=1,
                   help="--kolon ile kaç farklı 10'lu kolon seti üretileceği")
    p.add_argument("--sifirla", action="store_true",
                   help="--kolon: bu çekiliş için daha önce verilen kolonları unut")
    a = p.parse_args()

    veri = csv_oku() if a.analiz else guncelle()
    cekilisler = [veri[k] for k in sorted(veri)]
    if a.kolon or a.taklitci:
        an = numara_analizi(cekilisler)
        son = cekilisler[-1]
        tarih = an["sonraki_tarih"]
        gecmisli = a.tohum is None
        onceki = gecmis_oku(tarih) if gecmisli and not a.sifirla else []
        print(f"Son çekiliş #{son['no']} ({son['tarih']}), sonraki çekiliş: "
              f"{tarih} {an['sonraki_gun']}. Bu çekiliş için daha önce verilen kolon: "
              f"{len(onceki)}\n")
        for n in range(a.set):
            tohum = None if a.tohum is None else a.tohum + n
            baslik = f"Set {len(onceki) // 10 + 1}: 60 numaranın hepsini kullanan 10 kolon"
            try:
                if a.taklitci:
                    sonuc = taklit_uret(cekilisler, tohum, onceki)
                    kolonlar = [k for k, _ in sonuc]
                else:
                    kolonlar = kolon_uret(an, tohum, onceki)
            except RuntimeError as e:
                sys.exit(str(e))
            if a.taklitci:
                taklit_yazdir(sonuc, baslik + " (taklitçi)")
            else:
                kolon_yazdir(kolonlar, an, baslik)
            print()
            onceki = onceki + kolonlar
            if gecmisli:
                gecmis_yaz(tarih, onceki)
        taklit_aciklama() if a.taklitci else kolon_aciklama(an)
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
