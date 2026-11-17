"""Tıklayarak tarih / saat seçimi (elle yazmak yerine).

DateButton: alan gibi görünen düğme ("17 Kasım 2026, Salı"). Tıkla → açılır pencere: yazarak giriş
("17.11.2026" + Enter), ay takvimi (components.MonthCalendar; başlığa tıkla → 12 ay, bir daha → 12'şer yıl) +
Bugün / Yarın / Gelecek hafta çipleri. Tekerlek ya da ↑↓ = ±1 gün.
TimeButton: "09:30". Tıkla → saat ızgarası (00-23) + dakika ızgarası (5 dk) + yazarak giriş + Şimdi.
Tekerlek ya da ↑↓ = ±15 dk. İkisi de changed sinyali verir; value() / set_value() ile okunur.
"""
from datetime import date, timedelta, datetime

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit,
                             QApplication, QStackedWidget, QWidget)

from .config import day_today
from .i18n import t, fmt_long_date, fmt_month, WEEKDAYS_SHORT, MONTHS_LONG
from .widgets import IconButton


def _chip(text, checked=False):
    b = QPushButton(text)
    b.setObjectName("PickChip")
    b.setCheckable(True)
    b.setChecked(checked)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return b


class _Popup(QFrame):
    """Düğmenin altında açılan, dışarı tıklayınca kapanan pencere."""

    def __init__(self, anchor):
        super().__init__(anchor, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.NoDropShadowWindowHint)
        self.setObjectName("PickPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.anchor = anchor

    def show_below(self):
        self.adjustSize()
        a = self.anchor
        p = a.mapToGlobal(QPoint(0, a.height() + 4))
        scr = (a.screen() or QApplication.primaryScreen()).availableGeometry()
        x = min(max(scr.left() + 4, p.x()), scr.right() - self.width() - 4)
        y = p.y() if p.y() + self.height() <= scr.bottom() - 4 else a.mapToGlobal(QPoint(0, 0)).y() - self.height() - 4
        self.move(x, max(scr.top() + 4, y))
        self.show()


class _Field(QPushButton):
    changed = pyqtSignal()
    picked = pyqtSignal()       # kullanıcı bir değer seçti (aynı değer olsa da) → isteğe bağlı alan açılır

    def set_off(self, off):
        """İsteğe bağlı alan kapalıyken soluk görünür ama tıklanabilir kalır."""
        self.setProperty("off", bool(off))
        self.style().unpolish(self)
        self.style().polish(self)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PickField")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.open_popup)
        self.popup = None

    def wheelEvent(self, e):
        if not self.isEnabled():
            return
        self.step(1 if e.angleDelta().y() > 0 else -1)
        e.accept()

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key.Key_Up, Qt.Key.Key_Plus):
            self.step(1)
        elif k in (Qt.Key.Key_Down, Qt.Key.Key_Minus):
            self.step(-1)
        elif k in (Qt.Key.Key_Space, Qt.Key.Key_F4):
            self.open_popup()
        else:
            super().keyPressEvent(e)


