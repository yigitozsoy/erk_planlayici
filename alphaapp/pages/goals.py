"""Hayat hedefleri: iki görünüm.

  vision board    Pinterest tarzı pano: farklı boyda kartlar sütunlara akar (masonry). Görsel yoksa başlık büyük
                  yazılır (alıntı kartı). Görsel: sürükle-bırak ya da kopyala → Ctrl+V (kartın üstündeyken o karta).
  çark + yol      aylık hayat çarkı (1-10) ve hayat → 10 yıl → 3 yıl → bu yıl → bu dönem yol haritası

Hedefler ağaç (parent) + alışkanlık / ders / proje bağlantıları; etkinlik = son 30 gündeki etkin gün
(store.goal_activity).
"""
import os
import random
import uuid
import zlib
from datetime import timedelta

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import (QPainter, QPen, QColor, QFont, QFontMetrics, QLinearGradient, QPainterPath, QPixmap,
                         QImageReader, QKeySequence, QGuiApplication)
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from .. import icons
from ..config import day_today, prefs, IMAGES_DIR
from ..components import Page, Card, ChipBar, Row
from ..forms import edit_item, bind_row, GOAL_HORIZONS, AREA_ICONS
from ..i18n import t, fmt_day
from ..store import LIFE_AREAS, parse_date, life_area
from ..theme import theme, qcolor, GOOD, BAD, WARN

# alan renkleri: gri vurgulu arayüzde yalnızca küçük noktalar / ince tonlar (mor yok)
AREA_COLOR = {"education": "#7f9cb0", "career": "#c8a35b", "venture": "#d08a4e", "body": "#86a878",
              "mind": "#6fa3a0", "finance": "#d9c8a0", "growth": "#a8a8a8"}
VIEWS = ("board", "wheel")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")


def area_color(a):
    return QColor(AREA_COLOR[life_area(a)])


def area_icon(a):
    return AREA_ICONS[life_area(a)]


def area_name(a):
    return t("area_" + life_area(a))


def mix(a, b, k):
    """a → b arasında k (0-1) oranında karışım."""
    k = max(0.0, min(1.0, k))
    return QColor(int(a.red() + (b.red() - a.red()) * k), int(a.green() + (b.green() - a.green()) * k),
                  int(a.blue() + (b.blue() - a.blue()) * k), int(a.alpha() + (b.alpha() - a.alpha()) * k))


def with_alpha(c, a):
    c = QColor(c)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


def heat(n):
    """30 günde n etkin gün → 0-1 (12 gün ve üstü tam)."""
    return max(0.0, min(1.0, n / 12.0))


def _font(px, bold=False, family=None):
    f = QFont(family) if family else QFont()
    f.setPixelSize(px)
    if bold:
        f.setWeight(QFont.Weight.DemiBold)
    return f


# ============================================================ örnek veri
SAMPLE = [
    ("Ortalama 3.0+", "education", "year", ["Derslere düzenli gir", "Haftalık tekrar", "Vize takvimi", "Soru çözümü",
                                            "Ders notlarını temize çek", "Hocaya soru sor", "Final planı",
                                            "Çalışma grubu"]),
    ("İngilizce C1 · Almanca B1", "education", "y3", ["Günde 20 dk İngilizce dinleme", "Haftada 1 makale",
                                                      "IELTS denemesi", "Almanca kursu", "Duolingo serisi",
                                                      "Kelime defteri"]),
    ("CAD ve yazılım", "education", "y3", ["SolidWorks sertifikası", "Python ile hesap", "MATLAB",
                                           "Ansys temelleri", "GitHub'a yükle"]),
    ("Staj ve bağlantılar", "career", "year", ["CV'yi güncelle", "LinkedIn profili", "5 firmaya başvur",
                                               "Mülakat provası", "Aday mühendislik programları",
                                               "Ayda 2 yeni bağlantı", "Kariyer fuarı"]),
    ("Kendi işim", "venture", "y3", ["Fikir defteri", "Pazar araştırması", "İlk prototip", "İş planı taslağı",
                                     "Girişimcilik kulübü", "Mentor bul"]),
    ("Sağlıklı beden", "body", "y3", ["Haftada 4 gün spor", "Günde 140 g protein", "Günde 2 L su", "5 km koşu",
                                      "Esneme"]),
    ("Zihinsel denge", "mind", "year", ["7 saat uyku", "10 dk meditasyon", "Telefon < 2 saat", "Haftalık değerlendirme",
                                       "Doğada yürüyüş"]),
    ("Finansal düzen", "finance", "year", ["Aylık bütçe", "Gelirin %20'si birikim", "Acil durum fonu", "Borçsuz ol",
                                           "Yatırımı öğren"]),
    ("Kişisel gelişim", "growth", "year", ["Her sabah plan", "Ayda 1 kitap", "Yeni bir hobi", "Günlük yaz",
                                           "Yılda 1 yeni şehir"]),
]


