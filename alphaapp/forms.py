"""Kayıt ekleme / düzenleme: her koleksiyonun alanları şemayla tanımlanır, tek bir form penceresi hepsini çizer."""
from datetime import date

from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDateEdit, QTimeEdit,
                             QPlainTextEdit, QPushButton, QWidget, QMenu, QGridLayout, QButtonGroup)

from .config import day_today
from .config import prefs
from .i18n import t, WEEKDAYS_SHORT
from .store import parse_date, num
from .theme import theme
from .widgets import ThemedDialog, ToggleSwitch

LETTERS = ("AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF")

TASK_PRIORITIES = ("normal", "high", "low")
PROJECT_STATUS = ("doing", "todo", "waiting", "done")

WORKOUT_KINDS = ("Gym", "Koşu", "Yüzme", "Bisiklet", "Yürüyüş", "Futbol", "Basketbol", "Tenis", "Yoga", "Pilates",
                 "Dövüş sporu", "Diğer")
WORKOUT_FOCUS = ("Göğüs", "Sırt", "Bacak", "Omuz", "Kol", "Karın / core", "Tüm vücut", "Push", "Pull", "Legs",
                 "Kardiyo", "Esneme")
EXAM_NAMES = ("Vize", "Midterm", "Quiz", "Final", "Ödev", "Rapor teslimi", "Proje", "Sunum", "Lab", "Seminer",
              "Vize 2", "Bütünleme")


def guess_exam(store, title):
    """Görev başlığından ders ve sınav türü tahmini: "Fizik I: Vize (D118)" → (Fizik I'in id'si, "Vize")."""
    low = (title or "").casefold()
    course = None
    best = 0
    for c in store.all("courses"):
        for key in (c.get("name"), c.get("code")):
            k = (key or "").strip().casefold()
            if k and k in low and len(k) > best:
                course, best = c["id"], len(k)
    kind = None
    for n in sorted(EXAM_NAMES + ("Midterm 2",), key=len, reverse=True):
        if n.casefold() in low:
            kind = n
            break
    if kind is None:
        for word, n in (("rapor", "Rapor teslimi"), ("teslim", "Ödev"), ("ödev", "Ödev"), ("sınav", "Vize")):
            if word in low:
                kind = n
                break
    return course, kind
EXPENSE_CATS = ("Yemek", "Dışarıda yemek", "Market", "Akaryakıt", "Otopark", "Ulaşım", "Kira", "Faturalar", "Abonelik",
                "Hobi", "Kahve", "Seyahat", "Eğlence", "Giyim", "Eğitim", "Sağlık", "Spor", "Hediye", "Diğer")
INCOME_CATS = ("Maaş", "Burs", "Harçlık", "Serbest iş", "Satış", "Faiz / getiri", "Diğer")
INVEST_KINDS = ("Hisse", "Fon", "Altın", "Döviz", "Kripto", "Mevduat", "Tahvil / bono", "Diğer")


# alan: (anahtar, etiket anahtarı, tür, seçenekler)
#   tür: text · multiline · date · date? (isteğe bağlı) · time? · number · number? · money · money? · choice ·
#        combo (yazılabilir öneri listesi) · days · bool
def schema(coll, store):
    out = _schema(coll, store)
    if not prefs.get("show_place", True):
        out = [f for f in out if f[0] != "place"]
    return out


