"""Küçük grafikler ve çip çubuğu: ProgressBar, BarChart, HBars, WeekStrip, Ring, ChipBar."""
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QFontMetrics, QFont, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolTip

from ..theme import theme, qcolor
from .base import clear_layout


# ============================================================ grafikler
class ProgressBar(QWidget):
    """İnce ilerleme çubuğu; isteğe bağlı hedef işareti."""

    def __init__(self, value=0.0, role="text", marker=None, height=6, parent=None):
        super().__init__(parent)
        self.value, self.role, self.marker = value, role, marker
        self.setFixedHeight(height + (6 if marker is not None else 0))
        self._h = height
        theme.bind(self, lambda w: w.update())

    def set(self, value, role=None, marker=None):
        self.value = value
        if role:
            self.role = role
        self.marker = marker
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self._h
        y = (self.height() - h) / 2
        r = QRectF(0, y, self.width(), h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor("track"))
        p.drawRoundedRect(r, h / 2, h / 2)
        v = max(0.0, min(1.0, float(self.value or 0)))
        if v > 0:
            p.setBrush(qcolor(self.role))
            p.drawRoundedRect(QRectF(0, y, max(h, self.width() * v), h), h / 2, h / 2)
        if self.marker is not None:
            mx = max(1.0, min(self.width() - 1.0, self.width() * max(0.0, min(1.0, self.marker))))
            p.setPen(QPen(qcolor("text"), 2))
            p.drawLine(QPointF(mx, 0), QPointF(mx, self.height()))


class BarChart(QWidget):
    """Gruplu dikey çubuk grafik. data: [(etiket, [değer, ...])], roles: seri renkleri."""

    def __init__(self, roles=("good", "bad"), names=(), fmt=str, height=180, max_value=None, band=None, parent=None):
        super().__init__(parent)
        self.roles, self.names, self.fmt = roles, names, fmt
        self.max_value = max_value
        self.band = band          # (alt, üst): hedef aralığı gölgeli şerit; altındaki çubuklar soluk
        self.data = []
        self.setMinimumHeight(height)
        self.setMouseTracking(True)
        self._bars = []
        theme.bind(self, lambda w: w.update())

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._bars = []
        if not self.data:
            return
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        p.setFont(f)
        fm = QFontMetrics(f)
        top, bottom = 8, fm.height() + 8
        h = self.height() - top - bottom
        mx = max([max(v) if v else 0 for _, v in self.data] + [1e-9, self.max_value or 0])
        n = len(self.data)
        k = max(1, len(self.roles))
        slot = self.width() / n
        gap = 3
        bw = min(22.0, (slot * 0.62 - gap * (k - 1)) / k)
        # yatay kılavuz
        p.setPen(QPen(qcolor("divider"), 1))
        for i in range(4):
            y = top + h * i / 3
            p.drawLine(QPointF(0, y), QPointF(self.width(), y))
        if self.band and mx:
            lo, hi = self.band
            y1, y0 = top + h - h * min(hi, mx) / mx, top + h - h * min(lo, mx) / mx
            c = QColor(qcolor("good"))
            c.setAlpha(28)
            p.fillRect(QRectF(0, y1, self.width(), y0 - y1), c)
        for i, (label, vals) in enumerate(self.data):
            cx = slot * i + slot / 2
            total_w = bw * k + gap * (k - 1)
            x0 = cx - total_w / 2
            for j, v in enumerate(vals):
                bh = h * (v / mx) if mx else 0
                r = QRectF(x0 + j * (bw + gap), top + h - bh, bw, bh)
                if bh > 0:
                    p.setPen(Qt.PenStyle.NoPen)
                    low = self.band is not None and v < self.band[0]
                    p.setBrush(qcolor("text3" if low else self.roles[j % k]))
                    rad = min(4.0, bw / 2, bh / 2)
                    p.drawRoundedRect(r, rad, rad)
                self._bars.append((QRectF(x0 + j * (bw + gap), top, bw, h), label, j, v))
            p.setPen(qcolor("text2"))
            p.drawText(QRectF(slot * i, top + h + 4, slot, fm.height()), Qt.AlignmentFlag.AlignCenter, label)

    def mouseMoveEvent(self, e):
        pos = e.position()
        for r, label, j, v in self._bars:
            if r.contains(pos):
                name = self.names[j] if j < len(self.names) else ""
                QToolTip.showText(e.globalPosition().toPoint(), f"{label} · {name}: {self.fmt(v)}".replace(" · : ", " · "), self)
                return
        QToolTip.hideText()


