"""Kütüphane rafı: kitaplar sırtı dönük dizilir, filmler / diziler DVD kutusu, podcastler CD kutusu.

Shelf        raf görünümü (CoverWall'ın yerine). Fare yaklaşınca kayıt raftan dışarı çıkar: yukarı kalkar, sırtı
             döner ve kapağı perspektifle görünür, sağdakiler yer açmak için kayar (16 ms'lik yumuşak animasyon).
             Tıkla = MediaViewer, sağ tık = menü (library.media_menu).
MediaViewer  pencerenin üstüne açılan katman. Kitap / makale: kapak sol kenarından açılır, iki sayfada bilgiler.
             Film / dizi / belgesel / podcast: kutu kapağının arkasından disk kayarak çıkar ve döner, yanında
             bilgiler. Esc ya da boşluğa tıkla = kapat.
Yazılar doğrudan pencereye çizilir (DPR'li pixmap'e çizilen kalın yazı bozuk çıkıyordu).
"""
import math
import os
import zlib

from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal, QElapsedTimer, QEvent
from PyQt6.QtGui import (QPainter, QColor, QFont, QFontMetrics, QPainterPath, QTransform, QPolygonF,
                         QLinearGradient, QRadialGradient, QConicalGradient, QPen, QImage)
from PyQt6.QtWidgets import QWidget, QSizePolicy, QHBoxLayout

from .. import library
from ..components import button
from ..config import IMAGES_DIR
from ..i18n import t
from ..theme import theme, qcolor

DISC_TYPES = ("film", "series", "doc", "game", "podcast")


def _seed(m):
    return zlib.crc32((m.get("id") or m.get("title") or "x").encode("utf-8"))


def _cover_path(m):
    p = os.path.join(IMAGES_DIR, m["cover"]) if m.get("cover") else None
    return p if p and os.path.exists(p) else None


_avg = {}


def base_color(m):
    """Sırt rengi: kapağın ortalama rengi (koyulaştırılmış), kapak yoksa kayda göre sabit bir gri ton."""
    path = _cover_path(m)
    if path:
        if path not in _avg:
            img = QImage(path)
            if img.isNull():
                _avg[path] = None
            else:
                c = img.scaled(1, 1, Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation).pixelColor(0, 0)
                h, s, v, _a = c.getHsv()
                _avg[path] = QColor.fromHsv(max(0, h), min(s, 170), max(45, min(v, 150)))
        if _avg[path] is not None:
            return QColor(_avg[path])
    g = 48 + _seed(m) % 46
    return QColor(g, g, g + 4)


def _lum(c):
    return 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()


def spine_size(m):
    """(genişlik, yükseklik) — kitapta sayfa sayısına göre kalınlık."""
    ty, sd = m.get("type"), _seed(m)
    if ty == "book":
        pages = m.get("total") or 0
        try:
            pages = float(pages)
        except (TypeError, ValueError):
            pages = 0
        # kalınlık sayfa sayısıyla doğru orantılı (67 s. ≈ 14 px, 300 s. ≈ 30 px, 670 s. ≈ 54 px); bilinmiyorsa 26
        w = max(12.0, min(64.0, 10 + pages * 0.065)) if pages else 26
        return w, 168 + (sd >> 4) % 40
    if ty == "article":
        return 14, 176 + (sd >> 4) % 18
    if ty == "series":
        return 30, 196
    if ty == "podcast":
        return 13, 150
    if ty == "game":
        return 17, 188                  # oyun kutusu: DVD'den biraz ince
    return 21, 196                      # film, belgesel: DVD kutusu


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _quad(p, pm, pts):
    """pm'yi dört köşeye (sol üst, sağ üst, sağ alt, sol alt) gererek çizer: perspektif."""
    w, h = pm.width() / pm.devicePixelRatio(), pm.height() / pm.devicePixelRatio()
    src = QPolygonF([QPointF(0, 0), QPointF(w, 0), QPointF(w, h), QPointF(0, h)])
    tr = QTransform()
    if QTransform.quadToQuad(src, QPolygonF(pts), tr):
        p.save()
        p.setTransform(tr, True)
        p.drawPixmap(QPointF(0, 0), pm)
        p.restore()


