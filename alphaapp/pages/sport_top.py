"""Spor sayfasının en üstü: solda Vücudum (kilo, yağ oranı + grafikleri), sağda Gelişimim (3B modelin yakın planı,
kaslar girilen max değerlere göre renkli). Kartlara tıklamak aşağıdaki ayrıntıya kaydırır.

MaxDialog: ana hareketlerin maksimumu (kg × tekrar) → lifts kayıtları (fitness.history okur, development boyar).
"""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
                             QDoubleSpinBox, QSpinBox)

from .. import fitness
from ..body3d import body_view
from datetime import timedelta

from ..components import Card, Row, clear_layout, button, sub_label
from ..config import day_today, prefs
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_num, fmt_day
from ..store import parse_date, num
from ..widgets import ThemedDialog
from .sport_ui import LineChart, _box, e1rm_tip, level_tip

MAIN_LIFTS = ("Bench Press", "Squat", "Deadlift", "Barbell Overhead Press", "Barbell Row", "Lat Pulldown",
              "Barbell Curl", "Triceps Pushdown")


class ClickCard(Card):
    """Boş yerine tıklanınca opened yayan kart (içindeki düğmeler / model kendi tıklamasını alır)."""
    opened = pyqtSignal()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.opened.emit()
        super().mouseReleaseEvent(e)


def _link(text):
    b = button(text)
    b.setStyleSheet("min-width: 0px; padding: 4px 12px;")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return b


