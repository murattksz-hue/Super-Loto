#!/usr/bin/env bash
# Süper Loto panosu dosyaları GitHub bağlayıcısıyla doğrudan okuyamıyor
# (dosya içeriği ayrı bir ek olarak dönüyor), bu yüzden dosyaların
# güncel halini issue gövdesine kopyalar (#12, #13, #17, #19, #21, #22, #24). GH_TOKEN gerekir.
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
if [ -f analiz_karnesi.csv ]; then yaz analiz_karnesi.csv 19; fi
if [ -f ardisik_karnesi.csv ]; then yaz ardisik_karnesi.csv 21; fi
if [ -f ikili_karnesi.csv ]; then yaz ikili_karnesi.csv 22; fi
if [ -f dongu_karnesi.csv ]; then yaz dongu_karnesi.csv 24; fi
