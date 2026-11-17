"""Ekonomi > Alınacaklar: ürün kartlarından vitrin (görsel, ad, fiyat, "Aldım").

Kart görseli: wishlist.image (DATA_DIR\\images). Yoksa ve bağlantı varsa sayfanın og:image'i arka planda bir kez
denenir (img_tried); olmazsa kategori ikonu. Üstte kategori çipleri + "Alındı"; sağ tık = düzenle / sil / bağlantı.
"""
import os
from datetime import datetime

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton

from .. import icons
from ..components import Card, ChipBar, clear_layout, sub_label
from ..config import IMAGES_DIR, day_today
from ..forms import edit_item, item_menu
from ..i18n import t, fmt_money
from ..store import num
from ..theme import color, qcolor
from ..widgets import IconButton

CARD_W = 196
IMG_H = 150
_ICON = {"gadget": "build", "giyim": "checkroom", "ev": "home", "kitap": "menu_book", "elektronik": "headphones",
         "spor": "fitness", "mutfak": "restaurant"}
_cache = {}


def _open(url):
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl(url))


def image_pixmap(w, wd, ht, radius=10):
    path = os.path.join(IMAGES_DIR, w["image"]) if w.get("image") else None
    has = bool(path and os.path.exists(path))
    cat = (w.get("category") or "").strip().lower()
    key = (path if has else None, cat, wd, ht, color("surface_hover"), color("text3"))
    if key in _cache:
        return _cache[key]
    dpr = 2
    pm = QPixmap(int(wd * dpr), int(ht * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, wd, ht), radius, radius)
    p.setClipPath(clip)
    img = QPixmap(path) if has else QPixmap()
    if not img.isNull():
        p.fillRect(QRectF(0, 0, wd, ht), Qt.GlobalColor.white)       # ürün fotoğrafları çoğunlukla beyaz zeminli
        sc = img.scaled(int(wd * dpr), int(ht * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
        sc.setDevicePixelRatio(dpr)
        p.drawPixmap(QPointF((wd - sc.width() / dpr) / 2, (ht - sc.height() / dpr) / 2), sc)
    else:
        p.fillRect(QRectF(0, 0, wd, ht), qcolor("surface_hover"))
        isz = int(ht * 0.32)
        p.drawPixmap(QPointF((wd - isz) / 2, (ht - isz) / 2),
                     icons.pixmap(_ICON.get(cat, "shopping_bag"), color("text3"), isz))
    p.end()
    if len(_cache) > 300:
        _cache.clear()
    _cache[key] = pm
    return pm


class WishCard(QWidget):
    """Tek ürün: görsel, ad (2 satır), kategori · fiyat, Aldım düğmesi. Tıkla = düzenle."""
    clicked = pyqtSignal()
    menu = pyqtSignal(object)
    bought = pyqtSignal(bool)

    def __init__(self, w, parent=None):
        super().__init__(parent)
        self.w = w
        self.setObjectName("WishCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        done = bool(w.get("bought"))
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 10)
        v.setSpacing(6)
        self.img = img = QLabel()
        self.set_width(CARD_W)
        if done:
            from PyQt6.QtWidgets import QGraphicsOpacityEffect
            ef = QGraphicsOpacityEffect(img)
            ef.setOpacity(0.35)
            img.setGraphicsEffect(ef)
        v.addWidget(img)
        name = QLabel(w.get("name") or "")
        name.setObjectName("WishName")
        name.setWordWrap(True)
        name.setMaximumHeight(40)
        name.setToolTip(w.get("name") or "")
        v.addWidget(name)
        h = QHBoxLayout()
        h.setSpacing(4)
        pr = w.get("price")
        price = QLabel(fmt_money(pr) if pr not in (None, "") else t("wish_no_price"))
        price.setObjectName("WishPrice" if pr not in (None, "") and not done else "RowSub")
        h.addWidget(price, 1)
        if w.get("link"):
            lb = IconButton("open_in", t("wish_open_link"), 28, 16)
            lb.clicked.connect(lambda: _open(w["link"]))
            h.addWidget(lb)
        self.btn = QPushButton(t("wish_got") if done else t("wish_buy"))
        self.btn.setObjectName("WishBtnOn" if done else "WishBtn")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(lambda: self.bought.emit(not done))
        h.addWidget(self.btn)
        v.addLayout(h)
        sub = [w.get("category") or ""]
        if done and w.get("bought_at"):
            from ..i18n import fmt_day
            from ..store import parse_date
            sub.append(fmt_day(parse_date(w["bought_at"])))
        if any(sub):
            s = sub_label(" · ".join(x for x in sub if x))
            v.insertWidget(2, s)

    def set_width(self, wd):
        wd = int(wd)
        if getattr(self, "_wd", None) == wd:
            return
        self._wd = wd
        self.setFixedWidth(wd)
        self.img.setFixedSize(wd - 16, IMG_H)
        self.img.setPixmap(image_pixmap(self.w, wd - 16, IMG_H))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.menu.emit(e.globalPos())


class WishGrid(QWidget):
    """Kartları genişliğe göre sütunlara dizer (sola yaslı)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.g = QGridLayout(self)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setSpacing(12)
        self.cards = []
        self._cols = 0

    def set_cards(self, cards):
        for c in self.cards:
            self.g.removeWidget(c)
            c.hide()
            c.setParent(None)
            c.deleteLater()
        self.cards = list(cards)
        self._cols = 0
        self._place()

    def _place(self):
        W = self.width() if self.width() > 50 else 4 * (CARD_W + 12)
        cols = max(1, (W + 12) // (CARD_W + 12))
        cw = (W - 12 * (cols - 1)) / cols
        for c in self.cards:
            c.set_width(cw)
        if cols == self._cols:
            return
        self._cols = cols
        for c in self.cards:
            self.g.removeWidget(c)
        for i, c in enumerate(self.cards):
            self.g.addWidget(c, i // cols, i % cols, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for c in range(12):
            self.g.setColumnStretch(c, 0)
        self.g.setColumnStretch(cols, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place()


class WishlistCard(Card):
    def __init__(self, win, on_change):
        super().__init__(t("tab_wish"), add_tip=t("new_wishlist"))
        self.win, self.store, self.on_change = win, win.store, on_change
        self.add_clicked.connect(lambda: edit_item(win, "wishlist"))
        b = IconButton("open_in", t("wish_notion"), 32, 20)
        b.clicked.connect(self._open_notion)
        self.head_widget(b)
        self.filter = "all"
        self.chips_host = QWidget()
        self.chips_lay = QHBoxLayout(self.chips_host)
        self.chips_lay.setContentsMargins(0, 0, 0, 4)
        self.grid = WishGrid()
        self.layout().addWidget(self.chips_host)
        self.layout().addWidget(self.grid)
        self.empty_lbl = sub_label(t("no_wish"))
        self.layout().addWidget(self.empty_lbl)
        self.jobs = []

    def _chips(self, items):
        clear_layout(self.chips_lay)
        cats = sorted({(w.get("category") or "").strip() for w in items if not w.get("bought")} - {""},
                      key=str.lower)
        opts = [("all", t("all"))] + [("c:" + c, c) for c in cats]
        if any(w.get("bought") for w in items):
            opts.append(("bought", t("wish_bought_tab")))
        if self.filter not in [k for k, _ in opts]:
            self.filter = "all"
        bar = ChipBar(opts, self.filter)
        bar.changed.connect(self._set_filter)
        self.chips_lay.addWidget(bar)

    def _set_filter(self, k):
        self.filter = k
        self.refresh()

    def refresh(self):
        items = self.store.all("wishlist")
        self._chips(items)
        todo = [w for w in items if not w.get("bought")]
        if self.filter == "bought":
            show = sorted((w for w in items if w.get("bought")), key=lambda w: w.get("bought_at") or "",
                          reverse=True)
        elif self.filter.startswith("c:"):
            show = [w for w in todo if (w.get("category") or "").strip() == self.filter[2:]]
        else:
            # önce fiyatı / görseli olanlar (daha "hazır"), sonra eklenme sırası (en yeni üstte)
            show = sorted(todo, key=lambda w: (not (w.get("image") or w.get("price") not in (None, ""))))
        cards = []
        for w in show:
            c = WishCard(w)
            c.clicked.connect(lambda w=w: edit_item(self.win, "wishlist", w))
            extra = [(t("wish_open_link"), lambda u=w["link"]: _open(u))] if w.get("link") else ()
            c.menu.connect(lambda pos, w=w, extra=extra: item_menu(self.win, "wishlist", w, pos, extra))
            c.bought.connect(lambda on, w=w: self._buy(w, on))
            cards.append(c)
        self.grid.set_cards(cards)
        self.empty_lbl.setVisible(not show)
        known = sum(num(w.get("price")) for w in todo)
        n_price = sum(1 for w in todo if w.get("price") not in (None, ""))
        self.set_sub(t("wish_sub2", n=len(todo), v=fmt_money(known), k=n_price) if items else "")
        self._fetch_images(todo)

    def _buy(self, w, on):
        self.store.update("wishlist", w["id"], bought=on, bought_at=day_today().isoformat() if on else None)
        self.on_change()

    def _open_notion(self):
        from ..config import prefs
        url = prefs.get("notion_wishlist") or ""
        if not url:
            from PyQt6.QtWidgets import QInputDialog
            url, ok = QInputDialog.getText(self.win, t("wish_notion"), t("wish_notion_ask"))
            url = url.strip()
            if not ok or not url.startswith("http"):
                return
            prefs.set("notion_wishlist", url)
        _open(url)

    # ------------------------------------------------------------ bağlantıdan görsel (bir kez)
    def _fetch_images(self, items):
        from .assets import offline
        if offline():
            return
        from .. import library
        busy = {j.wid for j in self.jobs}
        for w in items:
            if w.get("image") or not w.get("link") or w.get("img_tried") or w["id"] in busy:
                continue

            def work(url=w["link"]):
                res = library.fetch_article(url)
                return library.download_cover(res[0].get("cover_url")) if res else None
            j = library.Job(work, parent=self)
            j.wid = w["id"]
            j.done.connect(lambda name, w=w, j=j: self._img_done(j, w, name))
            j.failed.connect(lambda _e, w=w, j=j: self._img_done(j, w, None))
            self.jobs.append(j)
            j.start()

    def _img_done(self, j, w, name):
        if j in self.jobs:
            self.jobs.remove(j)
        fields = {"img_tried": datetime.now().isoformat(timespec="seconds")}
        if name:
            fields["image"] = name
        if self.store.get("wishlist", w["id"]):
            self.store.update("wishlist", w["id"], **fields)
            if name:
                self.refresh()
