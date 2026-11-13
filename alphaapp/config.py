"""Uygulama yolları ve kalıcı tercihler (%LOCALAPPDATA%\\alpha\\preferences.json)."""
import json
import os
import sys
import threading

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "alpha")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
PREFS_FILE = os.path.join(DATA_DIR, "preferences.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

for _d in (DATA_DIR, BACKUP_DIR):
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
    "goal_kcal": 2400,
    "goal_protein": 140,
    "goal_carbs": 260,
    "goal_fat": 75,
    "last_plan": None,
    "plan_skipped": None,
    "last_page": "today",
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
