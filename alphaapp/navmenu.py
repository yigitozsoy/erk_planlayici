"""Sol menü düzeni: hangi sayfalar görünür, sırası, adları ve kullanıcının eklediği kategoriler.

prefs:
  nav_layout   [{"k": anahtar | "-", "h": gizli mi}]   ("-" = ayırıcı çizgi). Boşsa DEFAULT.
  nav_names    {anahtar: ad}                          kullanıcının verdiği ad (i18n.t nav_/cat_ için de kullanır)
  custom_cats  [{"id": "c_xxxxxx", "name": ad, "icon": ikon}]   eklenen kategoriler (genel kategori sayfası)
"""
import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget, QScrollArea,
                             QMenu, QMessageBox, QFrame)

from .config import prefs
from .i18n import t, S
from . import icons
from .theme import theme, color
from .widgets import IconButton, ThemedDialog, ToggleSwitch

# (anahtar, ikon, metin anahtarı) — menüde gösterilebilen yerleşik sayfalar
BUILTIN = {
    "today": ("today", "nav_today"),
    "schedule": ("schedule_week", "nav_schedule"),
    "habits": ("check_circle", "nav_habits"),
    "goals": ("track_changes", "nav_goals"),
    "education": ("cat_education", "nav_education"),
    "work": ("cat_work", "nav_work"),
    "projects": ("folder_open", "nav_projects"),
    "sport": ("cat_sport", "nav_sport"),
    "mind": ("spa", "nav_mind"),
    "social": ("group", "nav_social"),
    "finance": ("wallet", "nav_finance"),
    "personal": ("person", "nav_personal"),
    "library": ("library", "nav_library"),
    "notes": ("notes", "nav_notes"),
    "plan": ("sunrise", "nav_plan"),
}
# Varsayılan düzen (2.0'daki menü). Sonradan gelenler (Kişisel, Sabah planı) gizli olarak sona eklenir.
DEFAULT = ["today", "schedule", "habits", "goals", "-", "education", "work", "projects", "sport", "mind", "social", "finance", "-",
           "library", "notes"]
# Yeni kategori için seçilebilecek ikonlar
CAT_ICON_CHOICES = ("star", "flag", "lightbulb", "spa", "work_bag", "menu_book", "laptop", "directions_run", "cake",
                    "place", "trending_up", "calendar_month", "phone", "notes", "folder_open", "person", "group",
                    "wallet", "school", "fitness")


def custom_cats():
    return [c for c in (prefs.get("custom_cats") or []) if c.get("id")]


def is_custom(key):
    return any(c["id"] == key for c in custom_cats())


def icon(key):
    if key in BUILTIN:
        return BUILTIN[key][0]
    for c in custom_cats():
        if c["id"] == key:
            return c.get("icon") or "star"
    return "flag"


def default_label(key):
    if key in BUILTIN:
        v = S.get(BUILTIN[key][1])
        return (v[0] if prefs.get("language", "tr") == "tr" else v[1]) if v else key
    for c in custom_cats():
        if c["id"] == key:
            return c.get("name") or "—"
    return key


def label(key):
    return (prefs.get("nav_names") or {}).get(key) or default_label(key)


def all_keys():
    return list(BUILTIN) + [c["id"] for c in custom_cats()]


def layout():
    """Menü sırası: [(anahtar | "-", gizli)]; bilinmeyenler atılır, eksikler gizli olarak sona eklenir."""
    raw = prefs.get("nav_layout") or [{"k": k, "h": False} for k in DEFAULT]
    keys = set(all_keys())
    out, seen = [], set()
    for e in raw:
        k = e.get("k")
        if k == "-":
            out.append(("-", False))
        elif k in keys and k not in seen:
            seen.add(k)
            out.append((k, bool(e.get("h"))))
    for k in all_keys():
        if k not in seen:
            pos = len(out)
            if k in DEFAULT:            # sonradan eklenen varsayılan sayfa: DEFAULT'taki öncülünün ardına
                i = DEFAULT.index(k)
                prev = next((p for p in reversed(DEFAULT[:i]) if p != "-" and p in seen), None)
                if prev is not None:
                    pos = next(j for j, (kk, _h) in enumerate(out) if kk == prev) + 1
            out.insert(pos, (k, k not in DEFAULT))
            seen.add(k)
    return out


