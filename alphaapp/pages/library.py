"""Kütüphane: kitap, film, dizi, belgesel, oyun, podcast, makale. Üstte tür ve durum çipleri, altında raf
(pages/shelf.py: sırtlar, fareyle dışarı çıkma, tıkla = kitap açılır / disk çıkar).
Ekle → arama penceresi (library.search, arka planda) → sonucu seç → kapak iner → düzenleme formu (forms "media")."""
import os
import webbrowser

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer
from PyQt6.QtGui import QPainter, QPixmap, QPainterPath, QIcon
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget,
                             QListWidgetItem, QMenu)

from .. import icons, library
from ..config import IMAGES_DIR, prefs
from ..components import Page, Card, ChipBar, StatTile, TileGrid
from ..forms import edit_item, delete_item
from ..i18n import t
from ..theme import theme, qcolor, color
from ..widgets import ThemedDialog


def type_name(k):
    return t("mt_" + k)


# ============================================================ kapak
_cache = {}


def cover_pixmap(m, w, h, radius=8):
    """Kapak (kırpılarak doldurur, köşeler yuvarlak). Kapak yoksa tür ikonu + başlık gri karoda."""
    path = os.path.join(IMAGES_DIR, m["cover"]) if m.get("cover") else None
    has = bool(path and os.path.exists(path))
    key = (path if has else None, m.get("title"), m.get("type"), int(w), int(h), color("surface"), color("text2"))
    if key in _cache:
        return _cache[key]
    dpr = 2
    pm = QPixmap(int(w * dpr), int(h * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.setClipPath(clip)
    img = QPixmap(path) if has else QPixmap()
    if not img.isNull():
        sc = img.scaled(int(w * dpr), int(h * dpr), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation)
        sc.setDevicePixelRatio(dpr)
        sw, sh = sc.width() / dpr, sc.height() / dpr
        p.drawPixmap(QPointF((w - sw) / 2, (h - sh) / 2), sc)
    else:
        p.fillRect(QRectF(0, 0, w, h), qcolor("surface"))
        isz = int(min(w, h) * 0.34)       # kapak yok: tür ikonu (başlık zaten altında yazıyor)
        p.drawPixmap(QPointF((w - isz) / 2, (h - isz) / 2),
                     icons.pixmap(library.TYPE_ICON.get(m.get("type"), "library"), color("text3"), isz))
    p.end()
    if len(_cache) > 400:
        _cache.clear()
    _cache[key] = pm
    return pm


def stars(r):
    try:
        r = float(r)
    except (TypeError, ValueError):
        return ""
    if r <= 0:
        return ""
    return "★" * int(r) + ("½" if r - int(r) >= 0.5 else "")


def media_menu(win, m, pos):
    s = win.store
    menu = QMenu(win)
    menu.addAction(t("edit"), lambda: edit_item(win, "media", m))
    if m.get("status") == "doing":
        menu.addAction(t("lib_bump"), lambda: library.bump(s, m))
    menu.addSeparator()
    from datetime import date
    for st in library.STATUSES:
        if st != m.get("status"):
            fields = {"status": st}
            if st == "done" and not m.get("finished"):
                fields["finished"] = date.today().isoformat()
            if st == "doing" and not m.get("started"):
                fields["started"] = date.today().isoformat()
            menu.addAction(t("lib_mark", s=t("ms_" + st)), lambda f=fields: s.update("media", m["id"], **f))
    links = [(k, v) for k, v in (("link", m.get("link")),) + tuple((m.get("links") or {}).items()) if v]
    if links:
        menu.addSeparator()
        for k, url in links:
            menu.addAction(t("lib_open_" + k) if k != "link" else t("lib_open_link"),
                           lambda u=url: webbrowser.open(u))
    menu.addSeparator()
    menu.addAction(t("delete"), lambda: delete_item(win, "media", m))
    menu.exec(pos)


# ============================================================ arama penceresi
class SearchDialog(ThemedDialog):
    """Tür seç, yaz, Enter: sonuçlar kapaklarıyla gelir. Seç → ayrıntı + kapak iner → preset (düzenleme formu)."""

    def __init__(self, win, mtype="book", text=""):
        super().__init__(win, t("lib_add"))
        self.win = win
        self.preset = None
        self.results = []
        self.jobs = []
        self.resize(620, 620)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 16)
        v.setSpacing(10)
        h = QLabel(t("lib_add"))
        h.setStyleSheet("font-size: 18px; font-weight: 700;")
        v.addWidget(h)
        self.types = ChipBar([(k, type_name(k)) for k in library.TYPES], mtype)
        self.types.changed.connect(self._type_changed)
        v.addWidget(self.types)
        row = QHBoxLayout()
        self.ed = QLineEdit(text)
        self.ed.setObjectName("Search")
        self.ed.returnPressed.connect(self._search)
        row.addWidget(self.ed, 1)
        b = QPushButton(t("lib_search"))
        b.setObjectName("Primary")
        b.clicked.connect(self._search)
        row.addWidget(b)
        v.addLayout(row)
        # TMDB anahtarı (yalnızca film / dizi / belgesel ararken ve anahtar yoksa)
        self.key_box = QWidget()
        kl = QHBoxLayout(self.key_box)
        kl.setContentsMargins(0, 0, 0, 0)
        self.key_ed = QLineEdit()
        self.key_ed.setPlaceholderText(t("lib_tmdb_ph"))
        self.key_ed.setEchoMode(QLineEdit.EchoMode.Password)
        kl.addWidget(self.key_ed, 1)
        kb = QPushButton(t("save"))
        kb.setObjectName("Pill")
        kb.clicked.connect(self._save_key)
        kl.addWidget(kb)
        v.addWidget(self.key_box)
        self.info = QLabel("")
        self.info.setObjectName("Secondary")
        self.info.setWordWrap(True)
        self.info.setOpenExternalLinks(True)
        v.addWidget(self.info)
        self.list = QListWidget()
        self.list.setIconSize(QSize(46, 68))
        self.list.setSpacing(2)
        self.list.itemActivated.connect(self._pick)
        self.list.itemClicked.connect(self._pick)
        v.addWidget(self.list, 1)
        foot = QHBoxLayout()
        manual = QPushButton(t("lib_manual"))
        manual.setObjectName("Flat")
        manual.clicked.connect(self._manual)
        foot.addWidget(manual)
        foot.addStretch(1)
        c = QPushButton(t("cancel"))
        c.setObjectName("Flat")
        c.clicked.connect(self.reject)
        foot.addWidget(c)
        v.addLayout(foot)
        self._type_changed(mtype)
        if text:
            QTimer.singleShot(0, self._search)

    def _type_changed(self, k):
        self.ed.setPlaceholderText(t("lib_ph_" + k))
        need_key = k in ("film", "series", "doc") and not (prefs.get("tmdb_key") or "").strip()
        self.key_box.setVisible(need_key)
        self.info.setText(t("lib_tmdb_need") if need_key else "")
        self.list.clear()
        self.ed.setFocus()

    def _save_key(self):
        k = self.key_ed.text().strip()
        if k:
            prefs.set("tmdb_key", k)
            self.key_box.hide()
            self.info.setText("")
            if self.ed.text().strip():
                self._search()

    def _job(self, fn, *args, done=None, failed=None):
        j = library.Job(fn, *args, parent=self)
        if done:
            j.done.connect(done)
        if failed:
            j.failed.connect(failed)
        self.jobs.append(j)
        return j.start()

    def _search(self):
        text = self.ed.text().strip()
        if not text:
            return
        self.list.clear()
        self.info.setText(t("lib_searching"))
        self._job(library.search, self.types.current, text, done=self._show, failed=self._fail)

    def _fail(self, why):
        self.info.setText(t("lib_tmdb_need") if why == "nokey" else t("lib_error"))
        if why == "nokey":
            self.key_box.show()

    def _show(self, res):
        self.results = res or []
        self.list.clear()
        self.info.setText("" if self.results else t("lib_nothing"))
        ph = QPixmap(46, 68)
        ph.fill(qcolor("surface"))
        for i, r in enumerate(self.results):
            sub = " · ".join(str(x) for x in (r.get("creator"), r.get("year"), ", ".join(r.get("genres") or []))
                             if x)
            it = QListWidgetItem(QIcon(ph), f"{r.get('title')}\n{sub}")
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.list.addItem(it)
            if r.get("cover_url"):
                self._job(lambda u=r["cover_url"]: library._get(u, raw=True)[0],
                          done=lambda data, it=it: self._thumb(it, data))

    def _thumb(self, it, data):
        pm = QPixmap()
        if pm.loadFromData(data):
            try:
                it.setIcon(QIcon(pm.scaled(46, 68, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation)))
            except RuntimeError:
                pass

    def _pick(self, it):
        r = self.results[it.data(Qt.ItemDataRole.UserRole)]
        self.info.setText(t("lib_fetching"))
        self.list.setEnabled(False)
        mtype = self.types.current

        def work():
            extra = {}
            if (r.get("source") or "").startswith("tmdb:"):
                try:
                    extra = library.tmdb_details(r["source"])
                except Exception:
                    extra = {}
            elif (r.get("source") or "").startswith("steam:"):
                try:
                    extra = library.steam_details(r["source"])
                except Exception:
                    extra = {}
            # Steam'in dikey kapağı her oyunda yok → yatay başlık görseline düş
            cover = library.download_cover(r.get("cover_url")) or                 library.download_cover(extra.get("alt_cover") or r.get("alt_cover"))
            return extra, cover
        self._job(work, done=lambda res: self._picked(mtype, r, *res),
                  failed=lambda _w: self._picked(mtype, r, {}, None))

    def _picked(self, mtype, r, extra, cover):
        d = dict(r, **{k: v for k, v in extra.items() if v})
        self.preset = {"type": mtype, "title": d.get("title"), "creator": d.get("creator") or "",
                       "year": int(d["year"]) if str(d.get("year") or "").isdigit() else None,
                       "genres": ", ".join(g for g in (d.get("genres") or []) if g), "total": d.get("total"),
                       "cover": cover, "link": d.get("link"), "links": d.get("links") or {},
                       "source": d.get("source"), "status": "want", "seasons": d.get("seasons")}
        self.accept()

    def _manual(self):
        self.preset = {"type": self.types.current, "title": self.ed.text().strip(), "status": "want"}
        self.accept()


def add_media(win, mtype="book", text=""):
    d = SearchDialog(win, mtype, text)
    if d.exec() and d.preset is not None:
        return edit_item(win, "media", preset=d.preset)
    return None


# ============================================================ sayfa
class LibraryPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_library"), t("library_sub"))
        self.action(t("lib_add"), lambda: add_media(win, self.f_type.current if self.f_type.current != "all"
                                                   else "book"), primary=True, icon="add")
        self.t_books = StatTile(t("lib_books_year"))
        self.t_films = StatTile(t("lib_films_year"))
        self.t_series = StatTile(t("lib_series_year"))
        self.t_now = StatTile(t("lib_now"))
        self.add(TileGrid([self.t_books, self.t_films, self.t_series, self.t_now]))
        self.f_type = ChipBar([("all", t("all"))] + [(k, type_name(k)) for k in library.TYPES],
                              prefs.get("lib_type", "all"))
        self.f_type.changed.connect(lambda k: (prefs.set("lib_type", k), self.refresh()))
        self.add(self.f_type)
        self.f_status = ChipBar([("all", t("all"))] + [(k, t("ms_" + k)) for k in library.STATUSES],
                                prefs.get("lib_status", "all"))
        self.f_status.changed.connect(lambda k: (prefs.set("lib_status", k), self.refresh()))
        self.add(self.f_status)
        self.card = Card("")
        from .shelf import Shelf, open_viewer
        self.wall = Shelf()
        self.wall.clicked.connect(lambda m: open_viewer(win, m))
        self.wall.menu.connect(lambda m, pos: media_menu(win, m, pos))
        self.card.layout().addWidget(self.wall)
        self.add(self.card)

    def refresh(self):
        s = self.store
        items = s.all("media")
        self.t_books.set(str(library.year_count(s, "book")))
        self.t_films.set(str(library.year_count(s, "film") + library.year_count(s, "doc")))
        self.t_series.set(str(library.year_count(s, "series")))
        now = library.current(s)
        self.t_now.set(str(len(now)), now[0].get("title", "") if now else "")
        ty, st = self.f_type.current, self.f_status.current
        shown = [m for m in items if (ty == "all" or m.get("type") == ty) and (st == "all" or m.get("status") == st)]
        order = {k: i for i, k in enumerate(library.STATUSES)}
        tyo = {k: i for i, k in enumerate(library.TYPES)}     # rafta kitaplar, sonra DVD'ler … gruplu
        shown.sort(key=lambda m: (order.get(m.get("status"), 9), tyo.get(m.get("type"), 9),
                                  "" if m.get("status") != "done" else "~" + str(m.get("finished") or ""),
                                  (m.get("title") or "").lower()))
        # bitenler en yeni bitiş önce
        done = [m for m in shown if m.get("status") == "done"]
        done.sort(key=lambda m: str(m.get("finished") or ""), reverse=True)
        shown = [m for m in shown if m.get("status") != "done"] + done
        self.card.title_lbl.setText(t("lib_count", n=len(shown)))
        self.card.clear()
        if not shown:
            self.card.empty(t("lib_empty"))
        self.wall.setVisible(bool(shown))
        self.wall.set_items(shown)


def now_card(win):
    """Bugün sayfası için "Şu an" kartı: okunan / izlenen, + ile ilerleme. Boşsa gizli."""
    from ..components import Row
    from ..widgets import IconButton
    s = win.store
    card = Card(t("lib_now_card"), add_tip=t("lib_add"))
    card.add_clicked.connect(lambda: add_media(win))

    def fill():
        card.clear()
        items = library.current(s)[:4]
        card.setVisible(bool(items))
        for m in items:
            lead = QLabel()
            lead.setFixedSize(28, 42)
            theme.bind(lead, lambda l, m=m: l.setPixmap(cover_pixmap(m, 28, 42, 4)))
            sub = " · ".join(x for x in (type_name(m.get("type") or "book"), library.progress_text(m, t)) if x)
            r = Row(m.get("title") or "—", sub, lead=lead)
            r.clicked.connect(lambda m=m: edit_item(win, "media", m))
            r.menu_requested.connect(lambda pos, m=m: media_menu(win, m, pos))
            if m.get("type") != "film":
                b = IconButton("add", t("lib_bump"), 30, 20)
                b.clicked.connect(lambda _=False, m=m: QTimer.singleShot(0, lambda: _bump(win, m)))
                r.layout().addWidget(b)
            card.add(r)
    card.fill = fill
    return card


def _bump(win, m):
    if library.bump(win.store, m):
        win.toast(t("lib_finished", n=m.get("title") or ""))
