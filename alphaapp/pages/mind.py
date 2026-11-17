"""Zihin: günlük ruh hali / enerji / stres, meditasyon (kronometre, zamanlayıcı, nefes), uyku, neler iyi geliyor.

    sleep     date (uyanılan gün), bed, wake ("HH:MM"), quality (1-5), note
    sessions  clock.py (meditation / study oturumları)
Sayaç parçası ClockPanel, ders kartlarında da (education) kullanılan win.clock'a bağlanır.
"""
import math
from datetime import timedelta

from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpinBox)

from ..clock import fmt_clock
from ..pickers import TimeButton
from ..components import Page, Card, Row, StatTile, TileGrid, ChipBar, BarChart, DayGrid, HBars
from ..config import prefs, day_today
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_num, fmt_day, WEEKDAYS_SHORT, MONTHS_SHORT
from ..store import parse_date, num
from ..theme import theme, qcolor


# ============================================================ hesaplar
def sleep_hours(s):
    """Yatış → kalkış süresi (saat) ya da None."""
    try:
        bh, bm = map(int, str(s.get("bed")).split(":"))
        wh, wm = map(int, str(s.get("wake")).split(":"))
    except (ValueError, TypeError):
        return None
    m = (wh * 60 + wm - bh * 60 - bm) % (24 * 60)
    return m / 60.0 if m else None


def sleep_on(store, d):
    iso = d.isoformat()
    return next((s for s in store.all("sleep") if s.get("date") == iso), None)


def med_days(store):
    return {parse_date(s.get("date")) for s in store.all("sessions") if s.get("kind") == "meditation"} - {None}


def minutes_between(store, kind, a, b, course=None):
    tot = 0.0
    for s in store.all("sessions"):
        d = parse_date(s.get("date"))
        if s.get("kind") == kind and d and a <= d <= b and (course is None or s.get("course") == course):
            tot += num(s.get("minutes"))
    return tot


def fmt_minutes(m):
    m = int(round(m))
    h, mm = divmod(m, 60)
    return t("dur_hm", h=h, m=mm) if h else t("dur_m", m=mm)


def streak(days, td):
    n, d = 0, td if td in days else td - timedelta(days=1)
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


