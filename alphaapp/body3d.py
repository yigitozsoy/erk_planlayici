"""Döndürülebilir 3B kas modeli (kendi çizimimiz, numpy / OpenGL yok).

Gövde, birbirine geçen elipsoidlerden ("blob") kurulur: her kas bir ya da birkaç blob, iskelet parçaları (baş, el,
diz, kaval, ayak …) kas olmayan açık gri bloblar. Çizim: düşük poligonlu düz gölgeleme, ressam algoritması
(uzaktan yakına), arka yüz ayıklama. Birim santimetre: y yukarı (ayak 0, baş ~177), z ileri (yüz +z), x yanlar.

Body3D.set_heat({kas: 0..1}) kasları kırmızıya boyar; tips {kas: metin} üstüne gelince görünür.
Sürükle = döndür, çift tık = ön / arka. Kare, açı / boyut / ısı değişmedikçe önbellekten çizilir.
"""
import json
import math
import os
import zipfile

from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPolygonF, QColor, QPen, QPixmap, QImage, QRadialGradient
from PyQt6.QtWidgets import QWidget, QToolTip

U, V = 12, 7          # boylam / enlem bölümü

# (anahtar ya da None, merkez, yarıçaplar, (rz, rx, ry) derece, taper, aynala)
#  rz > 0: alt uç dışa açılır (sağ tarafta +x). taper > 0: üst taraf geniş.
_B = None
PARTS = [
    # --- iskelet / deri (kas değil)
    (_B, (0, 166, 1), (8.4, 10.8, 9.6), (0, 0, 0), 0.10, False),          # baş
    (_B, (0, 158.5, 3.2), (6.2, 5.0, 6.4), (0, 0, 0), 0.0, False),         # çene
    (_B, (0, 150, -0.5), (5.4, 7.5, 5.4), (0, 0, 0), 0.0, False),          # boyun
    (_B, (0, 127, -1.5), (13.6, 17, 9.4), (0, 0, 0), 0.12, False),         # göğüs kafesi
    (_B, (0, 106, 0), (11.6, 13, 7.8), (0, 0, 0), 0.0, False),             # karın içi
    (_B, (0, 91, -0.5), (14.2, 8.5, 9.2), (0, 0, 0), 0.0, False),          # leğen
    (_B, (23.4, 111, -0.8), (3.5, 3.8, 3.6), (8, 0, 0), 0.0, True),        # dirsek
    (_B, (26.6, 79.5, 1.5), (2.6, 6.2, 4.2), (6, 0, 0), -0.1, True),       # el
    (_B, (9.6, 50.5, 2.2), (4.7, 5.2, 5.0), (0, 0, 0), 0.0, True),         # diz
    (_B, (9.9, 30, 2.8), (3.1, 15.5, 3.3), (-1, 0, 0), 0.15, True),        # kaval
    (_B, (10.2, 3.8, 4.6), (3.7, 3.0, 9.2), (0, 0, 0), 0.0, True),         # ayak
    # --- kaslar
    ("traps", (6.2, 148.2, -3.2), (6.6, 4.8, 4.4), (-28, 0, 0), 0.0, True),
    ("traps", (0, 136, -7.6), (8.8, 13.5, 3.4), (0, 0, 0), 0.35, False),
    ("chest", (7.4, 131.2, 7.0), (7.9, 6.6, 4.1), (-8, 0, -10), 0.0, True),
    ("front_delts", (17.4, 138.2, 3.4), (4.4, 6.6, 4.0), (16, 0, 0), 0.15, True),
    ("side_delts", (20.0, 137.4, 0), (4.2, 7.0, 4.8), (13, 0, 0), 0.2, True),
    ("rear_delts", (17.8, 137.4, -4.0), (4.2, 6.2, 3.9), (16, 0, 0), 0.1, True),
    ("biceps", (21.4, 122.4, 2.4), (3.7, 9.2, 3.7), (6, 0, 0), 0.0, True),
    ("triceps", (21.9, 122.6, -2.4), (4.1, 10.2, 4.1), (6, 0, 0), 0.15, True),
    ("forearms", (24.6, 98.6, 1.0), (3.8, 11.6, 3.7), (6, 0, 0), 0.32, True),
    ("abs", (3.3, 117.2, 7.6), (3.3, 3.6, 2.4), (0, 0, 0), 0.0, True),
    ("abs", (3.3, 109.4, 7.9), (3.3, 3.6, 2.4), (0, 0, 0), 0.0, True),
    ("abs", (3.2, 101.6, 7.8), (3.2, 3.6, 2.4), (0, 0, 0), 0.0, True),
    ("abs", (0, 93.4, 6.9), (5.4, 5.6, 2.6), (0, 0, 0), 0.3, False),
    ("obliques", (10.2, 105, 4.0), (4.0, 10.4, 5.0), (-5, 0, 0), 0.1, True),
    ("lats", (10.8, 119, -5.0), (5.4, 13.4, 4.4), (-13, 0, 0), 0.35, True),
    ("upper_back", (7.0, 130, -7.8), (6.0, 7.2, 3.2), (0, 0, 0), 0.0, True),
    ("lower_back", (4.0, 104, -7.0), (3.5, 11, 3.2), (0, 0, 0), 0.0, True),
    ("glutes", (7.6, 88, -6.8), (7.8, 8.6, 6.0), (0, 0, 0), 0.0, True),
    ("quads", (9.6, 69.5, 4.0), (6.2, 17.2, 5.8), (-4, 0, 0), 0.25, True),
    ("quads", (6.8, 55.5, 4.4), (3.5, 5.2, 3.5), (0, 0, 0), -0.2, True),
    ("adductors", (4.9, 73, 0.4), (3.5, 12.4, 4.5), (-6, 0, 0), 0.3, True),
    ("hamstrings", (9.6, 69.5, -3.4), (5.8, 17.2, 5.0), (-4, 0, 0), 0.15, True),
    ("calves", (10.0, 36, -2.4), (4.6, 10.4, 4.2), (-1, 0, 0), 0.3, True),
]