def _schema(coll, store):
    if coll == "tasks":
        return [("title", "f_title", "text", None),
                ("category", "f_category", "cats", None),
                ("due", "f_due", "date?", None),
                ("time", "f_time", "time?", None),
                ("end", "f_end", "time?", None),
                ("priority", "f_priority", "choice", [(p, t("prio_" + p)) for p in TASK_PRIORITIES]),
                ("note", "f_note", "multiline", None)]
    if coll == "routine":
        return [("title", "f_title", "text", None),
                ("category", "f_category", "cats", None),
                ("days", "f_days", "days", None),
                ("start", "f_start", "time?", None),
                ("end", "f_end", "time?", None),
                ("place", "f_place", "text", None),
                ("from", "f_from", "date?", None),
                ("until", "f_until", "date?", None),
                ("important", "f_important", "bool", None)]
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
                ("time", "f_time", "time?", None),
                ("weight", "f_weight", "number?", None),
                ("target", "f_target_score", "number?", None),
                ("score", "f_score", "number?", None),
                ("note", "f_note", "multiline", None)]
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
                ("important", "f_important", "bool", None),
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
        out = [("name", "f_habit_name", "text", None),
               ("category", "f_category", "cats", None),
               ("goal", "f_goal_days", "number?", None)]
        if prefs.get("habits_in_schedule", False):
            out += [("weekdays", "f_habit_weekdays", "days", None),
                    ("time", "f_time", "time?", None)]
        return out + [("note", "f_note", "text", None)]
    if coll == "accounts":
        return [("name", "f_account_name", "combo", _with_used(["Nakit", "Banka hesabı"], store, "accounts", "name")),
                ("balance", "f_balance", "money", None),
                ("note", "f_note", "text", None)]
    if coll == "recurring":
        return [("kind", "f_tx_kind", "choice", [("expense", t("expense")), ("income", t("income"))]),
                ("name", "f_rec_name", "text", None),
                ("amount", "f_amount", "money", None),
                ("day", "f_day_of_month", "number?", None),
                ("category", "f_category", "combo",
                 _with_used(EXPENSE_CATS + INCOME_CATS, store, "recurring", "category")),
                ("active", "f_active", "bool", None),
                ("note", "f_note", "text", None)]
    if coll == "goals":
        parents = [("", "—")] + [(g["id"], g.get("title") or "—") for g in store.all("goals")
                                 if g.get("horizon") != "action"]
        return [("title", "f_goal_title", "text", None),
                ("area", "f_area", "areas", None),
                ("horizon", "f_horizon", "choice", [(h, t("hz_" + h)) for h in GOAL_HORIZONS]),
                ("parent", "f_parent", "choice", parents),
                ("due", "f_target_date", "date?", None),
                ("progress", "f_progress", "number?", None),
                ("links", "f_links", "links", None),
                ("image", "f_image", "image", None),
                ("done", "f_goal_done", "bool", None),
                ("note", "f_note", "multiline", None)]
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
            "transactions": "amount", "workouts": "date", "habits": "name", "meals": "name",
            "accounts": "name", "recurring": "name", "goals": "title"}

GOAL_HORIZONS = ("life", "y10", "y3", "year", "term", "action")


def _with_used(base, store, coll, key):
    seen = list(base)
    for x in store.all(coll):
        v = (x.get(key) or "").strip()
        if v and v not in seen:
            seen.append(v)
    return seen


