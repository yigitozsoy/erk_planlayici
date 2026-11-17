"""Kütüphane > Bucket list: hayatta bir kez yapmak istediklerin, vision board ile aynı Pinterest panosu.

bucket koleksiyonu: title, category (CATS), image (DATA_DIR\\images), year (hedef yıl), place (yer adı), note,
done, done_date. Görsel: karta sürükle-bırak ya da kartın üstündeyken Ctrl+V; boşa bırakılırsa yeni madde.
Telefon sayfasına GİTMEZ.
"""
from datetime import date

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu

from ..components import Card, ChipBar
from ..config import prefs
from ..forms import edit_item, delete_item
from ..i18n import t
from .goals import BoardView

CATS = ("travel", "event", "adventure", "experience", "learn", "other")
CAT_ICON = {"travel": "flight", "event": "trophy", "adventure": "landscape", "experience": "star",
            "learn": "menu_book", "other": "flag"}
CAT_COLOR = {"travel": "#7f9cb0", "event": "#c8a35b", "adventure": "#86a878", "experience": "#d08a4e",
             "learn": "#6fa3a0", "other": "#a8a8a8"}


def cat_name(k):
    return t("bk_" + (k if k in CATS else "other"))


def toggle_done(store, x):
    if x.get("done"):
        store.update("bucket", x["id"], done=False, done_date=None)
    else:
        store.update("bucket", x["id"], done=True, done_date=date.today().isoformat())


class BucketBoard(BoardView):
    SHOW_PROGRESS = False

    def color_of(self, g):
        return QColor(CAT_COLOR.get(g.get("category"), CAT_COLOR["other"]))

    def icon_of(self, g):
        return CAT_ICON.get(g.get("category"), "flag")

    def meta_of(self, g, pr, n):
        bits = [cat_name(g.get("category"))]
        if g.get("place"):
            bits.append(g["place"])
        if g.get("done"):
            bits.append(t("bk_done_on", d=(g.get("done_date") or "")[:4]) if g.get("done_date") else t("bk_done"))
        elif g.get("year"):
            bits.append(f"→ {g['year']}")
        return " · ".join(bits)

    def add_texts(self):
        return t("bk_add"), t("bk_add_sub")


class BucketView(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win, self.store = win, win.store
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.filter = ChipBar([("all", t("all")), ("open", t("bk_open")), ("done", t("bk_done"))] +
                              [(k, cat_name(k)) for k in CATS], prefs.get("bk_filter", "all"))
        self.filter.changed.connect(lambda k: (prefs.set("bk_filter", k), self.refresh()))
        v.addWidget(self.filter)
        self.card = Card(t("bucket"), t("bucket_sub"))
        self.board = BucketBoard()
        self.board.goal_clicked.connect(lambda x: edit_item(win, "bucket", x))
        self.board.add_requested.connect(self._add)
        self.board.image_in.connect(self._image_in)
        self.board.menu_at.connect(self._menu)
        self.card.layout().addWidget(self.board)
        v.addWidget(self.card)

    def _add(self, image=None):
        cat = self.filter.current if self.filter.current in CATS else "experience"
        pr = {"category": cat}
        if image:
            pr["image"] = image
        edit_item(self.win, "bucket", preset=pr)

    def _image_in(self, x, name):
        if x is not None:
            old = x.get("image")
            self.store.update("bucket", x["id"], image=name)
            self.win.toast(t("pin_image_set"), t("undo"), lambda: self.store.update("bucket", x["id"], image=old))
        else:
            self._add(name)

    def _menu(self, x, pos):
        m = QMenu(self.win)
        m.addAction(t("bk_undo_done") if x.get("done") else t("bk_mark_done"),
                    lambda: toggle_done(self.store, x))
        m.addAction(t("edit"), lambda: edit_item(self.win, "bucket", x))
        m.addSeparator()
        m.addAction(t("delete"), lambda: delete_item(self.win, "bucket", x))
        m.exec(pos)

    def refresh(self):
        items = self.store.all("bucket")
        f = self.filter.current
        shown = [x for x in items if f == "all" or (f == "open" and not x.get("done")) or
                 (f == "done" and x.get("done")) or x.get("category") == f]
        shown.sort(key=lambda x: (bool(x.get("done")), str(x.get("year") or 9999), x.get("created") or ""))
        done = sum(1 for x in items if x.get("done"))
        self.card.set_sub(t("bucket_stats", d=done, n=len(items)) if items else t("bucket_sub"))
        self.board.set_goals(shown, {}, {})
