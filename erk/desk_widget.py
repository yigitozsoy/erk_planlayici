"""Masaüstü widget'ı: masaüstüne sabitlenen küçük "Bugün" kartı (şimdi / program / yapılacaklar / yaklaşanlar / spor).

Varsayılan: masaüstünde, diğer pencerelerin ARKASINDA durur (WM_WINDOWPOSCHANGING ile hep en altta tutulur).
Sağ tık menüsünden "her zaman üstte" yapılabilir, saydamlık ve bölümler seçilir. Sürükleyerek taşınır, yeri saklanır.
"""
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QAction, QActionGroup, QGuiApplication, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu

from .config import day_today
from .components import Row, ProgressBar, ElideLabel, clear_layout
from .config import prefs
from .forms import edit_item
from .i18n import t, due_badge, WEEKDAYS_LONG, MONTHS_LONG
from .store import parse_date, week_start
from .theme import theme, qcolor, tinted_logo
from .widgets import IconButton

SECTIONS = ("now", "program", "todo", "upcoming", "sport")

WM_WINDOWPOSCHANGING = 0x0046
SWP_NOZORDER = 0x0004
HWND_BOTTOM = 1


class WINDOWPOS(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("hwndInsertAfter", wintypes.HWND), ("x", ctypes.c_int),
                ("y", ctypes.c_int), ("cx", ctypes.c_int), ("cy", ctypes.c_int), ("flags", wintypes.UINT)]


