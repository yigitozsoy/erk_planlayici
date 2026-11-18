"""Spor sayfasının ağırlık antrenmanı parçaları (hesaplar: fitness.py).

WorkoutDialog   antrenman kaydı: hareketler, her harekette set satırları (tekrar × kg), "geçen sefer" ipucu.
                Programdan başlatınca hareketler, set sayısı, tekrar ve son kullanılan kilolar dolu gelir.
TemplateDialog  program (şablon): hareket, set, tekrar ("6-8"), RiR.
LineChart       basit çizgi grafik (rekor ilerlemesi, kilo), isteğe bağlı hedef çizgisi.
TemplatesCard, RecordsCard, BodyCard   spor sayfasındaki kartlar (giriş: pages/sport_body.HeroCard).
"""

from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QFontMetrics
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                             QSpinBox, QDoubleSpinBox, QPushButton, QScrollArea, QFrame, QMenu,
                             QMessageBox, QInputDialog, QCompleter)

from .. import fitness
from ..components import Card, Row, ChipBar, button, sub_label
from ..config import prefs, day_today
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_num, fmt_day, fmt_day_month
from ..store import parse_date, num
from ..theme import theme, qcolor
from ..widgets import ThemedDialog, IconButton
from ..pickers import DateButton


def mus(m):
    return t("mus_" + m)


def _mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return QColor(int(a.red() + (b.red() - a.red()) * k), int(a.green() + (b.green() - a.green()) * k),
                  int(a.blue() + (b.blue() - a.blue()) * k))


def _sets_text(sets):
    out = []
    for s in sets:
        w, r = num(s.get("w")), int(num(s.get("r")))
        out.append(f"{fmt_num(w)}×{r}" if w else f"{r}")
    return ", ".join(out)


def focus_text(exercises):
    load = fitness.muscle_load(exercises)
    top = sorted((m for m, v in load.items() if v >= 1), key=lambda m: -load[m])[:3]
    return ", ".join(mus(m) for m in top)


# ============================================================ antrenman penceresi
class _ExerciseBlock(QFrame):
    def __init__(self, dlg, name="", sets=()):
        super().__init__()
        self.dlg = dlg
        self.setObjectName("CardToday")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)
        head = QHBoxLayout()
        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.addItems(dlg.names)
        self.name.setCurrentText(name)
        self.name.lineEdit().setPlaceholderText(t("ex_placeholder"))
        comp = QCompleter(dlg.names, self.name)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name.setCompleter(comp)
        self.name.currentTextChanged.connect(self._hint)
        head.addWidget(self.name, 1)
        rm = IconButton("delete", t("delete"), 30, 18)
        rm.clicked.connect(lambda: dlg.remove_block(self))
        head.addWidget(rm)
        v.addLayout(head)
        self.hint = sub_label("")
        v.addWidget(self.hint)
        self.grid = QVBoxLayout()
        self.grid.setSpacing(4)
        v.addLayout(self.grid)
        add = QPushButton("+ " + t("wd_add_set"))
        add.setObjectName("Chip")
        add.setStyleSheet("min-width: 0px; padding: 3px 12px;")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(self.add_set)
        v.addWidget(add, 0, Qt.AlignmentFlag.AlignLeft)
        self.rows = []
        for s in sets:
            self.add_set(int(num(s.get("r"))), num(s.get("w")))
        if not sets:
            self.add_set()
        self._hint()

    def add_set(self, r=None, w=None):
        if r is None:
            last = self.rows[-1] if self.rows else None
            r = last[1].value() if last else 8
            w = last[2].value() if last else 0.0
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        n = sub_label(str(len(self.rows) + 1))
        n.setFixedWidth(18)
        reps = QSpinBox()
        reps.setRange(0, 100)
        reps.setValue(int(r))
        reps.setSuffix(" " + t("wd_reps"))
        reps.setFixedWidth(110)
        kg = QDoubleSpinBox()
        kg.setRange(0, 1000)
        kg.setDecimals(1)
        kg.setSingleStep(2.5)
        kg.setValue(float(w or 0))
        kg.setSuffix(" " + t("wd_kg"))
        kg.setFixedWidth(110)
        x = sub_label("×")
        rm = IconButton("close", t("delete"), 26, 16)
        h.addWidget(n)
        h.addWidget(reps)
        h.addWidget(x)
        h.addWidget(kg)
        h.addWidget(rm)
        h.addStretch(1)
        entry = (row, reps, kg)
        rm.clicked.connect(lambda: self._remove_set(entry))
        self.rows.append(entry)
        self.grid.addWidget(row)

    def _remove_set(self, entry):
        if entry in self.rows:
            self.rows.remove(entry)
            entry[0].hide()
            entry[0].setParent(None)
            entry[0].deleteLater()
            for i, (row, _r, _k) in enumerate(self.rows):
                row.findChild(QLabel).setText(str(i + 1))

    def _hint(self, *_):
        name = self.name.currentText().strip()
        last = fitness.last_sets(self.dlg.store, name, before=self.dlg.day()) if name else []
        prim, _sec = fitness.muscles_of(name)
        bits = []
        if prim:
            bits.append(", ".join(mus(m) for m in prim))
        if last:
            bits.append(t("wd_last", x=_sets_text(last)))
        self.hint.setText("  ·  ".join(bits))
        self.hint.setVisible(bool(bits))

    def value(self):
        name = self.name.currentText().strip()
        sets = [{"r": r.value(), "w": round(k.value(), 2)} for _row, r, k in self.rows if r.value() > 0]
        return {"name": name, "sets": sets} if name and sets else None


