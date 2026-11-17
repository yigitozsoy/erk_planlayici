"""Hatırlatıcılar: bugünün saatli görevleri, program saatleri ve planları için "X dk önce" ses + sağ altta kutu.

Uygulama açıkken (ana pencere ya da yalnızca masaüstü widget'ı) çalışır. Her 20 sn'de bakar; bir hatırlatma
bir kez çalar (prefs "reminded" bugünün anahtarlarını tutar, yeniden açılışta tekrar çalmaz). Uygulama kapalıyken
kaçan ama henüz başlamamış olanlar açılınca hemen gelir; başlamış olanlar gelmez.
"""
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from . import sounds
from .components import sub_label
from .config import prefs
from .i18n import t
from .store import parse_date
from .widgets import IconButton

SNOOZE_MIN = 5


def _at(d, hhmm):
    try:
        h, m = (int(x) for x in str(hhmm).split(":")[:2])
        return datetime(d.year, d.month, d.day, h, m)
    except (ValueError, TypeError):
        return None


def upcoming(store, d):
    """O günün saatli kayıtları: dict(key, start (datetime), end (HH:MM|""), title, sub, important, coll, item)."""
    out = []
    for tk in store.all("tasks"):
        if not tk.get("done") and parse_date(tk.get("due")) == d and tk.get("time"):
            out.append(dict(coll="tasks", item=tk, start=_at(d, tk["time"]), end=tk.get("end") or "",
                            title=tk.get("title", ""), sub=t("cat_" + (tk.get("category") or "personal")),
                            important=tk.get("priority") == "high"))
    if prefs.get("remind_routine", True):
        for r in store.routine_for(d):
            if r.get("start"):
                out.append(dict(coll="routine", item=r, start=_at(d, r["start"]), end=r.get("end") or "",
                                title=r.get("title", ""),
                                sub=(r.get("place") if prefs.get("show_place", True) else "") or
                                t("cat_" + (r.get("category") or "personal")),
                                important=bool(r.get("important"))))
    for ev in store.all("events"):
        if parse_date(ev.get("date")) == d and ev.get("time"):
            out.append(dict(coll="events", item=ev, start=_at(d, ev["time"]), end="", title=ev.get("title", ""),
                            sub=" · ".join(x for x in (ev.get("people"), ev.get("place")) if x) or t("cat_social"),
                            important=bool(ev.get("important"))))
    out = [x for x in out if x["start"] is not None]
    for x in out:
        x["key"] = f"{x['coll']}:{x['item']['id']}:{x['start']:%Y-%m-%dT%H:%M}"
    return sorted(out, key=lambda x: x["start"])


class ReminderPopup(QWidget):
    """Sağ altta duran hatırlatma kutusu: başlık, saat, Ertele / Tamam. Gövdeye tıklamak kaydı açar."""
    snoozed = pyqtSignal(object)
    dismissed = pyqtSignal(object)
    opened = pyqtSignal(object)

    def __init__(self, r, now):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.r = r
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)   # yuvarlak köşeler için
        self.setFixedWidth(340)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QWidget(self)
        frame.setObjectName("ReminderImportant" if r.get("important") else "Reminder")
        frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer.addWidget(frame)
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 12, 10, 12)
        v.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(6)
        ic = IconButton("clock", "", 22, 18, role="bad" if r.get("important") else "text2")
        ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        head.addWidget(ic)
        mins = int(round((r["start"] - now).total_seconds() / 60))
        when = t("rem_now") if mins <= 0 else t("rem_in", n=mins)
        self.when = QLabel(f"{t('rem_title')} · {when}")
        self.when.setObjectName("RemindWhen")
        head.addWidget(self.when, 1)
        close = IconButton("close", t("rem_ok"), 26, 16, role="text2")
        close.clicked.connect(self._dismiss)
        head.addWidget(close)
        v.addLayout(head)
        title = QLabel(r["title"])
        title.setObjectName("RemindTitleBad" if r.get("important") else "RemindTitle")
        title.setWordWrap(True)
        title.setTextFormat(Qt.TextFormat.PlainText)
        v.addWidget(title)
        span = f"{r['start']:%H:%M}" + (f"–{r['end']}" if r.get("end") else "")
        sub = sub_label(" · ".join(x for x in (span, r.get("sub") or "") if x), wrap=True)
        v.addWidget(sub)
        foot = QHBoxLayout()
        foot.setContentsMargins(0, 6, 4, 0)
        foot.addStretch(1)
        b1 = QPushButton(t("rem_snooze", n=SNOOZE_MIN))
        b1.setObjectName("SmallPill")
        b1.clicked.connect(self._snooze)
        b2 = QPushButton(t("rem_ok"))
        b2.setObjectName("SmallPill")
        b2.clicked.connect(self._dismiss)
        for b in (b1, b2):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            foot.addWidget(b)
        v.addLayout(foot)

    def _snooze(self):
        self.snoozed.emit(self.r)
        self.close()

    def _dismiss(self):
        self.dismissed.emit(self.r)
        self.close()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.opened.emit(self.r)
            self.close()


