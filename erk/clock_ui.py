"""win.clock'un küçük görünümleri: başlık çubuğundaki sayaç düğmesi ve ders kartındaki çalışma satırı.
(Büyük panel: pages/mind.ClockPanel.)"""
from datetime import timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMenu

from .config import day_today
from .components import sub_label
from .i18n import t
from .store import num, parse_date
from .theme import theme
from .widgets import IconButton

TIMER_PRESETS = (25, 45, 60, 90)


def _fmt_minutes(m):
    m = int(round(m))
    h, mm = divmod(m, 60)
    return t("dur_hm", h=h, m=mm) if h else t("dur_m", m=mm)


class ClockPill(QPushButton):
    """Sayaç çalışırken başlık çubuğunda: süre + ne için. Tıkla = o işin sayfası."""

    def __init__(self, win):
        super().__init__()
        self.win, self.clock = win, win.clock
        self.setObjectName("Pill")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(t("clock_pill_tip"))
        theme.icon(self, "timer", "text", 18)
        self.clicked.connect(self._open)
        self.clock.changed.connect(self._sync)
        self.clock.ticked.connect(self._sync)
        self._sync()

    def _sync(self):
        st = self.clock.state
        self.setVisible(bool(st))
        if st:
            label = st.get("label") or t("clock_" + (st.get("kind") or "study"))
            pause = "" if self.clock.running() else " ‖"
            self.setText(f"{self.clock.display()}{pause} · {label}".replace("&", "&&"))

    def _open(self):
        st = self.clock.state or {}
        self.win.show_page("education" if st.get("kind") == "study" else "mind")


class CourseClock(QWidget):
    """Ders kartında: boştayken bugünkü / haftalık süre + kronometre / zamanlayıcı; çalışırken süre + duraklat / bitir."""

    def __init__(self, win, course):
        super().__init__()
        self.win, self.clock, self.c = win, win.clock, course
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 2, 0, 4)
        h.setSpacing(4)
        self.ic = IconButton("timer", "", 26, 18, role="text2")
        self.ic.setCursor(Qt.CursorShape.ArrowCursor)
        h.addWidget(self.ic)
        self.lbl = sub_label("")
        h.addWidget(self.lbl, 1)
        self.b_sw = IconButton("play", t("course_clock_sw"), 30, 20)
        self.b_sw.clicked.connect(lambda: self.clock.start("study", course["id"], "stopwatch",
                                                           label=course.get("name", "")))
        self.b_tm = IconButton("timer", t("course_clock_tm"), 30, 20)
        self.b_tm.clicked.connect(self._timer_menu)
        self.b_pause = IconButton("pause", t("clock_pause"), 30, 20)
        self.b_pause.clicked.connect(self.clock.toggle)
        self.b_stop = IconButton("stop", t("clock_finish"), 30, 20)
        self.b_stop.clicked.connect(lambda: self.clock.stop())
        for b in (self.b_sw, self.b_tm, self.b_pause, self.b_stop):
            h.addWidget(b)
        self.clock.changed.connect(self._sync)
        self.clock.ticked.connect(self._sync)
        self._sync()

    def _timer_menu(self):
        m = QMenu(self)
        for mins in TIMER_PRESETS:
            m.addAction(t("dur_m", m=mins), lambda mins=mins: self.clock.start(
                "study", self.c["id"], "timer", mins, label=self.c.get("name", "")))
        m.exec(self.b_tm.mapToGlobal(self.b_tm.rect().bottomLeft()))

    def totals(self):
        td = day_today()
        ws = td - timedelta(days=td.weekday())
        day = week = 0.0
        for s in self.win.store.all("sessions"):
            d = parse_date(s.get("date"))
            if s.get("kind") == "study" and s.get("course") == self.c["id"] and d:
                if d == td:
                    day += num(s.get("minutes"))
                if ws <= d <= td:
                    week += num(s.get("minutes"))
        return day, week

    def _sync(self):
        mine = self.clock.is_for("study", self.c["id"])
        for b in (self.b_sw, self.b_tm):
            b.setVisible(not mine)
        for b in (self.b_pause, self.b_stop):
            b.setVisible(mine)
        if mine:
            run = self.clock.running()
            self.b_pause.set_icon_name("pause" if run else "play")
            self.b_pause.setToolTip(t("clock_pause") if run else t("clock_resume"))
            left = f" {t('course_clock_left')}" if self.clock.remaining() is not None else ""
            self.lbl.setText(f"{t('course_clock_run') if run else t('course_clock_paused')} · "
                             f"{self.clock.display()}{left}")
        else:
            day, week = self.totals()
            self.lbl.setText(t("course_clock_idle", d=_fmt_minutes(day), w=_fmt_minutes(week)) if week
                             else t("course_clock_none"))