def add_sample(store):
    """Bakıp karar vermek için örnek hedef ağacı (sample=True; "Örnekleri sil" hepsini kaldırır).
    Eğitim sütununun eylemleri gerçek derslere, sütunlar aynı alandaki alışkanlıklara bağlanır."""
    rng = random.Random(7)
    td = day_today()
    root = store.add("goals", {"title": "Güçlü bir mühendis, dengeli bir hayat", "area": "growth",
                               "horizon": "life", "due": f"{td.year + 8}-06-30", "sample": True, "order": 0})
    courses = sorted(store.all("courses"), key=lambda c: c.get("name") or "")
    for i, (title, area, hz, acts) in enumerate(SAMPLE):
        links = [f"habits:{h['id']}" for h in store.all("habits") if life_area(h.get("category")) == area]
        p = store.add("goals", {"title": title, "area": area, "horizon": hz, "parent": root["id"], "order": i,
                                "links": links, "sample": True,
                                "due": f"{td.year + (3 if hz == 'y3' else 1)}-06-30"})
        if area == "education" and i == 0 and courses:
            acts = [c.get("name") or "—" for c in courses[:6]] + acts[:2]
        for j, a in enumerate(acts[:8]):
            n = rng.choice((0, 0, 1, 3, 5, 8, 12))
            days = sorted({(td - timedelta(days=rng.randrange(30))).isoformat() for _ in range(n)})
            g = {"title": a, "area": area, "horizon": "action", "parent": p["id"], "order": j, "days": days,
                 "sample": True, "done": rng.random() < 0.12}
            if area == "education" and i == 0 and j < len(courses[:6]):
                g["links"] = [f"courses:{courses[j]['id']}"]
                g["days"] = []
            store.add("goals", g)


def remove_sample(store):
    removed = []
    for coll in ("goals", "wheel"):
        for x in [x for x in store.all(coll) if x.get("sample")]:
            if store.get(coll, x["id"]) is not None:
                removed += store.delete(coll, x["id"])
    return removed


def theme_dark():
    from ..theme import is_dark
    return is_dark()


# ============================================================ görseller
def save_image(path=None, image=None):
    """Dosyayı ya da QImage'ı IMAGES_DIR'e kopyalar; dosya adını (ya da None) döndürür."""
    import shutil
    os.makedirs(IMAGES_DIR, exist_ok=True)
    try:
        if path:
            ext = os.path.splitext(path)[1].lower()
            if ext not in IMAGE_EXT or not os.path.isfile(path):
                return None
            name = uuid.uuid4().hex[:12] + ext
            shutil.copy2(path, os.path.join(IMAGES_DIR, name))
            return name
        if image is not None and not image.isNull():
            name = uuid.uuid4().hex[:12] + ".png"
            return name if image.save(os.path.join(IMAGES_DIR, name), "PNG") else None
    except OSError:
        return None
    return None


def image_from_mime(md):
    """Pano / sürükleme verisinden görsel: yerel görsel dosyası ya da doğrudan resim verisi."""
    if md is None:
        return None
    if md.hasUrls():
        for u in md.urls():
            if u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_EXT:
                return save_image(path=u.toLocalFile())
    if md.hasImage():
        from PyQt6.QtGui import QImage
        img = md.imageData()
        if isinstance(img, QImage):
            return save_image(image=img)
        if isinstance(img, QPixmap):
            return save_image(image=img.toImage())
    return None


def mime_has_image(md):
    if md.hasImage():
        return True
    return md.hasUrls() and any(u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_EXT
                                for u in md.urls())