def defaults(coll):
    d = day_today().isoformat()
    return {
        "tasks": {"category": "personal", "priority": "normal"},
        "routine": {"category": "education", "days": [day_today().weekday()], "start": "09:00", "end": "10:00"},
        "exams": {"name": "Vize", "weight": 40},
        "workouts": {"date": d, "kind": "Gym"},
        "projects": {"status": "doing", "progress": 0},
        "events": {"date": d},
        "transactions": {"kind": "expense", "date": d, "category": "Yemek"},
        "debts": {"direction": "owe"},
        "investments": {"date": d, "kind": "Hisse"},
        "habits": {"category": "personal", "goal": 7},
        "meals": {"date": d},
        "accounts": {"name": "Nakit"},
        "recurring": {"kind": "expense", "active": True, "category": "Faturalar"},
        "goals": {"area": "growth", "horizon": "year"},
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
        d = parse_date(value) or day_today()
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


CAT_ICONS = {"sport": "cat_sport", "work": "cat_work", "education": "cat_education", "social": "group",
             "finance": "wallet", "personal": "person"}
CAT_ORDER = ("sport", "work", "education", "social", "finance", "personal")
# hayat alanları (hedefler, çark): store.LIFE_AREAS sırasıyla
AREA_ICONS = {"education": "cat_education", "career": "work_bag", "venture": "lightbulb", "body": "cat_sport",
              "mind": "spa", "finance": "wallet", "growth": "star"}


class CategoryPicker(QWidget):
    """Kategori: tek tıkla seçilen ikon düğmeleri (spor, iş, eğitim, sosyal, ekonomi, kişisel).
    areas=True → hayat alanları (eğitim, kariyer, iş, beden, zihin, ekonomi, kişisel gelişim)."""

    def __init__(self, value, parent=None, areas=False):
        super().__init__(parent)
        from .store import LIFE_AREAS, life_area
        order, ic, self.prefix, self.default = ((LIFE_AREAS, AREA_ICONS, "area_", "growth") if areas else
                                                (CAT_ORDER, CAT_ICONS, "cat_", "personal"))
        if areas:
            value = life_area(value)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.btns = {}
        for c in order:
            b = QPushButton()
            b.setObjectName("CatChip")
            b.setCheckable(True)
            b.setFixedSize(40, 36)
            b.setToolTip(t(self.prefix + c))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            theme.icon(b, ic[c], "text", 20)
            self.group.addButton(b)
            self.btns[c] = b
            lay.addWidget(b)
            b.toggled.connect(self._label)
        self.lbl = QLabel("")
        self.lbl.setObjectName("Secondary")
        lay.addSpacing(4)
        lay.addWidget(self.lbl)
        lay.addStretch(1)
        self.btns.get(value if value in self.btns else self.default).setChecked(True)
        self._label()

    def _label(self, *_):
        self.lbl.setText(t(self.prefix + self.value()))

    def value(self):
        for c, b in self.btns.items():
            if b.isChecked():
                return c
        return self.default


class LinksPicker(QPushButton):
    """Hedefe bağlı alışkanlık / ders / projeler: tıkla → işaretlenebilir menü. Değer: ["habits:id", ...]."""

    def __init__(self, store, value, parent=None):
        super().__init__(parent)
        self.store = store
        self.links = [x for x in (value or []) if store.link_item(x)[1] is not None]
        self.setObjectName("Pill")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._menu)
        self._label()

    def _label(self):
        names = [(self.store.link_item(x)[1] or {}).get("name") or "—" for x in self.links]
        txt = ", ".join(names[:3]) + (f" +{len(names) - 3}" if len(names) > 3 else "") if names else t("links_none")
        self.setText(txt.replace("&", "&&"))
        self.setToolTip("\n".join(names))

    def _menu(self):
        m = QMenu(self)
        any_item = False
        for coll, key in (("habits", "nav_habits"), ("courses", "courses"), ("projects", "projects")):
            items = sorted(self.store.all(coll), key=lambda x: (x.get("name") or "").lower())
            if not items:
                continue
            any_item = True
            m.addSection(t(key))
            for x in items:
                ln = f"{coll}:{x['id']}"
                a = QAction(x.get("name") or "—", m)
                a.setCheckable(True)
                a.setChecked(ln in self.links)
                a.toggled.connect(lambda on, ln=ln: self._toggle(ln, on))
                m.addAction(a)
        if not any_item:
            a = QAction(t("links_empty"), m)
            a.setEnabled(False)
            m.addAction(a)
        m.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _toggle(self, ln, on):
        if on and ln not in self.links:
            self.links.append(ln)
        elif not on and ln in self.links:
            self.links.remove(ln)
        self._label()

    def value(self):
        return list(self.links)


