"""GitHub tarzı gün kareleri (DayGrid): alışkanlık / ders çalışma serileri."""
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QPen, QFont, QColor
from PyQt6.QtWidgets import QWidget, QToolTip, QSizePolicy

from ..config import day_today
from ..theme import theme, qcolor


# ============================================================ GitHub tarzı kareler
class DayGrid(QWidget):
    """Son haftaların günlük kareleri (sütun = hafta, satır = Pzt…Paz). Dolu kare = o gün yapıldı.
    Bugün ve geçmiş kareler tıklanınca day_toggled(date) yayılır; gelecek kareler soluk ve tıklanamaz.
    span=(geri ay, ileri ay) verilirse aralık sabittir (ör. (2, 1): son 2 ay + önümüzdeki 1 ay) ve kareler
    genişliğe göre büyür (kare, en fazla CELL_MAX).
    set_values({gün: 0 | 0.5 | 1}, ranges, quit): yarım = alt yarısı dolu; quit=True → 0 kırmızı (kayma),
    değeri olmayan gün (başlangıçtan önce) boş. ranges = seriler: seri içindeki ardışık günler zincirle bağlanır."""
    day_toggled = pyqtSignal(object)

    CELL = 13
    GAP = 3
    LEFT = 30
    TOP = 18

    CELL_MAX = 24

    def __init__(self, weekday_labels, month_labels, max_weeks=53, role="text", span=None, parent=None):
        super().__init__(parent)
        self.span = span
        self.CW = self.CELL          # sütun genişliği (span'de genişliğe yayılır, kare yüksekliği CELL)
        self.wd_labels = weekday_labels
        self.month_labels = month_labels
        self.max_weeks = max_weeks
        self.role = role
        self.days = set()
        self.vals = None          # None → days kümesi (eski kullanım)
        self.ranges = []
        self.quit = False
        self._hover = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self.TOP + 7 * (self.CELL + self.GAP))
        self.setMinimumWidth(self.LEFT + 8 * (self.CELL + self.GAP))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme.bind(self, lambda w: w.update())

    def set_days(self, days):
        self.days = set(days)
        self.vals = None
        self.update()

    def set_values(self, vals, ranges=(), quit=False):
        self.vals = dict(vals)
        self.days = {d for d, v in self.vals.items() if v > 0}
        self.ranges = list(ranges)
        self.quit = quit
        self.update()

    def value(self, d):
        if self.vals is None:
            return 1.0 if d in self.days else 0.0
        return self.vals.get(d)

    def _in_range(self, d):
        return any(a <= d <= b for a, b in self.ranges)

    def _span_range(self):
        from datetime import timedelta
        td = day_today()
        back, ahead = self.span

        def shift(k):
            m0 = td.year * 12 + td.month - 1 + k
            y, m = m0 // 12, m0 % 12 + 1
            import calendar
            return td.replace(year=y, month=m, day=min(td.day, calendar.monthrange(y, m)[1]))
        a, z = shift(-back), shift(ahead)
        a -= timedelta(days=a.weekday())
        z += timedelta(days=6 - z.weekday())
        return a, (z - a).days // 7 + 1

    def weeks(self):
        if self.span:
            return self._span_range()[1]
        return max(1, min(self.max_weeks, (self.width() - self.LEFT + self.GAP) // (self.CELL + self.GAP)))

    def first_day(self):
        from datetime import timedelta
        if self.span:
            return self._span_range()[0]
        td = day_today()
        return td - timedelta(days=td.weekday()) - timedelta(weeks=self.weeks() - 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.span:
            n = self._span_range()[1]
            cell = int(max(9, min(self.CELL_MAX, (self.width() - self.LEFT + self.GAP) / n - self.GAP)))
            self.CW = cell
            if cell != self.CELL:
                self.CELL = cell
                self.setFixedHeight(self.TOP + 7 * (self.CELL + self.GAP))
            self.update()

    def _day_at(self, pos):
        from datetime import timedelta
        x, y = pos.x() - self.LEFT, pos.y() - self.TOP
        step, xs = self.CELL + self.GAP, self.CW + self.GAP
        if x < 0 or y < 0:
            return None
        c, r = int(x // xs), int(y // step)
        if c >= self.weeks() or r > 6 or x - c * xs > self.CW or y - r * step > self.CELL:
            return None
        return self.first_day() + timedelta(days=c * 7 + r)

    def mouseMoveEvent(self, e):
        from ..i18n import fmt_long_date
        d = self._day_at(e.position())
        if d != self._hover:
            self._hover = d
            self.update()
            if d is not None:
                v = self.value(d) if d <= day_today() else None
                state = "" if v is None else "½" if 0 < v < 1 else ("✓" if v else ("✗" if self.quit else "·"))
                QToolTip.showText(e.globalPosition().toPoint(), f"{fmt_long_date(d)}  {state}", self)
            else:
                QToolTip.hideText()

    def leaveEvent(self, e):
        self._hover = None
        self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            d = self._day_at(e.position())
            if d is not None and d <= day_today():
                self.day_toggled.emit(d)
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        from datetime import timedelta
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        td = day_today()
        step, xs = self.CELL + self.GAP, self.CW + self.GAP
        n = self.weeks()
        start = self.first_day()
        f = QFont(self.font())
        f.setPointSizeF(7.5)
        p.setFont(f)
        # gün etiketleri (Pzt, Çar, Cum)
        p.setPen(qcolor("text3"))
        for r in (0, 2, 4):
            p.drawText(QRectF(0, self.TOP + r * step - 2, self.LEFT - 6, self.CELL + 4),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.wd_labels[r])
        # ay etiketleri: ayın ilk gününü içeren sütunun üstünde
        last_x = -100
        for c in range(n):
            wk = start + timedelta(weeks=c)
            first = next((wk + timedelta(days=i) for i in range(7) if (wk + timedelta(days=i)).day == 1), None)
            if c == 0 and first is None:
                first = wk
            if first is not None:
                x = self.LEFT + c * xs
                if x - last_x >= 30:
                    p.drawText(QRectF(x, 0, 40, self.TOP - 4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                               self.month_labels[first.month - 1])
                    last_x = x
        on = qcolor(self.role)
        off = qcolor("track")
        bad = qcolor("bad")
        # zincir: aynı sütunda alt alta iki seri günü arasındaki boşluğu doldur
        link = QColor(on)
        link.setAlphaF(0.55)
        for c in range(n):
            for r in range(6):
                d = start + timedelta(days=c * 7 + r)
                d2 = d + timedelta(days=1)
                if d2 > td:
                    continue
                v1, v2 = self.value(d) or 0, self.value(d2) or 0
                chained = (v1 > 0 and v2 > 0) or (self.ranges and self._in_range(d) and self._in_range(d2))
                if chained and not (self.quit and (v1 == 0 or v2 == 0)):
                    w = max(3.0, self.CW * 0.34)
                    x = self.LEFT + c * xs + (self.CW - w) / 2
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(link)
                    p.drawRect(QRectF(x, self.TOP + r * step + self.CELL - 2, w, self.GAP + 4))
        for c in range(n):
            for r in range(7):
                d = start + timedelta(days=c * 7 + r)
                rect = QRectF(self.LEFT + c * xs, self.TOP + r * step, self.CW, self.CELL)
                p.setPen(Qt.PenStyle.NoPen)
                v = self.value(d) if d <= td else None
                if d > td:
                    col = qcolor("track")
                    col.setAlphaF(0.35)
                elif v is None:
                    col = QColor(off)
                    col.setAlphaF(0.5)
                elif v >= 1:
                    col = on
                elif v > 0:
                    col = off
                elif self.quit:
                    col = bad
                else:
                    col = off
                p.setBrush(col)
                p.drawRoundedRect(rect, 3, 3)
                if v is not None and 0 < v < 1 and d <= td:          # yarım: alt yarısı dolu
                    p.save()
                    p.setClipRect(QRectF(rect.x(), rect.y() + rect.height() / 2, rect.width(), rect.height() / 2 + 1))
                    p.setBrush(on)
                    p.drawRoundedRect(rect, 3, 3)
                    p.restore()
                elif v == 0 and self.ranges and self._in_range(d) and not self.quit:   # serideki dinlenme günü
                    p.setBrush(link)
                    p.drawRoundedRect(QRectF(rect.center().x() - 2, rect.center().y() - 2, 4, 4), 2, 2)
                if d == td or d == self._hover and d <= td:
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(qcolor("text2" if d == td else "text"), 1.2))
                    p.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), 4, 4)
