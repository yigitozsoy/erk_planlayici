"""Ctrl+N: tek satırlık hızlı ekle (quick.parse). Yazarken altta ne ekleneceği görünür; Enter ekler, Esc kapatır.
"Formlar" düğmesi eski menüyü (window.quick_add_menu) açar."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton

from .i18n import t, fmt_day, fmt_money
from .quick import parse_for, repeat_label
from .widgets import ThemedDialog


def describe(store, coll, data):
    """Önizleme parçaları: [(etiket, değer)]."""
    if coll == "transactions":
        return [(t("qc_expense"), fmt_money(data.get("amount") or 0)), (t("f_category"), data.get("category", "")),
                ] + ([(t("f_note"), data["note"])] if data.get("note") else [])
    out = [(t("qc_task"), data.get("title", ""))]
    from .store import parse_date
    d = parse_date(data.get("due"))
    if d:
        out.append((t("f_due"), fmt_day(d) + (f" {data['time']}" if data.get("time") else "")
                    + (f"–{data['end']}" if data.get("end") else "")))
    out.append((t("f_category"), t("cat_" + data.get("category", "personal"))))
    if data.get("priority") != "normal":
        out.append((t("f_priority"), t("prio_" + data["priority"])))
    if data.get("repeat"):
        out.append((t("f_repeat"), repeat_label(data["repeat"], t)))
    if data.get("project"):
        p = store.get("projects", data["project"])
        if p:
            out.append((t("f_project"), p.get("name", "")))
    return out


class QuickDialog(ThemedDialog):
    def __init__(self, win):
        super().__init__(win, t("qc_title"))
        self.win = win
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)
        self.edit = QLineEdit()
        self.edit.setObjectName("Search")
        self.edit.setPlaceholderText(t("qc_ph"))
        self.edit.textChanged.connect(self._preview)
        self.edit.returnPressed.connect(self._add)
        v.addWidget(self.edit)
        self.prev = QLabel()
        self.prev.setObjectName("RowSub")
        self.prev.setWordWrap(True)
        self.prev.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(self.prev)
        help_ = QLabel(t("qc_help"))
        help_.setObjectName("Secondary")
        help_.setWordWrap(True)
        v.addWidget(help_)
        foot = QHBoxLayout()
        forms = QPushButton(t("qc_forms"))
        forms.setObjectName("Flat")
        forms.setCursor(Qt.CursorShape.PointingHandCursor)
        forms.clicked.connect(self._forms)
        foot.addWidget(forms)
        foot.addStretch(1)
        self.btn = QPushButton(t("qc_add"))
        self.btn.setObjectName("Primary")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._add)
        foot.addWidget(self.btn)
        v.addLayout(foot)
        self._preview("")

    def parsed(self):
        text = self.edit.text().strip()
        if not text:
            return None, None
        return parse_for(self.win.store, text)

    def _preview(self, _text):
        coll, data = self.parsed()
        self.btn.setEnabled(coll is not None)
        if coll is None:
            self.prev.setText(t("qc_empty"))
            return
        parts = describe(self.win.store, coll, data)
        self.prev.setText("  ·  ".join(f"{k}: <b>{_esc(v)}</b>" for k, v in parts if v))

    def _add(self):
        coll, data = self.parsed()
        if coll is None:
            return
        if coll == "transactions" and not data.get("amount"):
            self.prev.setText(t("qc_no_amount"))
            return
        x = self.win.store.add(coll, data)
        s = self.win.store
        self.accept()
        self.win.toast(t("qc_added_" + coll), t("undo"), lambda: s.delete(coll, x["id"]))

    def _forms(self):
        self.reject()
        self.win.quick_add_menu()


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def open_quick(win):
    d = QuickDialog(win)
    d.edit.setFocus()
    d.exec()
