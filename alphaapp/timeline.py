"""Günün zaman şeridi (sabah planı, 2. adım): saatli program kutuları + aradaki boş zamanlar.
Boş bir aralığa tıklanınca gap_clicked(başlangıç dk, bitiş dk, ekran konumu) yayılır; kutuya tıklanınca item_clicked."""
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QSizePolicy, QToolTip

from .i18n import t
from .theme import theme, qcolor, BAD

MIN_GAP = 30          # bundan kısa boşluklar gösterilmez (dk)


def to_min(hhmm):
    try:
        h, m = str(hhmm).split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def hhmm(m):
    m = max(0, min(24 * 60 - 1, int(m)))
    return f"{m // 60:02d}:{m % 60:02d}"


def fmt_dur(m):
    h, mm = divmod(int(m), 60)
    if h and mm:
        return t("dur_hm", h=h, m=mm)
    return t("dur_h", h=h) if h else t("dur_m", m=mm)


def find_gaps(blocks, start, end, min_gap=MIN_GAP):
    """blocks: (a, b) dakika aralıkları. [start, end] içindeki boşluklar."""
    out, cur = [], start
    for a, b in sorted(blocks):
        if b <= cur:
            continue
        if a > cur and a - cur >= min_gap:
            out.append((cur, min(a, end)))
        cur = max(cur, b)
        if cur >= end:
            break
    if end - cur >= min_gap:
        out.append((cur, end))
    return [(a, b) for a, b in out if b - a >= min_gap]


