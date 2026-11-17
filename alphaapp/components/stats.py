"""İstatistik kutuları: StatTile, tiles_row, TileGrid."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy


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
