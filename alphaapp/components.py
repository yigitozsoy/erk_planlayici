"""Gösterge paneli yapı taşları: sayfa iskeleti, kart, liste satırı, istatistik kutusu, küçük grafikler."""
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer, QRect, QSize, QPoint, QMimeData
from PyQt6.QtGui import QPainter, QPen, QFontMetrics, QFont, QDrag, QColor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QBoxLayout, QPushButton,
                             QToolTip, QSizePolicy, QFrame, QLayout, QApplication)

from .config import day_today
from .theme import theme, qcolor
from .widgets import IconButton

DRAG_MIME = "application/x-alpha-item"   # Row.drag_data -> Card.accept_drop


# ============================================================ sayfa iskeleti
class Page(QScrollArea):
    """Kaydırılabilir sayfa: başlık + kart satırları. Veri değişince görünürse yenilenir."""
    title_key = ""

    def __init__(self, store, win, title="", sub=""):
        super().__init__()
        self.store = store
        self.win = win
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName("PageHost")
        self.content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.vbox = QVBoxLayout(self.content)
        self.vbox.setContentsMargins(28, 18, 28, 28)
        self.vbox.setSpacing(16)
        self.setWidget(self.content)

        head = QHBoxLayout()
        head.setSpacing(8)
        tb = QVBoxLayout()
        tb.setSpacing(2)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("PageTitle")
        self.sub_lbl = QLabel(sub)
        self.sub_lbl.setObjectName("PageSub")
        self.sub_lbl.setVisible(bool(sub))
        tb.addWidget(self.title_lbl)
        tb.addWidget(self.sub_lbl)
        head.addLayout(tb, 1)
        self.head_actions = QHBoxLayout()
        self.head_actions.setSpacing(8)
        head.addLayout(self.head_actions)
        self.vbox.addLayout(head)
        self._body_index = self.vbox.count()
        self.vbox.addStretch(1)

        self._dirty = True
        self._pending = False
        store.changed.connect(self._on_change)

    def add(self, w, stretch=0):
        """Sayfaya (son esnemeden önce) bir öğe ekler."""
        self.vbox.insertWidget(self.vbox.count() - 1, w, stretch)
        return w

    def row(self, *cards, stretches=None, breakpoint=860):
        r = ResponsiveRow(breakpoint)
        for i, c in enumerate(cards):
            r.add(c, (stretches or [1] * len(cards))[i])
        return self.add(r)

    def action(self, text, cb, primary=False, icon=None):
        b = QPushButton(text)
        b.setObjectName("Primary" if primary else "Pill")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if icon:
            theme.icon(b, icon, "button_fg" if primary else "text", 18)
        b.clicked.connect(cb)
        self.head_actions.addWidget(b)
        return b

    def set_sub(self, text):
        self.sub_lbl.setText(text)
        self.sub_lbl.setVisible(bool(text))

    def _on_change(self, coll):
        if self.isVisible():
            if not self._pending:
                self._pending = True
                QTimer.singleShot(0, self._do_refresh)
        else:
            self._dirty = True

    def _do_refresh(self):
        self._pending = False
        self._dirty = False
        self.refresh()

    def mark_dirty(self):
        self._dirty = True
        if self.isVisible():
            self._do_refresh()

    def showEvent(self, e):
        super().showEvent(e)
        if self._dirty:
            self._do_refresh()

    def refresh(self):
        pass


class ResponsiveRow(QWidget):
    """Genişken kartları yan yana, darken alt alta dizer."""

    def __init__(self, breakpoint=860, parent=None):
        super().__init__(parent)
        self.bp = breakpoint
        self.lay = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(16)

    def add(self, w, stretch=1):
        self.lay.addWidget(w, stretch, Qt.AlignmentFlag.AlignTop)

    def resizeEvent(self, e):
        d = QBoxLayout.Direction.TopToBottom if self.width() < self.bp else QBoxLayout.Direction.LeftToRight
        if self.lay.direction() != d:
            self.lay.setDirection(d)
        super().resizeEvent(e)