# ============================================================ tarih
class DateButton(_Field):
    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self.d = value or day_today()
        self._label()

    def value(self):
        return self.d

    def set_value(self, d, emit=True):
        if d is None or d == self.d:
            return
        self.d = d
        self._label()
        if emit:
            self.changed.emit()

    def step(self, k):
        self.set_value(self.d + timedelta(days=k))
        self.picked.emit()

    def _label(self):
        self.setText(fmt_long_date(self.d))

    @staticmethod
    def parse(text):
        """"17.11.2026", "17/11/26", "2026-11-17", "17 11 2026" → date ya da None."""
        import re
        s = (text or "").strip()
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if m:
            y, mo, d = (int(x) for x in m.groups())
        else:
            m = re.fullmatch(r"(\d{1,2})[./\- ](\d{1,2})[./\- ](\d{2}|\d{4})", s)
            if not m:
                return None
            d, mo, y = (int(x) for x in m.groups())
            if y < 100:
                y += 2000 if y <= (day_today().year % 100) + 10 else 1900
        try:
            return date(y, mo, d)
        except ValueError:
            return None

    def open_popup(self):
        from .components import MonthCalendar
        pop = _Popup(self)
        v = QVBoxLayout(pop)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(6)

        def pick(d):
            self.set_value(d)
            self.picked.emit()
            pop.close()
        # yazarak: 17.11.2026 + Enter
        ed = QLineEdit(self.d.strftime("%d.%m.%Y"))
        ed.setPlaceholderText(t("pick_date_ph"))
        ed.returnPressed.connect(lambda: self.parse(ed.text()) and pick(self.parse(ed.text())))
        v.addWidget(ed)

        head = QHBoxLayout()
        title = QPushButton()
        title.setObjectName("PickTitle")
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        title.setToolTip(t("pick_title_tip"))
        head.addWidget(title, 1, Qt.AlignmentFlag.AlignLeft)
        cal = MonthCalendar(WEEKDAYS_SHORT())
        cal.setFixedWidth(294)
        stack = QStackedWidget()
        stack.addWidget(cal)
        months, years = QWidget(), QWidget()
        mg, yg = QGridLayout(months), QGridLayout(years)
        for g in (mg, yg):
            g.setContentsMargins(0, 6, 0, 0)
            g.setSpacing(6)
        stack.addWidget(months)
        stack.addWidget(years)
        mbtn = []
        for i, name in enumerate(MONTHS_LONG()):
            b = _chip(name)
            b.setMinimumHeight(40)
            mbtn.append(b)
            mg.addWidget(b, i // 3, i % 3)
        ybtn = []
        for i in range(12):
            b = _chip("")
            b.setMinimumHeight(40)
            ybtn.append(b)
            yg.addWidget(b, i // 3, i % 3)
        st = {"mode": "days", "y": self.d.year, "m": self.d.month, "y0": self.d.year - 7}

        def render():
            mode = st["mode"]
            if mode == "days":
                cal.set_month(st["y"], st["m"])
                title.setText(fmt_month(st["y"], st["m"]) + "  ▾")
                stack.setCurrentIndex(0)
            elif mode == "months":
                title.setText(f"{st['y']}  ▾")
                for i, b in enumerate(mbtn):
                    b.setChecked(st["y"] == self.d.year and i + 1 == self.d.month)
                stack.setCurrentIndex(1)
            else:
                title.setText(f"{st['y0']} – {st['y0'] + 11}")
                for i, b in enumerate(ybtn):
                    b.setText(str(st["y0"] + i))
                    b.setChecked(st["y0"] + i == self.d.year)
                stack.setCurrentIndex(2)

        def shift(k):
            mode = st["mode"]
            if mode == "days":
                m0 = st["y"] * 12 + st["m"] - 1 + k
                st["y"], st["m"] = m0 // 12, m0 % 12 + 1
            elif mode == "months":
                st["y"] += k
            else:
                st["y0"] += 12 * k
            render()

        def zoom_out():
            if st["mode"] == "days":
                st["mode"] = "months"
            elif st["mode"] == "months":
                st["mode"], st["y0"] = "years", st["y"] - 7
            render()

        def set_month(i):
            st["m"], st["mode"] = i + 1, "days"
            render()

        def set_year(i):
            st["y"], st["mode"] = st["y0"] + i, "months"
            render()
        title.clicked.connect(zoom_out)
        for i, b in enumerate(mbtn):
            b.clicked.connect(lambda _=False, i=i: set_month(i))
        for i, b in enumerate(ybtn):
            b.clicked.connect(lambda _=False, i=i: set_year(i))
        for ic, tip, k in (("chevron_left", t("pick_prev"), -1), ("chevron_right", t("pick_next"), 1)):
            b = IconButton(ic, tip, 30, 18)
            b.clicked.connect(lambda _=False, k=k: shift(k))
            head.addWidget(b)
        v.addLayout(head)
        cal.set_selected(self.d)
        cal.day_clicked.connect(pick)
        cal.day_activated.connect(pick)
        v.addWidget(stack)
        render()
        pop.st, pop.render, pop.zoom_out = st, render, zoom_out          # test için
        quick = QHBoxLayout()
        quick.setSpacing(6)
        td = day_today()
        for label, d in ((t("today"), td), (t("tomorrow"), td + timedelta(days=1)),
                         (t("pick_next_week"), td + timedelta(days=7 - td.weekday()))):
            b = _chip(label, d == self.d)
            b.clicked.connect(lambda _=False, d=d: pick(d))
            quick.addWidget(b)
        quick.addStretch(1)
        v.addLayout(quick)
        self.popup = pop
        pop.show_below()


# ============================================================ saat
class TimeButton(_Field):
    STEP = 15

    def __init__(self, value="09:00", parent=None):
        super().__init__(parent)
        self.h, self.m = self._parse(value) or (9, 0)
        self._label()

    @staticmethod
    def _parse(text):
        s = (text or "").strip().replace(".", ":").replace(" ", "")
        if not s:
            return None
        if ":" not in s and s.isdigit():
            s = s[:-2] + ":" + s[-2:] if len(s) > 2 else s + ":00"
        try:
            h, m = (int(x) for x in s.split(":")[:2])
        except ValueError:
            return None
        return (h, m) if 0 <= h < 24 and 0 <= m < 60 else None

    def value(self):
        return f"{self.h:02d}:{self.m:02d}"

    def set_value(self, text, emit=True):
        p = self._parse(text)
        if not p or p == (self.h, self.m):
            return
        self.h, self.m = p
        self._label()
        if emit:
            self.changed.emit()

    def step(self, k):
        tot, s = self.h * 60 + self.m, self.STEP          # bir sonraki / önceki çeyreğe
        tot = ((tot // s + 1) * s if k > 0 else ((tot - 1) // s) * s) % (24 * 60)
        self.set_value(f"{tot // 60:02d}:{tot % 60:02d}")
        self.picked.emit()

    def _label(self):
        self.setText(self.value())

    def open_popup(self):
        pop = _Popup(self)
        v = QVBoxLayout(pop)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(6)
        top = QHBoxLayout()
        ed = QLineEdit(self.value())
        ed.setPlaceholderText("09:30")
        ed.setFixedWidth(90)
        top.addWidget(ed)
        now = _chip(t("pick_now"))
        top.addWidget(now)
        top.addStretch(1)
        v.addLayout(top)
        cap = QLabel(t("pick_hour"))
        cap.setObjectName("StatLabel")
        v.addWidget(cap)
        hg = QGridLayout()
        hg.setSpacing(4)
        hours = {}
        for h in range(24):
            b = _chip(f"{h:02d}", h == self.h)
            hours[h] = b
            hg.addWidget(b, h // 6, h % 6)
        v.addLayout(hg)
        cap = QLabel(t("pick_minute"))
        cap.setObjectName("StatLabel")
        v.addWidget(cap)
        mg = QGridLayout()
        mg.setSpacing(4)
        mins = {}
        for i, m in enumerate(range(0, 60, 5)):
            b = _chip(f":{m:02d}", m == self.m)
            mins[m] = b
            mg.addWidget(b, i // 6, i % 6)
        v.addLayout(mg)
        state = {"h": self.h}

        def mark():
            for h, b in hours.items():
                b.setChecked(h == state["h"])
            for m, b in mins.items():
                b.setChecked(False)
            ed.setText(f"{state['h']:02d}:{self.m:02d}")

        def pick_hour(h):
            state["h"] = h
            self.set_value(f"{h:02d}:{self.m:02d}")
            self.picked.emit()
            mark()

        def pick_min(m):
            self.set_value(f"{state['h']:02d}:{m:02d}")
            self.picked.emit()
            pop.close()

        def typed():
            if self._parse(ed.text()):
                self.set_value(ed.text())
                self.picked.emit()
                pop.close()

        def set_now():
            n = datetime.now()
            m = (n.minute + 4) // 5 * 5
            h = n.hour + m // 60
            self.set_value(f"{h % 24:02d}:{m % 60:02d}")
            self.picked.emit()
            pop.close()
        for h, b in hours.items():
            b.clicked.connect(lambda _=False, h=h: pick_hour(h))
        for m, b in mins.items():
            b.clicked.connect(lambda _=False, m=m: pick_min(m))
        ed.returnPressed.connect(typed)
        now.clicked.connect(set_now)
        self.popup = pop
        pop.show_below()
        ed.setFocus()
        ed.selectAll()
