"""Form kısayolları: edit_item, delete_item (geri al), item_menu, bind_row."""
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from ..i18n import t
from .dialog import FormDialog


# ============================================================ yardımcılar
def edit_item(win, coll, item=None, preset=None):
    """Ekle / düzenle penceresini açar. Silinirse geri al bildirimi gösterir."""
    store = win.store
    if coll == "exams" and not store.all("courses"):
        win.toast(t("need_course"))
        return None
    d = FormDialog(win, store, coll, item, preset)
    if d.exec():
        if d.deleted:
            delete_item(win, coll, item)
            return None
        if d.coll != coll:            # görev formundan sınav olarak kaydedildi
            win.toast(t("saved_as_exam"))
        return d.item
    return None


def delete_item(win, coll, item):
    removed = win.store.delete(coll, item["id"])
    if removed:
        win.toast(t("deleted"), t("undo"), lambda: win.store.restore(removed))


def item_menu(win, coll, item, pos, extra=()):
    """Sağ tık menüsü: [ek eylemler] · Düzenle · Sil."""
    m = QMenu(win)
    for text, cb in extra:
        a = QAction(text, m)
        a.triggered.connect(cb)
        m.addAction(a)
    if extra:
        m.addSeparator()
    a = QAction(t("edit"), m)
    a.triggered.connect(lambda: edit_item(win, coll, item))
    m.addAction(a)
    a = QAction(t("delete"), m)
    a.triggered.connect(lambda: delete_item(win, coll, item))
    m.addAction(a)
    m.exec(pos)


def bind_row(win, row, coll, item, extra=()):
    row.clicked.connect(lambda: edit_item(win, coll, item))
    row.menu_requested.connect(lambda pos: item_menu(win, coll, item, pos, extra))
    return row
