"""Sayfa iskeleti (Page), kart (Card), liste satırı (Row) ve küçük kurucular (button, sub_label, clear_layout)."""
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QMimeData
from PyQt6.QtGui import QPainter, QDrag
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QBoxLayout, QPushButton, QSizePolicy, QFrame, QApplication)

from ..theme import theme, qcolor
from ..widgets import IconButton


DRAG_MIME = "application/x-erk-item"   # Row.drag_data -> Card.accept_drop


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
                clear_layout(it.layout())

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


def button(text, cb=None, kind="Pill"):
    """Tema düğmesi (Pill / Primary / Flat / Chip …), el imleci; cb verilirse tıklamaya bağlanır."""
    b = QPushButton(text)
    b.setObjectName(kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if cb is not None:
        b.clicked.connect(cb)
    return b


def sub_label(text="", wrap=False):
    """Satır altı gibi soluk küçük yazı (RowSub)."""
    lb = QLabel(text)
    lb.setObjectName("RowSub")
    if wrap:
        lb.setWordWrap(True)
    return lb


def clear_layout(lay):
    """Layout'u boşaltır (iç içe olanlar dahil): widget gizlenir, ebeveynden ayrılır, silinir."""
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif it.layout() is not None:
            clear_layout(it.layout())


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
            from .. import icons
            from ..theme import color
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
            from ..i18n import t
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