# ============================================================ parçalar
class ScaleRow(QWidget):
    """Etiket + 1..5 yuvarlak düğmeler (+ uç açıklamaları)."""
    picked = pyqtSignal(int)

    def __init__(self, label, value=None, low="", high=""):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(6)
        lb = QLabel(label)
        lb.setObjectName("RowTitle")
        lb.setFixedWidth(70)
        h.addWidget(lb)
        lo = QLabel(low)
        lo.setObjectName("RowSub")
        lo.setFixedWidth(44)
        lo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(lo)
        self.btns = []
        for i in range(1, 6):
            b = QPushButton(str(i))
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setChecked(value == i)
            b.setFixedSize(34, 34)
            b.setStyleSheet("min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px; "
                            "padding: 0px; border-radius: 17px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, v=i: self._pick(v))
            h.addWidget(b)
            self.btns.append(b)
        hi = QLabel(high)
        hi.setObjectName("RowSub")
        h.addWidget(hi)
        h.addStretch(1)

    def _pick(self, v):
        for i, b in enumerate(self.btns, 1):
            b.setChecked(i == v)
        self.picked.emit(v)


class ClockPanel(QWidget):
    """win.clock'a bağlı kronometre / zamanlayıcı. kind + ref hangi işin sayacı olduğunu söyler."""

    def __init__(self, win, kind, ref=None, label="", presets=(5, 10, 15, 20, 30), big=True):
        super().__init__()
        self.win, self.clock, self.kind, self.ref, self.label = win, win.clock, kind, ref, label
        self.presets = presets
        key = "clock_mode_" + kind
        self.mode = prefs.get(key) if prefs.get(key) in ("stopwatch", "timer") else "stopwatch"
        self.minutes = int(prefs.get("clock_min_" + kind) or presets[1 if len(presets) > 1 else 0])
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.modes = ChipBar([("stopwatch", t("clock_stopwatch")), ("timer", t("clock_timer"))], self.mode)
        self.modes.changed.connect(self._set_mode)
        v.addWidget(self.modes)
        self.digits = QLabel("00:00")
        self.digits.setObjectName("ClockBig" if big else "StatValue")
        self.digits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.digits)
        self.pre_host = QWidget()
        pre = QHBoxLayout(self.pre_host)
        pre.setContentsMargins(0, 0, 0, 0)
        pre.setSpacing(6)
        pre.addStretch(1)
        self.pre_btns = {}
        for m in presets:
            b = QPushButton(t("dur_m", m=m))
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setStyleSheet("min-width: 0px; padding: 3px 10px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, m=m: self._set_minutes(m))
            pre.addWidget(b)
            self.pre_btns[m] = b
        self.spin = QSpinBox()
        self.spin.setRange(1, 600)
        self.spin.setSuffix(" " + t("min_short"))
        self.spin.setValue(self.minutes)
        self.spin.setFixedWidth(84)
        self.spin.valueChanged.connect(self._set_minutes)
        pre.addWidget(self.spin)
        pre.addStretch(1)
        v.addWidget(self.pre_host)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addStretch(1)
        self.go = QPushButton(t("clock_start"))
        self.go.setObjectName("Primary")
        self.go.setCursor(Qt.CursorShape.PointingHandCursor)
        self.go.clicked.connect(self._go)
        self.done = QPushButton(t("clock_finish"))
        self.done.setObjectName("Pill")
        self.done.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done.clicked.connect(lambda: self.clock.stop())
        self.reset = QPushButton(t("clock_reset"))
        self.reset.setObjectName("Pill")
        self.reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset.clicked.connect(lambda: self.clock.cancel())
        for b in (self.go, self.done, self.reset):
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)
        self.note = QLabel("")
        self.note.setObjectName("RowSub")
        self.note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note.setWordWrap(True)
        v.addWidget(self.note)
        self.clock.changed.connect(self._sync)
        self.clock.ticked.connect(self._sync)
        self._sync()

    def mine(self):
        return self.clock.is_for(self.kind, self.ref)

    def _set_mode(self, m):
        self.mode = m
        prefs.set("clock_mode_" + self.kind, m)
        self._sync()

    def _set_minutes(self, m):
        self.minutes = int(m)
        prefs.set("clock_min_" + self.kind, self.minutes)
        if self.spin.value() != self.minutes:
            self.spin.blockSignals(True)
            self.spin.setValue(self.minutes)
            self.spin.blockSignals(False)
        self._sync()

    def _go(self):
        if self.mine():
            self.clock.toggle()
        else:
            self.clock.start(self.kind, self.ref, self.mode, self.minutes, self.label)

    def _sync(self):
        mine = self.mine()
        st = self.clock.state if mine else None
        mode = st.get("mode") if st else self.mode
        if mine:
            self.digits.setText(self.clock.display())
            self.go.setText(t("clock_pause") if self.clock.running() else t("clock_resume"))
        else:
            self.digits.setText(fmt_clock(self.minutes * 60) if mode == "timer" else "00:00")
            self.go.setText(t("clock_start"))
        self.done.setVisible(mine)
        self.reset.setVisible(mine)
        self.modes.setEnabled(not mine)
        self.pre_host.setVisible(mode == "timer" and not mine)
        for m, b in self.pre_btns.items():
            b.setChecked(m == self.minutes)
        other = self.clock.active() and not mine
        if other:
            st = self.clock.state
            self.note.setText(t("clock_other", x=st.get("label") or t("clock_" + (st.get("kind") or "study")),
                                v=self.clock.display()))
        else:
            self.note.setText(t("clock_hint_" + mode) if not mine else "")