def _rot(p, rz, rx, ry):
    x, y, z = p
    if rz:
        c, s = math.cos(rz), math.sin(rz)
        x, y = x * c - y * s, x * s + y * c
    if rx:
        c, s = math.cos(rx), math.sin(rx)
        y, z = y * c - z * s, y * s + z * c
    if ry:
        c, s = math.cos(ry), math.sin(ry)
        x, z = x * c + z * s, -x * s + z * c
    return x, y, z


def build_mesh(parts=PARTS):
    """(köşeler [(x, y, z)], yüzler [(i0, i1, i2, i3, anahtar)])"""
    verts, faces = [], []
    for key, c, r, ang, taper, mirror in parts:
        sides = ((1, ang), (-1, (-ang[0], ang[1], -ang[2]))) if mirror else ((1, ang),)
        for sx, (rz, rx, ry) in sides:
            cx = c[0] * sx
            base = len(verts)
            for j in range(V + 1):
                lat = -math.pi / 2 + math.pi * j / V
                yn = math.sin(lat)
                k = 1 + taper * yn
                for i in range(U):
                    lon = 2 * math.pi * i / U
                    p = (r[0] * k * math.cos(lat) * math.sin(lon), r[1] * yn, r[2] * k * math.cos(lat) * math.cos(lon))
                    p = _rot(p, math.radians(rz), math.radians(rx), math.radians(ry))
                    verts.append((p[0] + cx, p[1] + c[1], p[2] + c[2]))
            for j in range(V):
                for i in range(U):
                    a = base + j * U + i
                    b = base + j * U + (i + 1) % U
                    faces.append((a, b, b + U, a + U, key))
    return verts, faces


_MESH = None


def mesh():
    global _MESH
    if _MESH is None:
        _MESH = build_mesh()
    return _MESH


