# Super-Loto çalışma kuralları

## Testler yalnızca gerçek çekilişlerle yapılır

Bu kural her test ve analiz için geçerlidir.

- Testler her zaman `superloto.csv`'deki gerçekten çekilmiş çekilişlerin hepsiyle yapılır (#1'den son çekilişe kadar).
- Yeni bir çekiliş varsa önce veri güncellenir (`python3 superloto.py`); test o çekiliş de eklenerek yapılır.
- Rastgele üretilmiş, sanal ya da kurgu çekilişlerle test yapılmaz.
- Matematiksel ihtimal gerekiyorsa ayrıca ve "hesaplanan" diye belirtilerek yazılır; test sonucu olarak sunulmaz.
- Sonuçlarda hangi çekiliş aralığıyla test edildiği yazılır (örneğin "#1–#986, 986 çekiliş").
