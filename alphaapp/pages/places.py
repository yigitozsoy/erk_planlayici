"""Kütüphane > Harita: Türkiye (81 il) ve dünya haritası; gittiğin / gitmek istediğin yerleri işaretle.

Veri: alphaapp/assets/geo.json.gz (Natural Earth, kamu malı; packaging/make_geo.py üretir).
places koleksiyonu: kind province (key = plaka) | country (key = iso3) | city (key = "ad|iso3", lon/lat ile),
status been | want, date, note. Bir ülke, içinde gidilmiş bir il / şehir varsa da "gidildi" boyanır.
Haritada tıkla → menü (Gittim / Gitmek istiyorum / Kaldır); tekerlek = yakınlaş, sürükle = kaydır, çift tık = sıfırla.
Telefon sayfasına GİTMEZ.
"""
import gzip
import json
import math
import os

from PyQt6.QtCore import Qt, QPointF, QRectF, QStringListModel, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QTransform
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCompleter, QMenu,
                             QSizePolicy, QLabel)

from ..components import Card, ChipBar, Row, ResponsiveRow, button, sub_label
from ..config import prefs
from ..forms import bind_row
from ..i18n import t
from ..theme import theme, qcolor

GEO_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "geo.json.gz")
BEEN = "#4f9d74"
WANT = "#d1a04a"
_geo = None


def geo():
    global _geo
    if _geo is None:
        try:
            with gzip.open(GEO_FILE, "rt", encoding="utf-8") as fh:
                _geo = json.load(fh)
        except OSError:
            _geo = {"world": [], "tr": [], "cities": []}
    return _geo


def _path(rings, k):
    p = QPainterPath()
    for r in rings:
        p.moveTo(r[0][0] * k, -r[0][1])
        for x, y in r[1:]:
            p.lineTo(x * k, -y)
        p.closeSubpath()
    return p


_K = {"tr": math.cos(math.radians(39)), "world": 1.0}
_paths = {}


def regions(mode):
    """[(key, name, iso, QPainterPath)] — iller ya da ülkeler, projeksiyonlu (x = boylam·k, y = -enlem)."""
    if mode not in _paths:
        g, k = geo(), _K[mode]
        if mode == "tr":
            _paths[mode] = [(str(r["plate"]), r["name"], "TUR", _path(r["rings"], k)) for r in g["tr"]]
        else:
            _paths[mode] = [(r["iso"], r["name"], r["iso"], _path(r["rings"], k)) for r in g["world"]
                            if r["iso"] != "ATA"]
    return _paths[mode]


def province_at(lon, lat):
    pt = QPointF(lon * _K["tr"], -lat)
    for key, name, _iso, path in regions("tr"):
        if path.contains(pt):
            return key, name
    return None


def status_maps(store):
    """{(kind, key): status} kayıtları + türetilmiş il / ülke durumları (been > want)."""
    rec, prov, country = {}, {}, {}

    def up(d, k, st):
        if d.get(k) != "been":
            d[k] = st

    for x in store.all("places"):
        st = x.get("status") if x.get("status") in ("been", "want") else "want"
        kind, key = x.get("kind"), str(x.get("key"))
        rec[(kind, key)] = st
        if kind == "province":
            up(prov, key, st)
            up(country, "TUR", st)
        elif kind == "country":
            up(country, key, st)
        elif kind == "city":
            if x.get("iso"):
                up(country, x["iso"], st)
            if x.get("iso") == "TUR" and x.get("lon") is not None:
                p = province_at(x["lon"], x["lat"])
                if p:
                    up(prov, p[0], st)
    return rec, prov, country


def find_place(store, kind, key):
    return next((x for x in store.all("places") if x.get("kind") == kind and str(x.get("key")) == str(key)), None)


def set_status(store, kind, key, name, status, **extra):
    """status None → kaydı sil."""
    x = find_place(store, kind, key)
    if status is None:
        if x:
            store.delete("places", x["id"])
        return
    if x:
        if x.get("status") != status:
            store.update("places", x["id"], status=status)
    else:
        store.add("places", dict(kind=kind, key=str(key), name=name, status=status, **extra))