class BreathPanel(QWidget):
    """Nefes egzersizi: büyüyüp küçülen daire. Bitince (≥1 dk) meditasyon oturumu olarak kaydedilir."""
    PATTERNS = {"box": (4, 4, 4, 4), "478": (4, 7, 8, 0), "calm": (4, 0, 6, 0)}

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.pat = prefs.get("breath_pattern") if prefs.get("breath_pattern") in self.PATTERNS else "box"
        self.t0 = None
        self.elapsed = 0.0
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.chips = ChipBar([(k, t("breath_" + k)) for k in self.PATTERNS], self.pat)
        self.chips.changed.connect(self._set_pat)
        v.addWidget(self.chips)
        self.canvas = QWidget()
        self.canvas.setFixedHeight(190)
        self.canvas.paintEvent = self._paint
        v.addWidget(self.canvas)
        row = QHBoxLayout()
        row.addStretch(1)
        self.go = QPushButton(t("clock_start"))
        self.go.setObjectName("Primary")
        self.go.setCursor(Qt.CursorShape.PointingHandCursor)
        self.go.clicked.connect(self.toggle)
        row.addWidget(self.go)
        row.addStretch(1)
        v.addLayout(row)
        self._t = QTimer(self)
        self._t.setInterval(33)
        self._t.timeout.connect(self.canvas.update)
        theme.bind(self, lambda w: w.canvas.update())

    def _set_pat(self, k):
        self.pat = k
        prefs.set("breath_pattern", k)
        self.canvas.update()

    def _now(self):
        import time
        return time.time()

    def toggle(self):
        if self.t0 is None:
            self.t0 = self._now()
            self._t.start()
            self.go.setText(t("clock_finish"))
            self.chips.setEnabled(False)
        else:
            sec = self._now() - self.t0
            self.t0 = None
            self._t.stop()
            self.go.setText(t("clock_start"))
            self.chips.setEnabled(True)
            if sec >= 60:
                from datetime import datetime
                self.win.store.add("sessions", {"date": day_today().isoformat(), "kind": "meditation",
                                                "minutes": round(sec / 60.0, 1), "mode": "breath",
                                                "start": datetime.now().strftime("%H:%M")})
                self.win.toast(t("breath_saved", m=fmt_num(sec / 60.0, 0)))
            self.canvas.update()

    def phase(self, sec):
        """(aşama 0-3, aşama içi oran 0-1, kalan sn) — 0 al, 1 tut, 2 ver, 3 tut."""
        p = self.PATTERNS[self.pat]
        cyc = sum(p)
        x = sec % cyc
        for i, d in enumerate(p):
            if d and x < d:
                return i, x / d, d - x
            x -= d
        return 0, 0.0, p[0]

    def _paint(self, _e):
        c = self.canvas
        p = QPainter(c)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = c.width() / 2, c.height() / 2
        rmax, rmin = min(cx, cy) - 6, (min(cx, cy) - 6) * 0.45
        if self.t0 is None:
            k, label, rest = 0.0, t("breath_ready"), ""
        else:
            i, f, rem = self.phase(self._now() - self.t0)
            ease = 0.5 - 0.5 * math.cos(math.pi * f)
            k = {0: ease, 1: 1.0, 2: 1.0 - ease, 3: 0.0}[i]
            label, rest = t("breath_ph%d" % i), str(int(math.ceil(rem)))
        r = rmin + (rmax - rmin) * k
        p.setPen(QPen(qcolor("divider"), 1.5, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), rmax, rmax)
        col = QColor(qcolor("text"))
        col.setAlpha(40 + int(60 * k))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(qcolor("text"))
        f = QFont(c.font())
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, cy - 20, c.width(), 22), Qt.AlignmentFlag.AlignCenter, label)
        f.setPixelSize(13)
        f.setBold(False)
        p.setFont(f)
        p.setPen(qcolor("text2"))
        p.drawText(QRectF(0, cy + 2, c.width(), 20), Qt.AlignmentFlag.AlignCenter, rest)
        p.end()


