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
veri klasörünün (DATA_DIR) crc32'sine bağlı: geçici ALPHA_DATA_DIR ile açılan test exe'si gerçek alpha'ya bağlanmaz.
**Veri yerleri (2.0):** kayıtlar + hedef görselleri (images) + yedekler yerel `%USERPROFILE%\Documents\alpha`
(OneDrive DIŞI — kullanıcı OneDrive istemedi; `ALPHA_DATA_DIR` ezer). Tercihler + error.log `%LOCALAPPDATA%\alpha`
(APP_DIR). İlk açılışta eski yerden bir kez kopyalanır (config.migrate_old_data → _migrate_from; eskisi silinmez):
önce OneDrive\Belgeler\alpha (data.json + backups + images), yoksa 1.x'in %LOCALAPPDATA%\alpha'sı.
Kullanıcı kurulu sürümü (`%LOCALAPPDATA%\Programs\alpha\alpha.exe`, installer) çalıştırıyor.
Testte LOCALAPPDATA değiştirince `python` (py launcher) bozuluyor: tam yol
`%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe`'yi değişkeni değiştirmeden önce al.
**Web (web.py):** telefondan bakmak için gündemin anlık görüntüsü (dün..+30 gün program, geciken/tarihsiz işler,
yaklaşanlar) `https://yigitozsoy.net/api/alpha.php`'ye gider. Hedef / vision board / not / ekonomi kaydı ASLA
gitmez (kullanıcı kesin istemedi; smoke testi denetler). Site çıplak alan adını www.'ya 301'ler (POST kaybolur):
adres `https://www.yigitozsoy.net/api/alpha.php`; WebSync yönlendirmede adresi kendisi günceller. Anahtar prefs web_key, X-Alpha-Key başlığı; sunucuda yalnızca
sha256'sı (`api/_alpha_key.php`). Sayfa: site klasöründe `alpha/index.html` (salt okunur, anahtar #k= ile bir kez gelir,
localStorage'da önbellek). Site: `Desktop\yigitozsoy.net` (Apache + PHP, git yok, kullanıcı elle yükler).
Test `LOCALAPPDATA` **ve** `ALPHA_DATA_DIR`'ı geçici klasöre çevirir, offscreen çizer (`QT_QPA_FONTDIR` =
Windows\Fonts, yoksa yazılar kutu çıkar). Kendi betiklerinde ikisini de ayarla: yalnızca LOCALAPPDATA verirsen gerçek
Belgeler\alpha'ya yazarsın.

