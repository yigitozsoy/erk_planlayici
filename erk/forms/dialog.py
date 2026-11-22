"""Tek form penceresi (FormDialog): şemadaki alanları çizer, kaydeder, siler."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPlainTextEdit, QPushButton, QWidget, QGridLayout)

from ..config import day_today
from ..components import button
from ..i18n import t
from ..widgets import ThemedDialog, ToggleSwitch
from .fields import CategoryPicker, DaysPicker, ImagePicker, LinksPicker, OptDate, OptTime, _fmt_num, _parse_num
from .schemas import EXPENSE_CATS, INCOME_CATS, REQUIRED, defaults, exam_names, guess_exam, schema


# ============================================================ form penceresi
class FormDialog(ThemedDialog):
    def __init__(self, parent, store, coll, item=None, preset=None):
        title = t(("edit_" if item else "new_") + coll)
        super().__init__(parent, title)
        self.store, self.coll, self.item = store, coll, item
        self.preset = dict(preset or {})
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
        bc = button(t("cancel"), kind="Flat")
        bc.clicked.connect(self.reject)
        bs = button(t("save"), kind="Primary")
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
            if i < 0 and isinstance(v, str) and v.startswith("w:"):     # görev tekrarı: hızlı ekleden gelen günler
                from ..quick import repeat_label
                w.addItem(repeat_label(v, t), v)
                i = w.count() - 1
            w.setCurrentIndex(max(0, i))
            return w
        if kind == "combo":
            w = QComboBox()
            w.setEditable(True)
            w.addItems(list(opts))
            if self.coll == "exams" and v:
                from .. import grades
                from ..i18n import is_tr
                v = grades.exam_label(v, is_tr())
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
        self.exam_kind.addItems(exam_names(self.store))
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
        from .. import grades
        kind = grades.exam_canon(self.exam_kind.currentText()) or "Vize"
        ex = {"course": self.exam_course.currentData(), "name": kind, "date": v.get("due"),
              "time": v.get("time"), "end": v.get("end"), "weight": None, "target": None, "score": None}
        course_name = self.exam_course.currentText().strip()
        note = "\n".join(x for x in (title if title.casefold() not in (course_name.casefold(), kind.casefold(),
                                                                      f"{course_name}: {kind}".casefold()) else "",
                                     v.get("note") or "") if x)
        if note:
            ex["note"] = note
        self.coll = "exams"
        self.item, _before = self.store.add_exam(ex)
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
                    from ..i18n import fmt_num
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
        if self.coll == "exams" and v.get("name"):
            from .. import grades
            v["name"] = grades.exam_canon(v["name"])      # "Midterm 2" / "2. vize" → "Vize 2"
        if self.coll == "media":
            from datetime import datetime
            if self.item is None:      # aramadan gelen ve formda olmayan alanlar (bağlantılar, kaynak, sezon)
                for k in ("links", "source", "seasons"):
                    if self.preset.get(k):
                        v[k] = self.preset[k]
            today = day_today().isoformat()
            if v.get("status") == "done" and not v.get("finished"):
                v["finished"] = today
            if v.get("status") == "doing" and not v.get("started"):
                v["started"] = today
            if v.get("status") == "done" and v.get("total") and not v.get("progress"):
                v["progress"] = v["total"]
            v["updated"] = datetime.now().isoformat(timespec="seconds")
        if self.coll == "goals":
            v["parent"] = v.get("parent") or None
            if self.item and v["parent"] and (v["parent"] == self.item["id"] or v["parent"] in
                                              {g["id"] for g in self.store.goal_descendants(self.item["id"])}):
                v["parent"] = self.item.get("parent")      # döngü olmasın
            if v.get("progress") is not None:
                v["progress"] = max(0.0, min(100.0, v["progress"]))
        if self.item:
            self.store.update(self.coll, self.item["id"], **v)
        elif self.coll == "exams":
            self.item, _before = self.store.add_exam(v)     # aynı ders + tür varsa onu doldurur
        else:
            self.item = self.store.add(self.coll, v)
        self.accept()

    def _delete(self):
        self.deleted = True
        self.accept()
