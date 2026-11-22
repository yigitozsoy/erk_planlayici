# erk — Claude için proje notları

**erk**, Yiğit'in kişisel gösterge paneli. Uygulama ailesinin adı **tamga** (hep küçük harf):
kamug = oynatıcı, yazıt = toplantı tahtası + ekran alıntısı, erk = dashboard.
"erk" Göktürkçe "güç, iradesine hâkim olma"; logo Göktürk **e** harfi (dikey gövde, üstten sola inen + alttan sağa
çıkan kısa eğik kol), `packaging/make_logo.py` üretir (`--site` ile telefon sayfasının simgeleri de). Sabah açınca
günün planı hazır olsun diye yapıldı. Repo klasörü `Desktop\erk`, GitHub deposu `erk_planlayici`.
Geliştiriciyle çalışma tarzı, tasarım zevki ve iş akışı kuralları **gamma (kamug) ile aynı**:
`C:\Users\yigit\OneDrive\Desktop\gamma\CLAUDE.md` bölüm 2'yi oku (Türkçe yaz, makul varsayılanla ilerle,
gri vurgu / AMOLED siyah, mor yok, YouTube görünümü, önce çalıştırıp doğrula, commit yalnızca istenince).

## Çalıştırma / test
```powershell
python main.py                    # kaynaktan
python tests/smoke_test.py        # ~10 sn, örnek veriyle tüm sayfalar + formlar (gerçek veriye dokunmaz)
                                  # kurulum tests/smoke_base.py, adımlar tests/steps/*.py (sıra steps/__init__)
python tests/smoke_test.py --shots <klasör>   # her sayfanın koyu/açık PNG'si
python -m pyflakes erk tests      # temiz olmalı
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # build\dist\erk\erk.exe + build\installer\erk-setup-<sürüm>.exe
```
"sabah planı" adımı akşam (18:00 sonrası, akşam kapanışı daveti sabah davetini gizler) başarısız olur: saate bağlı,
kodla ilgisi yok. Kullanıcı kurulu sürümü (`%LOCALAPPDATA%\Programs\erk\erk.exe`, installer) çalıştırıyor;
kullanıcıya görünen bir değişiklikten sonra kurulumu yeniden derle (kullanıcı isteyince). Tek örnek kilidi
(QLocalServer adı `erk-<crc32>`) veri klasörünün (DATA_DIR) crc32'sine bağlı: geçici ERK_DATA_DIR ile açılan test
exe'si gerçek erk'e bağlanmaz. AppUserModelID `tamga.erk`.
**Veri yerleri:** kayıtlar + hedef görselleri (images) + yedekler yerel `%USERPROFILE%\Documents\erk`
(OneDrive DIŞI — kullanıcı OneDrive istemedi; `ERK_DATA_DIR` ezer). Tercihler +
error.log + sesler `%LOCALAPPDATA%\erk` (APP_DIR).
Testte LOCALAPPDATA değiştirince `python` (py launcher) bozuluyor: tam yol
`%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe`'yi değişkeni değiştirmeden önce al.
**Web (web.py):** telefondan bakmak için gündemin anlık görüntüsü (dün..+30 gün program, geciken/tarihsiz işler,
yaklaşanlar) `https://www.yigitozsoy.net/api/erk.php`'ye gider. Hedef / vision board / not / ekonomi kaydı ASLA
gitmez (kullanıcı kesin istemedi; smoke testi denetler). Site çıplak alan adını www.'ya 301'ler (POST kaybolur);
WebSync yönlendirmede adresi kendisi günceller. Anahtar prefs web_key, `X-Erk-Key` başlığı; sunucuda yalnızca
sha256'sı (`api/_erk_key.php`, gitignore). Sunucu betiği `api/erk.php` (veri `api/_state/erk.json`, gövdede app = "erk"
olmalı). Sayfa: sitede `erk/index.html` (web.PAGE_DIR)
(salt okunur, anahtar #k= ile bir kez gelir, localStorage'da `erk_*` önbellek); kopyası repoda
`erk-site-yukle/erk/` (index.html, logo.png, icon-192/512.png, manifest.webmanifest, .htaccess). Sunucuyu kullanıcı
elle yükler. Masaüstündeki Bugün / Program değişirse
index.html'i hem site klasöründe hem erk-site-yukle'de güncelle. Site: `Desktop\yigitozsoy.net` (Apache + PHP, kullanıcı
sunucuya elle yükler; yedek: gizli GitHub deposu yigitozsoy/yigitozsoy.net, archive/ ve api/_auth.php + _erk_key.php hariç).
Test `LOCALAPPDATA` **ve** `ERK_DATA_DIR`'ı geçici klasöre çevirir, offscreen çizer (`QT_QPA_FONTDIR` =
Windows\Fonts, yoksa yazılar kutu çıkar). Kendi betiklerinde ikisini de ayarla: yalnızca LOCALAPPDATA verirsen gerçek
Belgeler\erk'e yazarsın. Sesler offscreen'de ya da `ERK_MUTE=1`
iken çalmaz; `ERK_OFFLINE=1` ağa çıkmaz.

