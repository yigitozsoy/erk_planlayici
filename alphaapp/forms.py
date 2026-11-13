"""Kayıt ekleme / düzenleme: her koleksiyonun alanları şemayla tanımlanır, tek bir form penceresi hepsini çizer."""
from datetime import date

from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDateEdit, QTimeEdit,
                             QPlainTextEdit, QPushButton, QWidget, QMenu, QGridLayout)

from .i18n import t, WEEKDAYS_SHORT
from .store import CATEGORIES, parse_date, num
from .widgets import ThemedDialog, ToggleSwitch

LETTERS = ("AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF")

TASK_PRIORITIES = ("normal", "high", "low")
PROJECT_STATUS = ("doing", "todo", "waiting", "done")

WORKOUT_KINDS = ("Gym", "Koşu", "Yüzme", "Bisiklet", "Yürüyüş", "Futbol", "Basketbol", "Tenis", "Yoga", "Pilates",
                 "Dövüş sporu", "Diğer")
WORKOUT_FOCUS = ("Göğüs", "Sırt", "Bacak", "Omuz", "Kol", "Karın / core", "Tüm vücut", "Push", "Pull", "Legs",
                 "Kardiyo", "Esneme")
EXAM_NAMES = ("Vize", "Vize 2", "Final", "Bütünleme", "Quiz", "Ödev", "Proje", "Lab", "Sunum")
EXPENSE_CATS = ("Yemek", "Market", "Ulaşım", "Kira", "Faturalar", "Abonelik", "Eğlence", "Giyim", "Eğitim", "Sağlık",
                "Spor", "Hediye", "Diğer")
INCOME_CATS = ("Maaş", "Burs", "Harçlık", "Serbest iş", "Satış", "Faiz / getiri", "Diğer")
INVEST_KINDS = ("Hisse", "Fon", "Altın", "Döviz", "Kripto", "Mevduat", "Tahvil / bono", "Diğer")