# ============================================================ harita
class MapView(QWidget):
    region_clicked = pyqtSignal(str, str, str, object)          # kind, key, name, global konum
    city_clicked = pyqtSignal(object, object)                   # places kaydı, global konum

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "tr"
        self.rec, self.prov, self.country, self.cities = {}, {}, {}, []
        self.zoom, self.pan = 1.0, QPointF(0, 0)
        self._hover, self._press, self._dragged = None, None, False
        self.setMouseTracking(True)
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme.bind(self, lambda w: w.update())

    def set_mode(self, mode):
        self.mode = mode
        self.zoom, self.pan = 1.0, QPointF(0, 0)
        self._fit_height()
        self.update()

    def set_data(self, rec, prov, country, cities):
        self.rec, self.prov, self.country, self.cities = rec, prov, country, cities
        self.update()

    def _bounds(self):
        if self.mode == "tr":
            return QRectF(25.6 * _K["tr"], -42.4, 19.4 * _K["tr"], 6.7)
        return QRectF(-170, -84, 360, 142)

    def _fit_height(self):
        b = self._bounds()
        w = max(300, self.width())
        self.setFixedHeight(int(min(620, max(300, w * b.height() / b.width() + 8))))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if e.oldSize().width() != e.size().width():
            self._fit_height()

    def _xf(self):
        b = self._bounds()
        s = min(self.width() / b.width(), self.height() / b.height()) * self.zoom
        tx = self.width() / 2 - b.center().x() * s + self.pan.x()
        ty = self.height() / 2 - b.center().y() * s + self.pan.y()
        return QTransform(s, 0, 0, s, tx, ty)

    def _city_pts(self, xf):
        k = _K[self.mode]
        return [(x, xf.map(QPointF(x["lon"] * k, -x["lat"]))) for x in self.cities if x.get("lon") is not None]

    def _hit(self, pos):
        xf = self._xf()
        for x, p in self._city_pts(xf):
            if (p - pos).manhattanLength() < 9:
                return ("city", x)
        inv, _ok = xf.inverted()
        q = inv.map(pos)
        for key, name, iso, path in regions(self.mode):
            if path.boundingRect().contains(q) and path.contains(q):
                return ("region", (key, name))
        return None

    # ------------------------------------------------------------ çizim
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        xf = self._xf()
        base, line = qcolor("surface"), qcolor("bg")
        hov = self._hover[1][0] if self._hover and self._hover[0] == "region" else None
        kind = "province" if self.mode == "tr" else "country"
        derived = self.prov if self.mode == "tr" else self.country
        pen = QPen(line, 0.8 if self.mode == "tr" else 0.6)
        pen.setCosmetic(True)
        p.setPen(pen)
        for key, name, iso, path in regions(self.mode):
            st = self.rec.get((kind, key)) or derived.get(key)
            c = QColor(BEEN if st == "been" else WANT if st == "want" else base)
            if key == hov:
                c = c.lighter(125) if st else qcolor("surface_hover")
            p.setBrush(c)
            p.drawPath(xf.map(path))
        for x, pt in self._city_pts(xf):
            c = QColor(BEEN if x.get("status") == "been" else WANT)
            p.setPen(QPen(qcolor("bg"), 1.5))
            p.setBrush(c)
            p.drawEllipse(pt, 5, 5)
        if self._hover:
            name = self._hover[1][1] if self._hover[0] == "region" else self._hover[1].get("name", "")
            st = self.rec.get((kind, self._hover[1][0])) or derived.get(self._hover[1][0]) \
                if self._hover[0] == "region" else self._hover[1].get("status")
            text = name + (f"  ·  {t('pl_' + st)}" if st else "")
            f = p.font()
            f.setPointSizeF(10)
            f.setBold(True)
            p.setFont(f)
            w = p.fontMetrics().horizontalAdvance(text) + 20
            r = QRectF(10, self.height() - 38, w, 28)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor("card"))
            p.drawRoundedRect(r, 8, 8)
            p.setPen(qcolor("text"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
        p.end()

    # ------------------------------------------------------------ fare
    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._press is not None and e.buttons() & Qt.MouseButton.LeftButton:
            d = pos - self._press[0]
            if self._dragged or d.manhattanLength() > 5:
                self._dragged = True
                self.pan = self._press[1] + d
                self.update()
                return
        h = self._hit(pos)
        key = (h[0], h[1][0] if h[0] == "region" else h[1].get("id")) if h else None
        old = (self._hover[0], self._hover[1][0] if self._hover[0] == "region" else self._hover[1].get("id")) \
            if self._hover else None
        if key != old:
            self._hover = h
            self.setCursor(Qt.CursorShape.PointingHandCursor if h else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._hover = None
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press, self._dragged = (e.position(), QPointF(self.pan)), False

    def mouseReleaseEvent(self, e):
        if e.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        dragged, self._press = self._dragged, None
        if dragged:
            return
        self.click_at(e.position(), e.globalPosition().toPoint())

    def click_at(self, pos, gpos):
        h = self._hit(pos)
        if not h:
            return
        if h[0] == "city":
            self.city_clicked.emit(h[1], gpos)
        else:
            self.region_clicked.emit("province" if self.mode == "tr" else "country", h[1][0], h[1][1], gpos)

    def mouseDoubleClickEvent(self, _e):
        self.zoom, self.pan = 1.0, QPointF(0, 0)
        self.update()

    def wheelEvent(self, e):
        f = 1.25 if e.angleDelta().y() > 0 else 0.8
        z = max(1.0, min(12.0, self.zoom * f))
        f = z / self.zoom
        c = e.position() - QPointF(self.width() / 2, self.height() / 2)
        self.pan = c - (c - self.pan) * f
        self.zoom = z
        if z == 1.0:
            self.pan = QPointF(0, 0)
        self.update()
        e.accept()


# ============================================================ görünüm
class PlacesView(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win, self.store = win, win.store
        self.last_menu = None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.modes = ChipBar([("tr", t("pl_tr")), ("world", t("pl_world"))], prefs.get("pl_map", "tr"))
        self.modes.changed.connect(self._set_mode)
        top.addWidget(self.modes)
        top.addStretch(1)
        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText(t("pl_search"))
        self.search.setMinimumWidth(260)
        self._names = {}
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setModel(QStringListModel(self._choices(), self))
        self.search.setCompleter(self.completer)
        self.search.returnPressed.connect(lambda: self._add_search("been"))
        top.addWidget(self.search)
        for st in ("been", "want"):
            b = button(t("pl_mark_" + st))
            b.setStyleSheet("min-width: 0px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=st: self._add_search(s))
            top.addWidget(b)
        v.addLayout(top)

        self.card = Card(t("pl_map_title"), "")
        self.map = MapView()
        self.map.region_clicked.connect(self._region_menu)
        self.map.city_clicked.connect(self._city_menu)
        self.card.layout().addWidget(self.map)
        leg = QHBoxLayout()
        leg.setSpacing(8)
        for c, k in ((BEEN, "pl_been"), (WANT, "pl_want")):
            sw = QLabel()
            sw.setFixedSize(12, 12)
            sw.setStyleSheet(f"background: {c}; border-radius: 6px;")
            lb = sub_label(t(k))
            leg.addWidget(sw)
            leg.addWidget(lb)
            leg.addSpacing(8)
        hint = sub_label(t("pl_hint"))
        leg.addStretch(1)
        leg.addWidget(hint)
        self.card.layout().addLayout(leg)
        v.addWidget(self.card)

        lists = ResponsiveRow(860)
        self.c_been = Card(t("pl_been_list"))
        self.c_want = Card(t("pl_want_list"))
        lists.add(self.c_been, 1)
        lists.add(self.c_want, 1)
        v.addWidget(lists)
        self.map.set_mode(self.modes.current)

    # ------------------------------------------------------------ arama
    def _choices(self):
        g = geo()
        out = []
        for r in g["tr"]:
            s = f"{r['name']} ({t('pl_province')})"
            self._names[s] = ("province", str(r["plate"]), r["name"], {"iso": "TUR"})
            out.append(s)
        for r in g["world"]:
            s = f"{r['name']} ({t('pl_country')})"
            self._names[s] = ("country", r["iso"], r["name"], {"iso": r["iso"]})
            out.append(s)
        for nm, iso, cname, lon, lat, _pop in g["cities"]:
            s = f"{nm}, {cname}"
            if s not in self._names:
                self._names[s] = ("city", f"{nm}|{iso}", nm, {"iso": iso, "lon": lon, "lat": lat})
                out.append(s)
        return out

    def _add_search(self, status):
        text = self.search.text().strip()
        if not text:
            return
        hit = self._names.get(text)
        if hit is None:
            low = text.lower()
            hit = next((v for k, v in self._names.items() if k.lower().startswith(low)), None)
        if hit is None:
            self.win.toast(t("pl_not_found"))
            return
        kind, key, name, extra = hit
        set_status(self.store, kind, key, name, status, **extra)
        self.search.clear()
        if kind == "country" and key != "TUR" and self.modes.current == "tr":
            self.modes.select("world")
        self.win.toast(t("pl_added", n=name, s=t("pl_" + status)))

    # ------------------------------------------------------------ menüler
    def _status_menu(self, kind, key, name, gpos, extra=None):
        cur = (find_place(self.store, kind, key) or {}).get("status")
        m = QMenu(self.win)
        hdr = m.addAction(name)
        hdr.setEnabled(False)
        m.addSeparator()
        for st in ("been", "want"):
            a = m.addAction(t("pl_mark_" + st))
            a.setCheckable(True)
            a.setChecked(cur == st)
            a.triggered.connect(lambda _=False, s=st: set_status(self.store, kind, key, name,
                                                                 None if cur == s else s, **(extra or {})))
        if cur:
            m.addSeparator()
            m.addAction(t("pl_remove"), lambda: set_status(self.store, kind, key, name, None))
        self.last_menu = m
        m.popup(gpos)

    def _region_menu(self, kind, key, name, gpos):
        self._status_menu(kind, key, name, gpos, {"iso": "TUR" if kind == "province" else key})

    def _city_menu(self, x, gpos):
        self._status_menu("city", x.get("key"), x.get("name", ""), gpos)

    def _set_mode(self, m):
        prefs.set("pl_map", m)
        self.map.set_mode(m)

    # ------------------------------------------------------------ yenile
    def refresh(self):
        s = self.store
        rec, prov, country = status_maps(s)
        items = s.all("places")
        self.map.set_data(rec, prov, country, [x for x in items if x.get("kind") == "city"])
        nb = sum(1 for v in prov.values() if v == "been")
        cb = sum(1 for v in country.values() if v == "been")
        self.card.set_sub(t("pl_stats", p=nb, c=cb, w=sum(1 for x in items if x.get("status") == "want")))
        kinds = {"province": t("pl_province"), "country": t("pl_country"), "city": t("pl_city")}
        for card, st in ((self.c_been, "been"), (self.c_want, "want")):
            card.clear()
            rows = sorted((x for x in items if x.get("status", "want") == st),
                          key=lambda x: (str(x.get("date") or "~") if st == "been" else "", x.get("name") or ""))
            card.set_sub(str(len(rows)) if rows else "")
            if not rows:
                card.empty(t("pl_empty_" + st))
            other = "want" if st == "been" else "been"
            for x in rows:
                sub = " · ".join(b for b in (kinds.get(x.get("kind"), ""), x.get("date") or "", x.get("note") or "")
                                 if b)
                r = Row(x.get("name") or "—", sub, icon="flight" if st == "been" else "flag")
                bind_row(self.win, r, "places", x,
                         [(t("pl_mark_" + other), lambda x=x, o=other: s.update("places", x["id"], status=o))])
                card.add(r)
