"""Notlar: solda liste (arama + kategori), sağda düzenleyici. Yazdıkça kaydedilir."""
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPlainTextEdit, QComboBox, QScrollArea,
                             QFrame, QLabel)

from ..components import Card, Row, _clear_layout
from ..i18n import t, fmt_stamp
from ..store import CATEGORIES
from ..widgets import IconButton


class NotesPage(QWidget):
    def __init__(self, store, win):
        super().__init__()
        self.store, self.win = store, win
        self.setObjectName("PageHost")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.cur = None
        self._loading = False
        self._dirty = True

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 18, 28, 24)
        root.setSpacing(16)

        # --- liste
        left = QVBoxLayout()
        left.setSpacing(10)
        head = QHBoxLayout()
        title = QLabel(t("nav_notes"))
        title.setObjectName("PageTitle")
        head.addWidget(title, 1)
        self.btn_new = IconButton("add", t("new_note") + " (Ctrl+N)", 36, 22)
        self.btn_new.clicked.connect(self.new_note)
        head.addWidget(self.btn_new)
        left.addLayout(head)
        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText(t("search_notes"))
        self.search.textChanged.connect(lambda _: self.refresh())
        self.cat_filter = QComboBox()
        self.cat_filter.addItem(t("all"), "all")
        for c in CATEGORIES:
            self.cat_filter.addItem(t("cat_" + c), c)
        self.cat_filter.setFixedWidth(120)
        self.cat_filter.currentIndexChanged.connect(lambda _: self.refresh())
        sr = QHBoxLayout()
        sr.setSpacing(8)
        sr.addWidget(self.search, 1)
        sr.addWidget(self.cat_filter)
        left.addLayout(sr)
        self.list_area = QScrollArea()
        self.list_area.setWidgetResizable(True)
        self.list_area.setFrameShape(QFrame.Shape.NoFrame)
        self.list_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lw = QWidget()
        self.list_v = QVBoxLayout(lw)
        self.list_v.setContentsMargins(0, 0, 0, 0)
        self.list_v.setSpacing(0)
        self.list_area.setWidget(lw)
        left.addWidget(self.list_area, 1)
        lw_host = QWidget()
        lw_host.setLayout(left)
        lw_host.setFixedWidth(340)
        root.addWidget(lw_host)

        # --- düzenleyici
        self.editor = Card()
        self.editor.setSizePolicy(self.editor.sizePolicy().horizontalPolicy(),
                                  self.editor.sizePolicy().Policy.Expanding)
        ev = self.editor.layout()
        ev.setContentsMargins(24, 16, 16, 16)
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.ed_title = QLineEdit()
        self.ed_title.setObjectName("NoteTitleEdit")
        self.ed_title.setPlaceholderText(t("note_title_ph"))
        self.ed_title.textChanged.connect(self._changed)
        bar.addWidget(self.ed_title, 1)
        self.ed_cat = QComboBox()
        for c in CATEGORIES:
            self.ed_cat.addItem(t("cat_" + c), c)
        self.ed_cat.currentIndexChanged.connect(self._changed)
        self.ed_cat.setFixedWidth(150)
        bar.addWidget(self.ed_cat)
        self.btn_pin = IconButton("pin_outline", t("pin_note"), 36, 20, checkable=True)
        self.btn_pin.clicked.connect(self._pin)
        bar.addWidget(self.btn_pin)
        self.btn_del = IconButton("delete", t("delete"), 36, 20)
        self.btn_del.clicked.connect(self._delete)
        bar.addWidget(self.btn_del)
        ev.insertLayout(0, bar)
        self.editor.title_lbl.hide()
        self.stamp = QLabel()
        self.stamp.setObjectName("RowSub")
        ev.insertWidget(1, self.stamp)
        self.ed_body = QPlainTextEdit()
        self.ed_body.setObjectName("NoteBody")
        self.ed_body.setPlaceholderText(t("note_body_ph"))
        self.ed_body.textChanged.connect(self._changed)
        ev.addWidget(self.ed_body, 1)
        self.empty_lbl = QLabel(t("no_note_selected"))
        self.empty_lbl.setObjectName("Empty")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ev.addWidget(self.empty_lbl, 1)
        root.addWidget(self.editor, 1)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self.commit)
        self._pending = False
        store.changed.connect(self._on_change)
        self._show_editor(False)

    # ------------------------------------------------------------ sayfa arayüzü (Page ile aynı)
    def _on_change(self, coll):
        if coll != "notes":
            return
        if self.isVisible():
            if not self._pending:
                self._pending = True
                QTimer.singleShot(0, self._do_refresh)
        else:
            self._dirty = True

    def _do_refresh(self):
        self._pending = False
        self._dirty = False
        self.refresh()

    def mark_dirty(self):
        self._dirty = True
        if self.isVisible():
            self._do_refresh()

    def showEvent(self, e):
        super().showEvent(e)
        if self._dirty:
            self._do_refresh()
        if self.cur is None:
            notes = self._filtered()
            if notes:
                self.open_note(notes[0]["id"])

    # ------------------------------------------------------------ liste
    def _filtered(self):
        q = self.search.text().strip().lower()
        cat = self.cat_filter.currentData()
        out = []
        for n in self.store.all("notes"):
            if cat != "all" and n.get("category") != cat:
                continue
            if q and q not in (n.get("title", "") + "\n" + n.get("body", "")).lower():
                continue
            out.append(n)
        out.sort(key=lambda n: n.get("updated") or "", reverse=True)
        out.sort(key=lambda n: not n.get("pinned"))
        return out

    def refresh(self):
        _clear_layout(self.list_v)
        notes = self._filtered()
        for n in notes:
            body = (n.get("body") or "").strip().replace("\n", " ")
            sub = fmt_stamp(n.get("updated")) + ("  ·  " + body[:60] if body else "")
            r = Row(n.get("title") or t("untitled"), sub, icon="pin" if n.get("pinned") else "notes",
                    icon_role="text" if n["id"] == self.cur else "text2")
            if n["id"] == self.cur:
                r.setStyleSheet("#Row { background: rgba(127,127,127,0.18); }")
            r.clicked.connect(lambda nid=n["id"]: self.open_note(nid))
            self.list_v.addWidget(r)
        if not notes:
            lbl = QLabel(t("no_notes") if not self.search.text() else t("no_match"))
            lbl.setObjectName("Empty")
            lbl.setWordWrap(True)
            self.list_v.addWidget(lbl)
        self.list_v.addStretch(1)
        if self.cur and self.store.get("notes", self.cur) is None:
            self.cur = None
            self._show_editor(False)

    # ------------------------------------------------------------ düzenleyici
    def _show_editor(self, on):
        for w in (self.ed_title, self.ed_cat, self.btn_pin, self.btn_del, self.stamp, self.ed_body):
            w.setVisible(on)
        self.empty_lbl.setVisible(not on)

    def new_note(self):
        self.commit()
        cat = self.cat_filter.currentData()
        cat = cat if cat != "all" else "personal"
        n = self.store.add("notes", {"title": "", "body": "", "category": cat, "pinned": False,
                                     "updated": datetime.now().isoformat(timespec="seconds")})
        self.search.clear()
        self.open_note(n["id"])
        self.ed_title.setFocus()

    def open_note(self, nid):
        self.commit()
        self._drop_if_empty(except_id=nid)
        n = self.store.get("notes", nid)
        if n is None:
            return
        self.cur = nid
        self._loading = True
        self.ed_title.setText(n.get("title", ""))
        self.ed_body.setPlainText(n.get("body", ""))
        i = self.ed_cat.findData(n.get("category") or "personal")
        self.ed_cat.setCurrentIndex(max(0, i))
        self.btn_pin.setChecked(bool(n.get("pinned")))
        self.btn_pin.set_icon_name("pin" if n.get("pinned") else "pin_outline")
        self.stamp.setText(t("edited_at", d=fmt_stamp(n.get("updated"))))
        self._loading = False
        self._show_editor(True)
        self.refresh()

    def _drop_if_empty(self, except_id=None):
        """Hiç yazılmadan bırakılan yeni not sessizce silinir."""
        if self.cur and self.cur != except_id:
            n = self.store.get("notes", self.cur)
            if n is not None and not (n.get("title") or "").strip() and not (n.get("body") or "").strip():
                self.store.delete("notes", self.cur)

    def _changed(self, *_):
        if self._loading or self.cur is None:
            return
        self._save_timer.start()

    def commit(self):
        """Bekleyen yazıyı hemen kaydeder (sayfa değişirken / kapanırken)."""
        if not self._save_timer.isActive() or self.cur is None:
            self._save_timer.stop()
            return
        self._save_timer.stop()
        n = self.store.get("notes", self.cur)
        if n is None:
            return
        fields = {"title": self.ed_title.text().strip(), "body": self.ed_body.toPlainText(),
                  "category": self.ed_cat.currentData()}
        if any(n.get(k) != v for k, v in fields.items()):
            fields["updated"] = datetime.now().isoformat(timespec="seconds")
            self.store.update("notes", self.cur, **fields)
            self.stamp.setText(t("edited_at", d=fmt_stamp(fields["updated"])))

    def _pin(self):
        if self.cur is None:
            return
        on = self.btn_pin.isChecked()
        self.btn_pin.set_icon_name("pin" if on else "pin_outline")
        self.store.update("notes", self.cur, pinned=on)

    def _delete(self):
        if self.cur is None:
            return
        self._save_timer.stop()
        removed = self.store.delete("notes", self.cur)
        self.cur = None
        self._show_editor(False)
        if removed:
            self.win.toast(t("deleted"), t("undo"), lambda: (self.store.restore(removed),
                                                             self.open_note(removed[0][2]["id"])))

    def hideEvent(self, e):
        self.commit()
        self._drop_if_empty()
        if self.cur and self.store.get("notes", self.cur) is None:
            self.cur = None
            self._show_editor(False)
        super().hideEvent(e)