class DayTimeline(QWidget):
    item_clicked = pyqtSignal(object)            # öğe dict'i
    gap_clicked = pyqtSignal(int, int, object)   # başlangıç, bitiş (dk), QPoint

    TOP = 20
    BAR = 46

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(self.TOP + self.BAR + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.items, self.gaps = [], []
        self.h0, self.h1 = 8, 22
        self.now = None
        self._hover = None
        theme.bind(self, lambda w: w.update())

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(600, self.TOP + self.BAR + 8)

    def set_items(self, items, now=None):
        """items: dict(start, end (dk), title, important, ...). now: dakika (bugün değilse None)."""
        self.items = sorted(items, key=lambda x: x["start"])
        self.now = now
        h0, h1 = 8, 22
        for x in self.items:
            h0 = min(h0, x["start"] // 60)
            h1 = max(h1, -(-x["end"] // 60))
        self.h0, self.h1 = h0, min(24, h1)
        free_from = self.h0 * 60
        if now is not None:
            free_from = max(free_from, -(-now // 15) * 15)   # şu andan (çeyreğe yuvarla) sonrası
        self.gaps = find_gaps([(x["start"], x["end"]) for x in self.items], free_from, self.h1 * 60)
        self.update()

    # ------------------------------------------------------------ geometri
    def _x(self, m):
        w = self.width() - 2
        return 1 + (m - self.h0 * 60) / max(1, (self.h1 - self.h0) * 60) * w

    def _rect(self, a, b):
        return QRectF(self._x(a), self.TOP, max(3.0, self._x(b) - self._x(a)), self.BAR)

    def _hit(self, pos):
        for x in reversed(self.items):
            if self._rect(x["start"], x["end"]).contains(QPointF(pos)):
                return ("item", x)
        for g in self.gaps:
            if self._rect(*g).contains(QPointF(pos)):
                return ("gap", g)
        return None

    # ------------------------------------------------------------ çizim
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = QFont(self.font())
        f.setPixelSize(11)
        p.setFont(f)
        fm = QFontMetrics(f)
        text2, text3, text = qcolor("text2"), qcolor("text3"), qcolor("text")
        # saat çizgileri
        step = 1 if self.width() / max(1, self.h1 - self.h0) > 44 else 2
        for h in range(self.h0, self.h1 + 1, step):
            x = self._x(h * 60)
            p.setPen(text3)
            label = f"{h:02d}"
            tx = min(max(0.0, x - fm.horizontalAdvance(label) / 2), self.width() - fm.horizontalAdvance(label))
            p.drawText(QPointF(tx, 12), label)
            c = QColor(text3)
            c.setAlpha(60)
            p.setPen(QPen(c, 1))
            p.drawLine(QPointF(x, self.TOP - 3), QPointF(x, self.TOP + self.BAR))
        # zemin
        track = qcolor("surface")
        track.setAlpha(110)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(self._x(self.h0 * 60), self.TOP, self._x(self.h1 * 60) - self._x(self.h0 * 60),
                                 self.BAR), 8, 8)
        # geçmiş saatler soluk
        if self.now is not None and self.now > self.h0 * 60:
            shade = QColor(qcolor("bg"))
            shade.setAlpha(120)
            p.setBrush(shade)
            p.drawRoundedRect(QRectF(self._x(self.h0 * 60), self.TOP,
                                     self._x(min(self.now, self.h1 * 60)) - self._x(self.h0 * 60), self.BAR), 8, 8)
        # boşluklar
        for g in self.gaps:
            r = self._rect(*g).adjusted(2, 4, -2, -4)
            hov = self._hover == ("gap", g)
            pen = QPen(text2 if hov else text3, 1, Qt.PenStyle.DashLine)
            p.setPen(pen)
            hb = QColor(text)
            hb.setAlpha(22 if hov else 0)
            p.setBrush(hb)
            p.drawRoundedRect(r, 6, 6)
            label = t("tl_free", d=fmt_dur(g[1] - g[0]))
            if fm.horizontalAdvance(label) + 10 < r.width():
                p.setPen(text2 if hov else text3)
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, label)
            elif fm.horizontalAdvance("+") + 6 < r.width():
                p.setPen(text3)
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, "+")
        # kutular
        for x in self.items:
            r = self._rect(x["start"], x["end"]).adjusted(1, 2, -1, -2)
            imp = x.get("important")
            hov = self._hover == ("item", x)
            if imp:
                bg = QColor(BAD)
                bg.setAlpha(70 if hov else 48)
                border = QColor(BAD)
            else:
                bg = qcolor("surface_hover" if hov else "surface")
                border = None
            p.setPen(QPen(border, 1) if border else Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(r, 6, 6)
            if r.width() > 26:
                tr = r.adjusted(6, 3, -4, -3)
                p.setPen(QColor(BAD) if imp else text)
                fb = QFont(f)
                fb.setWeight(QFont.Weight.DemiBold)
                p.setFont(fb)
                p.drawText(tr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                           QFontMetrics(fb).elidedText(x["title"], Qt.TextElideMode.ElideRight, int(tr.width())))
                p.setFont(f)
                p.setPen(text2)
                p.drawText(tr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                           fm.elidedText(hhmm(x["start"]), Qt.TextElideMode.ElideRight, int(tr.width())))
        # şimdi çizgisi
        if self.now is not None and self.h0 * 60 <= self.now <= self.h1 * 60:
            x = self._x(self.now)
            p.setPen(QPen(QColor(BAD), 2))
            p.drawLine(QPointF(x, self.TOP - 4), QPointF(x, self.TOP + self.BAR + 2))
            p.setBrush(QColor(BAD))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, self.TOP - 4), 3.5, 3.5)
        p.end()

    # ------------------------------------------------------------ fare
    def mouseMoveEvent(self, e):
        h = self._hit(e.position().toPoint())
        if h != self._hover:
            self._hover = h
            self.setCursor(Qt.CursorShape.PointingHandCursor if h else Qt.CursorShape.ArrowCursor)
            self.update()
            if h and h[0] == "item":
                x = h[1]
                QToolTip.showText(e.globalPosition().toPoint(),
                                  f"{hhmm(x['start'])}–{hhmm(x['end'])}  {x['title']}", self)
            elif h:
                QToolTip.showText(e.globalPosition().toPoint(),
                                  f"{hhmm(h[1][0])}–{hhmm(h[1][1])} · {t('tl_free_tip')}", self)
            else:
                QToolTip.hideText()

    def leaveEvent(self, e):
        self._hover = None
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        h = self._hit(e.position().toPoint())
        if not h:
            return
        if h[0] == "item":
            self.item_clicked.emit(h[1])
        else:
            self.gap_clicked.emit(h[1][0], h[1][1], e.globalPosition().toPoint())


def now_minutes():
    n = datetime.now()
    return n.hour * 60 + n.minute
