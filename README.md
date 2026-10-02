# Haberlerim

BBC Türkçe, DW Türkçe, Euronews Türkçe, NTV, T24, Webtekno ve Ekonomim'den kişisel haber akışı. GitHub Pages üzerinde statik olarak çalışır. Kaynak/kategori filtreleri, mobil görünüm ve koyu tema içerir.

## GitHub Pages kurulumu

1. GitHub'da `ocalozdemir.github.io` adında bir repository kullan. Ücretsiz hesapta Pages için **Public** seç. Bu durumda sayfa ve kaynak listesi herkese açık olur; “kişisel” olması erişimin sana özel olduğu anlamına gelmez.
2. ZIP dosyasını çıkar. `haberlerim` klasöründeki **tüm içeriği**, `.github` klasörü dahil, repository'nin köküne yükle. Repository içinde fazladan bir `haberlerim/` üst klasörü oluşmamalı.
3. Repository'de **Settings → Pages → Build and deployment → Source → GitHub Actions** seç.
4. **Actions → Haberleri yenile ve yayınla → Run workflow** ile ilk çalıştırmayı başlat. GitHub Actions kapalıysa önce etkinleştir.
5. İşlem başarılı olunca sayfa adresi workflow'un `github-pages` ortamında ve Settings → Pages ekranında görünür. Bu repository için adres `https://ocalozdemir.github.io/` olur.

Git kuruluysa boş repository'ye yüklemek için proje klasöründe:

```bash
git init
git add .
git commit -m "Kişisel haber akışının ilk sürümü"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADI/haberlerim.git
git push -u origin main
```

`KULLANICI_ADI` bölümünü değiştir. Kimlik doğrulama için GitHub'ın sunduğu giriş yöntemini kullan; parolanı proje dosyalarına ekleme.

## Otomatik güncelleme

GitHub Actions her saatin 13. ve 43. dakikasında haberleri toplamayı planlar. Zamanlama yaklaşık 30 dakikadır; GitHub yoğunluğunda gecikebilir. Sayfadaki **Akışı yenile** düğmesi son yayımlanan JSON'u tekrar okur; sunucuda yeni toplama başlatmaz. Hemen toplamak için Actions → Run workflow kullan.

Açık repository'de 60 gün etkinlik olmazsa GitHub zamanlanmış workflow'ları devre dışı bırakabilir. Böyle bir durumda Actions ekranında yeniden etkinleştir. Arayüzde son kontrol zamanı ve iki saatten eski akış uyarısı vardır.

## Kaynaklar nasıl okunuyor?

- BBC Türkçe, DW, Euronews, NTV, Webtekno ve Ekonomim için RSS/Atom beslemeleri kullanılır.
- T24'ün eski RSS adresleri bu hazırlıkta çalışmadığı için ana sayfadaki haber başlıkları, görselleri ve bağlantıları okunur. Tam haber metinleri indirilmez. Başlıkta yayın tarihi yoksa **Tarih belirtilmemiş** gösterilir. Ana sayfanın yapısı değişirse bu okuyucu güncellenebilir.
- Yapılandırılmış kaynaklarda doğrudan besleme çalışmazsa Google Haberler RSS araması denenir. Sonuçların kaynak alanı ilgili sitenin alan adıyla doğrulanır. Bu yöntemde bağlantı Google Haberler üzerinden açılır; özet ve görsel eklenmez. Arayüz bunu belirtir.
- Kategori, beslemenin kategori etiketinden belirlenir; etiket yoksa `sources.json` içindeki kaynak kategorisi kullanılır. Bu nedenle kategori filtresi kaynakların etiketleme doğruluğuna bağlıdır. T24 ana sayfa başlıkları varsayılan olarak Gündem altında görünür.
- Kaynak başına en fazla 50 haber, en fazla 7 gün tutulur. Tekrarlanan URL'ler kaldırılır. Yayın tarihi olmayan başlıklarda ilk görülme zamanı yalnızca saklama süresi için kullanılır.
- Kaynak kesilirse önceki haberler korunur ve durum gösterilir. Çalıştırmalar arasında GitHub Actions cache kullanılır; cache kalıcı bir arşiv değildir, silinirse paket içindeki başlangıç akışı devreye girer. Hiç haber alınamaz ve kullanılabilir geçmiş de yoksa yayın adımı çalışmaz.
- Haberler tarayıcıdan kaynak sitelere istek atılarak toplanmaz. Yalnızca haber görselleri tarayıcıda ilgili sitelerden yüklenebilir; görsel yüklenmezse kart görselsiz görünür.

## Dosyalar

| Dosya | İşlev |
| --- | --- |
| `site/index.html` | Sayfa yapısı |
| `site/style.css` | Mobil/masaüstü ve tema |
| `site/app.js` | Filtreler ve akış görüntüleme |
| `site/news.json` | İlk çalıştırmada toplanan gerçek haberler |
| `sources.json` | Kaynaklar ve besleme adresleri |
| `scripts/fetch_news.py` | Bağımlılıksız Python toplayıcı |
| `.github/workflows/news-pages.yml` | Zamanlama ve Pages yayını |
| `tests/test_fetch_news.py` | Kaynak hatası, tarih ve bağlantı kontrolleri |

## Bilgisayarda çalıştırma

Python 3.10 veya üstü:

```bash
python scripts/fetch_news.py
python -m http.server 8000 --directory site
```

Tarayıcıda `http://localhost:8000` aç. İnternet erişimi gerekir. HTML'yi doğrudan dosya olarak açmak yerine HTTP sunucusu kullan; tarayıcılar yerel JSON okumasını engelleyebilir.

Kontroller:

```bash
python -m unittest discover -s tests -v
```

## GitHub belgeleri

- [GitHub Pages için Actions workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Zamanlanmış workflow davranışı](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

Yayın için repository üzerinde GitHub Pages kaynağının GitHub Actions olarak seçilmesi gerekir. Kaynak erişimi GitHub'ın çalıştırıcısında farklı olabilir; başarısız kaynaklar sayfadaki **Kaynakların durumu** bölümünde görünür.