# ============================================================ vision board (Pinterest tarzı)
class BoardView(QWidget):
    """Masonry pano: her kart en kısa sütuna eklenir. Görselin oranı kart boyunu belirler; görsel yoksa
    hedefin adı büyük yazılan, alan renginde bir "alıntı kartı" çizilir. İlk kutu: + yeni pin."""
    goal_clicked = pyqtSignal(object)
    add_requested = pyqtSignal()
    image_in = pyqtSignal(object, str)      # (hedef ya da None, görsel dosya adı)

    GAP = 16
    COL = 236
    RADIUS = 16
    CAPTION = 50
    PLACEHOLDER = (1.25, 0.95, 1.5, 1.1, 1.35, 0.85)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.goals, self.tiles = [], []
        self.heat, self.prog = {}, {}
        self._hover = None
        self._drop_hover = False
        self._pix, self._ratio = {}, {}
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(200)
        theme.bind(self, lambda w: w.update())

    def set_goals(self, goals, heat, prog):
        self.goals, self.heat, self.prog = goals, heat, prog
        self._layout()
        self.update()

    def resizeEvent(self, e):
        self._layout()
        super().resizeEvent(e)

    # ---------------------------------------------------------- yerleşim
    def _img_path(self, g):
        return os.path.join(IMAGES_DIR, g["image"]) if g.get("image") else None

    def has_image(self, g):
        path = self._img_path(g)
        if not path:
            return False
        self.ratio(g)
        return bool(self._ratio.get(path))

    def ratio(self, g):
        """Kartın görsel kısmının yüksekliği / genişliği."""
        path = self._img_path(g)
        if path:
            r = self._ratio.get(path)
            if r is None:
                sz = QImageReader(path).size()
                r = sz.height() / sz.width() if sz.isValid() and sz.width() > 0 else 0
                self._ratio[path] = r
            if r:
                return max(0.6, min(1.8, r))
        return self.PLACEHOLDER[zlib.crc32(g["id"].encode()) % len(self.PLACEHOLDER)]

    def _layout(self):
        w = max(300, self.width())
        cols = max(2, min(6, int((w + self.GAP) // (self.COL + self.GAP))))
        cw = (w - (cols - 1) * self.GAP) / cols
        heights = [0.0] * cols
        self.tiles = []
        for g in [None] + list(self.goals):
            c = min(range(cols), key=lambda i: heights[i])
            x, y = c * (cw + self.GAP), heights[c]
            if g is None:
                img = QRectF(x, y, cw, cw * 0.62)
                full = QRectF(img)
            else:
                img = QRectF(x, y, cw, cw * self.ratio(g))
                cap = self.CAPTION if self.has_image(g) else self.CAPTION - 20     # görselsizde başlık kartın içinde
                full = QRectF(x, y, cw, img.height() + cap)
            self.tiles.append((img, full, g))
            heights[c] = full.bottom() + self.GAP
        hgt = int(max(heights) - self.GAP) if self.tiles else 200
        if self.height() != hgt:
            self.setFixedHeight(max(200, hgt))

    def _pixmap(self, path, w, h):
        key = (path, int(w), int(h))
        pm = self._pix.get(key)
        if pm is None:
            src = QPixmap(path)
            if src.isNull():
                pm = QPixmap()
            else:
                dpr = self.devicePixelRatioF()
                pm = src.scaled(int(w * dpr), int(h * dpr), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation)
                pm.setDevicePixelRatio(dpr)
            if len(self._pix) > 120:
                self._pix.clear()
            self._pix[key] = pm
        return pm

    # ---------------------------------------------------------- fare / klavye / bırakma
    def _tile_at(self, pos):
        for i, (_img, full, _g) in enumerate(self.tiles):
            if full.contains(QPointF(pos)):
                return i
        return None

    def hovered_goal(self):
        return self.tiles[self._hover][2] if self._hover is not None and self._hover < len(self.tiles) else None

    def enterEvent(self, e):
        self.setFocus(Qt.FocusReason.MouseFocusReason)     # Ctrl+V doğrudan panoya gelsin
        super().enterEvent(e)

    def mouseMoveEvent(self, e):
        h = self._tile_at(e.position())
        if h != self._hover:
            self._hover = h
            self.setCursor(Qt.CursorShape.PointingHandCursor if h is not None else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._hover = None
        self.update()

    def mouseReleaseEvent(self, e):
        i = self._tile_at(e.position())
        if i is None or e.button() != Qt.MouseButton.LeftButton:
            return
        g = self.tiles[i][2]
        if g is None:
            self.add_requested.emit()
        else:
            self.goal_clicked.emit(g)

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.StandardKey.Paste):
            self.paste()
            return
        super().keyPressEvent(e)

    def paste(self):
        name = image_from_mime(QGuiApplication.clipboard().mimeData())
        if name:
            self.image_in.emit(self.hovered_goal(), name)
        return name

    def dragEnterEvent(self, e):
        if mime_has_image(e.mimeData()):
            e.acceptProposedAction()
            self._drop_hover = True
            self.update()

    def dragMoveEvent(self, e):
        h = self._tile_at(e.position())
        if h != self._hover:
            self._hover = h
            self.update()
        e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._drop_hover = False
        self._hover = None
        self.update()

    def dropEvent(self, e):
        self._drop_hover = False
        g = self.tiles[self._hover][2] if self._hover is not None else None
        name = image_from_mime(e.mimeData())
        self._hover = None
        self.update()
        if name:
            e.acceptProposedAction()
            self.image_in.emit(g, name)

    # ---------------------------------------------------------- çizim
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        text, text2, card = qcolor("text"), qcolor("text2"), qcolor("card")
        vis = e.rect()
        for i, (img, full, g) in enumerate(self.tiles):
            if not QRectF(vis).intersects(full):
                continue
            hover = i == self._hover
            path = QPainterPath()
            path.addRoundedRect(img, self.RADIUS, self.RADIUS)
            if g is None:
                p.setPen(QPen(qcolor("divider") if not self._drop_hover else text, 1.4, Qt.PenStyle.DashLine))
                p.setBrush(qcolor("hover") if hover or self._drop_hover else qcolor("card"))
                p.drawPath(path)
                cy = img.center().y()
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qcolor("surface"))
                p.drawEllipse(QPointF(img.center().x(), cy - 26), 20, 20)
                p.setPen(QPen(text, 2))
                p.drawLine(QPointF(img.center().x() - 7, cy - 26), QPointF(img.center().x() + 7, cy - 26))
                p.drawLine(QPointF(img.center().x(), cy - 33), QPointF(img.center().x(), cy - 19))
                p.setPen(text)
                p.setFont(_font(13, True))
                p.drawText(QRectF(img.x(), cy + 4, img.width(), 20), int(Qt.AlignmentFlag.AlignCenter), t("pin_add"))
                p.setFont(_font(11))
                p.setPen(text2)
                p.drawText(QRectF(img.x() + 14, cy + 26, img.width() - 28, 34), int(
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap),
                    t("pin_add_sub"))
                continue
            ac = area_color(g.get("area"))
            path_img = self._img_path(g)
            pm = self._pixmap(path_img, img.width(), img.height()) if path_img else QPixmap()
            p.save()
            p.setClipPath(path)
            has_img = not pm.isNull()
            if has_img:
                sw, sh = pm.width() / pm.devicePixelRatio(), pm.height() / pm.devicePixelRatio()
                p.drawPixmap(QPointF(img.x() - (sw - img.width()) / 2, img.y() - (sh - img.height()) / 2), pm)
            else:
                lg = QLinearGradient(img.topLeft(), img.bottomRight())
                lg.setColorAt(0, mix(card, ac, 0.42))
                lg.setColorAt(1, mix(card, ac, 0.14))
                p.fillRect(img, lg)
                ic = icons.pixmap(area_icon(g.get("area")), text.name(), 20)
                p.setOpacity(0.55)
                p.drawPixmap(QPointF(img.x() + 16, img.y() + 16), ic)
                p.setOpacity(1.0)
                self._quote(p, img, g.get("title") or "", text)
            if hover:
                p.fillRect(img, QColor(0, 0, 0, 70))
            p.restore()
            pr = self.prog.get(g["id"], 0.0)
            if hover:                            # Pinterest'teki gibi üstte düğme, altta ilerleme
                p.setFont(_font(12, True))
                lbl = t("edit")
                bw = QFontMetrics(p.font()).horizontalAdvance(lbl) + 28
                b = QRectF(img.right() - bw - 10, img.top() + 10, bw, 32)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#f1f1f1"))
                p.drawRoundedRect(b, 16, 16)
                p.setPen(QColor("#0f0f0f"))
                p.drawText(b, int(Qt.AlignmentFlag.AlignCenter), lbl)
                chip = f"%{int(round(pr * 100))}"
                cb = QRectF(img.left() + 10, img.bottom() - 34, QFontMetrics(p.font()).horizontalAdvance(chip) + 20, 24)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(255, 255, 255, 225))
                p.drawRoundedRect(cb, 12, 12)
                p.setPen(QColor("#0f0f0f"))
                p.drawText(cb, int(Qt.AlignmentFlag.AlignCenter), chip)
            if g.get("done"):
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.setBrush(QColor("#2ba640"))
                p.drawEllipse(QPointF(img.left() + 22, img.top() + 22), 9, 9)
            # alt yazı
            cap = QRectF(full.x() + 4, img.bottom() + 8, full.width() - 8, self.CAPTION - 10)
            if has_img:
                fm_t = QFontMetrics(_font(13, True))
                p.setFont(_font(13, True))
                p.setPen(text)
                p.drawText(QRectF(cap.x(), cap.y(), cap.width(), 18), int(Qt.AlignmentFlag.AlignVCenter),
                           fm_t.elidedText(g.get("title") or "", Qt.TextElideMode.ElideRight, int(cap.width())))
            else:
                cap.translate(0, -20)
            n = self.heat.get(g["id"], (0, 0))[1]
            due = (g.get("due") or "")[:4]
            meta = " · ".join(x for x in (t("hz_" + (g.get("horizon") or "year")), f"→ {due}" if due else "",
                                          f"%{int(round(pr * 100))}", t("goal_days_30", n=n) if n else "") if x)
            p.setFont(_font(11))
            p.setPen(text2)
            p.setBrush(ac)
            p.drawText(QRectF(cap.x() + 12, cap.y() + 20, cap.width() - 12, 16), int(Qt.AlignmentFlag.AlignVCenter),
                       QFontMetrics(p.font()).elidedText(meta, Qt.TextElideMode.ElideRight, int(cap.width() - 12)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cap.x() + 4, cap.y() + 28), 3.5, 3.5)
        p.end()

    @staticmethod
    def _quote(p, r, txt, color):
        """Görselsiz kart: başlık ortada, büyük serif yazı."""
        box = r.adjusted(18, 44, -18, -22)
        flags = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap)
        for px in (30, 26, 23, 20, 18, 16, 14):
            f = _font(px, False, "Georgia")
            br = QFontMetrics(f).boundingRect(box.toRect(), flags, txt)
            if br.height() <= box.height():
                break
        p.setFont(f)
        p.setPen(color)
        p.drawText(box, flags, txt)