class BodyStatsCard(ClickCard):
    def __init__(self, win):
        super().__init__(t("top_body"), t("top_body_sub"), add_tip=t("body_add"))
        self.win, self.store = win, win.store
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_clicked.connect(lambda: edit_item(win, "body"))
        self.host = QWidget()
        self.v = QVBoxLayout(self.host)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(8)
        self.body.addWidget(self.host)
        self.show_all = False

    def refresh(self):
        clear_layout(self.v)
        rows = sorted((b for b in self.store.all("body") if parse_date(b.get("date"))),
                      key=lambda b: (b.get("date"), b.get("created") or ""))
        series = {}
        series["weight"] = [(parse_date(b["date"]), num(b.get("weight"))) for b in rows if num(b.get("weight")) > 0]
        series["fat"] = [(parse_date(b["date"]), fitness.fat_of(b)) for b in rows if fitness.fat_of(b)]
        strip = QHBoxLayout()
        strip.setSpacing(8)
        wpts, fpts = series["weight"], series["fat"]
        cur = wpts[-1][1] if wpts else None
        ch = ""
        if len(wpts) > 1:
            d = wpts[-1][1] - wpts[0][1]
            ch = t("top_change", d=("+" if d >= 0 else "") + fmt_num(d, 1))
        strip.addWidget(_box(t("body_weight"), f"{fmt_num(cur, 1)} kg" if cur else "—", ch), 1)
        goal = num(prefs.get("goal_weight")) or None
        gb = _box(t("body_goal"), f"{fmt_num(goal, 1)} kg" if goal else "—",
                  t("body_left", d=fmt_num(abs(cur - goal), 1)) if cur and goal else t("top_goal_set"),
                  t("goal_weight_tip"))
        gb.setCursor(Qt.CursorShape.PointingHandCursor)
        gb.mousePressEvent = lambda _e: QTimer.singleShot(0, self._set_goal)
        strip.addWidget(gb, 1)
        fat = fpts[-1][1] if fpts else None
        lastf = next((b for b in reversed(rows) if fitness.fat_of(b)), None)
        ftip = ""
        if lastf:
            navy = lastf.get("fat_src") == "navy" or not num(lastf.get("fat"))
            ftip = t("tip_fat_navy" if navy else "tip_fat_manual") + "\n" + t("tip_lean")
        strip.addWidget(_box(t("body_fat"), f"%{fmt_num(fat, 1)}" if fat else "—",
                             t("top_lean_v", v=fmt_num(cur * (1 - fat / 100), 1)) if cur and fat else "", ftip), 1)
        self.v.addLayout(strip)
        # geçmiş: tıkla = düzenle, sağ tık = düzenle / sil; altta geçmiş tarihli kayıt
        hist = [b for b in reversed(rows) if num(b.get("weight")) > 0 or fitness.fat_of(b)]
        if hist:
            head = QHBoxLayout()
            lb = QLabel(t("top_history").upper())
            lb.setObjectName("StatLabel")
            head.addWidget(lb)
            head.addStretch(1)
            if len(hist) > 3:
                more = _link(t("top_less") if self.show_all else t("top_all", n=len(hist)))
                more.clicked.connect(self._toggle_all)
                head.addWidget(more)
            self.v.addLayout(head)
            for b in hist if self.show_all else hist[:3]:
                fv = fitness.fat_of(b)
                bits = ([f"{t('body_fat')} %{fmt_num(fv, 1)}"] if fv else []) +                     [f"{t(k).replace(' (cm)', '')} {fmt_num(num(b[f]), 1)}" for f, k in (
                        ("neck", "f_neck"), ("waist", "f_waist"), ("hip", "f_hip")) if num(b.get(f)) > 0]
                r = Row(fmt_day(parse_date(b["date"])), " · ".join(bits),
                        value=f"{fmt_num(num(b.get('weight')), 1)} kg" if num(b.get("weight")) else "")
                self.v.addWidget(bind_row(self.win, r, "body", b))
        if len(wpts) > 1 or (wpts and goal):
            c = LineChart(110, "kg")
            c.set_data(wpts, goal)
            self.v.addWidget(c)
        elif len(fpts) > 1:                  # kilo grafiği yoksa yağ oranınınki (ikisi de ayrıntıda)
            c = LineChart(110, "%")
            c.set_data(fpts)
            self.v.addWidget(c)
        if not rows:
            e = sub_label(t("top_body_empty"), wrap=True)
            self.v.addWidget(e)
        past = _link(t("top_add_past"))
        past.clicked.connect(lambda: edit_item(self.win, "body", preset={
            "date": (day_today() - timedelta(days=1)).isoformat()}))
        fc = _link(t("fat_calc"))
        fc.clicked.connect(lambda: QTimer.singleShot(0, lambda: FatDialog(self.win).exec()))
        b = _link(t("top_details"))
        b.clicked.connect(self.opened.emit)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(past)
        row.addWidget(fc)
        row.addStretch(1)
        row.addWidget(b)
        self.v.addLayout(row)

    def _toggle_all(self):
        self.show_all = not self.show_all
        QTimer.singleShot(0, self.refresh)

    def _set_goal(self):
        from PyQt6.QtWidgets import QInputDialog
        cur = float(num(prefs.get("goal_weight")) or 75.0)
        val, ok = QInputDialog.getDouble(self.win, t("body_goal"), t("goal_weight_q"), cur, 30.0, 250.0, 1)
        if ok:
            prefs.set("goal_weight", round(val, 1))
            self.refresh()