class DeskWidget(QWidget):
    closed = pyqtSignal()
    WIDTH = 340

    def __init__(self, store, win):
        super().__init__(None)
        self.store, self.win = store, win
        self.setWindowTitle("erk widget")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._apply_flags()
        self.setFixedWidth(self.WIDTH)
        self._drag = None

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 10, 14)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.logo = QLabel()
        theme.bind(self.logo, lambda l: l.setPixmap(tinted_logo(18, l.devicePixelRatioF())))
        head.addWidget(self.logo)
        tb = QVBoxLayout()
        tb.setSpacing(0)
        self.title = QLabel()
        self.title.setObjectName("CardTitle")
        self.sub = QLabel()
        self.sub.setObjectName("CardSub")
        tb.addWidget(self.title)
        tb.addWidget(self.sub)
        head.addLayout(tb, 1)
        self.btn_open = IconButton("open_in", t("desk_open"), 30, 18)
        self.btn_open.clicked.connect(self.win.bring_front)
        self.btn_more = IconButton("more_vert", t("desk_menu"), 30, 18)
        self.btn_more.clicked.connect(lambda: self._menu(self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft())))
        head.addWidget(self.btn_open, 0, Qt.AlignmentFlag.AlignTop)
        head.addWidget(self.btn_more, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(0)
        v.addLayout(self.body)

        self._pending = False
        store.changed.connect(self._schedule)
        theme.changed.connect(lambda _: self._schedule())
        self._clock = QTimer(self)
        self._clock.timeout.connect(self.refresh)
        self._clock.start(60_000)   # "şimdi / sıradaki" ve gece yarısı için
        self.refresh()
        self._restore_pos()

    # ------------------------------------------------------------ pencere davranışı
    def mode(self):
        return prefs.get("desk_mode", "bottom")

    def _apply_flags(self):
        f = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        f |= Qt.WindowType.WindowStaysOnTopHint if self.mode() == "top" else Qt.WindowType.WindowStaysOnBottomHint
        vis = self.isVisible()
        self.setWindowFlags(f)
        if vis:
            self.show()

    def set_mode(self, m):
        prefs.set("desk_mode", m)
        self._apply_flags()

    def nativeEvent(self, event_type, message):
        # masaüstü kipinde tıklansa bile öne gelmesin, hep en altta kalsın
        if self.mode() == "bottom":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_WINDOWPOSCHANGING:
                    wp = WINDOWPOS.from_address(msg.lParam)
                    wp.hwndInsertAfter = HWND_BOTTOM
                    wp.flags &= ~SWP_NOZORDER
            except Exception:
                pass
        return False, 0

    def _restore_pos(self):
        pos = prefs.get("desk_pos")
        self.adjustSize()
        scr = QGuiApplication.primaryScreen().availableGeometry()
        if pos and any(s.availableGeometry().contains(QPoint(pos[0] + 40, pos[1] + 20))
                       for s in QGuiApplication.screens()):
            self.move(pos[0], pos[1])
        else:   # ilk açılış: sağ üst köşe
            self.move(scr.right() - self.WIDTH - 24, scr.top() + 24)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            prefs.set("desk_pos", [self.x(), self.y()])
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.win.bring_front()

    def contextMenuEvent(self, e):
        self._menu(e.globalPos())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(qcolor("card"))
        c.setAlphaF(max(0.35, min(1.0, float(prefs.get("desk_opacity", 0.94)))))
        p.setPen(qcolor("divider"))
        p.setBrush(c)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)

    def remove(self):
        """Kullanıcı widget'ı kaldırdı (uygulama kapanırken gelen close'dan farklı: tercih yalnızca burada kapanır)."""
        prefs.set("desk_widget", False)
        self.close()

    def closeEvent(self, e):
        prefs.set("desk_pos", [self.x(), self.y()])
        super().closeEvent(e)
        self.closed.emit()

    # ------------------------------------------------------------ menü
    def _menu(self, pos):
        m = QMenu(self)
        a = QAction(t("desk_open"), m)
        a.triggered.connect(self.win.bring_front)
        m.addAction(a)
        a = QAction(t("plan_day"), m)
        a.triggered.connect(self.win.open_plan)
        m.addAction(a)
        m.addSeparator()
        grp = QActionGroup(m)
        for key, label in (("bottom", t("desk_mode_bottom")), ("top", t("desk_mode_top"))):
            a = QAction(("✓  " if self.mode() == key else "     ") + label, m)
            a.triggered.connect(lambda _=False, k=key: self.set_mode(k))
            grp.addAction(a)
            m.addAction(a)
        sm = m.addMenu(t("desk_opacity"))
        cur = float(prefs.get("desk_opacity", 0.94))
        for val in (1.0, 0.94, 0.85, 0.7, 0.5):
            a = QAction(("✓  " if abs(cur - val) < 0.01 else "     ") + f"%{int(val * 100)}", sm)
            a.triggered.connect(lambda _=False, x=val: (prefs.set("desk_opacity", x), self.update()))
            sm.addAction(a)
        sm = m.addMenu(t("desk_sections"))
        on = set(prefs.get("desk_sections", list(SECTIONS)))
        for key in SECTIONS:
            a = QAction(("✓  " if key in on else "     ") + t("desk_sec_" + key), sm)
            a.triggered.connect(lambda _=False, k=key: self._toggle_section(k))
            sm.addAction(a)
        m.addSeparator()
        a = QAction(t("desk_close"), m)
        a.triggered.connect(self.remove)
        m.addAction(a)
        m.exec(pos)

    def _toggle_section(self, key):
        on = list(prefs.get("desk_sections", list(SECTIONS)))
        if key in on:
            on.remove(key)
        else:
            on.append(key)
        prefs.set("desk_sections", [k for k in SECTIONS if k in on])
        self.refresh()

    # ------------------------------------------------------------ içerik
    def _schedule(self, *_):
        if not self._pending:
            self._pending = True
            QTimer.singleShot(0, self.refresh)

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        lbl.setContentsMargins(6, 10, 0, 2)
        self.body.addWidget(lbl)

    def _empty(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("Empty")
        lbl.setWordWrap(True)
        self.body.addWidget(lbl)

    def refresh(self):
        self._pending = False
        s = self.store
        td = day_today()
        now = datetime.now()
        hm = now.strftime("%H:%M")
        self.title.setText(t("today") + ", " + WEEKDAYS_LONG()[td.weekday()])
        intention = (s.day(td) or {}).get("intention", "")
        self.sub.setText(f"{td.day} {MONTHS_LONG()[td.month - 1]}" + (f"  ·  “{intention}”" if intention else ""))
        clear_layout(self.body)
        on = set(prefs.get("desk_sections", list(SECTIONS)))
        agenda = today_agenda(s, td)

        if "now" in on:
            cur = [a for a in agenda if a["start"] and a["end"] and a["start"] <= hm < a["end"]]
            nxt = [a for a in agenda if a["start"] and a["start"] > hm]
            if cur:
                text = t("desk_now", x=cur[0]["title"], e=cur[0]["end"])
            elif nxt:
                text = t("desk_next", x=nxt[0]["title"], s=nxt[0]["start"])
            else:
                text = t("desk_free")
            lbl = ElideLabel(text)
            lbl.setObjectName("RowValue")
            lbl.setContentsMargins(6, 4, 0, 2)
            lbl.setMinimumHeight(22)
            self.body.addWidget(lbl)

        if "program" in on:
            self._label(t("today_program").upper())
            for a in agenda:
                tm = f"{a['start']}–{a['end']}" if a["start"] and a["end"] else (a["start"] or t("all_day"))
                lead = QLabel(tm)
                lead.setObjectName("TimeLbl")
                lead.setFixedWidth(84)
                badges = [(t("now"), "good")] if a["start"] and a["end"] and a["start"] <= hm < a["end"] else []
                r = Row(a["title"], a["sub"], lead=lead, badges=badges)
                r.clicked.connect(lambda c=a["coll"], it=a["item"]: edit_item(self.win, c, it))
                self.body.addWidget(r)
            if not agenda:
                self._empty(t("desk_no_program"))

        if "todo" in on:
            tasks = [x for x in s.open_tasks() if parse_date(x.get("due")) and parse_date(x.get("due")) <= td]
            self._label(t("todo").upper() + (f"  ·  {len(tasks)}" if tasks else ""))
            for tk in tasks[:6]:
                d = parse_date(tk.get("due"))
                r = Row(tk.get("title", ""), check=False, badges=[due_badge(d)] if d < td else [])
                r.check_toggled.connect(lambda v, tid=tk["id"]: s.update(
                    "tasks", tid, done=v, done_at=datetime.now().isoformat(timespec="seconds") if v else None))
                r.clicked.connect(lambda it=tk: edit_item(self.win, "tasks", it))
                self.body.addWidget(r)
            if len(tasks) > 6:
                self._empty(t("and_more", n=len(tasks) - 6))
            if not tasks:
                self._empty(t("no_todo"))

        if "upcoming" in on:
            dl = [d for d in s.deadlines(7) if not (d["coll"] == "tasks" and d["date"] <= td)]
            if dl:
                self._label(t("upcoming").upper())
                for d in dl[:5]:
                    r = Row(d["title"], t("cat_" + d["category"]), badges=[due_badge(d["date"])])
                    it = s.get(d["coll"], d["id"])
                    if it is not None:
                        r.clicked.connect(lambda c=d["coll"], x=it: edit_item(self.win, c, x))
                    self.body.addWidget(r)

        if "sport" in on:
            ws = week_start(td)
            goal = s.sport_goal(ws) or max(1, int(prefs.get("sport_weekly_goal", 4)))
            n = len(s.sport_days(ws, ws + timedelta(days=6)))
            self._label(t("desk_sport", n=n, g=goal).upper())
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(6, 2, 8, 0)
            bl.addWidget(ProgressBar(n / goal, "good" if n >= goal else "text", height=5))
            self.body.addWidget(box)

        self.adjustSize()
        self.update()


def today_agenda(s, td):
    """Bugünün saatli programı: rutin + saatli görev + plan + sınav. Sıralı dict listesi."""
    out = []
    for r in s.routine_for(td):
        out.append(dict(start=r.get("start") or "", end=r.get("end") or "", title=r.get("title", ""),
                        sub=r.get("place") or t("cat_" + (r.get("category") or "personal")), coll="routine", item=r))
    for tk in s.all("tasks"):
        if not tk.get("done") and parse_date(tk.get("due")) == td and tk.get("time"):
            out.append(dict(start=tk["time"], end=tk.get("end") or "", title=tk.get("title", ""),
                            sub=t("cat_" + (tk.get("category") or "personal")), coll="tasks", item=tk))
    for ev in s.all("events"):
        if parse_date(ev.get("date")) == td:
            out.append(dict(start=ev.get("time") or "", end="", title=ev.get("title", ""),
                            sub=" · ".join(x for x in (ev.get("people"), ev.get("place")) if x) or t("cat_social"),
                            coll="events", item=ev))
    courses = {c["id"]: c for c in s.all("courses")}
    for ex in s.all("exams"):
        if parse_date(ex.get("date")) == td:
            c = courses.get(ex.get("course"), {})
            out.append(dict(start="", end="", title=f"{c.get('name', '')} · {ex.get('name', '')}", sub=t("exam"),
                            coll="exams", item=ex))
    out.sort(key=lambda a: a["start"] or "99:99")
    return out