# alan: (anahtar, etiket anahtarı, tür, seçenekler)
#   tür: text · multiline · date · date? (isteğe bağlı) · time? · number · number? · money · money? · choice ·
#        combo (yazılabilir öneri listesi) · days · bool
def schema(coll, store):
    if coll == "tasks":
        return [("title", "f_title", "text", None),
                ("category", "f_category", "choice", [(c, t("cat_" + c)) for c in CATEGORIES]),
                ("due", "f_due", "date?", None),
                ("time", "f_time", "time?", None),
                ("priority", "f_priority", "choice", [(p, t("prio_" + p)) for p in TASK_PRIORITIES]),
                ("note", "f_note", "multiline", None)]
    if coll == "routine":
        return [("title", "f_title", "text", None),
                ("category", "f_category", "choice", [(c, t("cat_" + c)) for c in CATEGORIES]),
                ("days", "f_days", "days", None),
                ("start", "f_start", "time?", None),
                ("end", "f_end", "time?", None),
                ("place", "f_place", "text", None)]
    if coll == "courses":
        return [("name", "f_course_name", "text", None),
                ("code", "f_code", "text", None),
                ("credits", "f_credits", "number?", None),
                ("target", "f_target_letter", "choice", [("", "—")] + [(x, x) for x in LETTERS]),
                ("note", "f_note", "multiline", None)]
    if coll == "exams":
        courses = [(c["id"], c.get("name", "")) for c in store.all("courses")]
        return [("course", "f_course", "choice", courses),
                ("name", "f_exam_name", "combo", _with_used(EXAM_NAMES, store, "exams", "name")),
                ("date", "f_date", "date?", None),
                ("weight", "f_weight", "number?", None),
                ("target", "f_target_score", "number?", None),
                ("score", "f_score", "number?", None)]
    if coll == "workouts":
        return [("date", "f_date", "date", None),
                ("kind", "f_kind", "combo", _with_used(WORKOUT_KINDS, store, "workouts", "kind")),
                ("focus", "f_focus", "combo", _with_used(WORKOUT_FOCUS, store, "workouts", "focus")),
                ("minutes", "f_minutes", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "projects":
        return [("name", "f_project_name", "text", None),
                ("status", "f_status", "choice", [(s, t("status_" + s)) for s in PROJECT_STATUS]),
                ("due", "f_due", "date?", None),
                ("progress", "f_progress", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "events":
        return [("title", "f_title", "text", None),
                ("date", "f_date", "date", None),
                ("time", "f_time", "time?", None),
                ("people", "f_people", "text", None),
                ("place", "f_place", "text", None),
                ("note", "f_note", "multiline", None)]
    if coll == "birthdays":
        return [("name", "f_person", "text", None),
                ("date", "f_birthday", "date", None)]
    if coll == "transactions":
        return [("kind", "f_tx_kind", "choice", [("expense", t("expense")), ("income", t("income"))]),
                ("amount", "f_amount", "money", None),
                ("category", "f_category", "combo",
                 _with_used(EXPENSE_CATS + INCOME_CATS, store, "transactions", "category")),
                ("date", "f_date", "date", None),
                ("note", "f_note", "text", None)]
    if coll == "debts":
        return [("direction", "f_direction", "choice", [("owe", t("dir_owe")), ("owed", t("dir_owed"))]),
                ("person", "f_person", "text", None),
                ("amount", "f_amount", "money", None),
                ("due", "f_due", "date?", None),
                ("settled", "f_settled", "bool", None),
                ("note", "f_note", "text", None)]
    if coll == "investments":
        return [("name", "f_inv_name", "text", None),
                ("kind", "f_kind", "combo", _with_used(INVEST_KINDS, store, "investments", "kind")),
                ("invested", "f_invested", "money", None),
                ("value", "f_value", "money?", None),
                ("date", "f_date", "date", None),
                ("note", "f_note", "text", None)]
    if coll == "habits":
        return [("name", "f_habit_name", "text", None),
                ("category", "f_category", "choice", [(c, t("cat_" + c)) for c in CATEGORIES]),
                ("goal", "f_goal_days", "number?", None),
                ("note", "f_note", "text", None)]
    if coll == "meals":
        return [("name", "f_meal_name", "combo", _with_used([], store, "meals", "name")),
                ("date", "f_date", "date", None),
                ("kcal", "f_kcal", "number?", None),
                ("protein", "f_protein", "number?", None),
                ("carbs", "f_carbs", "number?", None),
                ("fat", "f_fat", "number?", None)]
    raise KeyError(coll)


REQUIRED = {"tasks": "title", "routine": "title", "courses": "name", "exams": "course", "projects": "name",
            "events": "title", "birthdays": "name", "debts": "person", "investments": "name",
            "transactions": "amount", "workouts": "date", "habits": "name", "meals": "name"}


def _with_used(base, store, coll, key):
    seen = list(base)
    for x in store.all(coll):
        v = (x.get(key) or "").strip()
        if v and v not in seen:
            seen.append(v)
    return seen


def defaults(coll):
    d = date.today().isoformat()
    return {
        "tasks": {"category": "personal", "priority": "normal"},
        "routine": {"category": "education", "days": [date.today().weekday()], "start": "09:00", "end": "10:00"},
        "exams": {"name": "Vize", "weight": 40},
        "workouts": {"date": d, "kind": "Gym"},
        "projects": {"status": "doing", "progress": 0},
        "events": {"date": d},
        "transactions": {"kind": "expense", "date": d, "category": "Yemek"},
        "debts": {"direction": "owe"},
        "investments": {"date": d, "kind": "Hisse"},
        "habits": {"category": "personal", "goal": 7},
        "meals": {"date": d},
    }.get(coll, {})


# ============================================================ alan bileşenleri
class OptDate(QWidget):
    def __init__(self, value, optional, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.sw = None
        if optional:
            self.sw = ToggleSwitch(bool(value))
            self.sw.toggled.connect(self._sync)
            lay.addWidget(self.sw)
        self.ed = QDateEdit()
        self.ed.setCalendarPopup(True)
        self.ed.setDisplayFormat("d MMMM yyyy, dddd")
        d = parse_date(value) or date.today()
        self.ed.setDate(QDate(d.year, d.month, d.day))
        lay.addWidget(self.ed, 1)
        self._sync()

    def _sync(self, *_):
        self.ed.setEnabled(self.sw is None or self.sw.isChecked())

    def value(self):
        if self.sw is not None and not self.sw.isChecked():
            return None
        q = self.ed.date()
        return date(q.year(), q.month(), q.day()).isoformat()


class OptTime(QWidget):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.sw = ToggleSwitch(bool(value))
        self.sw.toggled.connect(lambda v: self.ed.setEnabled(v))
        lay.addWidget(self.sw)
        self.ed = QTimeEdit()
        self.ed.setDisplayFormat("HH:mm")
        tm = QTime.fromString(value or "09:00", "HH:mm")
        self.ed.setTime(tm if tm.isValid() else QTime(9, 0))
        self.ed.setEnabled(bool(value))
        lay.addWidget(self.ed, 1)

    def value(self):
        return self.ed.time().toString("HH:mm") if self.sw.isChecked() else None


class DaysPicker(QWidget):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.btns = []
        sel = set(value or [])
        for i, name in enumerate(WEEKDAYS_SHORT()):
            b = QPushButton(name)
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setChecked(i in sel)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(b)
            self.btns.append(b)
        lay.addStretch(1)

    def value(self):
        return [i for i, b in enumerate(self.btns) if b.isChecked()]


def _fmt_num(v):
    if v in (None, ""):
        return ""
    f = num(v)
    s = f"{f:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _parse_num(s):
    s = (s or "").strip().replace(" ", "")
    if not s:
        return None
    # 12.345,67 → 12345.67 · 12,5 → 12.5 · 12.5 → 12.5
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# ============================================================ form penceresi
class FormDialog(ThemedDialog):
    def __init__(self, parent, store, coll, item=None, preset=None):
        title = t(("edit_" if item else "new_") + coll)
        super().__init__(parent, title)
        self.store, self.coll, self.item = store, coll, item
        self.deleted = False
        self.setMinimumWidth(460)
        data = dict(defaults(coll))
        data.update(preset or {})
        if item:
            data.update(item)
        self.fields = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(12)
        h = QLabel(title)
        h.setObjectName("SectionTitle")
        h.setStyleSheet("font-size: 18px; font-weight: 700;")
        outer.addWidget(h)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        first = None
        for r, (key, label, kind, opts) in enumerate(schema(coll, store)):
            lbl = QLabel(t(label))
            lbl.setObjectName("FieldLabel")
            w = self._make(kind, data.get(key), opts)
            self.fields[key] = (kind, w)
            al = Qt.AlignmentFlag.AlignTop if kind == "multiline" else Qt.AlignmentFlag.AlignVCenter
            grid.addWidget(lbl, r, 0, al)
            grid.addWidget(w, r, 1)
            if first is None and kind in ("text", "money", "combo"):
                first = w
        outer.addLayout(grid)
        self.err = QLabel("")
        self.err.setObjectName("StatBad")
        self.err.hide()
        outer.addWidget(self.err)
        foot = QHBoxLayout()
        foot.setSpacing(8)
        if item:
            bd = QPushButton(t("delete"))
            bd.setObjectName("Danger")
            bd.clicked.connect(self._delete)
            foot.addWidget(bd)
        foot.addStretch(1)
        bc = QPushButton(t("cancel"))
        bc.setObjectName("Flat")
        bc.clicked.connect(self.reject)
        bs = QPushButton(t("save"))
        bs.setObjectName("Primary")
        bs.setDefault(True)
        bs.clicked.connect(self._save)
        foot.addWidget(bc)
        foot.addWidget(bs)
        outer.addSpacing(4)
        outer.addLayout(foot)
        if first is not None:
            first.setFocus()
            if isinstance(first, QLineEdit):
                first.selectAll()
        if coll == "transactions":
            self._tx_hook()
        if coll == "meals" and item is None:
            self._meal_hook()

    def _make(self, kind, v, opts):
        if kind == "text":
            w = QLineEdit(str(v or ""))
            w.returnPressed.connect(self._save)
            return w
        if kind == "multiline":
            w = QPlainTextEdit(str(v or ""))
            w.setFixedHeight(76)
            w.setTabChangesFocus(True)
            return w
        if kind in ("number", "number?", "money", "money?"):
            w = QLineEdit(_fmt_num(v))
            w.setPlaceholderText("0" if not kind.endswith("?") else "—")
            w.returnPressed.connect(self._save)
            return w
        if kind in ("date", "date?"):
            return OptDate(v, kind == "date?")
        if kind == "time?":
            return OptTime(v)
        if kind == "choice":
            w = QComboBox()
            for k, label in opts:
                w.addItem(label, k)
            i = w.findData(v)
            w.setCurrentIndex(max(0, i))
            return w
        if kind == "combo":
            w = QComboBox()
            w.setEditable(True)
            w.addItems(list(opts))
            w.setCurrentText(str(v or ""))
            w.lineEdit().returnPressed.connect(self._save)
            return w
        if kind == "days":
            return DaysPicker(v)
        if kind == "bool":
            box = QWidget()
            lay = QHBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            sw = ToggleSwitch(bool(v))
            lay.addWidget(sw)
            lay.addStretch(1)
            box.sw = sw
            return box
        raise ValueError(kind)

    def _meal_hook(self):
        """Daha önce yenmiş bir öğün seçilince kalori / makrolar son kayıttan dolsun (boşsa)."""
        name_w = self.fields["name"][1]

        def changed(text):
            key = text.strip().lower()
            prev = [m for m in self.store.all("meals") if (m.get("name") or "").strip().lower() == key]
            if not prev:
                return
            last = max(prev, key=lambda m: m.get("created") or "")
            for k in ("kcal", "protein", "carbs", "fat"):
                w = self.fields[k][1]
                if not w.text().strip() and last.get(k) not in (None, ""):
                    from .i18n import fmt_num
                    w.setText(fmt_num(last[k], 1))
        name_w.currentTextChanged.connect(changed)

    def _tx_hook(self):
        """Gelir seçilince kategori önerisi gelir kategorilerine geçsin."""
        kind_w = self.fields["kind"][1]
        cat_w = self.fields["category"][1]

        def changed():
            cur = cat_w.currentText()
            if kind_w.currentData() == "income" and (not cur or cur in EXPENSE_CATS):
                cat_w.setCurrentText(INCOME_CATS[0])
            elif kind_w.currentData() == "expense" and (not cur or cur in INCOME_CATS):
                cat_w.setCurrentText(EXPENSE_CATS[0])
        kind_w.currentIndexChanged.connect(changed)

    def values(self):
        out = {}
        for key, (kind, w) in self.fields.items():
            if kind == "text":
                out[key] = w.text().strip()
            elif kind == "multiline":
                out[key] = w.toPlainText().strip()
            elif kind in ("number", "money"):
                out[key] = _parse_num(w.text()) or 0.0
            elif kind in ("number?", "money?"):
                out[key] = _parse_num(w.text())
            elif kind in ("date", "date?", "time?", "days"):
                out[key] = w.value()
            elif kind == "choice":
                out[key] = w.currentData()
            elif kind == "combo":
                out[key] = w.currentText().strip()
            elif kind == "bool":
                out[key] = w.sw.isChecked()
        return out

    def _save(self):
        v = self.values()
        req = REQUIRED.get(self.coll)
        if req and not v.get(req):
            self.err.setText(t("err_required", f=t(dict((k, l) for k, l, _, _ in schema(self.coll, self.store))[req])))
            self.err.show()
            return
        for key, (kind, w) in self.fields.items():
            if kind.startswith(("number", "money")) and w.text().strip() and _parse_num(w.text()) is None:
                self.err.setText(t("err_number"))
                self.err.show()
                w.setFocus()
                return
        if self.coll == "projects" and v.get("progress") is not None:
            v["progress"] = max(0.0, min(100.0, v["progress"]))
            if v["progress"] >= 100 and v.get("status") != "done":
                pass
        if self.coll == "tasks" and self.item is None:
            v["done"] = False
        if self.item:
            self.store.update(self.coll, self.item["id"], **v)
        else:
            self.item = self.store.add(self.coll, v)
        self.accept()

    def _delete(self):
        self.deleted = True
        self.accept()


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