def visible():
    """Görünen menü: anahtarlar ve ayırıcılar; art arda / baştaki / sondaki ayırıcılar atılır."""
    out = []
    for k, hidden in layout():
        if hidden:
            continue
        if k == "-" and (not out or out[-1] == "-"):
            continue
        out.append(k)
    while out and out[-1] == "-":
        out.pop()
    return out


def category_keys():
    """Görev / kayıt kategorisi olarak seçilebilecekler: yerleşik altı kategori + eklenenler."""
    return [c["id"] for c in custom_cats()]


# ============================================================ düzenleme penceresi
class NavEditor(ThemedDialog):
    def __init__(self, win):
        super().__init__(win, t("nav_edit"))
        self.win = win
        self.resize(520, 640)
        self.items = [[k, h] for k, h in layout()]
        self.names = dict(prefs.get("nav_names") or {})
        self.cats = [dict(c) for c in custom_cats()]
        self.removed = []

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)
        title = QLabel(t("nav_edit"))
        title.setObjectName("CardTitle")
        v.addWidget(title)
        sub = QLabel(t("nav_edit_sub"))
        sub.setObjectName("Secondary")
        sub.setWordWrap(True)
        v.addWidget(sub)

        self.host = QWidget()
        self.list = QVBoxLayout(self.host)
        self.list.setContentsMargins(0, 0, 0, 0)
        self.list.setSpacing(2)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidget(self.host)
        v.addWidget(sc, 1)

        tools = QHBoxLayout()
        for text, ic, fn in ((t("nav_add_cat"), "add", self._add_cat), (t("nav_add_divider"), None, self._add_div),
                             (t("nav_reset"), None, self._reset)):
            b = QPushButton(text)
            b.setObjectName("Pill")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if ic:
                theme.icon(b, ic, "text", 18)
            b.clicked.connect(fn)
            tools.addWidget(b)
        tools.addStretch(1)
        v.addLayout(tools)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        cancel = QPushButton(t("cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setObjectName("Primary")
        save.setDefault(True)
        save.clicked.connect(self._save)
        bottom.addWidget(cancel)
        bottom.addWidget(save)
        v.addLayout(bottom)
        self._build()

    # ------------------------------------------------------------ liste
    def _cat(self, key):
        for c in self.cats:
            if c["id"] == key:
                return c
        return None

    def _icon_of(self, key):
        c = self._cat(key)
        return (c.get("icon") or "star") if c else icon(key)

    def _build(self):
        while self.list.count():
            w = self.list.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for i, (k, hidden) in enumerate(self.items):
            self.list.addWidget(self._row(i, k, hidden))
        self.list.addStretch(1)

    def _row(self, i, k, hidden):
        w = QWidget()
        w.setObjectName("Row")
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(6)
        up = IconButton("arrow_up", t("nav_up"), 28, 18)
        dn = IconButton("arrow_down", t("nav_down"), 28, 18)
        up.setEnabled(i > 0)
        dn.setEnabled(i < len(self.items) - 1)
        up.clicked.connect(lambda _=False, i=i: self._move(i, -1))
        dn.clicked.connect(lambda _=False, i=i: self._move(i, 1))
        h.addWidget(up)
        h.addWidget(dn)
        if k == "-":
            lbl = QLabel(t("nav_divider"))
            lbl.setObjectName("Secondary")
            h.addWidget(lbl, 1)
            rm = IconButton("delete", t("delete"), 28, 18)
            rm.clicked.connect(lambda _=False, i=i: self._remove(i))
            h.addWidget(rm)
            return w
        ib = IconButton(self._icon_of(k), t("nav_cat_icon") if self._cat(k) else "", 32, 20)
        if self._cat(k):
            ib.clicked.connect(lambda _=False, k=k, b=ib: self._pick_icon(k, b))
        h.addWidget(ib)
        ed = QLineEdit(self.names.get(k) or (self._cat(k) or {}).get("name") or default_label(k))
        ed.setPlaceholderText(default_label(k) if not self._cat(k) else t("nav_cat_name"))
        ed.textChanged.connect(lambda s, k=k: self._rename(k, s))
        h.addWidget(ed, 1)
        sw = ToggleSwitch(not hidden)
        sw.setToolTip(t("nav_show"))
        sw.toggled.connect(lambda on, i=i: self._set_hidden(i, not on))
        h.addWidget(sw)
        if self._cat(k):
            rm = IconButton("delete", t("delete"), 28, 18)
            rm.clicked.connect(lambda _=False, i=i: self._remove(i))
            h.addWidget(rm)
        else:
            h.addSpacing(28)
        return w

    def _move(self, i, d):
        j = i + d
        if 0 <= j < len(self.items):
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self._build()

    def _set_hidden(self, i, hidden):
        self.items[i][1] = hidden

    def _rename(self, k, text):
        text = text.strip()
        c = self._cat(k)
        if c is not None:
            c["name"] = text or c.get("name") or "—"
        elif text and text != default_label(k):
            self.names[k] = text
        else:
            self.names.pop(k, None)

    def _pick_icon(self, k, btn):
        m = QMenu(self)
        for ic in CAT_ICON_CHOICES:
            a = m.addAction(icons.icon(ic, color("text"), 20), "")
            a.triggered.connect(lambda _=False, ic=ic: self._set_icon(k, ic))
        m.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _set_icon(self, k, ic):
        c = self._cat(k)
        if c is not None:
            c["icon"] = ic
            self._build()

    def _remove(self, i):
        k = self.items[i][0]
        c = self._cat(k)
        if c is not None:
            n = count_items(self.win.store, k)
            if n and QMessageBox.question(self, t("nav_edit"), t("nav_del_cat_q", n=c.get("name") or "—", k=n)) \
                    != QMessageBox.StandardButton.Yes:
                return
            self.cats.remove(c)
            self.removed.append(k)
        del self.items[i]
        self._build()

    def _add_div(self):
        self.items.append(["-", False])
        self._build()

    def _add_cat(self):
        cid = "c_" + uuid.uuid4().hex[:6]
        self.cats.append({"id": cid, "name": t("nav_add_cat"), "icon": "star"})
        # notların / ekonominin üstüne, son ayırıcıdan önce koy
        pos = len(self.items)
        for j in range(len(self.items) - 1, -1, -1):
            if self.items[j][0] == "-":
                pos = j
                break
        self.items.insert(pos, [cid, False])
        self._build()
        # yeni satırın ad alanına odaklan, yazınca adı değişsin
        row = self.list.itemAt(pos).widget()
        ed = row.findChild(QLineEdit) if row else None
        if ed:
            ed.setFocus()
            ed.selectAll()

    def _reset(self):
        self.items = [[k, False] for k in DEFAULT] + [[c["id"], False] for c in self.cats]
        for k in BUILTIN:
            if k not in DEFAULT:
                self.items.append([k, True])
        self.names = {}
        self._build()

    def _save(self):
        prefs.set("custom_cats", self.cats)
        prefs.set("nav_names", self.names)
        prefs.set("nav_layout", [{"k": k, "h": bool(h)} for k, h in self.items])
        for k in self.removed:
            move_items(self.win.store, k, "personal")
        self.accept()


COLLS_WITH_CATEGORY = ("tasks", "routine", "notes", "habits", "projects")


def count_items(store, cat):
    return sum(1 for coll in COLLS_WITH_CATEGORY for x in store.all(coll) if x.get("category") == cat)


def move_items(store, cat, to):
    for coll in COLLS_WITH_CATEGORY:
        for x in store.all(coll):
            if x.get("category") == cat:
                store.update(coll, x["id"], category=to)