## Yapı
```
erk/
  app.py          tek örnek (QLocalServer), dil/yerel ayar, excepthook (hata → APP_DIR\error.log)
  config.py       yollar, Prefs (preferences.json)
  store.py        tüm veriler tek JSON (data.json), 400 ms gecikmeli kayıt, günlük yedek (backups/, 14 gün; prefs
                  backup_dir seçiliyse oraya da, yoksa atlanır; Seçenekler > Veriler > Şimdi yedekle = backup_now),
                  sorgular: deadlines(), routine_for(), month_totals(), course_average() …
  forms/          paket (dışa verim __init__'te, import'lar `from .forms import X` olarak kalır): schemas (schema(coll),
                  defaults), fields (alan bileşenleri), dialog (FormDialog), actions (edit_item / delete_item / item_menu)
  components/     paket, aynı düzen: base (Page görünür olunca yenilenir, Card, Row, button / sub_label /
                  clear_layout = layout boşaltmanın TEK yeri), stats, charts (ChipBar dahil), month_calendar, daygrid, flow
  theme.py        gamma paletleri + kart/rozet stilleri; sayı kutusu okları assets/spin_*.svg (theme.spin_img)
  i18n.py         t() + biçimler; metinler erk/locales/tr.json, en.json (spec datas'ta). Yeni anahtar iki dosyaya da
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
                  başlık "kurum — unvan"). Kullanıcının CV'si cv_for_erk.pdf (gitignore) → gerçek veriye bir kez
                  içe alındı (src "cv_pdf"). Bölüm "experience" ekranda "İş tecrübeleri"; gönüllü işler "volunteer".
                  Şu anki maddede hide_dream=True → hayal sayfasında hiç çıkmaz (sağ tık > Hayalimdeki CV'de gösterme).
                  Telefona gitmez.
  görev → sınav   Görev formunda (yeni kayıt) kategori Eğitim iken "Sınav / teslim" satırı (FormDialog._exam_row):
                  açılırsa kayıt exams'e gider (ders + tür forms.guess_exam ile başlıktan tahmin; time/end/note da
                  sınava yazılır). Eğitim görevlerinin sağ tık menüsünde "Sınavlara taşı" (pages.task_to_exam).
  dialogs.py      Seçenekler: solda kategoriler (Genel, Bugün ve program, Hatırlatıcılar, Spor ve beslenme,
                  Masaüstü widget'ı, Telefonda aç, Veriler, Hakkında), sağda QStackedWidget. category()/section().
  web sayfası     site klasöründe erk/index.html (kopyası erk-site-yukle/erk/) masaüstü temasının (theme.py renkleri, Card/Row/Block,
                  MonthCalendar) birebir HTML kopyası: yalnızca Bugün + Haftalık program. Metinler, ikon yolları,
                  hafta/ay adları anlık görüntüyle (web.build_snapshot v2: days[blocks, prog], tasks, deadlines, cal,
                  str, icons) gelir. Masaüstünde bu iki sayfa değişirse web.py + index.html'i de güncelle.
  window.py       çerçevesiz pencere + Snap (delta'dan), sol menü, hızlı ekle (Ctrl+N). Sayfalar tembel:
                  pages.build_pages → LazyPages (ilk win.pages[k]'de kurulur; values()/items() yalnızca kurulmuşlar;
                  içe aktarmalar açık yazılı ki PyInstaller görsün). Kurulmamış sayfayı values() ile arama.
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
  Eğitim sayfası  pages/education.py sekmeleri (ChipBar, her açılışta ev): home = ev ikonu (karolar: çalışma kareleri
                  dolu/toplam, AGNO / prefs agno_goal, sıradaki sınav; Yaklaşan sınavlar = puansız tüm sınav / quiz /
                  sunum ISO haftalara bölünmüş, tarihsizler sonda; Derslerim = ders satırı + ExamBar; görevler,
                  projeler), courses = Dersler (solda liste, sağda seçili dersin kartı; show_course(cid) oraya geçer),
                  grades = Notlar (GradesCard + TranscriptCard). Ayrı Takvim sekmesi ve "hedefin altında" kutusu
                  kullanıcı istemedi (kaldırıldı). Ders ikonu addan: education.course_icon (COURSE_ICONS: ısı / akış
                  → ateş, temel bilimler → mikroskop, mekanik / tasarım → dişli, yoksa kitap). Sınav çalışma kareleri pages/edu_study.py: exams.study =
                  [{t konu, n kare, d dolu}] — her konu bir satır, uzunluk serbest (Excel tablo seçici gibi: soluk
                  kareye tıkla = uzat, alttaki soluk satır = yeni konu, sağ tık adlandır / kısalt / sil). Sabit 4×3
                  ızgara ve sayı kutusu kullanıcı istemedi. Eski study_goal/study_done rows_of() ile satırlara bölünür.
                  Her sınavda (geçmiş / puanlı dahil) gösterilir. Transkript = sınıf × dönem ızgarası (_TermTile,
                  yıl 2-6, dönem 2-3 olabilir), tıkla = altta o dönemin dersleri.
  not kartı      grades_view.GradesCard: ExamBar (sınav ağırlığı kadar parça, not dolumu), kalem = sınav çipleri, ⋮ = Dönemi
                  bitir, Hedef AGNO sabit (prefs agno_goal). Sınav türleri grades.EXAM_KINDS (kayıtta Türkçe ad, ekranda
                  dile göre; "Midterm 2" → "Vize 2"). store.add_exam aynı ders + türdeki boş sınavı doldurur (yenisini açmaz).
  grades.py       ANO / AGNO = kullanıcının Excel'i (assets/lectures_for_erk.xlsx, .gitignore'da; kök assets/ = kişisel kaynaklar: CV PDF, Excel, muscle-body, hepsi gitignore, pakete girmez). Harf → puan grades.points()
                  (varsayılan YÖK, prefs grade_points farklılar; Seçenekler > Genel > Not sistemi). transcript koleksiyonu,
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
  Beden sayfası   eski adı Spor (anahtar hâlâ "sport", nav_sport = "Beden"; görev kategorisi cat_sport "Spor" kalır).
                  Üç sekme (ChipBar, her açılışta ev): home = ev ikonu (Vücudum kilo/yağ, Gelişimim, HeroCard,
                  BodyCard), train = Antrenmanlar (hafta + son haftalar, kutular, rekorlar, günlük, programlar),
                  food = Beslenme (halkalar, öğünler, besin kütüphanesi). Kart eklerken tab_widgets'a koy; üst
                  düğmeler tab_actions'ta. scroll_to kartın sekmesine geçer.
  spor (ağırlık)  fitness.py: hareket kataloğu (EXERCISES → ana/yardımcı kaslar, _GUESS ile addan tahmin), e1RM
                  (Epley), kas yükü (fitness.weights_of: ana 1, yardımcı 0.5; ACTIVATION'daki 17 hareket kullanıcının
                  uygulamasının kas haritasından: çok yüksek 1 / yüksek .75 / sinerjist .5 / biraz .35 / düşük .2),
                  rekorlar. 2026-11: kullanıcının uygulamasındaki eksikler eklendi (adlar İngilizce, uygulamadaki
                  gibi; renk → ağırlık lejantı ACTIVATION başında). fitness.ALIASES + canonical(): uygulama adı →
                  katalog adı (Barbell Squat → Squat, Face Pull → Cable Face Pull), listede tek görünür.
                  workouts.exercises [{name, sets [{r, w}]}],
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
                  (elipsoidlerden basit model, CI'da bu). Paket packaging/make_body.py ile assets/muscle-body/anatomy.OBJ'den
                  üretilir (numpy + Pillow); model lisansı belirsiz → ikisi de .gitignore'da, depoya girmez.
                  Referans: spor/ klasöründeki "Lightweight" ekran görüntüleri (yalnızca veri/fikir, görünüm erk'in).
  pages/          today, schedule, habits, education, work, sport, mind, social, finance, notes
  zihin           pages/mind.py: sleep (bed/wake, kalite), meditasyon (ClockPanel: kronometre / zamanlayıcı +
                  BreathPanel nefes), ders çalışma özeti; denge "mind" parçaları. Güne puan verme (ruh hali / enerji /
                  stres) 3.0'da KALDIRILDI (kullanıcı beğenmedi); eski mood kayıtları data.json'da durur, okunmaz.
  sayaç           clock.py: tek Clock (win.clock, durum prefs "clock" → yeniden başlatmada sürer), ≥60 sn "sessions"a
                  yazılır, ders çalışması courses.study_days'i işaretler. clock_ui: başlık çubuğunda ClockPill, ders
                  kartında CourseClock. Adı "pomodoro" değil (kullanıcı istemedi): kronometre + zamanlayıcı.
  ekonomi         markets.py: Yahoo chart uç noktası (anahtarsız) + ECB yedeği, TL'ye çevrilir, prefs "prices"
                  önbelleği; yatırımda asset (kod / Yahoo sembolü) + qty → anlık değer (value_of, net_worth). Ekranda
                  pages/assets.AssetsCard (5 dk'da bir, yalnızca görünürken; offscreen / ERK_OFFLINE=1 ağa çıkmaz).
                  Alınacaklar sekmesi = pages/wishlist.py ürün kartı vitrini (görsel: image ya da bağlantının og:image'i,
                  bir kez denenir → img_tried; kategori çipleri; Aldım) = wishlist koleksiyonu (Notion "Wishlist"ten içe alındı; Notion
                  adresi prefs notion_wishlist'te, koda yazılmaz). Ekonomi / alınacaklar telefona gitmez.
  pages/plan.py   sabah planı (menüde yok, "plan" anahtarı): 1 dünden kalanlar (karar çipleri, İleri'de uygulanır + geri al)
                  2 bugün 3 odak (task.focus = bugünün iso'su, en fazla 3) + günün hedefi ("days" koleksiyonu) 4 hazır.
                  win.open_plan() / maybe_plan(): öğleden önce ilk açılışta, prefs last_plan/plan_skipped/morning_plan.
                  2.0: dünün özeti (StatTile'lar), ilerleme çubuğu, 1. adımda 1-5/Del/↑↓/Enter kısayolları (QShortcut,
                  yalnızca adım 0'da etkin — yazı alanları yutulmasın), 2. adımda timeline.DayTimeline (boşluğa tıkla →
                  saatsiz bir işi o saate koy). "plan" hiçbir zaman last_page olmaz; prefs değişince Bugün'ü mark_dirty() ile yenile.
  pages/shutdown.py akşam kapanışı ("shutdown" anahtarı, menüde yok, win.open_shutdown): 1 bugün (karolar + sabahki
                  hedef oldu / kısmen / olmadı → days.intention_met) 2 kalanlar (yarın / tarihsiz / bitti / sil, plan.CarryRow
                  choices=..., İleri'de uygulanır + geri al; işaretlenmemiş alışkanlıklar) 3 yarın (program, odak = task.focus
                  yarının iso'su → sabah planında seçili gelir, bütçe uyarıları) 4 not (days.shutdown_note → sabah planı 1. adımda
                  "Dün akşamki notun"). Bugün'de davet kartı c_shut: shutdown.is_due() (prefs evening_shutdown, shutdown_hour 18,
                  last_shutdown); akşam sabah davetini gizler.
  bütçe           budget.py: GROUPS (grup → alt kategoriler; gider formundaki kategori listesi EXPENSE_CATS bu sırayla), group_of
                  (eski / serbest adlar _ALIAS ile), prefs budgets {grup: tavan}, status / alerts (%80), subscriptions (recurring,
                  kategori Abonelik). Ekonomi'de pages/budget_view: BudgetCard (çubuk + ayın geçen kısmı çizgisi, tıkla = tavan)
                  + SubsCard ("Nereye harcadım" kartının yerine, grafiğin sağında).
  antrenman hedef overload.py + pages/sport_goals.py: lift_goals koleksiyonu (name, w, r, by) → hedef e1RM; trend (son 10 hafta
                  eğim, kg/hafta) + eta; suggest = çift ilerleme (tekrar aralığı programdaki reps'ten, yoksa 6-10; step_of artış);
                  weekly_volume. Rekorlar kartında seçili hareket: öneri satırı, hedef satırı / "Hedef koy", grafikte hedef
                  çizgisi, haftalık hacim; yanında LiftGoalsCard. Kullanıcı antrenmanda uygulamayı kullanmıyor: dinlenme
                  sayacı vb. antrenman içi özellik ekleme.
  hızlı komut     quick.py (İngilizce, Todoist tarzı; parse saf fonksiyon, parse_for store'la): tarih / saat / aralık / #kategori /
                  !öncelik / +proje / every … tekrar; "spent 120 coffee" → harcama. Ctrl+N = quick_ui.QuickDialog (önizleme,
                  "Formlar…" eski menü; titlebar + düğmesi menü). QuickTask satırları da çözümler. Tekrarlayan görev: task.repeat
                  (daily / weekdays / weekly / monthly / "w:0,2,4"); store.update done=True → _repeat_task sonrakini açar
                  (next_id, biten kopyada repeat_was), done=False geri alır.
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

## Komut satırı: kullanıcının verisine kayıt ekle / oku (Claude bunu kullanır)
Yiğit "şunu yedim / antrenman yaptım / uyudum / görev ekle" derse data.json'a ELLE YAZMA, kodu okuma: şunu çalıştır
(proje kökünden; uygulama açıksa istek ona gider, kapalıysa dosyaya güvenle yazılır):
```bash
python -X utf8 -m erk.cli help          # tüm komutlar (kısa)
python -X utf8 -m erk.cli day           # bugünün özeti (öğün toplamı / hedef, antrenman, uyku, görev, alışkanlık)
python -X utf8 -m erk.cli meal "pirinç:200" "tavuk göğsü:400" "protein tozu:2 ölçek"   # besin kütüphanesinden
python -X utf8 -m erk.cli food add "Mercimek (çiğ)" kcal=343 protein=24 carbs=60 fat=1.5 src=<kaynak>
python -X utf8 -m erk.cli add sleep date=dün bed=23:40 wake=07:10 quality=4
python -X utf8 -m erk.cli add tasks title="..." due=yarın category=education
python -X utf8 -m erk.cli list workouts --from -7 --fields date,kind,exercises
```
Python tam yolu: `%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe`. Koleksiyon alanları: `cli colls` (store.py belge
metni). Besin yoksa `meal` hiçbir şey yazmaz ve "kütüphanede yok" der: değeri (100 g, çiğ/pişmiş belirt) diyetkolik gibi
bir kaynaktan bul, `food add` ile ekle, sonra `meal`. Kullanıcı gramı çiğ ağırlıkla söyler ("200 g çiğ pirinç").
Kod: erk/cli.py (run = komutlar, handle_request = app.py sunucusu {"cli": argv}
 → {"code", "out"}),
erk/nutrition.py (find_food, parse_amount: birim tanımlı besinde 20'den küçük çıplak sayı = birim).
Spor sayfasında "Besin kütüphanesi" kartı (sağ tık / ⋮ > Bugüne ekle…). Yeni komut eklersen smoke tests/steps/komut.py.

## Tuzaklar
- PyQt, slot / sanal metottaki yakalanmamış hatada süreci **0xC0000409 ile sessizce kapatır**. Testte excepthook
  bunları toplayıp başarısız sayar.
- Tema değişiminde çizilen widget'ları güncellemek için `theme.bind(self, ...)` kullan (zayıf referans);
  `theme.changed.connect(lambda: self.update())` silinen widget'ta çöker.
- Kart içeriği her yenilemede baştan kurulur: `_clear_layout` widget'ı gizleyip ebeveynden ayırır, yoksa eski satırlar
  üst üste çizilir.
- Hesaplanan sayıların (1RM, seviye, yağ oranı, denge puanı) üzerine gelince nasıl hesaplandığı yazar
  (sport_ui.e1rm_tip / level_tip, i18n tip_*); yeni hesaplı sayı eklersen ipucunu da ekle.
- Uzun satır metni `ElideLabel` ile "…" olur; düz QLabel sayfayı yatayda taşırır.
- QPushButton metninde `&` kısayol işaretidir → `&&` yaz.
- Heredoc ile Python yaması yazarken `\n` gerçek satır sonuna dönüşüyor; çok satırlı değişiklikte Edit kullan.

## Sürüm ve yayın
- Repo: https://github.com/yigitozsoy/erk_planlayici (3.0'dan beri GİZLİ, açık kaynak değil; LICENSE = tüm hakları saklıdır). Sürüm tek yerde: `erk/__init__.py`.
- `packaging\build.ps1` → `build\installer\erk-setup-<sürüm>.exe` + `erk-portable-<sürüm>.zip` (Inno Setup 6).
  erk.spec DROP listesi paketi hafifletir (opengl32sw, Qt OpenSSL arka ucu + libssl/libcrypto-3-x64, tr/en dışı Qt
  çevirileri, kullanılmayan görüntü / platform eklentileri): kurulum ~23 MB. TLS için web.WebSync Schannel seçer.
  Sihirbaz gamma ile aynı: `WizardStyle=modern dynamic windows11 hidebevels` (Inno 6.7+), görseller
  make_meta.py'de logodan üretilir (build\wizard, Pillow gerekir; CI pip satırında var), lisans sayfası yok.
- AppId (`{F860D8FB-…}`) kurulu sürümle aynı kalmalı (yerinde güncelleme), DEĞİŞTİRME; kurulum veri klasörlerine dokunmaz.
- Yeni sürüm: sürümü artır → commit → push → `git tag vX.Y.Z` → `git push origin vX.Y.Z`; GitHub Actions
  (`.github/workflows/build.yml`) testi koşup derler ve Releases'a ekler (CI'da body_frames.zip yok → Body3D;
  yerel derlemedeki kurulum sürüme --clobber ile yüklenir). Yayından önce onay al.
- Commit kimliği yerel: `Yiğit Özsoy <yigitozsoy@users.noreply.github.com>`. Kişisel e-posta / veri commit'e girmez
  (`.gitignore` data.json ve preferences.json'u da dışlar).

## Açık fikirler (sürüm 2)
Google Takvim (iki yönlü) + hatırlatıcılarla telefona bildirim, Gmail'den kredi kartı ekstresi → Ekonomi,
Google Tasks eşitleme, sistem tepsisi. (Bütçe tavanı, tekrarlayan görev, kilo takibi yapıldı.) Öneri listesinden kalan: "Bugün neye çalışayım" (sınava kalan gün × eksik kare).