class Body3D(QWidget):
    hovered = pyqtSignal(object)      # kas anahtarı ya da None

    SKIN = QColor(196, 196, 198)
    MUSCLE = QColor(132, 132, 136)
    HOT = QColor(229, 57, 53)
    LIGHT = (-0.45, 0.55, 0.70)

    def __init__(self, height=440):
        super().__init__()
        self.verts, self.faces = mesh()
        self.heat, self.tips, self.names = {}, {}, {}
        self.yaw, self.pitch = math.radians(-24), math.radians(6)
        self._target = None
        self._drag = None
        self._cache = None
        self._polys = []
        self.hover = None
        self.setFixedHeight(height)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        lx, ly, lz = self.LIGHT
        n = math.sqrt(lx * lx + ly * ly + lz * lz)
        self.light = (lx / n, ly / n, lz / n)
        self._anim = QTimer(self)
        self._anim.setInterval(16)
        self._anim.timeout.connect(self._tick)

    # ---------------------------------------------------------------- veri
    def set_heat(self, heat, tips=None, names=None):
        self.heat = {k: max(0.0, min(1.0, float(v))) for k, v in (heat or {}).items()}
        self.tips = dict(tips or {})
        if names is not None:
            self.names = dict(names)
        self._cache = None
        self.update()

    def color_for(self, key):
        if key is None:
            return self.SKIN
        h = self.heat.get(key, 0.0)
        if h <= 0:
            return self.MUSCLE
        k = 0.22 + 0.78 * h
        a, b = self.MUSCLE, self.HOT
        return QColor(int(a.red() + (b.red() - a.red()) * k), int(a.green() + (b.green() - a.green()) * k),
                      int(a.blue() + (b.blue() - a.blue()) * k))

    # ---------------------------------------------------------------- dönüş
    def turn_to(self, deg):
        """Yumuşakça verilen açıya döner (0 = önden, 180 = arkadan)."""
        t = math.radians(deg)
        cur = self.yaw % (2 * math.pi)
        d = (t - cur + math.pi) % (2 * math.pi) - math.pi
        self._target = self.yaw + d
        self._anim.start()

    def _tick(self):
        if self._target is None:
            self._anim.stop()
            return
        d = self._target - self.yaw
        if abs(d) < 0.003:
            self.yaw, self._target = self._target, None
            self._anim.stop()
        else:
            self.yaw += d * 0.18
        self._cache = None
        self.update()

    def facing_back(self):
        return math.cos(self.yaw) < 0

    # ---------------------------------------------------------------- çizim
    def _project(self):
        W, H = self.width(), self.height()
        s = (H - 16) / 182.0
        cx, cy = W / 2, H - 8
        cyw, syw = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        D = 900.0
        pts, cam = [], []
        for x, y, z in self.verts:
            y -= 88
            x1 = x * cyw + z * syw
            z1 = -x * syw + z * cyw
            y2 = y * cp - z1 * sp
            z2 = y * sp + z1 * cp
            f = D / (D - z2)
            cam.append((x1, y2, z2))
            pts.append(QPointF(cx + x1 * s * f, cy - (y2 + 88) * s * f))
        return pts, cam

    def _render(self):
        dpr = self.devicePixelRatioF()
        pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)
        pts, cam = self._project()
        lx, ly, lz = self.light
        draw = []
        for a, b, c, d, key in self.faces:
            A, B, C, Dd = cam[a], cam[b], cam[c], cam[d]
            ux, uy, uz = C[0] - A[0], C[1] - A[1], C[2] - A[2]
            vx, vy, vz = Dd[0] - B[0], Dd[1] - B[1], Dd[2] - B[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            n = math.sqrt(nx * nx + ny * ny + nz * nz)
            if n < 1e-9:
                continue
            nx, ny, nz = nx / n, ny / n, nz / n
            if nz >= 0.02:          # yüz kameraya bakmıyor (dış normal −z yönünde değil)
                continue
            depth = A[2] + B[2] + C[2] + Dd[2]
            lam = max(0.0, -(nx * lx + ny * ly + nz * lz))
            draw.append((depth, (a, b, c, d), key, 0.42 + 0.66 * lam))
        draw.sort(key=lambda x: x[0])
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        polys = []
        cache = {}
        for _dz, idx, key, sh in draw:
            base = cache.get(key)
            if base is None:
                base = cache[key] = self.color_for(key)
            col = QColor(min(255, int(base.red() * sh)), min(255, int(base.green() * sh)),
                         min(255, int(base.blue() * sh)))
            poly = QPolygonF([pts[i] for i in idx])
            p.setPen(QPen(col, 0.7))
            p.setBrush(col)
            p.drawPolygon(poly)
            if key:
                polys.append((poly, key))
        p.end()
        self._polys = polys
        return pm

    def paintEvent(self, _e):
        if self._cache is None or self._cache.size() != self.size() * self.devicePixelRatioF():
            self._cache = self._render()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)
        p.end()

    def resizeEvent(self, e):
        self._cache = None
        super().resizeEvent(e)

    # ---------------------------------------------------------------- fare
    def muscle_at(self, pos):
        for poly, key in reversed(self._polys):
            if poly.containsPoint(pos, Qt.FillRule.OddEvenFill):
                return key
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = (e.position().x(), self.yaw)
            self._target = None
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            x0, y0 = self._drag
            self.yaw = y0 + (e.position().x() - x0) * 0.012
            self._cache = None
            self.update()
            return
        k = self.muscle_at(e.position())
        if k != self.hover:
            self.hover = k
            self.hovered.emit(k)
            if k:
                text = self.names.get(k, k)
                if self.tips.get(k):
                    text += "\n" + self.tips[k]
                QToolTip.showText(e.globalPosition().toPoint(), text, self)
            else:
                QToolTip.hideText()

    def mouseReleaseEvent(self, _e):
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, _e):
        self.turn_to(0 if self.facing_back() else 180)

    def leaveEvent(self, _e):
        if self.hover:
            self.hover = None
            self.hovered.emit(None)


