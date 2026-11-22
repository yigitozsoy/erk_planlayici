"""Uygulama yolları ve kalıcı tercihler (%LOCALAPPDATA%\\erk\\preferences.json)."""
import json
import os
import sys
import threading

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _documents_dir():
    """Windows'un Belgeler klasörü (OneDrive'a yönlendirilmiş olabilir)."""
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:   # CSIDL_PERSONAL
            return buf.value
    except (AttributeError, OSError):
        pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def _local_documents_dir():
    """OneDrive'a yönlendirilmemiş yerel Belgeler: %USERPROFILE%\\Documents."""
    return os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "Documents")


# Uygulamanın eski adı alpha'ydı (tamga ailesinde erk oldu). Eski klasörler ilk açılışta bir kez yeniden adlandırılır
# (_adopt_dir); yeniden adlandırılamazsa (dosya kilitli, eski alpha hâlâ açık) o oturumda eski klasör kullanılır.
OLD_NAME = "alpha"
_LOCAL = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
# veri klasörünü ezen ortam değişkeni (testler geçici klasör verir); eski ad ALPHA_DATA_DIR de okunur
_ENV_DATA_DIR = os.environ.get("ERK_DATA_DIR") or os.environ.get("ALPHA_DATA_DIR")


def _norm(p):
    return os.path.normcase(os.path.normpath(p)) if p else ""


def _old_alpha_running():
    """Eski alpha açık mı: tek örnek sunucusunun adlandırılmış borusu (QLocalServer adı Documents\\alpha'nın crc32'si).
    Açıkken klasörleri altından çekmeyelim (yazmaya devam ederdi)."""
    import zlib
    old = os.path.join(_local_documents_dir(), OLD_NAME)
    name = "alpha-dashboard-%08x" % zlib.crc32(os.path.normcase(old).encode("utf-8"))
    try:
        return name in os.listdir("\\\\.\\pipe\\")
    except OSError:
        return False


def _adopt_dir(new, old, marker=None, can_rename=True):
    """Kullanılacak klasör: new varsa (ve marker dosyası içindeyse) o; yoksa old → new yeniden adlandırılır.
    new boş bir klasörse önce silinir. Yeniden adlandırma olmazsa old döner (veri asla silinmez / üzerine yazılmaz).
    marker: new'in "dolu" sayılması için içinde olması gereken dosya (data.json); new dolu ama marker yoksa ve old'da
    varsa, iki klasör karıştırılmaz: bu oturum old ile çalışır."""
    if not old or not os.path.isdir(old) or _norm(old) == _norm(new):
        return new
    if os.path.isdir(new):
        try:
            empty = not os.listdir(new)
        except OSError:
            return new
        if empty:
            try:
                os.rmdir(new)
            except OSError:
                return new
        elif marker and not os.path.exists(os.path.join(new, marker)) and os.path.exists(os.path.join(old, marker)):
            return old
        else:
            return new
    if not can_rename:
        return old
    try:
        os.rename(old, new)
        return new
    except OSError:
        return old


_CAN_RENAME = not _old_alpha_running()
# Bu bilgisayara özel olanlar (tercihler, pencere yeri, hata günlüğü, sesler): %LOCALAPPDATA%\erk
APP_DIR = _adopt_dir(os.path.join(_LOCAL, "erk"), os.path.join(_LOCAL, OLD_NAME), can_rename=_CAN_RENAME)
# Kayıtlar + görseller + yedekler: yerel Documents\erk (OneDrive dışında). Sıra: (1) Documents\erk varsa o,
# (2) yoksa Documents\alpha → Documents\erk yeniden adlandırılır, (3) ikisi de yoksa migrate_old_data eski kopyalardan
# (OneDrive\Belgeler\alpha, 1.x %LOCALAPPDATA%\alpha) bir kez kopyalar. ERK_DATA_DIR / ALPHA_DATA_DIR ezer.
if _ENV_DATA_DIR:
    DATA_DIR = _ENV_DATA_DIR
    OLD_DATA_DIR = None
else:
    OLD_DATA_DIR = os.path.join(_local_documents_dir(), OLD_NAME)       # 2.0-3.x alpha'nın veri klasörü
    DATA_DIR = _adopt_dir(os.path.join(_local_documents_dir(), "erk"), OLD_DATA_DIR, "data.json", _CAN_RENAME)
