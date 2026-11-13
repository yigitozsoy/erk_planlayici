# alpha — Claude için proje notları

**alpha**, Yiğit'in kişisel gösterge paneli (gamma ailesinin üçüncü uygulaması: gamma = oynatıcı, delta = toplantı
tahtası + ekran alıntısı, alpha = dashboard). Sabah açınca günün planı hazır olsun diye yapıldı.
Geliştiriciyle çalışma tarzı, tasarım zevki ve iş akışı kuralları **gamma ile aynı**:
`C:\Users\yigit\OneDrive\Desktop\gamma\CLAUDE.md` bölüm 2'yi oku (Türkçe yaz, makul varsayılanla ilerle,
gri vurgu / AMOLED siyah, mor yok, YouTube görünümü, önce çalıştırıp doğrula, commit yalnızca istenince).

## Çalıştırma / test
```powershell
python main.py                    # kaynaktan
python tests/smoke_test.py        # ~10 sn, örnek veriyle tüm sayfalar + formlar (gerçek veriye dokunmaz)
python tests/smoke_test.py --shots <klasör>   # her sayfanın koyu/açık PNG'si
python -m pyflakes alphaapp tests # temiz olmalı
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # build\dist\alpha\alpha.exe (~1 dk)
```
Masaüstü kısayolu `build\dist\alpha\alpha.exe`'yi açar (pythonw ile görev çubuğu / Görev Yöneticisi "Python"
gösteriyordu). Kullanıcıya görünen bir değişiklikten sonra exe'yi yeniden derle. Tek örnek kilidi (QLocalServer adı)
veri klasörünün crc32'sine bağlı: geçici LOCALAPPDATA ile açılan test exe'si gerçek alpha'ya bağlanmaz.
Test `LOCALAPPDATA`'yı geçici klasöre çevirir, offscreen çizer (`QT_QPA_FONTDIR` = Windows\Fonts, yoksa yazılar kutu
çıkar). Kendi betiklerinde de gerçek `%LOCALAPPDATA%\alpha`'ya yazma.

## Yapı
```
alphaapp/
  app.py          tek örnek (QLocalServer), dil/yerel ayar, excepthook (hata → %LOCALAPPDATA%\alpha\error.log)
  config.py       yollar, Prefs (preferences.json)
  store.py        tüm veriler tek JSON (data.json), 400 ms gecikmeli kayıt, günlük yedek (backups/, 14 gün),
                  sorgular: deadlines(), routine_for(), month_totals(), course_average() …
  forms.py        şemaya dayalı ekle/düzenle penceresi (schema(coll)), edit_item / delete_item (geri al) / item_menu
  components.py   Page (görünür olunca yenilenir), Card, Row, StatTile, TileGrid, ResponsiveRow, grafikler
  theme.py        gamma paletleri + kart/rozet stilleri · i18n.py (tr, en) + biçimler
  icons.py        Material yolları; kategori ikonları cat_education / cat_work / cat_sport takma adları (tek satırda değişir)
                  Bugün'deki ay takvimi: components.MonthCalendar + store.items_between(a, b)
  kareler         components.DayGrid (GitHub tarzı, tıkla = store.toggle_day). Alışkanlıklar sayfası (habits.days),
                  ders kartlarında çalışma günleri (courses.study_days); seri: store.streaks(). Form kaydı birleştirir,
                  gün listelerini silmez. Spor'da beslenme: meals koleksiyonu + prefs goal_kcal/protein/carbs/fat,
                  sık yenen çipleri components.FlowLayout ile satıra sarılır.
  window.py       çerçevesiz pencere + Snap (delta'dan), sol menü, hızlı ekle (Ctrl+N)
  pages/          today, schedule, habits, education, work, sport, social, finance, notes
  pages/plan.py   sabah planı (menüde yok, "plan" anahtarı): 1 dünden kalanlar (karar çipleri, İleri'de uygulanır + geri al)
                  2 bugün 3 odak (task.focus = bugünün iso'su, en fazla 3) + günün hedefi ("days" koleksiyonu) 4 hazır.
                  win.open_plan() / maybe_plan(): öğleden önce ilk açılışta, prefs last_plan/plan_skipped/morning_plan.
                  "plan" hiçbir zaman last_page olmaz; prefs değişince Bugün'ü mark_dirty() ile yenile.
  desk_widget.py  masaüstü widget'ı (Tool + çerçevesiz + saydam). "bottom" kipinde WM_WINDOWPOSCHANGING ile hep
                  en altta tutulur; "top" kipinde her zaman üstte. Yer/saydamlık/bölümler prefs'te (desk_*).
```
Uygulama yaşam döngüsü: `setQuitOnLastWindowClosed(False)`. Ana pencere kapanınca widget açıksa uygulama yaşar,
değilse kapanır; widget kaldırılınca (`remove()`) ana pencere de kapalıysa kapanır. `desk_widget` tercihi yalnızca
`remove()` ile kapanır (Qt 6 çıkışta tüm pencerelere close gönderir, closeEvent'te kapatma!). Windows ile başlat
komutu `--widget` ekler: widget açıksa yalnızca widget gelir.
Koleksiyonlar `store.py` başındaki belge metninde. Kategori: education, work, sport, social, finance, personal.

## Tuzaklar
- PyQt, slot / sanal metottaki yakalanmamış hatada süreci **0xC0000409 ile sessizce kapatır**. Testte excepthook
  bunları toplayıp başarısız sayar.
- Tema değişiminde çizilen widget'ları güncellemek için `theme.bind(self, ...)` kullan (zayıf referans);
  `theme.changed.connect(lambda: self.update())` silinen widget'ta çöker.
- Kart içeriği her yenilemede baştan kurulur: `_clear_layout` widget'ı gizleyip ebeveynden ayırır, yoksa eski satırlar
  üst üste çizilir.
- Uzun satır metni `ElideLabel` ile "…" olur; düz QLabel sayfayı yatayda taşırır.
- QPushButton metninde `&` kısayol işaretidir → `&&` yaz.
- Heredoc ile Python yaması yazarken `\n` gerçek satır sonuna dönüşüyor; çok satırlı değişiklikte Edit kullan.

## Sürüm ve yayın
- Repo: https://github.com/yigitozsoy/alpha_dashboard (herkese açık, GPL-3.0). Sürüm tek yerde: `alphaapp/__init__.py`.
- `packaging\build.ps1` → `build\installer\alpha-setup-<sürüm>.exe` + `alpha-portable-<sürüm>.zip` (Inno Setup 6).
- Yeni sürüm: sürümü artır → commit → push → `git tag vX.Y.Z` → `git push origin vX.Y.Z`; GitHub Actions
  (`.github/workflows/build.yml`) testi koşup derler ve Releases'a ekler. Herkese açık yayından önce onay al.
- Commit kimliği yerel: `Yiğit Özsoy <yigitozsoy@users.noreply.github.com>`. Kişisel e-posta / veri commit'e girmez
  (`.gitignore` data.json ve preferences.json'u da dışlar).

## Açık fikirler (sürüm 2)
Google Takvim (iki yönlü) + hatırlatıcılarla telefona bildirim, Gmail'den kredi kartı ekstresi → Ekonomi,
Google Tasks eşitleme, kilo/ölçü takibi, aylık bütçe hedefi, tekrarlayan görevler, sistem tepsisi.