## Yapı
```
alphaapp/
  app.py          tek örnek (QLocalServer), dil/yerel ayar, excepthook (hata → APP_DIR\error.log)
  config.py       yollar, Prefs (preferences.json)
  store.py        tüm veriler tek JSON (data.json), 400 ms gecikmeli kayıt, günlük yedek (backups/, 14 gün),
                  sorgular: deadlines(), routine_for(), month_totals(), course_average() …
  forms.py        şemaya dayalı ekle/düzenle penceresi (schema(coll)), edit_item / delete_item (geri al) / item_menu
  components.py   Page (görünür olunca yenilenir), Card, Row, StatTile, TileGrid, ResponsiveRow, grafikler
  theme.py        gamma paletleri + kart/rozet stilleri · i18n.py (tr, en) + biçimler
  icons.py        Material yolları; kategori ikonları cat_education / cat_work / cat_sport takma adları (tek satırda değişir)
                  Bugün'deki ay takvimi: components.MonthCalendar + store.items_between(a, b)
  kareler         components.DayGrid (GitHub tarzı). span=(2, 1): son 2 ay + önümüzdeki 1 ay; kareler KARE, en
                  fazla 24 px (genişliğe yayılan büyük kareleri kullanıcı beğenmedi). set_values(vals, ranges, quit):
                  yarım = alt yarısı dolu, seri içindeki komşu kareler zincirle bağlanır, bırakmada kayma kırmızı.
                  Alışkanlık mantığı habits_core.py: kind build/quit (NoFap, ekran süresi: her gün temiz, slips
                  işaretlenir), half, source "study" (sessions'tan ≥ target_h saat tam, yarısı yarım), goal (haftada
                  ideal), week_min (ör. 3.5), gap (üst üste kaç boş gün bozar). Tıkla = hc.cycle (tam → yarım → boş).
                  Hazır şablonlar hc.TEMPLATES (Alışkanlıklar'da çip). Başka yerler hc.state / streak_info kullanır,
                  day_set(h.days) değil. source "workout" = antrenman girilen gün tam ("Spora git" şablonu; varsa
                  Spor sayfasındaki seri kutusu hc.auto_source'un serisini gösterir). Bugün sayfasında
                  "Alışkanlıklar" kartı (habits.habit_row, prefs show_habits_on_today). Haftalık programda
                  saatsiz alışkanlıklar günde TEK kutu ("Alışkanlık 3/6", tıkla = işaretleme menüsü,
                  schedule._habit_menu); saatliler ayrı kutu. Alışkanlık kartları iki sütun (ResponsiveRow 900).
                  Ders çalışma kareleri Eğitim'deki ders kartlarında (courses.study_days, store.toggle_day;
                  kronometre süresi < 1 sa → yarım kare); Alışkanlıklar'da yalnızca alışkanlıklar. Form kaydı birleştirir,
                  gün listelerini silmez. Spor'da beslenme: meals koleksiyonu + prefs goal_kcal/protein/carbs/fat,
                  sık yenen çipleri components.FlowLayout ile satıra sarılır.
  sürüm 2         Program: iki hafta alt alta (schedule.WEEKS = 2: bu hafta + önümüzdeki hafta, cols 14 sütun; telefon
                  sayfası tek hafta + oklar), her haftanın başında "47. hafta" (ISO). Kutu renkleri theme.BLOCK_KINDS
                  (Block kind özelliği → #Block[kind=...]): spor yeşil, ders mavi, toplantı / etkinlik (iş, sosyal,
                  events) sarı, görev camgöbeği; önemli kırmızı hepsini ezer. Programa yalnızca spor alışkanlıkları
                  girer (hc.is_sport; prefs habits_in_schedule varsayılan açık). Her kayıt ayrı kutu (schedule.Block; important → #BlockImportant kırmızı: routine/events
                  "important", görev priority=high, puansız sınav, proje deadline'ı). Formda kategori = ikon düğmeleri
                  (forms.CategoryPicker, tür "cats"). prefs show_place=False → schema() "place" alanını çıkarır
                  (kayıtlı yer silinmez), programda konum yazmaz. prefs habits_in_schedule → alışkanlıklar programda
                  (habits.weekdays boşsa her gün, time isteğe bağlı; tıkla = o günü işaretle).
                  QDialog QPushButton'da min-width: 64px var; dialog içi küçük düğmelerde ez.
  pages/goals.py  Hayat (menü adı; anahtar hâlâ "goals"). Sekmeler goals.VIEWS (prefs goals_view): Vision board,
                  Denge ve yol haritası, Bucket list, Harita, CV. Hedefler: goals ağacı (parent, horizon, links "habits:id"/"courses:id"/"projects:id", image) +
                  wheel (aylık 1-10). İki sekme: Pinterest tarzı vision board (BoardView, masonry, görsel
                  Ctrl+V / sürükle-bırak → DATA_DIR\images) ve çark + yol haritası. 9×9 ızgara ve 3B hedef ağı
                  denendi, kullanıcı beğenmedi (kaldırıldı). "Örnek hedeflerle doldur" sample=True kayıtlar ekler.
                  Hayat alanları (store.LIFE_AREAS, görev kategorilerinden ayrı): eğitim (ders, CAD, dil), kariyer
                  (staj, iş bulma, bağlantılar), iş = kendi işini kurma, beden, zihin, ekonomi, kişisel gelişim.
                  Aile / arkadaş alanı istenmedi. Eski kategori değerleri life_area / life_scores ile okunurken eşlenir.
                  Denge (eski "hayat çarkı"): elle puan YOK (kullanıcı istemedi), örümcek ağı grafiği de beğenilmedi.
                  balance.area_report() her alanı verilerden 0-10 puanlar (parçalar + "nereden geldi" metni),
                  history() son 6 ay; BalanceView alan kartları (puan, değişim, çizgi, parçalar) + özet kartı.
                  Üçüncü sekme CV (pages/cv.py, cv koleksiyonu): solda şu anki CV (+ PDF → DATA_DIR\cv, prefs cv_file),
                  sağda hayalimdeki CV; ikisi de gerçek CV sayfası gibi çizilir (cv.CvSheet: fotoğraf prefs cv_photo,
                  section "profile" = ad / bilgi satırı / iletişim / Hakkımda, bölüm başlığı + çizgi, detail satırları
                  madde işareti). Hayal sayfasında şu anki maddeler soluk (ayrıntısız) görünür; aynı bölümde aynı
                  kurumlu hayal maddesi varsa gizlenir. Sağ tık > Gerçekleşti (realize) / Hedefe çevir (to_goal,
                  başlık "kurum — unvan"). Kullanıcının CV'si cv_for_alpha.pdf (gitignore) → gerçek veriye bir kez
                  içe alındı (src "cv_pdf"). Bölüm "experience" ekranda "İş tecrübeleri"; gönüllü işler "volunteer".
                  Şu anki maddede hide_dream=True → hayal sayfasında hiç çıkmaz (sağ tık > Hayalimdeki CV'de gösterme).
                  Telefona gitmez.
  görev → sınav   Görev formunda (yeni kayıt) kategori Eğitim iken "Sınav / teslim" satırı (FormDialog._exam_row):
                  açılırsa kayıt exams'e gider (ders + tür forms.guess_exam ile başlıktan tahmin; time/end/note da
                  sınava yazılır). Eğitim görevlerinin sağ tık menüsünde "Sınavlara taşı" (pages.task_to_exam).
  dialogs.py      Seçenekler: solda kategoriler (Genel, Bugün ve program, Hatırlatıcılar, Spor ve beslenme,
                  Masaüstü widget'ı, Telefonda aç, Veriler, Hakkında), sağda QStackedWidget. category()/section().
  web sayfası     site klasöründe alpha/index.html masaüstü temasının (theme.py renkleri, Card/Row/Block,
                  MonthCalendar) birebir HTML kopyası: yalnızca Bugün + Haftalık program. Metinler, ikon yolları,
                  hafta/ay adları anlık görüntüyle (web.build_snapshot v2: days[blocks, prog], tasks, deadlines, cal,
                  str, icons) gelir. Masaüstünde bu iki sayfa değişirse web.py + index.html'i de güncelle.
  window.py       çerçevesiz pencere + Snap (delta'dan), sol menü, hızlı ekle (Ctrl+N)
  navmenu.py      sol menü düzeni (sağ tık > Menüyü düzenle): prefs nav_layout [{k, h}] ("-" ayırıcı), nav_names
                  (i18n.t nav_/cat_ anahtarlarında da kullanılır → kategori adı her yerde değişir), custom_cats
                  [{id "c_xxxxxx", name, icon}] → pages/category.CategoryPage (window._ensure_pages). Varsayılan = DEFAULT.
                  Kategori silinince kayıtları personal'a geçer. Ctrl+1..9 menü sırasına göre.
                  Sadeleştirme: navmenu.SectionsDialog (hazır çipler Öğrenci / Spor ve sağlık / Hepsi + bölüm
                  anahtarları; apply_sections → nav_layout gizli bayrakları, kayıt silinmez). İlk açılışta yalnızca
                  hiç veri yoksa (should_onboard, prefs sections_done); sonra Seçenekler > Genel > Bölümler.
                  Bugün / Program hep açık (ALWAYS). Row'da menüsü olan satırlara fareyle gelince ⋮ düğmesi
                  (receivers(menu_requested) > 0 ise kurulur).
  pages/projects.py Projeler: projects (category work/education, start, due, logo, status) + task.project.
                  İlerleme store.project_progress (görev varsa biten oranı). Timeline (Gantt), Logo (harf yol olarak
                  çizilir: Segoe UI Variable kalını pixmap'te bozuk çıkıyor). İş / Eğitim sayfalarında project_row.
  not kartı      grades_view.GradesCard: ExamBar (sınav ağırlığı kadar parça, not dolumu), kalem = sınav çipleri, ⋮ = Dönemi
                  bitir, Hedef AGNO sabit (prefs agno_goal). Sınav türleri grades.EXAM_KINDS (kayıtta Türkçe ad, ekranda
                  dile göre; "Midterm 2" → "Vize 2"). store.add_exam aynı ders + türdeki boş sınavı doldurur (yenisini açmaz).
  grades.py       ANO / AGNO = kullanıcının Excel'i (lectures_for_alpha.xlsx, .gitignore'da). transcript koleksiyonu,
                  dersler letter / guess / target / retake. Excel'in "*ad*" eşleşmesi yerine tam ad → kod → en kısa
                  içeren. read_transcript_xlsx openpyxl'siz (zip+XML), "AGNO" satırında durur. Sonuçlar Excel'le
                  birebir aynı. pages/grades_view.py: GradesCard + TranscriptCard (Eğitim).
  library.py      Kütüphane (media): Open Library / Google Books, TMDB (prefs tmdb_key, kullanıcı alır), Apple
                  Podcasts, makale og:, oyun = Steam storesearch + appdetails (anahtarsız; konsol oyunu elle, ilerleme
                  saat, rafta DVD gibi kutu). Job = thread + sinyal. Goodreads / Letterboxd kazınmaz (yalnızca bağlantı).
                  pages/library.py: raf (pages/shelf.py: Shelf sırtlar + fareyle dışarı çıkma, MediaViewer kitap açılır /
                  DVD-CD diski çıkar), SearchDialog → edit_item("media", preset). Bugün'de "Şu an" kartı.
                  Kütüphane yalnızca medya rafı (3.1'de harita + bucket list Hayat sayfasına taşındı).
                  Harita = pages/places.py (places koleksiyonu; Türkiye 81 il / dünya; tıkla → Gittim / Gitmek
                  istiyorum; arama il / ülke / şehir; il ve ülke kendi içindeki şehirden de boyanır). Veri
                  assets/geo.json.gz (Natural Earth, kamu malı) ← packaging/make_geo.py.
                  Bucket list = pages/bucket.py (bucket koleksiyonu), goals.BoardView'in alt sınıfı (color_of /
                  icon_of / meta_of / add_texts kancaları, menu_at sinyali).
                  Kütüphane / harita / bucket telefon sayfasına GİTMEZ (smoke denetler).
  sürükle-bırak   Row.drag_data "coll:id" + Card.accept_drop(colls, fn) (components.DRAG_MIME): görev → Yaklaşan
                  sınavlar / ders kartı (sınav), proje kartı (projeye ata).
  spor (ağırlık)  fitness.py: hareket kataloğu (EXERCISES → ana/yardımcı kaslar, _GUESS ile addan tahmin), e1RM
                  (Epley), kas yükü (fitness.weights_of: ana 1, yardımcı 0.5; ACTIVATION'daki 17 hareket kullanıcının
                  uygulamasının kas haritasından: çok yüksek 1 / yüksek .75 / sinerjist .5 / biraz .35 / düşük .2),
                  rekorlar. workouts.exercises [{name, sets [{r, w}]}],
                  templates (program: name, exercises [{name, sets, reps, rir}]), body (kilo/ölçü) + prefs goal_weight.
                  pages/sport_ui.py: WorkoutDialog (programdan başlat → geçen seferki kilolar dolu), TemplateDialog,
                  LineChart, Templates/Records/Body kartları. lifts = tek başına girilen rekor (PR), history() okur.
                  En üst: pages/sport_top (BodyStatsCard: kilo / yağ / yağsız kütle + grafikler; DevPreviewCard:
                  ModelView zoom/focus ile yakın plan, development renkleri; MaxDialog → lifts; FatDialog: mezura
                  ölçüleri → fitness.navy_bodyfat (ABD Donanması; prefs body_height / body_sex), fat_of yağ girilmemiş
                  kayıtta boyun + bel (+ kalça) varsa hesaplar). Tıkla → ayrıntıya
                  kaydırır (SportPage.scroll_to). Altında: pages/sport_body.HeroCard — 3B vücut + kipler: Gelişimim (fitness.development: 1RM /
                  vücut ağırlığı / STANDARDS, seviye 0-4), Son 7 gün, Programlarım, Hazır programlar (fitness.POPULAR,
                  8 program kullanıcının seçimi: kendi PPL + Power'ı (Pzt/Çar/Cum/Paz), PPL, ULPPL, Güray's
                  Hypertrophy (Boostcamp 1. hafta), 5×5, 3×5, Full Body ABC / ABAB; günler _week() ile haftalığa
                  toplanır, split metni altta). body3d.py: ModelView = önceden çizilmiş 72 kare (assets/body_frames.zip,
                  piksel = 1 + kas×13 + gölge, boyama = renk tablosu, sürükle = döndür); paket yoksa Body3D
                  (elipsoidlerden basit model, CI'da bu). Paket packaging/make_body.py ile muscle-body/ OBJ'sinden
                  üretilir (numpy + Pillow); model lisansı belirsiz → ikisi de .gitignore'da, depoya girmez.
                  Referans: spor/ klasöründeki "Lightweight" ekran görüntüleri (yalnızca veri/fikir, görünüm alpha'nın).
  pages/          today, schedule, habits, education, work, sport, mind, social, finance, notes
  zihin           pages/mind.py: sleep (bed/wake, kalite), meditasyon (ClockPanel: kronometre / zamanlayıcı +
                  BreathPanel nefes), ders çalışma özeti; denge "mind" parçaları. Güne puan verme (ruh hali / enerji /
                  stres) 3.0'da KALDIRILDI (kullanıcı beğenmedi); eski mood kayıtları data.json'da durur, okunmaz.
  sayaç           clock.py: tek Clock (win.clock, durum prefs "clock" → yeniden başlatmada sürer), ≥60 sn "sessions"a
                  yazılır, ders çalışması courses.study_days'i işaretler. clock_ui: başlık çubuğunda ClockPill, ders
                  kartında CourseClock. Adı "pomodoro" değil (kullanıcı istemedi): kronometre + zamanlayıcı.
  ekonomi         markets.py: Yahoo chart uç noktası (anahtarsız) + ECB yedeği, TL'ye çevrilir, prefs "prices"
                  önbelleği; yatırımda asset (kod / Yahoo sembolü) + qty → anlık değer (value_of, net_worth). Ekranda
                  pages/assets.AssetsCard (5 dk'da bir, yalnızca görünürken; offscreen / ALPHA_OFFLINE=1 ağa çıkmaz).
                  Alınacaklar sekmesi = pages/wishlist.py ürün kartı vitrini (görsel: image ya da bağlantının og:image'i,
                  bir kez denenir → img_tried; kategori çipleri; Aldım) = wishlist koleksiyonu (Notion "Wishlist"ten içe alındı; Notion
                  adresi prefs notion_wishlist'te, koda yazılmaz). Ekonomi / alınacaklar telefona gitmez.
  pages/plan.py   sabah planı (menüde yok, "plan" anahtarı): 1 dünden kalanlar (karar çipleri, İleri'de uygulanır + geri al)
                  2 bugün 3 odak (task.focus = bugünün iso'su, en fazla 3) + günün hedefi ("days" koleksiyonu) 4 hazır.
                  win.open_plan() / maybe_plan(): öğleden önce ilk açılışta, prefs last_plan/plan_skipped/morning_plan.
                  2.0: dünün özeti (StatTile'lar), ilerleme çubuğu, 1. adımda 1-5/Del/↑↓/Enter kısayolları (QShortcut,
                  yalnızca adım 0'da etkin — yazı alanları yutulmasın), 2. adımda timeline.DayTimeline (boşluğa tıkla →
                  saatsiz bir işi o saate koy). "plan" hiçbir zaman last_page olmaz; prefs değişince Bugün'ü mark_dirty() ile yenile.
  pickers.py      DateButton / TimeButton: formlarda (OptDate / OptTime), spor arası, antrenman, uyku. Tıkla → açılır
                  takvim (MonthCalendar; başlık → 12 ay → 12'şer yıl; üstte "17.11.2026" yazıp Enter; Bugün / Yarın /
                  Gelecek hafta) ya da saat (00-23) + dakika (5 dk) ızgarası,
                  yazarak giriş ("0830", "9.30"), Şimdi. Tekerlek / ↑↓: ±1 gün, ±15 dk. İsteğe bağlı alan kapalıyken
                  soluk ama tıklanabilir; seçim yapınca anahtar açılır (picked sinyali). Kapanan açılır pencere silinir.
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
- Repo: https://github.com/yigitozsoy/alpha_dashboard (3.0'dan beri GİZLİ, açık kaynak değil; LICENSE = tüm hakları saklıdır). Sürüm tek yerde: `alphaapp/__init__.py`.
- `packaging\build.ps1` → `build\installer\alpha-setup-<sürüm>.exe` + `alpha-portable-<sürüm>.zip` (Inno Setup 6).
  alpha.spec DROP listesi paketi hafifletir (opengl32sw, Qt OpenSSL arka ucu + libssl/libcrypto-3-x64, tr/en dışı Qt
  çevirileri, kullanılmayan görüntü / platform eklentileri): kurulum ~23 MB. TLS için web.WebSync Schannel seçer.
  Sihirbaz gamma ile aynı: `WizardStyle=modern dynamic windows11 hidebevels` (Inno 6.7+), görseller
  make_meta.py'de logodan üretilir (build\wizard, Pillow gerekir; CI pip satırında var), lisans sayfası yok.
- Yeni sürüm: sürümü artır → commit → push → `git tag vX.Y.Z` → `git push origin vX.Y.Z`; GitHub Actions
  (`.github/workflows/build.yml`) testi koşup derler ve Releases'a ekler (CI'da body_frames.zip yok → Body3D;
  yerel derlemedeki kurulum sürüme --clobber ile yüklenir). Yayından önce onay al.
- Commit kimliği yerel: `Yiğit Özsoy <yigitozsoy@users.noreply.github.com>`. Kişisel e-posta / veri commit'e girmez
  (`.gitignore` data.json ve preferences.json'u da dışlar).

## Açık fikirler (sürüm 2)
Google Takvim (iki yönlü) + hatırlatıcılarla telefona bildirim, Gmail'den kredi kartı ekstresi → Ekonomi,
Google Tasks eşitleme, kilo/ölçü takibi, aylık bütçe hedefi, tekrarlayan görevler, sistem tepsisi.
