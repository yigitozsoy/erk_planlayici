"""Sınava çalışma kareleri: konu konu satırlar (Excel'de tablo seçer gibi).

Kayıt: exams.study = [{"t": konu adı, "n": kare sayısı, "d": dolu kare}, ...]. Her satır bir konu; satır uzunluğu
serbest (3x3 olmak zorunda değil). Fareyle bir satırın üzerine gelince sağında soluk kareler çıkar: soluk kareye
tıkla = satırı oraya kadar uzat. En alttaki soluk satır = yeni konu (tıkladığın kadar kare). Dolu olmayan kareye
tıkla = o kareye kadar doldur, son dolu kareye tıkla = bir geri al. Sağ tık: adlandır / buradan sonrasını sil /
konuyu sil. Konu adına çift tık = adlandır.

Eski kayıtlar (study_goal + study_done) okunurken satırlara bölünür; ilk değişiklikte "study"ye yazılır.
Geçmiş ve puanı girilmiş sınavlarda da gösterilir (önceki sınavlara da kare atanabilsin).
"""
import math

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QFontMetrics
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu, QInputDialog

from ..components import sub_label
from ..config import day_today
from ..i18n import t
from ..store import num, parse_date
from ..theme import theme, qcolor

MAX_COLS = 12          # bir konu satırında en fazla kare


def cols_for(n):
    """Eski tek tablo kayıtlarını satırlara bölerken sütun sayısı: 12 → 4×3, 20 → 5×4 …"""
    if n <= 4:
        return n
    if n <= 16:
        return 4
    return min(10, math.ceil(math.sqrt(n * 1.25)))


def rows_of(e):
    """[{"t", "n", "d"}] (kopya). Eski study_goal / study_done kayıtlarını satırlara böler."""
    rows = e.get("study")
    if isinstance(rows, list):
        out = []
        for r in rows:
            if isinstance(r, dict):
                n = max(0, min(MAX_COLS, int(num(r.get("n")))))
                if n:
                    out.append({"t": str(r.get("t") or ""), "n": n, "d": max(0, min(n, int(num(r.get("d")))))})
        return out
    g = int(num(e.get("study_goal")))
    d = int(num(e.get("study_done")))
    if g <= 0 and d <= 0:
        return []
    g = max(g, d, 1) if g > 0 else 12
    c = cols_for(g)
    out = []
    while g > 0:
        n = min(c, g)
        out.append({"t": "", "n": n, "d": max(0, min(n, d))})
        d -= n
        g -= n
    return out


def goal_of(e):
    return sum(r["n"] for r in rows_of(e))


def done_of(e):
    return sum(r["d"] for r in rows_of(e))


def wants_blocks(e, td=None):
    """Özetlerde sayılsın mı: karesi var, puansız ve tarihi geçmemiş."""
    if not goal_of(e) or e.get("score") not in (None, ""):
        return False
    d = parse_date(e.get("date"))
    return d is None or d >= (td or day_today())