class DevPreviewCard(ClickCard):
    def __init__(self, win):
        super().__init__(t("top_dev"), t("top_dev_sub"))
        self.win, self.store = win, win.store
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.model = body_view(330)
        self.model.zoom, self.model.focus = 1.75, 0.34      # yakın plan: gövde + kollar
        self.model.setMinimumWidth(220)
        self.model.set_heat({}, names={m: t("mus_" + m) for m in fitness.MUSCLES})
        row.addWidget(self.model, 5)
        right = QVBoxLayout()
        right.setSpacing(4)
        self.lifts_host = QWidget()
        self.lifts = QVBoxLayout(self.lifts_host)
        self.lifts.setContentsMargins(0, 0, 0, 0)
        self.lifts.setSpacing(2)
        right.addWidget(self.lifts_host)
        right.addStretch(1)
        b = _link(t("top_enter_max"))
        b.clicked.connect(lambda: QTimer.singleShot(0, self._enter))
        right.addWidget(b)
        d = _link(t("top_details"))
        d.clicked.connect(self.opened.emit)
        right.addWidget(d)
        row.addLayout(right, 4)
        self.body.addLayout(row)

    def _enter(self):
        dlg = MaxDialog(self.win)
        dlg.exec()

    def refresh(self):
        bw = fitness.body_weight(self.store)
        dev = fitness.development(self.store, bw)
        heat = {m: fitness.dev_heat(d["q"]) for m, d in dev.items()}
        tips = {m: t("dev_%d" % d["level"]) + " · " + d["ex"] + f" · 1RM ≈ {fmt_num(d['e1rm'], 1)} kg"
                for m, d in dev.items()}
        self.model.set_heat(heat, tips)
        clear_layout(self.lifts)
        shown = 0
        for name in MAIN_LIFTS:
            b = fitness.best(self.store, name)
            if not b:
                continue
            std = fitness.standard(name)
            lvl = fitness.level_of(b["e1rm"] / (bw or 75.0) / std) if std else None
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 2, 0, 2)
            h.setSpacing(6)
            a = QLabel(name)
            a.setObjectName("RowTitle")
            h.addWidget(a, 1)
            v = sub_label(f"{fmt_num(b['e1rm'], 0)} kg" + (f"  ·  {t('dev_%d' % lvl)}" if lvl is not None else ""))
            h.addWidget(v)
            w.setToolTip(e1rm_tip(b) + "\n" + level_tip(name, b["e1rm"], bw))
            self.lifts.addWidget(w)
            shown += 1
        if not shown:
            e = sub_label(t("top_dev_empty"), wrap=True)
            self.lifts.addWidget(e)
        self.set_sub(t("top_dev_sub_bw", bw=fmt_num(bw, 1)) if bw else t("top_dev_sub"))


