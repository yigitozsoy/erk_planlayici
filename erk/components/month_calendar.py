"""Bugün sayfasındaki ay takvimi (MonthCalendar); tarih seçicide de kullanılır."""
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QFont
from PyQt6.QtWidgets import QWidget

from ..config import day_today
from ..theme import theme, qcolor


# ============================================================ ay takvimi
class MonthCalendar(QWidget):
    """Ay görünümü: bugün dolu daire, seçili gün çerçeveli, altında en fazla 3 nokta (o günkü kayıtlar).
    Tıkla: day_clicked(date) · çift tıkla: day_activated(date)."""
    day_clicked = pyqtSignal(object)
    day_activated = pyqtSignal(object)

    HEAD = 26
    CELL_H = 42

    def __init__(self, weekday_labels, parent=None):
        super().__init__(parent)
        self.labels = weekday_labels
        td = day_today()
        self.year, self.month = td.year, td.month
        self.marks = {}          # date → ["bad", "good", "text2", ...]
        self.selected = None
        self._hover = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(240)
        self._relayout()
        theme.bind(self, lambda w: w.update())

    # ------------------------------------------------------------ veri
    def set_month(self, y, m):
        self.year, self.month = y, m
        self._relayout()
        self.update()

    def set_marks(self, marks):
        self.marks = marks
        self.update()

    def set_selected(self, d):
        self.selected = d
        self.update()

    def first_cell(self):
        from datetime import date, timedelta
        first = date(self.year, self.month, 1)
        return first - timedelta(days=first.weekday())

    def visible_range(self):
        from datetime import timedelta
        a = self.first_cell()
        return a, a + timedelta(days=self.rows * 7 - 1)

    def _relayout(self):
        import calendar
        from datetime import date
        n_days = calendar.monthrange(self.year, self.month)[1]
        lead = date(self.year, self.month, 1).weekday()
        self.rows = (lead + n_days + 6) // 7
        self.setFixedHeight(self.HEAD + self.rows * self.CELL_H)

    # ------------------------------------------------------------ geometri
    def _cell_at(self, pos):
        from datetime import timedelta
        y = pos.y() - self.HEAD
        if y < 0 or pos.x() < 0 or pos.x() >= self.width():
            return None
        r, c = int(y // self.CELL_H), int(pos.x() // (self.width() / 7))
        if r >= self.rows or c > 6:
            return None
        return self.first_cell() + timedelta(days=r * 7 + c)

    def mouseMoveEvent(self, e):
        d = self._cell_at(e.position())
        if d != self._hover:
            self._hover = d
            self.update()

    def leaveEvent(self, e):
        self._hover = None
        self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            d = self._cell_at(e.position())
            if d is not None:
                self.day_clicked.emit(d)
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        d = self._cell_at(e.position())
        if d is not None:
            self.day_activated.emit(d)

    # ------------------------------------------------------------ çizim
    def paintEvent(self, e):
        from datetime import timedelta
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width() / 7
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        p.setFont(f)
        for i, lab in enumerate(self.labels):
            p.setPen(qcolor("text3" if i >= 5 else "text2"))
            p.drawText(QRectF(i * w, 0, w, self.HEAD - 6), Qt.AlignmentFlag.AlignCenter, lab)
        f.setPointSizeF(9.5)
        td = day_today()
        start = self.first_cell()
        r = min(15.0, w / 2 - 3)
        for k in range(self.rows * 7):
            d = start + timedelta(days=k)
            row, col = divmod(k, 7)
            cx = col * w + w / 2
            cy = self.HEAD + row * self.CELL_H + r + 2
            c = QPointF(cx, cy)
            in_month = d.month == self.month
            is_today = d == td
            if is_today:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor("chip_active_bg"))
                p.drawEllipse(c, r, r)
            elif d == self._hover:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor("hover"))
                p.drawEllipse(c, r, r)
            if d == self.selected and not is_today:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(qcolor("text"), 1.5))
                p.drawEllipse(c, r, r)
            elif d == self.selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(qcolor("text2"), 1.5))
                p.drawEllipse(c, r + 3, r + 3)
            f.setBold(is_today)
            p.setFont(f)
            if is_today:
                p.setPen(qcolor("chip_active_fg"))
            elif not in_month:
                p.setPen(qcolor("text3"))
            elif d < td:
                p.setPen(qcolor("text2"))
            else:
                p.setPen(qcolor("text"))
            p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter, str(d.day))
            dots = self.marks.get(d) or []
            if dots:
                dots = dots[:3]
                gap = 6.0
                x0 = cx - gap * (len(dots) - 1) / 2
                p.setPen(Qt.PenStyle.NoPen)
                for j, role in enumerate(dots):
                    col_ = qcolor(role)
                    if not in_month:
                        col_.setAlphaF(0.45)
                    p.setBrush(col_)
                    p.drawEllipse(QPointF(x0 + j * gap, cy + r + 5), 2.2, 2.2)