# ============================================================ sayfa
class MindPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_mind"), t("mind_sub"))
        self.action(t("add_sleep"), lambda: edit_item(win, "sleep"), primary=True, icon="add")

        self.t_sleep = StatTile(t("sleep_avg"))
        self.t_med = StatTile(t("med_week"))
        self.t_streak = StatTile(t("med_streak"))
        self.t_study = StatTile(t("study_week"))
        self.add(TileGrid([self.t_sleep, self.t_med, self.t_streak, self.t_study]))

        self.c_med = Card(t("med_title"), t("med_sub"))
        self.med_clock = ClockPanel(win, "meditation", label=t("med_title"))
        self.med_clock.modes.hide()          # tek çip satırı: Kronometre · Zamanlayıcı · Nefes
        self.breath = BreathPanel(win)
        m = prefs.get("med_mode")
        self.med_mode = m if m == "breath" else self.med_clock.mode
        self.med_tabs = ChipBar([("stopwatch", t("clock_stopwatch")), ("timer", t("clock_timer")),
                                 ("breath", t("med_tab_breath"))], self.med_mode)
        self.med_tabs.changed.connect(self._med_tab)
        lay = self.c_med.layout()
        lay.addWidget(self.med_tabs)
        lay.addWidget(self.med_clock)
        lay.addWidget(self.breath)
        self.med_grid = DayGrid(WEEKDAYS_SHORT(), MONTHS_SHORT(), max_weeks=20)
        self.med_grid.setCursor(Qt.CursorShape.ArrowCursor)
        lay.addWidget(self.med_grid)
        self.med_info = QLabel("")
        self.med_info.setObjectName("RowSub")
        lay.addWidget(self.med_info)
        self._med_tab(self.med_mode)

        self.c_sleep = Card(t("sleep_title"), add_tip=t("add_sleep"))
        self.c_sleep.add_clicked.connect(lambda: edit_item(win, "sleep"))
        self.row(self.c_med, self.c_sleep)

        self.c_study = Card(t("mind_study_title"), t("study_sub"))
        self.study = HBars("text", fmt=fmt_minutes)
        self.c_study.layout().addWidget(self.study)
        self.add(self.c_study)

    def _med_tab(self, k):
        if self.med_clock.mine() and k != self.med_clock.clock.state.get("mode"):
            k = self.med_clock.clock.state.get("mode")      # sayaç çalışırken kip değişmez
            self.med_tabs.select(k, emit=False)
        if self.med_tabs.current != k:
            self.med_tabs.select(k, emit=False)
        self.med_mode = k
        prefs.set("med_mode", k)
        if k != "breath":
            self.med_clock._set_mode(k)
        self.med_clock.setVisible(k != "breath")
        self.breath.setVisible(k == "breath")

    # ---------------------------------------------------------------- yenile
    def refresh(self):
        s = self.store
        td = day_today()
        hrs = [h for x in s.all("sleep") for h in [sleep_hours(x)]
               if h and parse_date(x.get("date")) and td - timedelta(days=6) <= parse_date(x["date"]) <= td]
        # yatış düzeni: son 7 gecenin yatış saatinin ortalamadan sapması (18:00'den sonraki dakika)
        beds = []
        for x in s.all("sleep"):
            d = parse_date(x.get("date"))
            try:
                bh, bm = map(int, str(x.get("bed")).split(":"))
            except (ValueError, TypeError):
                continue
            if d and td - timedelta(days=6) <= d <= td:
                beds.append(((bh - 18) % 24) * 60 + bm)
        note = t("n_nights", n=len(hrs)) if hrs else ""
        if len(beds) >= 3:
            avg = sum(beds) / len(beds)
            dev = (sum((b - avg) ** 2 for b in beds) / len(beds)) ** 0.5
            note += " · " + t("bed_spread", m=int(round(dev)))
        self.t_sleep.set(fmt_minutes(60 * sum(hrs) / len(hrs)) if hrs else "—", note,
                         "good" if len(beds) >= 3 and dev <= 30 else None)
        md = med_days(s)
        wm = minutes_between(s, "meditation", td - timedelta(days=td.weekday()), td)
        lw = minutes_between(s, "meditation", td - timedelta(days=td.weekday() + 7), td - timedelta(days=td.weekday() + 1))
        self.t_med.set(fmt_minutes(wm) if wm else "—", t("last_week_v", v=fmt_minutes(lw)) if lw else "")
        sk = streak(md, td)
        self.t_streak.set(str(sk) if sk else "—", t("days") + " · " + t("med_total_days", n=len(md)) if md else "",
                          "good" if sk >= 3 else None)
        st = minutes_between(s, "study", td - timedelta(days=td.weekday()), td)
        self.t_study.set(fmt_minutes(st) if st else "—", "")
        self.med_grid.set_days(md)
        n_ses = sum(1 for x in s.all("sessions") if x.get("kind") == "meditation")
        self.med_info.setText(t("med_info", n=n_ses, m=fmt_minutes(minutes_between(
            s, "meditation", td - timedelta(days=29), td))) if n_ses else t("med_empty"))
        self._fill_sleep(td)
        self._fill_study(td)

    def _fill_sleep(self, td):
        c = self.c_sleep
        c.clear()
        last = sleep_on(self.store, td)
        quick = QWidget()
        h = QHBoxLayout(quick)
        h.setContentsMargins(0, 0, 0, 4)
        h.setSpacing(8)
        lb = QLabel(t("sleep_last_night"))
        lb.setObjectName("RowTitle")
        h.addWidget(lb)
        bed = TimeButton((last or {}).get("bed") or prefs.get("sleep_bed", "23:30"))
        wake = TimeButton((last or {}).get("wake") or prefs.get("sleep_wake", "07:30"))
        for w, tip in ((bed, "sleep_bed"), (wake, "sleep_wake")):
            w.setToolTip(t(tip))
            w.setFixedWidth(84)
        h.addWidget(bed)
        arrow = QLabel("→")
        arrow.setObjectName("RowSub")
        h.addWidget(arrow)
        h.addWidget(wake)
        save = QPushButton(t("save"))
        save.setObjectName("Pill")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(lambda: self._save_sleep(td, bed.value(), wake.value()))
        h.addWidget(save)
        h.addStretch(1)
        c.add(quick)
        q = ScaleRow(t("sleep_quality"), int(num((last or {}).get("quality"))) or None, t("q_lo"), t("q_hi"))
        q.picked.connect(lambda v: self._save_sleep(td, quality=v))
        c.add(q)
        rows = sorted((x for x in self.store.all("sleep") if parse_date(x.get("date"))), key=lambda x: x["date"])
        data = []
        for i in range(13, -1, -1):
            d = td - timedelta(days=i)
            x = next((r for r in rows if r["date"] == d.isoformat()), None)
            data.append((WEEKDAYS_SHORT()[d.weekday()], [round(sleep_hours(x) or 0, 1) if x else 0]))
        if rows:
            ch = BarChart(roles=("text",), names=(t("sleep_hours"),), fmt=lambda v: fmt_num(v, 1), height=140,
                          max_value=10, band=(7, 9))
            ch.setToolTip(t("sleep_band_tip"))
            ch.set_data(data)
            c.add(ch)
        for x in list(reversed(rows))[:4]:
            hrs = sleep_hours(x)
            sub = " · ".join(v for v in (f"{x.get('bed', '')} → {x.get('wake', '')}",
                                         t("quality_n", n=int(num(x["quality"]))) if num(x.get("quality")) else "") if v)
            r = Row(fmt_day(parse_date(x["date"])), sub, value=fmt_minutes(hrs * 60) if hrs else "", icon="bedtime")
            c.add(bind_row(self.win, r, "sleep", x))
        if not rows:
            c.empty(t("sleep_empty"))

    def _save_sleep(self, td, bed=None, wake=None, quality=None):
        x = sleep_on(self.store, td)
        fields = {k: v for k, v in (("bed", bed), ("wake", wake), ("quality", quality)) if v is not None}
        if bed:
            prefs.set("sleep_bed", bed)
        if wake:
            prefs.set("sleep_wake", wake)
        if x:
            self.store.update("sleep", x["id"], **fields)
        else:
            fields.setdefault("bed", prefs.get("sleep_bed", "23:30"))
            fields.setdefault("wake", prefs.get("sleep_wake", "07:30"))
            self.store.add("sleep", {"date": td.isoformat(), **fields})

    def _fill_study(self, td):
        s = self.store
        ws = td - timedelta(days=td.weekday())
        data = []
        for co in s.all("courses"):
            m = minutes_between(s, "study", ws, td, co["id"])
            if m > 0:
                data.append((co.get("name", ""), m))
        data.sort(key=lambda x: -x[1])
        tot = sum(m for _n, m in data)
        self.c_study.set_sub(t("study_sub_tot", v=fmt_minutes(tot)) if tot else t("study_sub"))
        self.study.set_data(data, t("study_empty"))