# ============================================================ gerçek model: önceden çizilmiş kareler
FRAMES_ZIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "body_frames.zip")
_FRAMES = None


def load_frames(path=FRAMES_ZIP):
    """(meta, [QImage Indexed8]) ya da None. Paket yerelde üretilir (packaging/make_body.py), depoda yok."""
    global _FRAMES
    if _FRAMES is None:
        _FRAMES = False
        try:
            with zipfile.ZipFile(path) as zf:
                meta = json.loads(zf.read("meta.json"))
                imgs = []
                for i in range(meta["frames"]):
                    im = QImage.fromData(zf.read("f%02d.png" % i))
                    if im.format() != QImage.Format.Format_Indexed8:
                        im = im.convertToFormat(QImage.Format.Format_Indexed8)
                    imgs.append(im)
            _FRAMES = (meta, imgs)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            _FRAMES = False
    return _FRAMES or None


class ModelView(QWidget):
    """Gerçek anatomi modeli: her açı için bir kare, piksel = kas × gölge indeksi. Isı = renk tablosu."""
    hovered = pyqtSignal(object)

    SKIN = (206, 206, 208)
    MUSCLE = (150, 150, 156)
    HOT = (229, 57, 53)

    def __init__(self, height=440, frames=None):
        super().__init__()
        self.meta, self.imgs = frames or load_frames()
        self.keys = self.meta["keys"]
        self.ns = self.meta["shades"]
        self.n = len(self.imgs)
        self.heat, self.tips, self.names = {}, {}, {}
        self.yaw = -25.0
        self._target = None
        self._drag = None
        self._cache = None
        self.hover = None
        self.setFixedHeight(height)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._anim = QTimer(self)
        self._anim.setInterval(16)
        self._anim.timeout.connect(self._tick)
        self._make_table()

    # ---------------------------------------------------------------- renkler
    def base_rgb(self, key):
        if key == "skin":
            return self.SKIN
        h = self.heat.get(key, 0.0)
        if h <= 0:
            return self.MUSCLE
        k = 0.22 + 0.78 * h
        a, b = self.MUSCLE, self.HOT
        return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))

    def _make_table(self):
        t = [0] * 256
        for ki, key in enumerate(self.keys):
            r, g, b = self.base_rgb(key)
            boost = 1.18 if key == self.hover and key != "skin" else 1.0
            for s in range(self.ns):
                f = (0.16 + 0.98 * s / (self.ns - 1)) * boost
                t[1 + ki * self.ns + s] = (0xFF << 24) | (min(255, int(r * f)) << 16) | \
                    (min(255, int(g * f)) << 8) | min(255, int(b * f))
        self._table = t
        self._cache = None

    def set_heat(self, heat, tips=None, names=None):
        self.heat = {k: max(0.0, min(1.0, float(v))) for k, v in (heat or {}).items()}
        self.tips = dict(tips or {})
        if names is not None:
            self.names = dict(names)
        self._make_table()
        self.update()

    # ---------------------------------------------------------------- dönüş
    def frame_index(self):
        return int(round(self.yaw / self.meta["step"])) % self.n

    def facing_back(self):
        return math.cos(math.radians(self.yaw)) < 0

    def turn_to(self, deg):
        cur = self.yaw % 360
        d = (deg - cur + 180) % 360 - 180
        self._target = self.yaw + d
        self._anim.start()

    def _tick(self):
        if self._target is None:
            self._anim.stop()
            return
        d = self._target - self.yaw
        if abs(d) < 0.5:
            self.yaw, self._target = self._target, None
            self._anim.stop()
        else:
            self.yaw += d * 0.16
        self.update()

    # ---------------------------------------------------------------- çizim
    def _rect(self):
        h = self.height()
        w = h * self.meta["w"] / self.meta["h"]
        return QRectF((self.width() - w) / 2, 0, w, h)

    def paintEvent(self, _e):
        i = self.frame_index()
        r = self._rect()
        dpr = self.devicePixelRatioF()
        key = (i, int(r.width() * dpr), int(r.height() * dpr), id(self._table))
        if self._cache is None or self._cache[0] != key:
            im = self.imgs[i]
            im.setColorTable(self._table)
            pm = QPixmap.fromImage(im.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied).scaled(
                key[1], key[2], Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
            pm.setDevicePixelRatio(dpr)
            self._cache = (key, pm)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, fy = r.center().x(), r.bottom() - r.height() * 0.02      # zemin gölgesi
        rad = r.width() * 0.36
        g = QRadialGradient(QPointF(0, 0), rad)
        g.setColorAt(0, QColor(0, 0, 0, 130))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.save()
        p.translate(cx, fy)
        p.scale(1, 0.16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawEllipse(QPointF(0, 0), rad, rad)
        p.restore()
        p.drawPixmap(r.topLeft(), self._cache[1])
        p.end()

    # ---------------------------------------------------------------- fare
    def muscle_at(self, pos):
        r = self._rect()
        if not r.contains(pos):
            return None
        im = self.imgs[self.frame_index()]
        x = int((pos.x() - r.x()) / r.width() * im.width())
        y = int((pos.y() - r.y()) / r.height() * im.height())
        if not (0 <= x < im.width() and 0 <= y < im.height()):
            return None
        idx = im.pixelIndex(x, y)
        if idx <= 0:
            return None
        k = self.keys[(idx - 1) // self.ns]
        return None if k == "skin" else k

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = (e.position().x(), self.yaw)
            self._target = None
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            x0, y0 = self._drag
            self.yaw = y0 + (e.position().x() - x0) * 0.75
            self.update()
            return
        k = self.muscle_at(e.position())
        if k != self.hover:
            self.hover = k
            self._make_table()
            self.update()
            self.hovered.emit(k)
            if k:
                text = self.names.get(k, k)
                if self.tips.get(k):
                    text += "\n" + self.tips[k]
                QToolTip.showText(e.globalPosition().toPoint(), text, self)
            else:
                QToolTip.hideText()

    def mouseReleaseEvent(self, _e):
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, _e):
        self.turn_to(0 if self.facing_back() else 180)

    def leaveEvent(self, _e):
        if self.hover:
            self.hover = None
            self._make_table()
            self.update()
            self.hovered.emit(None)


def body_view(height=440):
    """Gerçek model paketi varsa ModelView, yoksa elipsoidlerden kurulan Body3D."""
    fr = load_frames()
    return ModelView(height, fr) if fr else Body3D(height)