# ============================================================ denge: alan kartları
class BalanceView(QWidget):
    """7 alan kartı + özet kartı. Puanlar balance.area_report'tan (verilerden) gelir; çizgi son 6 ay."""
    area_clicked = pyqtSignal(str)
    add_for = pyqtSignal(str)

    GAP = 12
    H = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.report, self.hist, self.rects = {}, {}, []
        self._hover = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme.bind(self, lambda w: w.update())

    def set_data(self, report, hist):
        self.report, self.hist = report, hist
        self._layout()
        self.update()

    def resizeEvent(self, e):
        self._layout()
        super().resizeEvent(e)

    def keys(self):
        return list(LIFE_AREAS) + ["_sum"]

    def _layout(self):
        w = max(300, self.width())
        cols = 4 if w >= 1000 else 3 if w >= 720 else 2 if w >= 440 else 1
        cw = (w - (cols - 1) * self.GAP) / cols
        self.rects = []
        for i, k in enumerate(self.keys()):
            r, c = divmod(i, cols)
            self.rects.append((QRectF(c * (cw + self.GAP), r * (self.H + self.GAP), cw, self.H), k))
        rows = (len(self.rects) + cols - 1) // cols
        h = int(rows * self.H + (rows - 1) * self.GAP)
        if self.height() != h:
            self.setFixedHeight(h)

    def scored(self):
        return [(a, self.report[a]["score"]) for a in LIFE_AREAS if self.report.get(a, {}).get("score") is not None]

    def weakest(self):
        sc = self.scored()
        return min(sc, key=lambda x: x[1])[0] if sc else LIFE_AREAS[0]

    def _at(self, pos):
        for i, (r, _k) in enumerate(self.rects):
            if r.contains(QPointF(pos)):
                return i
        return None

    def mouseMoveEvent(self, e):
        h = self._at(e.position())
        if h != self._hover:
            self._hover = h
            self.setCursor(Qt.CursorShape.PointingHandCursor if h is not None else Qt.CursorShape.ArrowCursor)
            k = self.rects[h][1] if h is not None else None
            if k and k != "_sum":
                ps = self.report.get(k, {}).get("parts") or []
                self.setToolTip("\n".join(s for s, _f in ps) or t("bal_no_data_hint"))
            else:
                self.setToolTip("")
            self.update()

    def leaveEvent(self, e):
        self._hover = None
        self.update()

    def mouseReleaseEvent(self, e):
        i = self._at(e.position())
        if i is None or e.button() != Qt.MouseButton.LeftButton:
            return
        k = self.rects[i][1]
        if k == "_sum":
            self.add_for.emit(self.weakest())
        elif self.report.get(k, {}).get("score") is None:
            self.add_for.emit(k)
        else:
            self.area_clicked.emit(k)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, (r, k) in enumerate(self.rects):
            hover = i == self._hover
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor("card_hover") if hover else qcolor("card"))
            p.drawRoundedRect(r, 12, 12)
            if k == "_sum":
                self._paint_sum(p, r, hover)
            else:
                self._paint_area(p, r, k)
        p.end()

    @staticmethod
    def _num(v):
        return f"{v:.1f}".replace(".", ",")

    def _paint_area(self, p, r, k):
        text, text2, text3 = qcolor("text"), qcolor("text2"), qcolor("text3")
        rep = self.report.get(k, {})
        score, parts = rep.get("score"), rep.get("parts") or []
        hist = self.hist.get(k) or []
        x0, y0 = r.x() + 16, r.y() + 14
        # başlık
        ic = icons.pixmap(area_icon(k), text2.name(), 18)
        p.drawPixmap(QPointF(x0, y0 + 1), ic)
        p.setFont(_font(13, True))
        p.setPen(text)
        p.drawText(QRectF(x0 + 26, y0, r.width() - 120, 20), int(Qt.AlignmentFlag.AlignVCenter), area_name(k))
        # değişim
        prev = hist[-2] if len(hist) >= 2 else None
        if score is not None and prev is not None:
            d = score - prev
            if abs(d) >= 0.1:
                txt = ("↑ " if d > 0 else "↓ ") + self._num(abs(d))
                col = QColor(GOOD if d > 0 else BAD)
            else:
                txt, col = "=", text3
            p.setFont(_font(11, True))
            fm = p.fontMetrics()
            cw = fm.horizontalAdvance(txt) + 16
            chip = QRectF(r.right() - 16 - cw, y0, cw, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(with_alpha(col, 0.16))
            p.drawRoundedRect(chip, 10, 10)
            p.setPen(col)
            p.drawText(chip, int(Qt.AlignmentFlag.AlignCenter), txt)
        # puan
        sy = y0 + 30
        if score is None:
            p.setFont(_font(28, True))
            p.setPen(text3)
            p.drawText(QRectF(x0, sy, 120, 40), int(Qt.AlignmentFlag.AlignVCenter), "—")
            p.setFont(_font(12))
            p.setPen(text2)
            p.drawText(QRectF(x0, sy + 50, r.width() - 32, 60),
                       int(Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                       t("bal_no_data") + "\n" + t("bal_no_data_hint"))
            return
        p.setFont(_font(34, True))
        p.setPen(text)
        big = self._num(score)
        fm = p.fontMetrics()
        bw = fm.horizontalAdvance(big)
        p.drawText(QRectF(x0, sy, bw + 4, 42), int(Qt.AlignmentFlag.AlignVCenter), big)
        p.setFont(_font(13))
        p.setPen(text3)
        p.drawText(QRectF(x0 + bw + 4, sy + 8, 40, 30), int(Qt.AlignmentFlag.AlignVCenter), "/10")
        # 6 aylık çizgi
        sx0, sx1 = x0 + bw + 52, r.right() - 16
        spark = QRectF(sx0, sy + 4, max(30.0, sx1 - sx0), 34)
        pts = [(i, v) for i, v in enumerate(hist) if v is not None]
        if len(pts) >= 2 and spark.width() > 40:
            n = max(1, len(hist) - 1)
            xy = [QPointF(spark.x() + spark.width() * i / n, spark.bottom() - spark.height() * v / 10) for i, v in pts]
            path = QPainterPath(xy[0])
            for q in xy[1:]:
                path.lineTo(q)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(with_alpha(text2, 0.9), 1.6))
            p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(text3)
            for q in xy[:-1]:
                p.drawEllipse(q, 2, 2)
            p.setBrush(text)
            p.drawEllipse(xy[-1], 3.5, 3.5)
        # çubuk
        by = sy + 50
        bar = QRectF(x0, by, r.width() - 32, 4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor("track"))
        p.drawRoundedRect(bar, 2, 2)
        p.setBrush(area_color(k))
        p.drawRoundedRect(QRectF(bar.x(), bar.y(), bar.width() * score / 10, 4), 2, 2)
        # nereden geldi
        p.setFont(_font(11))
        fm = p.fontMetrics()
        ly = by + 14
        for s, f in parts[:3]:
            col = QColor(GOOD) if f >= 0.7 else QColor(WARN) if f >= 0.4 else QColor(BAD)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawEllipse(QPointF(x0 + 3, ly + 8), 3, 3)
            p.setPen(text2)
            p.drawText(QRectF(x0 + 12, ly, r.width() - 44, 16), int(Qt.AlignmentFlag.AlignVCenter),
                       fm.elidedText(s, Qt.TextElideMode.ElideRight, int(r.width() - 44)))
            ly += 18

    def _paint_sum(self, p, r, hover):
        text, text2, text3 = qcolor("text"), qcolor("text2"), qcolor("text3")
        x0, y0 = r.x() + 16, r.y() + 14
        p.setFont(_font(13, True))
        p.setPen(text)
        p.drawText(QRectF(x0, y0, r.width() - 32, 20), int(Qt.AlignmentFlag.AlignVCenter), t("bal_title"))
        sc = self.scored()
        if not sc:
            p.setFont(_font(12))
            p.setPen(text2)
            p.drawText(QRectF(x0, y0 + 30, r.width() - 32, 80), int(Qt.TextFlag.TextWordWrap), t("bal_no_data_hint"))
            return
        avg = sum(v for _a, v in sc) / len(sc)
        p.setFont(_font(34, True))
        big = self._num(avg)
        bw = p.fontMetrics().horizontalAdvance(big)
        p.drawText(QRectF(x0, y0 + 30, bw + 4, 42), int(Qt.AlignmentFlag.AlignVCenter), big)
        p.setFont(_font(13))
        p.setPen(text3)
        p.drawText(QRectF(x0 + bw + 4, y0 + 38, 120, 30), int(Qt.AlignmentFlag.AlignVCenter),
                   "/10 · " + t("bal_avg").lower())
        best = max(sc, key=lambda x: x[1])
        worst = min(sc, key=lambda x: x[1])
        p.setFont(_font(12))
        p.setPen(text2)
        p.drawText(QRectF(x0, y0 + 80, r.width() - 32, 18), int(Qt.AlignmentFlag.AlignVCenter),
                   t("bal_best", a=area_name(best[0]), v=self._num(best[1])))
        p.drawText(QRectF(x0, y0 + 100, r.width() - 32, 18), int(Qt.AlignmentFlag.AlignVCenter),
                   t("bal_worst", a=area_name(worst[0]), v=self._num(worst[1])))
        lbl = t("bal_add_weak", a=area_name(worst[0]))
        p.setFont(_font(12, True))
        bw = p.fontMetrics().horizontalAdvance(lbl) + 28
        b = QRectF(x0, r.bottom() - 46, min(bw, r.width() - 32), 32)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor("button_bg") if hover else qcolor("surface"))
        p.drawRoundedRect(b, 16, 16)
        p.setPen(qcolor("button_fg") if hover else text)
        p.drawText(b, int(Qt.AlignmentFlag.AlignCenter), lbl)