class MaxDialog(ThemedDialog):
    """Ana hareketlerin maksimumu: kg + tekrar (1 = gerçek max). Değişen satırlar bugünün lifts kaydı olur."""

    def __init__(self, win):
        super().__init__(win, t("top_enter_max"))
        self.win, self.store = win, win.store
        self.resize(460, 0)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 16)
        v.setSpacing(10)
        h = QLabel(t("top_enter_max"))
        h.setStyleSheet("font-size: 18px; font-weight: 700;")
        v.addWidget(h)
        sub = sub_label(t("max_hint"), wrap=True)
        v.addWidget(sub)
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        for c, text in enumerate(("", t("max_kg"), t("max_reps"))):
            if text:
                lb = sub_label(text)
                g.addWidget(lb, 0, c)
        self.rows = {}
        for i, name in enumerate(MAIN_LIFTS, 1):
            b = fitness.best(self.store, name) or {}
            g.addWidget(QLabel(name), i, 0)
            kg = QDoubleSpinBox()
            kg.setRange(0, 500)
            kg.setDecimals(1)
            kg.setSingleStep(2.5)
            kg.setSuffix(" kg")
            kg.setValue(float(b.get("w") or 0))
            reps = QSpinBox()
            reps.setRange(1, 30)
            reps.setValue(int(b.get("r") or 1))
            g.addWidget(kg, i, 1)
            g.addWidget(reps, i, 2)
            self.rows[name] = (kg, reps, (float(b.get("w") or 0), int(b.get("r") or 1)))
        v.addLayout(g)
        btns = QHBoxLayout()
        btns.addStretch(1)
        c = button(t("cancel"), kind="Flat")
        c.clicked.connect(self.reject)
        ok = button(t("save"), kind="Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.save)
        btns.addWidget(c)
        btns.addWidget(ok)
        v.addLayout(btns)

    def save(self):
        n = 0
        for name, (kg, reps, old) in self.rows.items():
            w, r = round(kg.value(), 1), reps.value()
            if w > 0 and (w, r) != old:
                self.store.add("lifts", {"name": name, "w": w, "r": r, "date": day_today().isoformat()})
                n += 1
        if n:
            self.win.toast(t("max_saved", n=n))
        self.accept()


class FatDialog(ThemedDialog):
    """Mezura ölçüleriyle yağ oranı (fitness.navy_bodyfat). Boy ve cinsiyet prefs'te kalır.
    Kaydet: bugünün vücut kaydına (yoksa yeni) ölçüler + hesaplanan yağ oranı yazılır."""

    FIELDS = (("neck", "f_neck"), ("waist", "f_waist"), ("hip", "f_hip"), ("chest", "f_chest_cm"))

    def __init__(self, win):
        super().__init__(win, t("fat_calc_title"))
        from ..components import ChipBar
        self.win, self.store, self.prefs = win, win.store, prefs
        self.resize(460, 0)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 16)
        v.setSpacing(10)
        h = QLabel(t("fat_calc_title"))
        h.setStyleSheet("font-size: 18px; font-weight: 700;")
        v.addWidget(h)
        hint = sub_label(t("fat_calc_hint"), wrap=True)
        v.addWidget(hint)
        self.sex = ChipBar([("m", t("fat_m")), ("f", t("fat_f"))], prefs.get("body_sex", "m"))
        self.sex.changed.connect(lambda _k: self._update())
        v.addWidget(self.sex)
        rows = sorted((b for b in self.store.all("body") if parse_date(b.get("date"))),
                      key=lambda b: (b.get("date"), b.get("created") or ""))
        last = {}
        for b in rows:                       # her ölçünün son girilen değeri ön değer olur
            for k in ("weight", "neck", "waist", "hip", "chest"):
                if num(b.get(k)) > 0:
                    last[k] = num(b.get(k))
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        self.spins = {}

        def spin(key, label, lo, hi, val, suffix, r):
            s = QDoubleSpinBox()
            s.setRange(0, hi)
            s.setDecimals(1)
            s.setSingleStep(0.5)
            s.setSuffix(suffix)
            s.setValue(float(val or 0))
            s.valueChanged.connect(lambda _v: self._update())
            g.addWidget(QLabel(label), r, 0)
            g.addWidget(s, r, 1)
            self.spins[key] = s
            return s

        spin("height", t("fat_height"), 100, 230, prefs.get("body_height") or 175, " cm", 0)
        spin("weight", t("body_weight"), 30, 250, last.get("weight"), " kg", 1)
        for i, (k, lk) in enumerate(self.FIELDS, 2):
            spin(k, t(lk).replace(" (cm)", ""), 0, 250, last.get(k), " cm", i)
        self.opt = sub_label(t("fat_optional"))
        g.addWidget(self.opt, len(self.FIELDS) + 1, 2)
        v.addLayout(g)
        self.result = QLabel("")
        self.result.setStyleSheet("font-size: 20px; font-weight: 700;")
        v.addWidget(self.result)
        btns = QHBoxLayout()
        btns.addStretch(1)
        c = button(t("cancel"), kind="Flat")
        c.clicked.connect(self.reject)
        self.ok = button(t("save"), kind="Primary")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.save)
        btns.addWidget(c)
        btns.addWidget(self.ok)
        v.addLayout(btns)
        self._update()

    def value(self):
        s = self.spins
        return fitness.navy_bodyfat(self.sex.current, s["height"].value(), s["neck"].value(), s["waist"].value(),
                                    s["hip"].value())

    def _update(self):
        fem = self.sex.current == "f"
        self.spins["hip"].setToolTip("" if fem else t("fat_optional"))
        v = self.value()
        if v is None:
            self.result.setText(t("fat_result_none", h=", " + t("f_hip").replace(" (cm)", "").lower() if fem else ""))
        else:
            self.result.setText(t("fat_result", v=fmt_num(v, 1)) + "  ·  " +
                                t("fat_cls_%d" % fitness.fat_class(self.sex.current, v)))
        self.ok.setEnabled(v is not None)

    def save(self):
        v = self.value()
        if v is None:
            return
        self.prefs.set("body_sex", self.sex.current)
        self.prefs.set("body_height", round(self.spins["height"].value(), 1))
        fields = {"fat": v, "fat_src": "navy"}
        for k in ("weight", "neck", "waist", "hip", "chest"):
            x = round(self.spins[k].value(), 1)
            if x > 0:
                fields[k] = x
        today = day_today().isoformat()
        cur = next((b for b in self.store.all("body") if b.get("date") == today), None)
        if cur:
            self.store.update("body", cur["id"], **fields)
        else:
            self.store.add("body", dict(fields, date=today))
        self.win.toast(t("fat_saved", v=fmt_num(v, 1)))
        self.accept()