class StudyRows(QWidget):
    """Konu satırları. changed(rows) her değişiklikte."""
    changed = pyqtSignal(list)
    CELL = 20
    GAP = 5
    LABEL_W = 120

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = [dict(r) for r in rows]
        self.hover = (-1, -1)            # (satır, sütun); satır == len(rows) → yeni konu satırı
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("study_rows_tip"))
        self._resize()
        theme.bind(self, lambda w: w.update())

    def _resize(self):
        self.setFixedSize(self.LABEL_W + MAX_COLS * (self.CELL + self.GAP),
                          (len(self.rows) + 1) * (self.CELL + self.GAP))

    def _rect(self, r, c):
        return QRectF(self.LABEL_W + c * (self.CELL + self.GAP), r * (self.CELL + self.GAP), self.CELL, self.CELL)

    def _at(self, pos):
        p = pos.toPointF() if hasattr(pos, "toPointF") else pos
        r = int(p.y() // (self.CELL + self.GAP))
        if r < 0 or r > len(self.rows):
            return -1, -1
        if p.x() < self.LABEL_W:
            return r, -1
        c = int((p.x() - self.LABEL_W) // (self.CELL + self.GAP))
        return (r, c) if 0 <= c < MAX_COLS else (r, -1)

    def _label(self, i):
        r = self.rows[i]
        return r["t"] or t("study_topic_n", n=i + 1)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on, off, ghost = qcolor("text"), qcolor("track"), qcolor("text3")
        fm = QFontMetrics(self.font())
        hr, hc = self.hover
        for i, row in enumerate(self.rows + [None]):
            y = i * (self.CELL + self.GAP)
            # konu adı
            p.setPen(qcolor("text2" if row else "text3"))
            txt = self._label(i) if row else t("study_new_topic")
            p.drawText(QRectF(0, y, self.LABEL_W - 10, self.CELL),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       fm.elidedText(txt, Qt.TextElideMode.ElideRight, self.LABEL_W - 10))
            n = row["n"] if row else 0
            d = row["d"] if row else 0
            for c in range(n):
                col = on if c < d else off
                if (i, c) == (hr, hc):
                    col = col.darker(115) if c < d else off.lighter(140)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(col)
                p.drawRoundedRect(self._rect(i, c), 4, 4)
            # soluk kareler: Excel'deki tablo seçici gibi, üzerine gelinen yere kadar
            if i == hr:
                upto = max(hc, n) if hc >= n else n
                pen = QPen(ghost, 1, Qt.PenStyle.DashLine)
                p.setBrush(Qt.BrushStyle.NoBrush)
                for c in range(n, MAX_COLS):
                    pen.setColor(on if c <= upto and hc >= n else ghost)
                    p.setPen(pen)
                    p.drawRoundedRect(self._rect(i, c).adjusted(.5, .5, -.5, -.5), 4, 4)
            elif row is None:
                pen = QPen(ghost, 1, Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(self._rect(i, 0).adjusted(.5, .5, -.5, -.5), 4, 4)
                p.drawText(self._rect(i, 0), Qt.AlignmentFlag.AlignCenter, "+")
        p.end()

    def mouseMoveEvent(self, e):
        h = self._at(e.position())
        if h != self.hover:
            self.hover = h
            self.update()

    def leaveEvent(self, e):
        self.hover = (-1, -1)
        self.update()

    def _emit(self):
        self._resize()
        self.update()
        self.changed.emit([dict(r) for r in self.rows])

    def click(self, r, c):
        """r satırı (len(rows) = yeni konu), c sütunu: doldur / uzat / yeni konu."""
        if r == len(self.rows):
            if c < 0:
                return
            self.rows.append({"t": "", "n": c + 1, "d": 0})
        elif c < 0:
            return self.rename(r)
        else:
            row = self.rows[r]
            if c >= row["n"]:
                row["n"] = c + 1
            else:
                row["d"] = c if c + 1 == row["d"] else c + 1
        self._emit()

    def rename(self, r):
        txt, ok = QInputDialog.getText(self, t("study_rename"), t("study_topic"), text=self.rows[r]["t"])
        if ok:
            self.rows[r]["t"] = txt.strip()
            self._emit()

    def cut(self, r, c):
        """r satırını c karede bırak (c=0 → konuyu sil)."""
        if c <= 0:
            self.rows.pop(r)
        else:
            self.rows[r]["n"] = c
            self.rows[r]["d"] = min(self.rows[r]["d"], c)
        self._emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.click(*self._at(e.position()))

    def mouseDoubleClickEvent(self, e):
        r, c = self._at(e.position())
        if c < 0 and 0 <= r < len(self.rows):
            self.rename(r)

    def contextMenuEvent(self, e):
        r, c = self._at(e.pos())
        if not 0 <= r < len(self.rows):
            return
        m = QMenu(self)
        m.addAction(t("study_rename"), lambda: self.rename(r))
        if 0 <= c < self.rows[r]["n"] - 1:
            m.addAction(t("study_cut_after"), lambda: self.cut(r, c + 1))
        m.addAction(t("study_del_topic"), lambda: self.cut(r, 0))
        m.exec(e.globalPos())


class ExamStudy(QWidget):
    """Bir sınavın konu satırları + "Çalışma kareleri · 5/12" başlığı."""

    def __init__(self, store, e, parent=None):
        super().__init__(parent)
        self.store, self.eid = store, e["id"]
        rows = rows_of(e)
        v = QVBoxLayout(self)
        v.setContentsMargins(40, 0, 8, 8)
        v.setSpacing(6)
        self.lbl = sub_label("")
        v.addWidget(self.lbl)
        self.blocks = StudyRows(rows)
        self.blocks.changed.connect(self._save)
        v.addWidget(self.blocks)
        self._label(rows)

    def _label(self, rows):
        g, d = sum(r["n"] for r in rows), sum(r["d"] for r in rows)
        self.lbl.setText(t("exam_study_info", d=d, g=g))
        self.lbl.setVisible(bool(g))

    def _save(self, rows):
        self._label(rows)
        self.store.update("exams", self.eid, study=rows, study_goal=None, study_done=None)