# ============================================================ sayfa
class GoalsPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_goals"), t("goals_sub"))
        self.sample_btn = self.action(t("goals_sample_del"), self._remove_sample, icon="delete")
        self.action(t("add_goal"), lambda: edit_item(win, "goals", preset=self._new_preset()), primary=True, icon="add")
        view = prefs.get("goals_view", "board")
        self.view = view if view in VIEWS else "board"
        self.area = "all"
        self.tabs = ChipBar([(v, t("gv_" + v)) for v in VIEWS], self.view)
        self.tabs.changed.connect(self._set_view)
        self.add(self.tabs)

        # boş durum
        self.c_empty = Card(t("goals_empty_title"))
        lbl = QLabel(t("goals_empty"))
        lbl.setObjectName("RowSub")
        lbl.setWordWrap(True)
        self.c_empty.add(lbl)
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 12, 0, 4)
        bl.setSpacing(8)
        b1 = QPushButton(t("goals_sample"))
        b1.setObjectName("Primary")
        b1.setCursor(Qt.CursorShape.PointingHandCursor)
        b1.clicked.connect(self._add_sample)
        b2 = QPushButton(t("add_goal"))
        b2.setObjectName("Pill")
        b2.setCursor(Qt.CursorShape.PointingHandCursor)
        b2.clicked.connect(lambda: edit_item(win, "goals", preset={"horizon": "life"}))
        bl.addWidget(b1)
        bl.addWidget(b2)
        bl.addStretch(1)
        self.c_empty.add(bar)
        self.add(self.c_empty)

        # vision board
        self.board_host = QWidget()
        bv = QVBoxLayout(self.board_host)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(14)
        self.filter_host = QWidget()
        self.filter_lay = QHBoxLayout(self.filter_host)
        self.filter_lay.setContentsMargins(0, 0, 0, 0)
        bv.addWidget(self.filter_host)
        self.board = BoardView()
        self.board.goal_clicked.connect(lambda g: edit_item(win, "goals", g))
        self.board.add_requested.connect(lambda: edit_item(win, "goals", preset=self._new_preset()))
        self.board.image_in.connect(self._image_in)
        bv.addWidget(self.board)
        self.add(self.board_host)

        # çark + yol haritası
        self.wheel_row = QWidget()
        wv = QVBoxLayout(self.wheel_row)
        wv.setContentsMargins(0, 0, 0, 0)
        wv.setSpacing(16)
        self.c_bal = Card(t("bal_title"), t("bal_sub"))
        self.balance = BalanceView()
        self.balance.area_clicked.connect(self._show_area)
        self.balance.add_for.connect(lambda a: edit_item(win, "goals", preset=dict(self._new_preset(), area=a)))
        self.c_bal.add(self.balance)
        wv.addWidget(self.c_bal)
        self.c_road = Card(t("roadmap_title"), t("roadmap_sub"))
        wv.addWidget(self.c_road)
        self.add(self.wheel_row)
        self._apply_view()

    # ---------------------------------------------------------- görünüm
    def _set_view(self, v):
        self.view = v
        prefs.set("goals_view", v)
        self._apply_view()

    def _apply_view(self):
        has = bool(self.store.all("goals"))
        self.c_empty.setVisible(not has)
        self.tabs.setVisible(has)
        self.board_host.setVisible(has and self.view == "board")
        self.wheel_row.setVisible(has and self.view == "wheel")

    def _new_preset(self):
        roots = [g for g in self.store.goal_roots() if g.get("horizon") == "life"]
        pr = {"horizon": "y3" if roots else "life"}
        if roots:
            pr["parent"] = roots[0]["id"]
        if self.area != "all":
            pr["area"] = self.area
        return pr

    # ---------------------------------------------------------- yenile
    def refresh(self):
        s, td = self.store, day_today()
        goals = s.all("goals")
        self.sample_btn.setVisible(any(g.get("sample") for g in goals) or
                                   any(w.get("sample") for w in s.all("wheel")))
        self._apply_view()
        if not goals:
            return
        heat = {}
        for g in goals:
            n, _last = s.goal_activity(g, td)
            heat[g["id"]] = (heat_of(n), n)
        prog = {g["id"]: s.goal_progress(g) for g in goals}
        self._fill_board(goals, heat, prog)
        self._fill_balance(td)
        self._fill_road(prog, heat)

    def _fill_board(self, goals, heat, prog):
        pins = [g for g in goals if g.get("horizon") != "action" or g.get("image")]
        areas = [a for a in LIFE_AREAS if any(life_area(g.get("area")) == a for g in pins)]
        if self.area not in areas:
            self.area = "all"
        while self.filter_lay.count():
            w = self.filter_lay.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        self.filter = ChipBar([("all", t("all"))] + [(a, area_name(a)) for a in areas], self.area)
        self.filter.changed.connect(self._set_area)
        self.filter_lay.addWidget(self.filter, 1)
        hint = QLabel(t("board_hint"))
        hint.setObjectName("RowSub")
        self.filter_lay.addWidget(hint)
        if self.area != "all":
            pins = [g for g in pins if life_area(g.get("area")) == self.area]
        hz_rank = {h: i for i, h in enumerate(GOAL_HORIZONS)}
        pins.sort(key=lambda g: (hz_rank.get(g.get("horizon") or "year", 9), not g.get("image"),
                                 float(g.get("order") or 0), g.get("created") or ""))
        self.board.set_goals(pins, heat, prog)

    def _set_area(self, a):
        self.area = a
        # çip kendi tıklama sinyalindeyken yeniden kurulmasın: bir sonraki turda yenile
        QTimer.singleShot(0, self.mark_dirty)

    def _image_in(self, goal, name):
        """Panoya görsel geldi: kartın üstüne bırakıldıysa o kartın görseli olur, değilse yeni hedef formu açılır."""
        if goal is not None:
            old = goal.get("image")
            self.store.update("goals", goal["id"], image=name)
            self.win.toast(t("pin_image_set"), t("undo"),
                           lambda: self.store.update("goals", goal["id"], image=old))
        else:
            pr = self._new_preset()
            pr["image"] = name
            edit_item(self.win, "goals", preset=pr)

    def _fill_balance(self, td):
        from ..balance import area_report, history
        self.balance.set_data(area_report(self.store, td), history(self.store, td)[0])

    def _show_area(self, area):
        """Alan kartı → panoda o alanın hedefleri."""
        self.area = area
        self.tabs.select("board")
        self.mark_dirty()

    def _fill_road(self, prog, heat):
        s, win = self.store, self.win
        c = self.c_road
        c.clear()
        goals = s.all("goals")
        by_id = {g["id"]: g for g in goals}
        for hz in GOAL_HORIZONS[:-1]:
            items = [g for g in goals if (g.get("horizon") or "year") == hz]
            head = QLabel(t("hz_" + hz).upper())
            head.setObjectName("SubTitle")
            head.setContentsMargins(6, 10, 0, 2)
            c.add(head)
            if not items:
                e = QLabel(t("roadmap_empty"))
                e.setObjectName("Empty")
                e.setContentsMargins(6, 0, 0, 4)
                c.add(e)
                continue
            for g in sorted(items, key=lambda g: (g.get("due") or "9999", g.get("title") or "")):
                sub = []
                par = by_id.get(g.get("parent"))
                if par:
                    sub.append("↳ " + (par.get("title") or ""))
                sub.append(area_name(g.get("area")))
                d = parse_date(g.get("due"))
                if d:
                    sub.append(fmt_day(d))
                n = heat.get(g["id"], (0, 0))[1]
                badges = [(f"%{int(round(prog.get(g['id'], 0) * 100))}", "good" if g.get("done") else None)]
                if n:
                    badges.append((t("goal_days_30", n=n), None))
                r = Row(g.get("title") or "—", " · ".join(sub), icon=area_icon(g.get("area")),
                        badges=badges)
                c.add(bind_row(win, r, "goals", g, self._goal_extra(g)))

    # ---------------------------------------------------------- eylemler
    def _goal_extra(self, g):
        td = day_today()
        on = td.isoformat() in (g.get("days") or [])
        return [(t("goal_unmark_today") if on else t("goal_mark_today"),
                 lambda: self.store.toggle_day("goals", g["id"], td)),
                (t("goal_add_child"), lambda: edit_item(self.win, "goals", preset={
                    "parent": g["id"], "area": life_area(g.get("area")),
                    "horizon": "action" if g.get("horizon") in ("year", "term") or g.get("parent") else "year"}))]

    def _add_sample(self):
        add_sample(self.store)
        self.win.toast(t("goals_sample_added"))

    def _remove_sample(self):
        removed = remove_sample(self.store)
        if removed:
            self.win.toast(t("goals_sample_removed"), t("undo"), lambda: self.store.restore(removed))


def heat_of(n):
    return heat(n)