class WorkoutDialog(ThemedDialog):
    def __init__(self, win, item=None, template=None):
        super().__init__(win, t("wd_title"))
        self.win, self.store, self.item = win, win.store, item
        self.names = fitness.exercise_names(self.store)
        self.resize(640, 720)
        data = dict(item or {})
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.kind = QLineEdit(data.get("kind") or (template or {}).get("name") or "Gym")
        self.kind.setPlaceholderText(t("wd_name"))
        top.addWidget(self.kind, 1)
        d0 = parse_date(data.get("date")) or day_today()
        self.date = DateButton(d0)
        self.date.changed.connect(lambda: [b._hint() for b in self.blocks])
        top.addWidget(self.date)
        self.minutes = QSpinBox()
        self.minutes.setRange(0, 600)
        self.minutes.setSingleStep(5)
        self.minutes.setSuffix(" dk")
        self.minutes.setValue(int(num(data.get("minutes"))))
        self.minutes.setToolTip(t("wd_minutes"))
        top.addWidget(self.minutes)
        v.addLayout(top)

        self.host = QWidget()
        self.list = QVBoxLayout(self.host)
        self.list.setContentsMargins(0, 0, 4, 0)
        self.list.setSpacing(8)
        self.list.addStretch(1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidget(self.host)
        v.addWidget(sc, 1)
        self.blocks = []

        tools = QHBoxLayout()
        add = button(t("wd_add_ex"))
        theme.icon(add, "add", "text", 18)
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(lambda: self.add_block())
        tools.addWidget(add)
        tools.addStretch(1)
        self.summary = sub_label("")
        tools.addWidget(self.summary)
        v.addLayout(tools)
        self.note = QLineEdit(data.get("note") or "")
        self.note.setPlaceholderText(t("f_note"))
        v.addWidget(self.note)
        bar = QHBoxLayout()
        bar.addStretch(1)
        cancel = QPushButton(t("cancel"))
        cancel.clicked.connect(self.reject)
        save = button(t("save"), kind="Primary")
        save.clicked.connect(self._save)
        bar.addWidget(cancel)
        bar.addWidget(save)
        v.addLayout(bar)

        if data.get("exercises"):
            for e in data["exercises"]:
                self.add_block(e.get("name", ""), e.get("sets") or [])
        elif template:
            self.template_id = template.get("id")
            for e in template.get("exercises") or []:
                n = max(1, int(num(e.get("sets")) or 3))
                reps = fitness.first_int(e.get("reps"))
                last = fitness.last_sets(self.store, e.get("name"), before=self.day())
                sets = [{"r": reps, "w": num(last[min(i, len(last) - 1)].get("w")) if last else 0} for i in range(n)]
                self.add_block(e.get("name", ""), sets)
        else:
            self.add_block()
        self.template_id = getattr(self, "template_id", data.get("template"))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_summary)
        self._timer.start(500)
        self._update_summary()

    def day(self):
        return self.date.value()

    def add_block(self, name="", sets=()):
        b = _ExerciseBlock(self, name, sets)
        self.blocks.append(b)
        self.list.insertWidget(self.list.count() - 1, b)
        if not name:
            QTimer.singleShot(0, b.name.setFocus)
        return b

    def remove_block(self, b):
        if b in self.blocks:
            self.blocks.remove(b)
            b.hide()
            b.setParent(None)
            b.deleteLater()

    def exercises(self):
        return [x for x in (b.value() for b in self.blocks) if x]

    def _update_summary(self):
        ex = self.exercises()
        n = sum(len(e["sets"]) for e in ex)
        vol = sum(s["w"] * s["r"] for e in ex for s in e["sets"])
        self.summary.setText(" · ".join(x for x in (t("wd_sets_n", n=n) if n else "",
                                                    t("wd_vol", v=fmt_num(vol, 0)) if vol else "") if x))

    def record(self):
        ex = self.exercises()
        rec = {"date": self.day().isoformat(), "kind": self.kind.text().strip() or "Gym",
               "focus": focus_text(ex) if ex else (self.item or {}).get("focus", ""),
               "minutes": self.minutes.value() or None, "note": self.note.text().strip(), "exercises": ex}
        if self.template_id:
            rec["template"] = self.template_id
        return rec

    def _save(self):
        rec = self.record()
        if self.item:
            self.store.update("workouts", self.item["id"], **rec)
            self.item = self.store.get("workouts", self.item["id"])
        else:
            self.item = self.store.add("workouts", rec)
        self.accept()