class HBars(QWidget):
    """Yatay oran çubukları: [(etiket, değer)] — gider kategorileri, çalışılan bölgeler."""

    def __init__(self, role="text", fmt=str, parent=None):
        super().__init__(parent)
        self.role, self.fmt = role, fmt
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 4, 0, 0)
        self.v.setSpacing(8)

    def set_data(self, data, empty_text=""):
        clear_layout(self.v)
        if not data:
            lbl = QLabel(empty_text)
            lbl.setObjectName("Empty")
            self.v.addWidget(lbl)
            return
        mx = max(v for _, v in data) or 1
        for label, val in data:
            box = QVBoxLayout()
            box.setSpacing(3)
            top = QHBoxLayout()
            a = QLabel(label)
            a.setObjectName("RowTitle")
            b = QLabel(self.fmt(val))
            b.setObjectName("RowSub")
            top.addWidget(a, 1)
            top.addWidget(b)
            box.addLayout(top)
            box.addWidget(ProgressBar(val / mx, self.role, height=5))
            self.v.addLayout(box)


class WeekStrip(QWidget):
    """Haftanın 7 günü: yapılan gün dolu daire, bugün çerçeveli."""

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.labels = labels
        self.done = [False] * 7
        self.today = -1
        self.setFixedHeight(58)
        theme.bind(self, lambda w: w.update())

    def set(self, done, today_idx):
        self.done, self.today = done, today_idx
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        slot = self.width() / 7
        r = min(15.0, slot / 2 - 4)
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        p.setFont(f)
        for i in range(7):
            c = QPointF(slot * i + slot / 2, r + 4)
            if self.done[i]:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor("text"))
                p.drawEllipse(c, r, r)
                p.setPen(QPen(qcolor("bg"), 2.2))
                p.drawLine(QPointF(c.x() - r * .38, c.y()), QPointF(c.x() - r * .08, c.y() + r * .3))
                p.drawLine(QPointF(c.x() - r * .08, c.y() + r * .3), QPointF(c.x() + r * .42, c.y() - r * .3))
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor("track"))
                p.drawEllipse(c, r, r)
            if i == self.today:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(qcolor("text2"), 1.5))
                p.drawEllipse(c, r + 3, r + 3)
            p.setPen(qcolor("text" if i == self.today else "text2"))
            p.drawText(QRectF(slot * i, 2 * r + 12, slot, 16), Qt.AlignmentFlag.AlignCenter, self.labels[i])


class Ring(QWidget):
    """Halka ilerleme göstergesi (ortasında metin)."""

    def __init__(self, size=92, parent=None, thick=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.thick = thick or (8 if size >= 90 else 6)
        self.value = 0.0
        self.text = ""
        self.sub = ""
        self.role = "text"
        theme.bind(self, lambda w: w.update())

    def set(self, value, text, sub="", role="text"):
        self.value, self.text, self.sub, self.role = value, text, sub, role
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.thick
        r = QRectF(w / 2 + 1, w / 2 + 1, self.width() - w - 2, self.height() - w - 2)
        p.setPen(QPen(qcolor("track"), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, 0, 360 * 16)
        v = max(0.0, min(1.0, self.value))
        if v > 0:
            p.setPen(QPen(qcolor(self.role), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(r, 90 * 16, -int(360 * 16 * v))
        f = QFont(self.font())
        big = max(10.0, min(22.0, self.width() / 7))
        f.setPointSizeF(big)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(qcolor("text"))
        h = big * 1.6
        tr = QRectF(0, self.height() / 2 - h * 0.66, self.width(), h)
        p.drawText(tr, Qt.AlignmentFlag.AlignCenter, self.text)
        if self.sub:
            f.setPointSizeF(max(7.0, big * 0.52))
            f.setWeight(QFont.Weight.Normal)
            p.setFont(f)
            p.setPen(qcolor("text2"))
            p.drawText(QRectF(0, self.height() / 2 + h * 0.36, self.width(), h * 0.7),
                       Qt.AlignmentFlag.AlignCenter, self.sub)


class ChipBar(QWidget):
    """YouTube filtre çipleri; tek seçim."""
    changed = pyqtSignal(object)

    def __init__(self, items, current=None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.btns = {}
        for key, label in items:
            b = QPushButton(label.replace("&", "&&"))
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, k=key: self.select(k))
            lay.addWidget(b)
            self.btns[key] = b
        lay.addStretch(1)
        self.current = None
        self.select(current if current in self.btns else (items[0][0] if items else None), emit=False)

    def select(self, key, emit=True):
        self.current = key
        for k, b in self.btns.items():
            b.setChecked(k == key)
        if emit:
            self.changed.emit(key)