def _cover(m, w, h, radius=3):
    from .library import cover_pixmap
    return cover_pixmap(m, w, h, radius)


# ============================================================ raf
class Shelf(QWidget):
    clicked = pyqtSignal(object)
    menu = pyqtSignal(object, object)
    GAP, LIFT, PLANK, ROW_GAP, TOP = 3, 22, 14, 26, 30
    ROW_H = 212

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.rows = []                 # [[index, …], …]
        self.anim = {}                 # index → 0..1 (dışarı çıkma)
        self.hover = -1
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme.bind(self, lambda w: w.update())

    # ------------------------------------------------------------ düzen
    def set_items(self, items):
        self.items = list(items)
        self.anim = {}
        self.hover = -1
        self._layout()
        self.update()

    def resizeEvent(self, e):
        self._layout()
        super().resizeEvent(e)

    @staticmethod
    def face_w(m):
        _w, h = spine_size(m)
        return h * (0.62 if m.get("type") in ("book", "article") else 0.70 if m.get("type") != "podcast" else 0.9)

    def _layout(self):
        W = max(200, self.width())
        reserve = 150                  # sağda dışarı çıkan kapağa yer
        self.rows, row, x = [], [], 0.0
        for i, m in enumerate(self.items):
            w = spine_size(m)[0]
            if row and x + w > W - reserve:
                self.rows.append(row)
                row, x = [], 0.0
            row.append(i)
            x += w + self.GAP
        if row:
            self.rows.append(row)
        n = max(1, len(self.rows))
        self.setFixedHeight(int(n * (self.ROW_H + self.TOP + self.PLANK + self.ROW_GAP)))

    def _geom(self):
        """[(index, spine rect, kapak genişliği, k)] animasyonun şu anki hâline göre."""
        out = []
        for r, row in enumerate(self.rows):
            base = self.TOP + r * (self.ROW_H + self.TOP + self.PLANK + self.ROW_GAP) + self.ROW_H
            x = 2.0
            for i in row:
                m = self.items[i]
                w, h = spine_size(m)
                k = _ease(self.anim.get(i, 0.0))
                fw = self.face_w(m) * k
                sw = w * (1 - 0.25 * k)          # sırt dönerken incelir
                rect = QRectF(x, base - h - self.LIFT * k, sw, h)
                out.append((i, rect, fw, k))
                x += sw + fw + self.GAP + 4 * k
        return out

    # ------------------------------------------------------------ animasyon
    def _tick(self):
        moving = False
        for i in set(self.anim) | ({self.hover} if self.hover >= 0 else set()):
            target = 1.0 if i == self.hover else 0.0
            v = self.anim.get(i, 0.0)
            nv = v + (target - v) * 0.22
            if abs(target - nv) < 0.01:
                nv = target
            else:
                moving = True
            if nv == 0.0:
                self.anim.pop(i, None)
            else:
                self.anim[i] = nv
        if not moving:
            self.timer.stop()
        self.update()

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0 else Qt.CursorShape.ArrowCursor)
            if not self.timer.isActive():
                self.timer.start()

    def _at(self, pos):
        for i, r, fw, _k in self._geom():
            if r.adjusted(-1, -4, fw + 2, self.LIFT + 4).contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        self._set_hover(self._at(e.position()))

    def leaveEvent(self, e):
        self._set_hover(-1)

    def mouseReleaseEvent(self, e):
        i = self._at(e.position())
        if i < 0:
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.items[i])
        elif e.button() == Qt.MouseButton.RightButton:
            self.menu.emit(self.items[i], e.globalPosition().toPoint())

    # ------------------------------------------------------------ çizim
    def paintEvent(self, e):
        if not self.items:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        geom = self._geom()
        # raf tahtaları
        for r in range(len(self.rows)):
            y = self.TOP + r * (self.ROW_H + self.TOP + self.PLANK + self.ROW_GAP) + self.ROW_H
            plank = QRectF(0, y, self.width(), self.PLANK)
            g = QLinearGradient(0, y, 0, y + self.PLANK)
            top = qcolor("surface_hover")
            g.setColorAt(0, top)
            g.setColorAt(0.25, qcolor("track"))
            g.setColorAt(1, qcolor("track").darker(118))
            p.fillRect(plank, g)
            sh = QLinearGradient(0, y + self.PLANK, 0, y + self.PLANK + 10)
            sh.setColorAt(0, QColor(0, 0, 0, 90))
            sh.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(QRectF(0, y + self.PLANK, self.width(), 10), sh)
        # önce duranlar, en son dışarı çıkanlar (üstte görünsün)
        for i, r, fw, k in sorted(geom, key=lambda g: g[3]):
            self._draw_item(p, self.items[i], r, fw, k)
        p.end()

    def _draw_item(self, p, m, r, fw, k):
        ty = m.get("type")
        if k > 0.01:                     # gölge
            p.setPen(Qt.PenStyle.NoPen)
            g = QRadialGradient(QPointF(r.x() + (r.width() + fw) / 2, r.bottom() + self.LIFT * k), (r.width() + fw) / 2)
            g.setColorAt(0, QColor(0, 0, 0, int(80 * k)))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(g)
            p.drawEllipse(QPointF(r.x() + (r.width() + fw) / 2, r.bottom() + self.LIFT * k), (r.width() + fw) / 2, 5)
        if ty in DISC_TYPES:
            self._case_spine(p, m, r)
        else:
            self._book_spine(p, m, r)
        if fw > 2:                       # dönen kapak: sırtın sağında perspektifle
            persp = r.height() * 0.06 * k
            pts = [QPointF(r.right(), r.top()), QPointF(r.right() + fw, r.top() + persp),
                   QPointF(r.right() + fw, r.bottom() - persp), QPointF(r.right(), r.bottom())]
            pm = _cover(m, self.face_w(m), r.height(), 3)
            _quad(p, pm, pts)
            g = QLinearGradient(r.right(), 0, r.right() + fw, 0)      # sırta yakın gölge
            g.setColorAt(0, QColor(0, 0, 0, 110))
            g.setColorAt(0.35, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawPolygon(QPolygonF(pts))

    def _spine_text(self, p, m, r, fg, top_pad=10, bottom_pad=10):
        f = QFont(self.font())
        f.setPixelSize(11 if r.width() >= 16 else 9)
        f.setWeight(QFont.Weight.DemiBold)
        fm = QFontMetrics(f)
        room = int(r.height() - top_pad - bottom_pad)
        if r.width() < 10 or room < 20:
            return
        text = m.get("title") or "—"
        creator = m.get("creator") or ""
        if creator and fm.horizontalAdvance(text + "   " + creator) <= room and r.width() >= 22:
            text = text + "   " + creator
        p.save()
        p.translate(r.center().x(), r.top() + top_pad)
        p.rotate(90)
        p.setFont(f)
        p.setPen(fg)
        p.drawText(QRectF(0, -r.width() / 2, room, r.width()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   fm.elidedText(text, Qt.TextElideMode.ElideRight, room))
        p.restore()

    def _book_spine(self, p, m, r):
        c = base_color(m)
        g = QLinearGradient(r.left(), 0, r.right(), 0)        # silindir gibi: kenarlar koyu
        g.setColorAt(0, c.darker(150))
        g.setColorAt(0.3, c.lighter(112))
        g.setColorAt(0.7, c)
        g.setColorAt(1, c.darker(160))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 2.5, 2.5)
        fg = QColor("#f4f1ea") if _lum(c) < 140 else QColor("#1b1b1b")
        if m.get("type") == "book":                 # sırt bantları
            band = QColor(fg)
            band.setAlpha(70)
            p.fillRect(QRectF(r.x() + 1, r.top() + 8, r.width() - 2, 1.4), band)
            p.fillRect(QRectF(r.x() + 1, r.bottom() - 10, r.width() - 2, 1.4), band)
        self._spine_text(p, m, r, fg, 14, 14)

    def _case_spine(self, p, m, r):
        disc = m.get("type") == "podcast"
        body = QColor(28, 28, 30) if not disc else QColor(70, 74, 80, 200)
        g = QLinearGradient(r.left(), 0, r.right(), 0)
        g.setColorAt(0, body.darker(140))
        g.setColorAt(0.45, body.lighter(160))
        g.setColorAt(1, body.darker(150))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 2, 2)
        c = base_color(m)                            # üstte kapak renginde bant (DVD logosu yeri)
        band = QRectF(r.x() + 1.5, r.top() + 2, r.width() - 3, 22 if not disc else 14)
        p.setBrush(c.lighter(115))
        p.drawRoundedRect(band, 1.5, 1.5)
        hl = QColor(255, 255, 255, 40)               # plastik parlaması
        p.fillRect(QRectF(r.x() + r.width() * 0.3, r.top() + 2, 1.2, r.height() - 4), hl)
        self._spine_text(p, m, r, QColor("#ececec"), (26 if not disc else 18), 10)