class ImagePicker(QWidget):
    """Hedef görseli: dosya seç → DATA_DIR\\images'a kopyalanır, değer dosya adıdır."""

    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.val = value or None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.btn = QPushButton()
        self.btn.setObjectName("Pill")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._pick)
        lay.addWidget(self.btn)
        self.clear_btn = QPushButton(t("clear_image"))
        self.clear_btn.setObjectName("Flat")
        self.clear_btn.setStyleSheet("min-width: 0px;")
        self.clear_btn.clicked.connect(self._clear)
        lay.addWidget(self.clear_btn)
        lay.addStretch(1)
        self._label()

    def _label(self):
        self.btn.setText(t("change_image") if self.val else t("pick_image"))
        self.clear_btn.setVisible(bool(self.val))

    def _pick(self):
        import os
        import shutil
        import uuid
        from PyQt6.QtWidgets import QFileDialog
        from .config import IMAGES_DIR
        path, _ = QFileDialog.getOpenFileName(self, t("pick_image"), "",
                                              "Görseller (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if not path:
            return
        os.makedirs(IMAGES_DIR, exist_ok=True)
        name = uuid.uuid4().hex[:12] + os.path.splitext(path)[1].lower()
        try:
            shutil.copy2(path, os.path.join(IMAGES_DIR, name))
        except OSError:
            return
        self.val = name
        self._label()

    def _clear(self):
        self.val = None
        self._label()

    def value(self):
        return self.val


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
        self.setMinimumWidth(540)
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
        self.exam_row = None
        r = 0
        for key, label, kind, opts in schema(coll, store):
            lbl = QLabel(t(label))
            lbl.setObjectName("FieldLabel")
            w = self._make(kind, data.get(key), opts)
            self.fields[key] = (kind, w)
            al = Qt.AlignmentFlag.AlignTop if kind == "multiline" else Qt.AlignmentFlag.AlignVCenter
            grid.addWidget(lbl, r, 0, al)
            grid.addWidget(w, r, 1)
            r += 1
            if first is None and kind in ("text", "money", "combo"):
                first = w
            if coll == "tasks" and key == "category" and item is None and store.all("courses"):
                self._exam_row(grid, r)       # Eğitim seçilince: "sınav / teslim" → Sınavlar'a kaydedilir
                r += 1
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
        if kind == "cats":
            return CategoryPicker(v)
        if kind == "areas":
            return CategoryPicker(v, areas=True)
        if kind == "links":
            return LinksPicker(self.store, v)
        if kind == "image":
            return ImagePicker(v)
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

    # ------------------------------------------------------------ görev → sınav / teslim
    def _exam_row(self, grid, r):
        """Kategori Eğitim iken görünen satır: [anahtar] [ders] [tür]. Açıksa kayıt görev değil sınav olur
        (Eğitim > Yaklaşan sınavlar, Yaklaşanlar, takvim)."""
        lbl = QLabel(t("f_as_exam"))
        lbl.setObjectName("FieldLabel")
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.exam_sw = ToggleSwitch(False)
        h.addWidget(self.exam_sw)
        self.exam_course = QComboBox()
        for c in self.store.all("courses"):
            self.exam_course.addItem(c.get("name", ""), c["id"])
        self.exam_kind = QComboBox()
        self.exam_kind.setEditable(True)
        self.exam_kind.addItems(list(_with_used(EXAM_NAMES, self.store, "exams", "name")))
        self.exam_kind.setMinimumWidth(130)
        h.addWidget(self.exam_course, 1)
        h.addWidget(self.exam_kind)
        self.exam_hint = QLabel(t("f_as_exam_hint"))
        self.exam_hint.setObjectName("Secondary")
        h.addWidget(self.exam_hint, 1)
        grid.addWidget(lbl, r, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(box, r, 1)
        self.exam_row = (lbl, box)
        cat = self.fields["category"][1]
        for b in cat.btns.values():
            b.toggled.connect(lambda _on: self._exam_update())
        self.exam_sw.toggled.connect(self._exam_toggled)
        self._exam_update()

    def exam_on(self):
        return self.exam_row is not None and not self.exam_row[1].isHidden() and self.exam_sw.isChecked()

    def _exam_toggled(self, on):
        if on:
            title = self.fields["title"][1].text()
            course, kind = guess_exam(self.store, title)
            if course:
                self.exam_course.setCurrentIndex(max(0, self.exam_course.findData(course)))
            if kind:
                self.exam_kind.setCurrentText(kind)
        self._exam_update()

    def _exam_update(self):
        if self.exam_row is None:
            return
        edu = self.fields["category"][1].value() == "education"
        for w in self.exam_row:
            w.setVisible(edu)
        on = edu and self.exam_sw.isChecked()
        self.exam_course.setVisible(on)
        self.exam_kind.setVisible(on)
        self.exam_hint.setVisible(edu and not on)
        if "priority" in self.fields:          # sınavlar zaten "önemli" (kırmızı) görünür
            self.fields["priority"][1].setEnabled(not on)
        self.adjustSize()

    def _save_exam(self, v):
        title = v.get("title") or ""
        kind = self.exam_kind.currentText().strip() or "Vize"
        ex = {"course": self.exam_course.currentData(), "name": kind, "date": v.get("due"),
              "time": v.get("time"), "end": v.get("end"), "weight": None, "target": None, "score": None}
        course_name = self.exam_course.currentText().strip()
        note = "\n".join(x for x in (title if title.casefold() not in (course_name.casefold(), kind.casefold(),
                                                                      f"{course_name}: {kind}".casefold()) else "",
                                     v.get("note") or "") if x)
        if note:
            ex["note"] = note
        self.coll = "exams"
        self.item = self.store.add("exams", ex)
        self.accept()

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
            elif kind in ("date", "date?", "time?", "days", "cats", "areas", "links", "image"):
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
        if self.coll == "tasks" and self.item is None and self.exam_on():
            return self._save_exam(v)
        if self.coll == "tasks" and self.item is None:
            v["done"] = False
        if self.coll == "goals":
            v["parent"] = v.get("parent") or None
            if self.item and v["parent"] and (v["parent"] == self.item["id"] or v["parent"] in
                                              {g["id"] for g in self.store.goal_descendants(self.item["id"])}):
                v["parent"] = self.item.get("parent")      # döngü olmasın
            if v.get("progress") is not None:
                v["progress"] = max(0.0, min(100.0, v["progress"]))
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
