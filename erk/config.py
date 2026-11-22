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


def _local_documents_dir():
    """OneDrive'a yönlendirilmemiş yerel Belgeler: %USERPROFILE%\\Documents."""
    return os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "Documents")


_LOCAL = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
# Bu bilgisayara özel olanlar (tercihler, pencere yeri, hata günlüğü, sesler): %LOCALAPPDATA%\erk
APP_DIR = os.path.join(_LOCAL, "erk")
# Kayıtlar + görseller + yedekler: yerel Documents\erk (OneDrive dışında). ERK_DATA_DIR ezer (testler geçici klasör verir).
DATA_DIR = os.environ.get("ERK_DATA_DIR") or os.path.join(_local_documents_dir(), "erk")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
PREFS_FILE = os.path.join(APP_DIR, "preferences.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
IMAGES_DIR = os.path.join(DATA_DIR, "images")   # hedef görselleri (kopyalanır; asıl dosya taşınsa da kalır)

for _d in (APP_DIR, DATA_DIR, BACKUP_DIR):
    os.makedirs(_d, exist_ok=True)


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
    "web_url": "",                  # https://.../api/erk.php
    "web_key": "",                  # gizli anahtar; sunucuda yalnızca sha256'sı
    "web_site_dir": "",             # sitenin yerel klasörü (_erk_key.php buraya yazılır)
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