def open_workout(win, item=None, template=None):
    d = WorkoutDialog(win, item, template)
    return d.item if d.exec() else None


# ============================================================ program penceresi
class TemplateDialog(ThemedDialog):
    def __init__(self, win, item=None):
        super().__init__(win, t("tpl_edit") if item else t("tpl_new"))
        self.win, self.store, self.item = win, win.store, item
        self.names = fitness.exercise_names(self.store)
        self.resize(620, 560)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)
        self.name = QLineEdit((item or {}).get("name", ""))
        self.name.setPlaceholderText(t("tpl_name"))
        v.addWidget(self.name)
        head = QHBoxLayout()
        for text, w in ((t("ex_placeholder"), 1), (t("tpl_sets"), 0), (t("tpl_reps"), 0), (t("tpl_rir"), 0)):
            lb = QLabel(text)
            lb.setObjectName("StatLabel")
            if not w:
                lb.setFixedWidth(70)
            head.addWidget(lb, w)
        head.addSpacing(34)
        v.addLayout(head)
        self.host = QWidget()
        self.list = QVBoxLayout(self.host)
        self.list.setContentsMargins(0, 0, 0, 0)
        self.list.setSpacing(4)
        self.list.addStretch(1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidget(self.host)
        v.addWidget(sc, 1)
        self.rows = []
        for e in (item or {}).get("exercises") or [{}]:
            self.add_row(e)
        add = button(t("wd_add_ex"))
        theme.icon(add, "add", "text", 18)
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(lambda: self.add_row({}))
        v.addWidget(add, 0, Qt.AlignmentFlag.AlignLeft)
        bar = QHBoxLayout()
        if item:
            dl = QPushButton(t("delete"))
            dl.clicked.connect(self._delete)
            bar.addWidget(dl)
        bar.addStretch(1)
        cancel = QPushButton(t("cancel"))
        cancel.clicked.connect(self.reject)
        save = button(t("save"), kind="Primary")
        save.clicked.connect(self._save)
        bar.addWidget(cancel)
        bar.addWidget(save)
        v.addLayout(bar)
        self.deleted = False

    def add_row(self, e):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        name = QComboBox()
        name.setEditable(True)
        name.addItems(self.names)
        name.setCurrentText(e.get("name", ""))
        comp = QCompleter(self.names, name)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        name.setCompleter(comp)
        sets = QSpinBox()
        sets.setRange(1, 12)
        sets.setValue(int(num(e.get("sets")) or 3))
        sets.setFixedWidth(70)
        reps = QLineEdit(str(e.get("reps") or "8"))
        reps.setFixedWidth(70)
        rir = QLineEdit(str(e.get("rir") or ""))
        rir.setFixedWidth(70)
        rm = IconButton("delete", t("delete"), 28, 18)
        for x, st in ((name, 1), (sets, 0), (reps, 0), (rir, 0), (rm, 0)):
            h.addWidget(x, st)
        entry = (w, name, sets, reps, rir)
        rm.clicked.connect(lambda: self._remove(entry))
        self.rows.append(entry)
        self.list.insertWidget(self.list.count() - 1, w)

    def _remove(self, entry):
        if entry in self.rows:
            self.rows.remove(entry)
            entry[0].hide()
            entry[0].setParent(None)
            entry[0].deleteLater()

    def record(self):
        ex = []
        for _w, name, sets, reps, rir in self.rows:
            n = name.currentText().strip()
            if n:
                ex.append({"name": n, "sets": sets.value(), "reps": reps.text().strip() or "8",
                           "rir": rir.text().strip()})
        return {"name": self.name.text().strip() or t("tpl_new"), "exercises": ex}

    def _save(self):
        rec = self.record()
        if self.item:
            self.store.update("templates", self.item["id"], **rec)
        else:
            self.item = self.store.add("templates", rec)
        self.accept()

    def _delete(self):
        if QMessageBox.question(self, t("tpl_edit"), t("tpl_del_q", n=self.item.get("name", ""))) \
                == QMessageBox.StandardButton.Yes:
            self.store.delete("templates", self.item["id"])
            self.deleted = True
            self.accept()


def edit_template(win, item=None):
    d = TemplateDialog(win, item)
    return d.item if d.exec() else None


# ============================================================ çizgi grafik
class LineChart(QWidget):
    def __init__(self, height=170, unit=""):
        super().__init__()
        self.pts, self.goal, self.unit = [], None, unit
        self.setFixedHeight(height)
        theme.bind(self, lambda w: w.update())

    def set_data(self, pts, goal=None):
        """pts: [(date, value)]"""
        self.pts, self.goal = list(pts), goal
        self.update()

    def paintEvent(self, _e):
        if not self.pts:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = QFont(self.font())
        f.setPixelSize(11)
        p.setFont(f)
        fm = QFontMetrics(f)
        vals = [v for _d, v in self.pts] + ([self.goal] if self.goal else [])
        lo, hi = min(vals), max(vals)
        pad = max(1.0, (hi - lo) * 0.15)
        lo, hi = lo - pad, hi + pad
        left, right, top, bottom = 40, 14, 10, 22
        W, H = self.width() - left - right, self.height() - top - bottom
        d0, d1 = self.pts[0][0], self.pts[-1][0]
        span = max(1, (d1 - d0).days)

        def X(d):
            return left + (W * (d - d0).days / span if len(self.pts) > 1 else W / 2)

        def Y(v):
            return top + H * (1 - (v - lo) / (hi - lo))
        p.setPen(QPen(qcolor("divider"), 1))
        for k in range(3):
            v = lo + (hi - lo) * (k + 0.5) / 3
            y = Y(v)
            p.drawLine(QPointF(left, y), QPointF(left + W, y))
            p.setPen(qcolor("text3"))
            p.drawText(QRectF(0, y - 8, left - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       fmt_num(v, 0))
            p.setPen(QPen(qcolor("divider"), 1))
        if self.goal:
            pen = QPen(qcolor("good"), 1.2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(left, Y(self.goal)), QPointF(left + W, Y(self.goal)))
        path = QPainterPath()
        for i, (d, v) in enumerate(self.pts):
            pt = QPointF(X(d), Y(v))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        p.setPen(QPen(qcolor("text"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.setBrush(qcolor("text"))
        for d, v in self.pts:
            p.drawEllipse(QPointF(X(d), Y(v)), 3, 3)
        d, v = self.pts[-1]
        label = f"{fmt_num(v, 1)} {self.unit}".strip()
        p.setPen(qcolor("text"))
        p.drawText(QRectF(X(d) - fm.horizontalAdvance(label) - 6, Y(v) - 20, fm.horizontalAdvance(label) + 4, 16),
                   Qt.AlignmentFlag.AlignRight, label)
        p.setPen(qcolor("text3"))
        p.drawText(QRectF(left, top + H + 4, 120, 16), Qt.AlignmentFlag.AlignLeft, fmt_day_month(d0, short=True))
        if len(self.pts) > 1:
            p.drawText(QRectF(left + W - 120, top + H + 4, 120, 16), Qt.AlignmentFlag.AlignRight,
                       fmt_day_month(d1, short=True))
        p.end()


# ============================================================ kartlar
def e1rm_tip(b):
    """Rekor kaydının 1RM'si nasıl hesaplandı (Epley)."""
    return t("tip_e1rm", w=fmt_num(b["w"], 1), r=b["r"], e=fmt_num(b["e1rm"], 1))


def level_tip(name, e1rm, bw):
    """Seviye neye göre: 1RM / vücut ağırlığı ve bu hareketin kg cinsinden eşikleri."""
    std = fitness.standard(name)
    bw = bw or 75.0
    if not std:
        return ""
    a, b, c, d = (fmt_num(x * std * bw, 0) for x in fitness.LEVELS)
    return t("tip_level", e=fmt_num(e1rm, 1), bw=fmt_num(bw, 1), x=fmt_num(e1rm / bw, 2), a=a, b=b, c=c, d=d)


def _box(title, value, sub="", tip=""):
    box = QWidget()
    box.setObjectName("CardToday")
    box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    v = QVBoxLayout(box)
    v.setContentsMargins(12, 8, 12, 8)
    v.setSpacing(1)
    for text, obj in ((title, "StatLabel"), (value, "StatValue"), (sub, "RowSub")):
        if text:
            lb = QLabel(text)
            lb.setObjectName(obj)
            v.addWidget(lb)
    if tip:
        box.setToolTip(tip)
    return box



class TemplatesCard(Card):
    def __init__(self, win):
        super().__init__(t("templates_title"), t("templates_sub"), add_tip=t("add_template"))
        self.win, self.store = win, win.store
        self.add_clicked.connect(lambda: edit_template(win))

    def refresh(self):
        self.clear()
        tps = sorted(self.store.all("templates"), key=lambda x: x.get("created") or "")
        for tp in tps:
            n = len(tp.get("exercises") or [])
            s = fitness.template_sets(tp)
            lvl = fitness.intensity(s)
            sub = t("tpl_sub", n=n, s=s) + " · " + t("lvl_%d" % lvl) + "  " + "●" * lvl + "○" * (5 - lvl)
            mus_txt = focus_text(tp.get("exercises") or [])
            r = Row(tp.get("name", ""), sub + (f" · {mus_txt}" if mus_txt else ""), icon="cat_sport")
            b = button(t("tpl_start"))
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, tp=tp: open_workout(self.win, template=tp))
            r.layout().addWidget(b)
            r.clicked.connect(lambda tp=tp: edit_template(self.win, tp))
            r.menu_requested.connect(lambda pos, tp=tp: self._menu(tp, pos))
            self.add(r)
        if not tps:
            self.empty(t("tpl_empty"))

    def _menu(self, tp, pos):
        m = QMenu(self)
        m.addAction(t("tpl_start"), lambda: open_workout(self.win, template=tp))
        m.addAction(t("edit"), lambda: edit_template(self.win, tp))
        m.addSeparator()
        m.addAction(t("delete"), lambda: self.store.delete("templates", tp["id"]))
        m.exec(pos)


class RecordsCard(Card):
    def __init__(self, win):
        super().__init__(t("pr_title"), t("pr_sub"), add_tip=t("add_lift"))
        self.win, self.store = win, win.store
        self.add_clicked.connect(lambda: edit_item(win, "lifts"))

    def refresh(self):
        self.clear()
        names = fitness.logged_exercises(self.store)
        if not names:
            self.empty(t("pr_empty"))
            return
        sel = prefs.get("pr_ex") if prefs.get("pr_ex") in names else names[0]
        bar = ChipBar([(n, n) for n in names[:8]], sel)
        bar.changed.connect(lambda k: (prefs.set("pr_ex", k), QTimer.singleShot(0, self.refresh)))
        self.add(bar)
        from .sport_goals import suggest_row, goal_rows, volume_chart
        from .. import overload
        sr = suggest_row(self.store, sel)
        if sr is not None:
            self.add(sr)
        for w in goal_rows(self.win, sel):
            self.add(w)
        series = fitness.progress_series(self.store, sel)
        if series:
            lb = sub_label(t("pr_chart", n=sel))
            self.add(lb)
            ch = LineChart(150, "kg")
            gs = overload.goals_for(self.store, sel)
            ch.set_data(series, min(overload.goal_e1rm(g) for g in gs) if gs else None)
            self.add(ch)
        vc = volume_chart(self.store, sel)
        if vc is not None:
            self.add(sub_label(t("ov_volume_title")))
            self.add(vc)
        rows = []
        for n in names:
            b = fitness.best(self.store, n)
            if b:
                rows.append((b["e1rm"], n, b))
        for _v, n, b in sorted(rows, key=lambda x: -x[0])[:8]:
            r = Row(n, t("pr_row", w=fmt_num(b["w"]), r=b["r"], e=fmt_num(b["e1rm"], 1)),
                    value=fmt_day_month(b["date"], short=True), icon="cat_sport")
            r.setToolTip(e1rm_tip(b) + "\n" + level_tip(n, b["e1rm"], fitness.body_weight(self.store)))
            self.add(r)


class BodyCard(Card):
    def __init__(self, win):
        super().__init__(t("body_title"), add_tip=t("body_add"))
        self.win, self.store = win, win.store
        self.add_clicked.connect(lambda: edit_item(win, "body"))

    def refresh(self):
        self.clear()
        rows = sorted((b for b in self.store.all("body") if parse_date(b.get("date"))),
                      key=lambda b: (b.get("date"), b.get("created") or ""))
        wts = [(parse_date(b["date"]), num(b.get("weight"))) for b in rows if num(b.get("weight")) > 0]
        goal = num(prefs.get("goal_weight")) or None
        strip = QWidget()
        h = QHBoxLayout(strip)
        h.setContentsMargins(0, 0, 0, 4)
        h.setSpacing(8)
        cur = wts[-1][1] if wts else None
        ch = ""
        if len(wts) > 1:
            d = wts[-1][1] - wts[0][1]
            ch = t("body_change", d=("+" if d >= 0 else "") + fmt_num(d, 1), n=len(wts))
        h.addWidget(_box(t("body_weight"), f"{fmt_num(cur, 1)} kg" if cur else "—", ch), 1)
        left = t("body_left", d=fmt_num(abs(cur - goal), 1)) if cur and goal else ""
        gb = _box(t("body_goal"), f"{fmt_num(goal, 1)} kg" if goal else "—", left, t("goal_weight_tip"))
        gb.setCursor(Qt.CursorShape.PointingHandCursor)
        gb.mousePressEvent = lambda _e: QTimer.singleShot(0, self._set_goal)
        h.addWidget(gb, 1)
        fat = next((fitness.fat_of(b) for b in reversed(rows) if fitness.fat_of(b)), None)
        h.addWidget(_box(t("body_fat"), f"%{fmt_num(fat, 1)}" if fat else "—"), 1)
        self.add(strip)
        if len(wts) > 1 or (wts and goal):
            ch = LineChart(150, "kg")
            ch.set_data(wts, goal)
            self.add(ch)
        fpts = [(parse_date(b["date"]), fitness.fat_of(b)) for b in rows if fitness.fat_of(b)]
        if len(fpts) > 1:
            lb = sub_label(t("body_fat"))
            self.add(lb)
            fc = LineChart(110, "%")
            fc.set_data(fpts)
            self.add(fc)
        for b in list(reversed(rows))[:5]:
            fv = fitness.fat_of(b)
            meas = (("neck", "f_neck"), ("waist", "f_waist"), ("hip", "f_hip"), ("chest", "f_chest_cm"),
                    ("arm", "f_arm"), ("thigh", "f_thigh"))
            bits = ([f"{t('body_fat')} %{fmt_num(fv, 1)}"] if fv else []) + \
                [f"{t(k)} {fmt_num(num(b[f]), 1)}" for f, k in meas if num(b.get(f)) > 0]
            r = Row(fmt_day(parse_date(b["date"])), " · ".join(bits),
                    value=f"{fmt_num(num(b.get('weight')), 1)} kg" if num(b.get("weight")) else "")
            self.add(bind_row(self.win, r, "body", b))
        if not rows:
            self.empty(t("body_empty"))

    def _set_goal(self):
        cur = float(num(prefs.get("goal_weight")) or 75.0)
        val, ok = QInputDialog.getDouble(self.win, t("body_goal"), t("goal_weight_q"), cur, 30.0, 250.0, 1)
        if ok:
            prefs.set("goal_weight", round(val, 1))
            self.refresh()


def workout_sub(w):
    """Günlük satırı için: hareketler (3×5 …) ve hacim."""
    ex = w.get("exercises") or []
    if not ex:
        return ""
    parts = [f"{e.get('name')} {len(fitness.valid_sets(e))}×" for e in ex[:3]]
    more = f" +{len(ex) - 3}" if len(ex) > 3 else ""
    vol = fitness.volume(w)
    return ", ".join(parts) + more + (f" · {t('wd_vol', v=fmt_num(vol, 0))}" if vol else "")