# 2.0 önizlemesinin veri yeri (Windows Belgeler kısayolu; OneDrive'a yönlendirilmiş, eski kopya)
OLD_DOCS_DATA_DIR = None if _ENV_DATA_DIR else os.path.join(_documents_dir(), OLD_NAME)
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
PREFS_FILE = os.path.join(APP_DIR, "preferences.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
IMAGES_DIR = os.path.join(DATA_DIR, "images")   # hedef görselleri (kopyalanır; asıl dosya taşınsa da kalır)

for _d in (APP_DIR, DATA_DIR, BACKUP_DIR):
    os.makedirs(_d, exist_ok=True)


def remap_path(p):
    """Eski klasörlerin (Documents\\alpha, %LOCALAPPDATA%\\alpha) içini gösteren bir yolu yenisine çevirir; değilse aynen."""
    if not isinstance(p, str) or not p:
        return p
    for old, new in ((OLD_DATA_DIR, DATA_DIR), (os.path.join(_LOCAL, OLD_NAME), APP_DIR)):
        if not old or _norm(old) == _norm(new):
            continue
        o = _norm(old)
        n = _norm(p)
        if n == o or n.startswith(o + os.sep):
            return new + os.path.normpath(p)[len(os.path.normpath(old)):]
    return p


def migrate_old_data():
    """Veri klasörü boşsa (Documents\\erk de Documents\\alpha da yoktu) eski kopyadan bir kez kopyala: önce
    OneDrive\\Belgeler\\alpha (2.0 önizlemesi), yoksa %LOCALAPPDATA%\\alpha (1.x; artık APP_DIR). data.json varsa
    HİÇBİR ŞEY yapılmaz: güncel kayıtlar eski bir kopyayla asla değişmez. Uygulama açılışında (app.main) çağrılır."""
    if os.path.exists(DATA_FILE):
        return
    if OLD_DATA_DIR and os.path.exists(os.path.join(OLD_DATA_DIR, "data.json")):
        return      # Documents\alpha duruyor (yeniden adlandırılamadı): ona dokunma, eski kopyayı da getirme
    if OLD_DOCS_DATA_DIR and _norm(OLD_DOCS_DATA_DIR) != _norm(DATA_DIR) \
            and os.path.exists(os.path.join(OLD_DOCS_DATA_DIR, "data.json")):
        _migrate_from(OLD_DOCS_DATA_DIR, ("backups", "images"))
    else:
        _migrate_from(APP_DIR, ("backups",))


def _migrate_from(src_dir, subdirs):
    """src_dir\\data.json (+ alt klasörler) → DATA_DIR. Yalnızca DATA_DIR'de data.json yokken. Eski dosyalar silinmez."""
    import shutil
    old = os.path.join(src_dir, "data.json")
    if _norm(src_dir) == _norm(DATA_DIR) or not os.path.exists(old) or os.path.exists(DATA_FILE):
        return
    try:
        shutil.copy2(old, DATA_FILE)
        for sub in subdirs:
            old_sub, new_sub = os.path.join(src_dir, sub), os.path.join(DATA_DIR, sub)
            if os.path.isdir(old_sub):
                os.makedirs(new_sub, exist_ok=True)
                for f in os.listdir(old_sub):
                    src, dst = os.path.join(old_sub, f), os.path.join(new_sub, f)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
        with open(os.path.join(DATA_DIR, ".tasindi.json"), "w", encoding="utf-8") as f:
            json.dump({"old_mtime": os.path.getmtime(old), "new_mtime": os.path.getmtime(DATA_FILE),
                       "from": src_dir}, f)
        with open(os.path.join(src_dir, "VERILER-TASINDI.txt"), "w", encoding="utf-8") as f:
            f.write(f"erk (eski adı alpha) kayıtları artık burada: {DATA_DIR}\n"
                    "Bu klasördeki data.json eski kopyadır, artık kullanılmıyor.\n")
    except OSError:
        pass


def asset(name: str) -> str:
    return os.path.join(ASSETS_DIR, name)


DEFAULTS = {
    "language": "tr",
    "theme": "amoled",
    "accent": "gray",
    "name": "",                     # selamlamada görünen ad (boşsa yalnızca "Günaydın")
    "currency": "₺",
    "nav_visible": True,
    "start_page": "today",
    "autostart": False,
    "deadline_days": 14,            # "Yaklaşanlar" kaç gün ileriye baksın
    "sport_weekly_goal": 4,         # haftada kaç gün spor
    "sport_break": {},              # spora ara: {"from", "until", "note"}
    "show_finance_on_today": True,
    "show_sport_on_today": True,
    "window_geometry": None,
    # masaüstü widget'ı
    "desk_widget": False,
    "desk_mode": "bottom",          # bottom (masaüstünde, pencerelerin arkasında) | top (her zaman üstte)
    "desk_opacity": 0.94,
    "desk_sections": ["now", "program", "todo", "upcoming", "sport"],
    "desk_pos": None,
    "morning_plan": True,
    "debt_free_goal": "2027-01-01",  # Ekonomi: bu tarihe borçsuz girme hedefi
    "day_end_hour": 4,              # gün bu saatte biter: gece 02:00 hâlâ "bugün" sayılır (0 = gece yarısı)
    "reminders_on": True,           # saatli işler için ses + sağ altta kutu
    "reminder_lead": 10,            # kaç dk önce
    "reminder_sound": "chime",      # chime | soft | alarm | system | none
    "reminder_volume": 70,
    "important_alarm": True,        # önemli işlerde alarm sesi
    "remind_routine": True,         # dersler / program saatleri de
    "reminded": None,               # {"date", "keys"}: bugün çalanlar
    "show_place": True,             # formlarda "Yer" alanı + programda konum
    "habits_in_schedule": False,    # alışkanlıklar haftalık programda
    "goal_kcal": 2400,
    "goal_protein": 140,
    "goal_carbs": 260,
    "goal_fat": 75,
    "last_plan": None,
    "plan_skipped": None,
    "last_page": "today",
    # web görünümü (telefondan bakmak için): web.py
    "agno_goal": 3.0,            # Eğitim > Not ortalaması: sabit AGNO hedefi
    "tmdb_key": "",              # kütüphane: film / dizi bilgisi (themoviedb.org, ücretsiz)
    "web_on": False,
    "web_url": "",                  # https://.../api/alpha.php (sunucu dosyasının adı eski adla kalır)
    "web_key": "",                  # gizli anahtar; sunucuda yalnızca sha256'sı
    "web_site_dir": "",             # sitenin yerel klasörü (_alpha_key.php buraya yazılır)
    "web_last_ok": None,
    "web_last_hash": "",
    "web_error": "",
}


class Prefs:
    def __init__(self, path=PREFS_FILE):
        self.path = path
        self.data = {}
        self._lock = threading.Lock()
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, ValueError):
            pass
        # eski adın klasörlerini gösteren yollar (ör. yedek klasörü Documents\alpha\...) yeni klasöre
        moved = {k: remap_path(v) for k, v in self.data.items() if isinstance(v, str) and remap_path(v) != v}
        if moved:
            self.data.update(moved)
            self.save()

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        return DEFAULTS.get(key, default)

    def set(self, key, value):
        if key in self.data and self.data.get(key) == value:
            return
        self.data[key] = value
        self.save()

    def save(self):
        with self._lock:
            tmp = self.path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=1)
                os.replace(tmp, self.path)
            except OSError:
                pass


prefs = Prefs()


# ------------------------------------------------------------ mantıksal gün
# Gece yarısından sonra da çalışan biri için "bugün", day_end_hour'a (varsayılan 04:00) kadar sürer.
def day_end_hour():
    try:
        return max(0, min(12, int(prefs.get("day_end_hour", 4) or 0)))
    except (TypeError, ValueError):
        return 0


def day_today():
    """Uygulamanın "bugün"ü: saat day_end_hour'dan önceyse bir önceki takvim günü."""
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(hours=day_end_hour())).date()


def day_of(stamp):
    """ISO zaman damgasının (ör. done_at) ait olduğu mantıksal gün; okunamazsa None."""
    from datetime import datetime, timedelta
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    if len(str(stamp)) <= 10:          # yalnızca tarih
        return dt.date()
    return (dt - timedelta(hours=day_end_hour())).date()
