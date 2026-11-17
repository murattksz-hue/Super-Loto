#!/usr/bin/env bash
# Süper Loto panosu dosyaları GitHub bağlayıcısıyla doğrudan okuyamıyor
# (dosya içeriği ayrı bir ek olarak dönüyor), bu yüzden dosyaların
# güncel halini issue gövdesine kopyalar (#12, #13, #17, #19, #21, #24). GH_TOKEN gerekir.
set -euo pipefail
yaz() {  # dosya issue_no
  govde=$(mktemp)
  { echo "Bu issue Süper Loto panosu için otomatik güncellenir; kapatmayın, düzenlemeyin."
    echo
    cat "$1"; } > "$govde"
  gh issue edit "$2" --body-file "$govde"
  rm -f "$govde"
}
yaz superloto.csv 12
yaz oyun_kolonlari.txt 13
if [ -f kural_karnesi.csv ]; then yaz kural_karnesi.csv 17; fi
if [ -f pencere_analizi.csv ]; then yaz pencere_analizi.csv 19; fi
if [ -f pencere_listeleri.csv ]; then yaz pencere_listeleri.csv 21; fi
if [ -f dongu_karnesi.csv ]; then yaz dongu_karnesi.csv 24; fi