# ============================================================ açılan görünüm
class MediaViewer(QWidget):
    """Pencerenin üstünü kaplayan katman. Kitap açılır / disk çıkar, yanında bilgiler."""

    def __init__(self, win, m):
        super().__init__(win)
        self.win, self.m = win, m
        self.kind = "disc" if m.get("type") in DISC_TYPES else "book"
        self.t = 0.0            # açılma 0..1
        self.closing = False
        self.spin = 0.0
        self.clock = QElapsedTimer()
        self.clock.start()
        self.last = 0
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        # düğmeler
        self.btns = QWidget(self)
        h = QHBoxLayout(self.btns)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        links = [v for v in ((m.get("link"),) + tuple((m.get("links") or {}).values())) if v]
        if links:
            b = button(t("lib_open_link"))
            b.clicked.connect(lambda: __import__("webbrowser").open(links[0]))
            h.addWidget(b)
        ed = button(t("edit"))
        ed.clicked.connect(self._edit)
        h.addWidget(ed)
        cl = button(t("lib_close"), kind="Primary")
        cl.clicked.connect(self.close_anim)
        h.addWidget(cl)
        self.btns.adjustSize()
        self.btns.hide()
        win.installEventFilter(self)
        self.setGeometry(win.rect())
        self.show()
        self.raise_()
        self.setFocus()
        self.timer.start()

    def eventFilter(self, obj, ev):
        if obj is self.win and ev.type() == QEvent.Type.Resize:
            self.setGeometry(self.win.rect())
        return False

    # ------------------------------------------------------------ yaşam döngüsü
    def _tick(self):
        now = self.clock.elapsed()
        dt = (now - self.last) / 1000.0 if self.last else 0.016
        self.last = now
        dur = 0.6 if self.kind == "book" else 0.75
        if self.closing:
            self.t = max(0.0, self.t - dt / 0.3)
            if self.t <= 0:
                self.timer.stop()
                self.win.removeEventFilter(self)
                self.hide()
                self.deleteLater()
                return
        else:
            self.t = min(1.0, self.t + dt / dur)
        if self.kind == "disc":
            self.spin = (self.spin + dt * (40 + 400 * (1 - _ease(self.t)))) % 360
        self.btns.setVisible(self.t >= 1.0 and not self.closing)
        if self.kind == "book" and self.t >= 1.0 and not self.closing:
            self.timer.stop()                 # kitap durunca çizim gerekmez (disk dönmeye devam eder)
        self.update()

    def close_anim(self):
        if not self.closing:
            self.closing = True
            self.btns.hide()
            self.last = 0
            self.timer.start()

    def _edit(self):
        from ..forms import edit_item
        m = self.m
        self.close_anim()
        QTimer.singleShot(320, lambda: edit_item(self.win, "media", self.win.store.get("media", m["id"]) or m))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.close_anim()
        else:
            super().keyPressEvent(e)

    def mouseReleaseEvent(self, e):
        if not self._content().contains(e.position()):
            self.close_anim()

    # ------------------------------------------------------------ geometri
    def _sizes(self):
        H = min(380.0, self.height() * 0.62)
        if self.kind == "book":
            return H * 0.68, H
        if self.m.get("type") == "podcast":
            return H * 0.9, H * 0.9
        return H * 0.7, H

    def _content(self):
        W, H = self._sizes()
        cx, cy = self.width() / 2, self.height() / 2
        if self.kind == "book":
            return QRectF(cx - W - 20, cy - H / 2 - 20, 2 * W + 40, H + 90)
        D = H * 0.92
        total = W + D * 0.2 + D / 2 + 30 + 360
        return QRectF(cx - total / 2 - 20, cy - H / 2 - 20, total + 40, H + 90)

    def _info_rect(self):
        """Bilgi metninin alanı (açılma bittiğindeki hâliyle); düğmeler bunun altına hizalanır."""
        W, H = self._sizes()
        top = self.height() / 2 - H / 2 - 10
        if self.kind == "book":
            spine = self.width() / 2
            return QRectF(spine + 26, top + 26, W - 48, H - 86)
        D = H * 0.92
        x0 = self._content().left() + 20
        dcx = x0 + W + D * 0.2
        return QRectF(dcx + D / 2 + 30, top + 6, self._content().right() - 20 - (dcx + D / 2 + 30), H - 56)

    def resizeEvent(self, e):
        self.btns.adjustSize()
        W, H = self._sizes()
        top = self.height() / 2 - H / 2 - 10
        r = self._info_rect()
        if self.kind == "book":
            self.btns.move(int(r.right() + 4 - self.btns.width()), int(top + H + 18))
        else:
            self.btns.move(int(r.left()), int(top + H - self.btns.height()))
        super().resizeEvent(e)

    # ------------------------------------------------------------ çizim
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        a = _ease(self.t)
        p.fillRect(self.rect(), QColor(0, 0, 0, int(215 * min(1.0, self.t * 1.6))))
        if self.kind == "book":
            self._paint_book(p, a)
        else:
            self._paint_disc(p, a)
        p.end()

    def _font(self, px, weight=QFont.Weight.Normal):
        f = QFont(self.font())
        f.setPixelSize(int(px))
        f.setWeight(weight)
        return f

    def _info(self, p, rect, fg, fg2, alpha):
        """Bilgi metni: başlık, yazar, tür · yıl · türler, durum, puan, ilerleme, tarihler, not."""
        m = self.m
        if alpha <= 0:
            return
        p.save()
        p.setOpacity(alpha)
        y = rect.top()
        f = self._font(22, QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(fg)
        r = p.boundingRect(QRectF(rect.left(), y, rect.width(), 200), Qt.TextFlag.TextWordWrap, m.get("title") or "—")
        p.drawText(QRectF(rect.left(), y, rect.width(), r.height()), Qt.TextFlag.TextWordWrap, m.get("title") or "—")
        y += r.height() + 4
        if m.get("creator"):
            p.setFont(self._font(14, QFont.Weight.DemiBold))
            p.setPen(fg2)
            p.drawText(QRectF(rect.left(), y, rect.width(), 20), Qt.AlignmentFlag.AlignLeft, m["creator"])
            y += 24
        meta = " · ".join(str(x) for x in (t("mt_" + (m.get("type") or "book")),
                                            int(m["year"]) if m.get("year") else None, m.get("genres")) if x)
        p.setFont(self._font(12))
        p.setPen(fg2)
        r = p.boundingRect(QRectF(rect.left(), y, rect.width(), 60), Qt.TextFlag.TextWordWrap, meta)
        p.drawText(QRectF(rect.left(), y, rect.width(), r.height()), Qt.TextFlag.TextWordWrap, meta)
        y += r.height() + 14
        # durum ve puan
        from .library import stars
        st = m.get("status") or "want"
        line = t("ms_" + st)
        sr = stars(m.get("rating"))
        p.setFont(self._font(13, QFont.Weight.DemiBold))
        p.setPen(fg)
        p.drawText(QRectF(rect.left(), y, rect.width(), 20), Qt.AlignmentFlag.AlignLeft,
                   line + (f"   {sr}" if sr else ""))
        y += 26
        prog = library.progress_text(m, t)
        if prog:
            p.setFont(self._font(12))
            p.setPen(fg2)
            p.drawText(QRectF(rect.left(), y, rect.width(), 18), Qt.AlignmentFlag.AlignLeft, prog)
            y += 20
            if m.get("total"):
                k = max(0.0, min(1.0, float(m.get("progress") or 0) / float(m["total"])))
                bar = QRectF(rect.left(), y, min(rect.width(), 260), 5)
                c = QColor(fg2)
                c.setAlpha(60)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(bar, 2.5, 2.5)
                p.setBrush(fg)
                p.drawRoundedRect(QRectF(bar.x(), bar.y(), max(5.0, bar.width() * k), 5), 2.5, 2.5)
                y += 16
        dates = " · ".join(f"{t(k)} {m[f]}" for f, k in (("started", "f_started"), ("finished", "f_finished"))
                           if m.get(f))
        if dates:
            p.setFont(self._font(12))
            p.setPen(fg2)
            p.drawText(QRectF(rect.left(), y, rect.width(), 18), Qt.AlignmentFlag.AlignLeft, dates)
            y += 24
        note = (m.get("note") or "").strip()
        if note and y < rect.bottom() - 30:
            p.setFont(self._font(13))
            p.setPen(fg)
            box = QRectF(rect.left(), y + 4, rect.width(), rect.bottom() - y - 4)
            fm = QFontMetrics(p.font())
            lines = max(1, int(box.height() // fm.lineSpacing()))
            words, out, cur = note.replace("\n", " \n ").split(" "), [], ""
            for w in words:
                if w == "\n":
                    out.append(cur)
                    cur = ""
                    continue
                trial = (cur + " " + w).strip()
                if fm.horizontalAdvance(trial) <= box.width():
                    cur = trial
                else:
                    out.append(cur)
                    cur = w
            out.append(cur)
            if len(out) > lines:
                out = out[:lines]
                out[-1] = fm.elidedText(out[-1] + " …", Qt.TextElideMode.ElideRight, int(box.width()))
            for i, ln in enumerate(out):
                p.drawText(QPointF(box.left(), box.top() + fm.ascent() + i * fm.lineSpacing()), ln)
        p.restore()

    def _paint_book(self, p, a):
        W, H = self._sizes()
        cx, cy = self.width() / 2, self.height() / 2
        top = cy - H / 2 - 10
        spine = cx - W / 2 * (1 - a)
        paper, ink, ink2 = QColor("#e9e4d8"), QColor("#1d1b18"), QColor("#5d574d")
        # gölge
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(QRectF(spine - W * a + 6, top + H - 2, W * (1 + a), 14), 7, 7)
        # sağ sayfa (bilgiler)
        right = QRectF(spine, top, W, H)
        g = QLinearGradient(right.left(), 0, right.right(), 0)
        g.setColorAt(0, paper.darker(118))
        g.setColorAt(0.06, paper)
        g.setColorAt(1, paper.darker(104))
        p.setBrush(g)
        p.drawRoundedRect(right, 3, 3)
        for i in range(1, 4):              # sayfa kenarları
            p.setPen(QPen(paper.darker(112 + i * 4), 1))
            p.drawLine(QPointF(right.right() - i * 1.6, top + 3 + i), QPointF(right.right() - i * 1.6, top + H - 3 - i))
        self._info(p, QRectF(spine + 26, top + 26, W - 48, H - 86), ink, ink2, max(0.0, (a - 0.55) / 0.45))
        # kapak: sırt çizgisi etrafında döner
        th = math.pi * a
        fx = spine + W * math.cos(th)
        lift = H * 0.07 * math.sin(th)
        pts = [QPointF(spine, top), QPointF(fx, top - lift), QPointF(fx, top + H + lift), QPointF(spine, top + H)]
        if math.cos(th) > 0:
            _quad(p, _cover(self.m, W, H, 3), pts)
            sh = QColor(0, 0, 0, int(140 * (1 - math.cos(th))))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(sh)
            p.drawPolygon(QPolygonF(pts))
        else:
            # kapağın içi = sol sayfa
            g = QLinearGradient(fx, 0, spine, 0)
            g.setColorAt(0, paper.darker(104))
            g.setColorAt(0.94, paper)
            g.setColorAt(1, paper.darker(120))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawPolygon(QPolygonF(pts))
            if a > 0.85:                   # sol sayfada küçük kapak ve tür
                op = (a - 0.85) / 0.15
                left = QRectF(spine - W, top, W, H)
                cw, ch = W * 0.62, W * 0.62 * 1.5
                if ch > H - 90:
                    ch = H - 90
                    cw = ch / 1.5
                p.save()
                p.setOpacity(op)
                p.drawPixmap(QPointF(left.center().x() - cw / 2, top + 34), _cover(self.m, cw, ch, 4))
                p.setFont(self._font(11, QFont.Weight.DemiBold))
                p.setPen(ink2)
                p.drawText(QRectF(left.x(), top + 44 + ch, W, 18), Qt.AlignmentFlag.AlignHCenter,
                           t("mt_" + (self.m.get("type") or "book")).upper())
                p.restore()
        # sırt kenarındaki kat yeri
        if a > 0.5:
            g = QLinearGradient(spine - 14, 0, spine + 14, 0)
            g.setColorAt(0, QColor(0, 0, 0, 0))
            g.setColorAt(0.5, QColor(0, 0, 0, 60))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(QRectF(spine - 14, top, 28, H), g)

    def _paint_disc(self, p, a):
        W, H = self._sizes()
        D = H * 0.92
        c = self._content()
        x0 = c.left() + 20
        top = self.height() / 2 - H / 2 - 10
        # disk: kapağın arkasından sağa kayar
        dcx = x0 + W / 2 + (W / 2 + D * 0.2) * a
        dcy = top + H / 2
        self._disc(p, QPointF(dcx, dcy), D / 2)
        # kutu / kapak
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawRoundedRect(QRectF(x0 + 6, top + H - 2, W, 14), 7, 7)
        case = QRectF(x0 - 4, top - 4, W + 8, H + 8)
        p.setBrush(QColor(20, 20, 22))
        p.drawRoundedRect(case, 6, 6)
        p.drawPixmap(QPointF(x0, top), _cover(self.m, W, H, 3))
        g = QLinearGradient(x0, top, x0 + W, top + H)       # plastik parlaması
        g.setColorAt(0, QColor(255, 255, 255, 40))
        g.setColorAt(0.4, QColor(255, 255, 255, 0))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(x0, top, W, H), 3, 3)
        self._info(p, self._info_rect(), QColor("#f1f1f1"), QColor("#b4b4b4"), max(0.0, (a - 0.5) / 0.5))

    def _disc(self, p, c, R):
        p.save()
        p.translate(c)
        p.rotate(self.spin)
        ring = QPainterPath()
        ring.addEllipse(QPointF(0, 0), R, R)
        hole = QPainterPath()
        hole.addEllipse(QPointF(0, 0), R * 0.085, R * 0.085)
        disc = ring.subtracted(hole)
        p.setPen(Qt.PenStyle.NoPen)
        g = QRadialGradient(QPointF(0, 0), R)
        g.setColorAt(0, QColor("#d7dbe0"))
        g.setColorAt(0.6, QColor("#b8bec6"))
        g.setColorAt(1, QColor("#8e959e"))
        p.setBrush(g)
        p.drawPath(disc)
        # baskı: kapak görseli diskin yüzünde
        label = QPainterPath()
        label.addEllipse(QPointF(0, 0), R * 0.96, R * 0.96)
        inner = QPainterPath()
        inner.addEllipse(QPointF(0, 0), R * 0.30, R * 0.30)
        p.setClipPath(label.subtracted(inner))
        pm = _cover(self.m, 2 * R, 2 * R, 0)
        p.setOpacity(0.92)
        p.drawPixmap(QPointF(-R, -R), pm)
        p.setOpacity(1.0)
        p.setClipping(False)
        # gökkuşağı yansıması
        cg = QConicalGradient(QPointF(0, 0), 0)
        for pos, col in ((0, (255, 255, 255, 0)), (0.12, (180, 220, 255, 70)), (0.25, (255, 255, 255, 0)),
                         (0.5, (255, 255, 255, 0)), (0.62, (255, 210, 170, 60)), (0.75, (255, 255, 255, 0)),
                         (1, (255, 255, 255, 0))):
            cg.setColorAt(pos, QColor(*col))
        p.setBrush(cg)
        p.drawPath(disc)
        # orta halka
        hub = QPainterPath()
        hub.addEllipse(QPointF(0, 0), R * 0.30, R * 0.30)
        p.setBrush(QColor(225, 228, 232, 235))
        p.drawPath(hub.subtracted(hole))
        p.setPen(QPen(QColor(150, 155, 162), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), R * 0.18, R * 0.18)
        p.drawEllipse(QPointF(0, 0), R - 0.5, R - 0.5)
        p.restore()


def open_viewer(win, m):
    old = getattr(win, "_media_viewer", None)
    if old is not None:
        try:
            old.deleteLater()
        except RuntimeError:
            pass
    win._media_viewer = MediaViewer(win, m)
    return win._media_viewer