class ElideLabel(QLabel):
    """Sığmayan tek satırlık metni "…" ile kısaltır (taşma yapmaz); tam metin ipucunda görünür."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMinimumWidth(20)

    def minimumSizeHint(self):
        sh = super().minimumSizeHint()
        return sh.__class__(20, sh.height())

    def paintEvent(self, e):
        p = QPainter(self)
        fm = self.fontMetrics()
        txt = fm.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        self.setToolTip(self.text() if txt != self.text() else "")
        p.setPen(self.palette().color(self.foregroundRole()))
        p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), txt)


# ============================================================ kart
class Card(QWidget):
    add_clicked = pyqtSignal()

    def __init__(self, title="", sub="", add_tip=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 12, 14)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(4)
        tb = QVBoxLayout()
        tb.setSpacing(0)
        self.title_lbl = ElideLabel(title)
        self.title_lbl.setObjectName("CardTitle")
        tb.addWidget(self.title_lbl)
        self.sub_lbl = ElideLabel(sub)
        self.sub_lbl.setObjectName("CardSub")
        self.sub_lbl.setVisible(bool(sub))
        tb.addWidget(self.sub_lbl)
        head.addLayout(tb, 1)
        self.head = head
        self.add_btn = None
        if add_tip:
            self.add_btn = IconButton("add", add_tip, 32, 20)
            self.add_btn.clicked.connect(self.add_clicked.emit)
            head.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(0)
        self.body.setContentsMargins(0, 2, 0, 0)
        v.addLayout(self.body)

    def head_widget(self, w):
        self.head.insertWidget(self.head.count() - (1 if self.add_btn else 0), w, 0, Qt.AlignmentFlag.AlignTop)
        return w

    def set_sub(self, text):
        self.sub_lbl.setText(text)
        self.sub_lbl.setVisible(bool(text))

    def clear(self):
        while self.body.count():
            it = self.body.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif it.layout() is not None:
                _clear_layout(it.layout())

    def add(self, w):
        self.body.addWidget(w)
        return w

    def empty(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("Empty")
        lbl.setWordWrap(True)
        self.body.addWidget(lbl)
        return lbl

    # --- sürükle-bırak hedefi: Row.drag_data "coll:id" ve coll kabul edilenlerdense on_drop(coll, id) çağrılır
    _drop = None

    def accept_drop(self, colls, on_drop):
        self._drop = (tuple(colls), on_drop)
        self.setAcceptDrops(True)

    def _drop_item(self, e):
        if not self._drop or not e.mimeData().hasFormat(DRAG_MIME):
            return None
        coll, _, iid = bytes(e.mimeData().data(DRAG_MIME)).decode("utf-8").partition(":")
        if coll not in self._drop[0] or not iid:
            return None
        src = e.source()
        if src is not None and self.isAncestorOf(src):   # kendi kartına bırakmak bir şey yapmasın
            return None
        return coll, iid

    def _hover(self, on):
        self.setProperty("drop", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, e):
        if self._drop_item(e):
            e.acceptProposedAction()
            self._hover(True)
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._drop_item(e):
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._hover(False)

    def dropEvent(self, e):
        self._hover(False)
        item = self._drop_item(e)
        if item:
            e.acceptProposedAction()
            # Bırakma sırasında kayıt değişirse kaynak satır silinir; işi sürükleme bittikten sonra yap
            QTimer.singleShot(0, lambda: self._drop[1](*item))


def _clear_layout(lay):
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif it.layout() is not None:
            _clear_layout(it.layout())


# ============================================================ liste satırı
class Row(QWidget):
    """Kart içindeki tek satır: [onay/ikon] başlık + alt satır ... rozetler · değer.
    Tıkla: düzenle · sağ tık: menü."""
    clicked = pyqtSignal()
    menu_requested = pyqtSignal(object)   # QPoint (global)
    check_toggled = pyqtSignal(bool)

    def __init__(self, title, sub="", value="", value_role=None, icon=None, icon_role="text2", check=None,
                 badges=(), lead=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Row")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 8, 6)
        lay.setSpacing(10)
        self.check_btn = None
        if check is not None:
            self.check_btn = IconButton("box_checked" if check else "box", "", 28, 20,
                                        role="text" if check else "text2")
            self._checked = bool(check)
            self.check_btn.clicked.connect(self._toggle)
            lay.addWidget(self.check_btn)
        elif icon:
            ic = QLabel()
            ic.setFixedSize(28, 28)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            from . import icons
            from .theme import color
            theme.bind(ic, lambda l, n=icon, r=icon_role: l.setPixmap(icons.pixmap(n, color(r), 20)))
            lay.addWidget(ic)
        if lead is not None:
            lay.addWidget(lead)
        tb = QVBoxLayout()
        tb.setSpacing(1)
        self.title_lbl = ElideLabel(title)
        self.title_lbl.setObjectName("RowTitleDone" if check else "RowTitle")
        tb.addWidget(self.title_lbl)
        if sub:
            s = ElideLabel(sub)
            s.setObjectName("RowSub")
            tb.addWidget(s)
        lay.addLayout(tb, 1)
        for text, kind in badges:
            if not text:
                continue
            b = QLabel(text)
            b.setObjectName({"bad": "BadgeBad", "warn": "BadgeWarn", "good": "BadgeGood"}.get(kind, "Badge"))
            lay.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        if value != "" and value is not None:
            v = QLabel(str(value))
            v.setObjectName("RowValue")
            if value_role:
                theme.bind(v, lambda l, r=value_role: l.setStyleSheet(f"color: {qcolor(r).name()};"))
            lay.addWidget(v, 0, Qt.AlignmentFlag.AlignVCenter)

    def _toggle(self):
        self._checked = not self._checked
        self.check_toggled.emit(self._checked)

    # Sürükle-bırak: drag_data ("koleksiyon:id") verilmişse satır sürüklenebilir; Card.accept_drop ile yakalanır.
    drag_data = None
    _press = None
    _dragged = False

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press, self._dragged = e.position().toPoint(), False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if (self.drag_data and self._press is not None and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position().toPoint() - self._press).manhattanLength() >= QApplication.startDragDistance()):
            self._press, self._dragged = None, True
            md = QMimeData()
            md.setData(DRAG_MIME, self.drag_data.encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(md)
            pm = self.grab()
            drag.setPixmap(pm)
            drag.setHotSpot(e.position().toPoint())
            drag.exec(Qt.DropAction.MoveAction)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if (e.button() == Qt.MouseButton.LeftButton and not self._dragged
                and self.rect().contains(e.position().toPoint())):
            self.clicked.emit()
        self._press, self._dragged = None, False
        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e):
        self.menu_requested.emit(e.globalPos())

    # sağ tık menüsü olan satırda fareyle üzerine gelince görünen ⋮ düğmesi (menü yalnızca sağ tıkla kalmasın)
    _more = None

    def showEvent(self, e):
        super().showEvent(e)
        if self._more is None and self.receivers(self.menu_requested) > 0:
            from .i18n import t
            b = IconButton("more_vert", t("row_more"), 26, 18, role="text2")
            sp = b.sizePolicy()
            sp.setRetainSizeWhenHidden(True)
            b.setSizePolicy(sp)
            b.setVisible(self.underMouse())
            b.clicked.connect(lambda: self.menu_requested.emit(b.mapToGlobal(QPoint(0, b.height()))))
            self.layout().addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
            self._more = b

    def enterEvent(self, e):
        if self._more is not None:
            self._more.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._more is not None:
            self._more.setVisible(False)
        super().leaveEvent(e)


# ============================================================ istatistik kutusu
class StatTile(QWidget):
    clicked = pyqtSignal()

    def __init__(self, label, value="", note="", note_kind=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(2)
        self.lbl = QLabel(label)
        self.lbl.setObjectName("StatLabel")
        self.val = QLabel(value)
        self.val.setObjectName("StatValue")
        self.note = QLabel(note)
        self.note.setObjectName("StatLabel")
        v.addWidget(self.lbl)
        v.addWidget(self.val)
        v.addWidget(self.note)
        self.set(value, note, note_kind)

    def set(self, value, note="", note_kind=None):
        self.val.setText(value)
        self.note.setText(note)
        self.note.setObjectName({"good": "StatGood", "bad": "StatBad"}.get(note_kind, "StatLabel"))
        self.note.style().unpolish(self.note)
        self.note.style().polish(self.note)
        if not note:
            self.note.setText(" ")


def tiles_row(*tiles):
    w = QWidget()
    g = QHBoxLayout(w)
    g.setContentsMargins(0, 0, 0, 0)
    g.setSpacing(12)
    for t in tiles:
        g.addWidget(t, 1)
    return w


class TileGrid(QWidget):
    """İstatistik kutularını genişliğe göre 2 / 3 / 6 sütuna dizer."""

    def __init__(self, tiles, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QGridLayout
        self.tiles = list(tiles)
        self.g = QGridLayout(self)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setSpacing(12)
        self._cols = 0
        self._place(len(self.tiles))

    def _place(self, cols):
        if cols == self._cols:
            return
        self._cols = cols
        for t in self.tiles:
            self.g.removeWidget(t)
        for c in range(8):
            self.g.setColumnStretch(c, 0)
        for i, t in enumerate(self.tiles):
            self.g.addWidget(t, i // cols, i % cols)
        for c in range(cols):
            self.g.setColumnStretch(c, 1)

    def resizeEvent(self, e):
        n = len(self.tiles)
        w = self.width()
        per = 170
        cols = max(1, min(n, w // per))
        # dengeli dağıt: 6 kutu → 6, 3 ya da 2 sütun
        while n % cols and cols > 1 and cols > n // 2:
            cols -= 1
        self._place(cols)
        super().resizeEvent(e)


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
        _clear_layout(self.v)
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
        from .i18n import fmt_long_date
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


# ============================================================ akış düzeni (çipler satıra sığmazsa alta geçer)
class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._items = []
        self._sp = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._place(QRect(0, 0, w, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for it in self._items:
            size = size.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _place(self, rect, test):
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = r.x(), r.y(), 0
        for it in self._items:
            hint = it.sizeHint()
            nx = x + hint.width() + self._sp
            if nx - self._sp > r.right() + 1 and line_h > 0:
                x = r.x()
                y += line_h + self._sp
                nx = x + hint.width() + self._sp
                line_h = 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x = nx
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()