class ReminderManager:
    def __init__(self, store, win):
        self.store, self.win = store, win
        self.popups = []
        self.snoozes = {}          # anahtar → yeniden çalma zamanı
        self._timer = QTimer(win)
        self._timer.timeout.connect(self.check)
        self._timer.start(20_000)
        QTimer.singleShot(3000, self.check)

    # ------------------------------------------------------------ durum
    def _fired(self, d):
        x = prefs.get("reminded") or {}
        return set(x.get("keys", [])) if x.get("date") == d.isoformat() else set()

    def _mark(self, d, key):
        keys = self._fired(d) | {key}
        prefs.set("reminded", {"date": d.isoformat(), "keys": sorted(keys)})

    def due(self, now=None):
        """Şu an çalması gerekenler (henüz çalmamış, vakti gelmiş, başlamamış) + vakti gelen ertelemeler."""
        now = now or datetime.now()
        if not prefs.get("reminders_on", True):
            return []
        lead = timedelta(minutes=int(prefs.get("reminder_lead", 10) or 0))
        d = now.date()
        fired = self._fired(d)
        out = []
        for r in upcoming(self.store, d):
            if r["key"] in fired:
                continue
            if r["start"] - lead <= now < r["start"] + timedelta(minutes=1):
                out.append(r)
        for key, when in list(self.snoozes.items()):
            if when <= now:
                del self.snoozes[key]
                r = next((x for x in upcoming(self.store, d) if x["key"] == key), None)
                if r is not None:
                    out.append(r)
        return out

    def check(self, now=None):
        now = now or datetime.now()
        items = self.due(now)
        for r in items:
            self._mark(now.date(), r["key"])
            self.show(r, now)
        if items:
            imp = any(r.get("important") for r in items)
            name = prefs.get("reminder_sound", "chime")
            if imp and prefs.get("important_alarm", True) and name != "none":
                name = "alarm"
            sounds.play(name, int(prefs.get("reminder_volume", 70)) / 100)
        return items

    # ------------------------------------------------------------ kutular
    def show(self, r, now=None):
        p = ReminderPopup(r, now or datetime.now())
        p.snoozed.connect(self.snooze)
        p.opened.connect(self.open)
        p.destroyed.connect(lambda *_: self._layout())
        self.popups = [x for x in self.popups if _alive(x)] + [p]
        p.adjustSize()
        p.show()
        self._layout()
        return p

    def _layout(self):
        self.popups = [x for x in self.popups if _alive(x) and x.isVisible()]
        scr = QGuiApplication.primaryScreen()
        if scr is None:
            return
        g = scr.availableGeometry()
        y = g.bottom() - 16
        for p in reversed(self.popups):
            y -= p.height()
            p.move(g.right() - p.width() - 16, y)
            y -= 10

    def snooze(self, r):
        self.snoozes[r["key"]] = datetime.now() + timedelta(minutes=SNOOZE_MIN)

    def open(self, r):
        from .forms import edit_item
        self.win.bring_front()
        edit_item(self.win, r["coll"], self.store.get(r["coll"], r["item"]["id"]) or r["item"])

    def test(self):
        """Ayarlardaki "Dene": örnek bir hatırlatma + ses."""
        now = datetime.now()
        r = dict(key="test", coll="tasks", item={"id": "test"}, start=now + timedelta(
            minutes=int(prefs.get("reminder_lead", 10) or 0)), end="", title=t("rem_test_title"),
            sub=t("rem_test_sub"), important=False)
        p = self.show(r, now)
        p.opened.disconnect()
        sounds.play(prefs.get("reminder_sound", "chime"), int(prefs.get("reminder_volume", 70)) / 100)
        return p


def _alive(w):
    try:
        w.isVisible()
        return True
    except RuntimeError:
        return False
