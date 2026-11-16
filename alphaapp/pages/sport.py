"""Spor: haftalık hedef (haftada kaç gün), bu hafta, son haftalar, ne çalıştım, antrenman günlüğü."""
from collections import Counter
from datetime import timedelta

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QWidget, QSpinBox, QPushButton, QDialog,
                             QDateEdit, QLineEdit, QGridLayout)

from ..config import day_today
from ..components import (Page, Card, Row, StatTile, TileGrid, BarChart, HBars, WeekStrip, Ring,
                          FlowLayout)
from ..widgets import IconButton
from ..config import prefs
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_day, fmt_day_month, fmt_num, WEEKDAYS_SHORT
from ..store import parse_date, num, week_start
from . import task_row


class SportPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_sport"), t("sport_sub"))
        self.action(t("add_routine"), lambda: edit_item(win, "routine", preset={"category": "sport"}))
        self.action(t("add_workout"), lambda: edit_item(win, "workouts"), primary=True, icon="add")

        self.t_week = StatTile(t("this_week"))
        self.t_month = StatTile(t("this_month"))
        self.t_minutes = StatTile(t("minutes_month"))
        self.t_streak = StatTile(t("streak"))
        self.add(TileGrid([self.t_week, self.t_month, self.t_minutes, self.t_streak]))

        # bu hafta + hedef
        self.c_week = Card(t("this_week"))
        top = QHBoxLayout()
        top.setSpacing(18)
        self.ring = Ring(104)
        top.addWidget(self.ring)
        right = QVBoxLayout()
        right.setSpacing(6)
        self.strip = WeekStrip(WEEKDAYS_SHORT())
        right.addWidget(self.strip)
        gl = QHBoxLayout()
        lbl = QLabel(t("weekly_goal"))
        lbl.setObjectName("RowSub")
        self.goal = QSpinBox()
        self.goal.setRange(1, 7)
        self.goal.setSuffix(" " + t("days_per_week"))
        self.goal.setValue(int(prefs.get("sport_weekly_goal", 4)))
        self.goal.valueChanged.connect(self._goal)
        self.goal.setFixedWidth(130)
        gl.addWidget(lbl)
        gl.addWidget(self.goal)
        gl.addSpacing(8)
        self.break_btn = QPushButton(t("sport_break"))
        self.break_btn.setObjectName("Chip")
        self.break_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.break_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.break_btn.clicked.connect(self._edit_break)
        gl.addWidget(self.break_btn)
        gl.addStretch(1)
        right.addLayout(gl)
        top.addLayout(right, 1)
        w = QWidget()
        w.setLayout(top)
        self.c_week.layout().insertWidget(1, w)

        self.c_chart = Card(t("last_weeks"))
        self.chart = BarChart(roles=("text",), names=(t("days"),), fmt=lambda v: str(int(v)), height=150, max_value=7)
        self.c_chart.layout().addWidget(self.chart)
        self.row(self.c_week, self.c_chart)

        # beslenme: bugünkü kalori / makrolar + öğünler
        self.c_food = Card(t("nutrition"))
        gear = IconButton("settings", t("nutrition_goals"), 32, 20)
        gear.clicked.connect(win.show_prefs)
        self.c_food.head_widget(gear)
        self.c_meals = Card(t("add_meal"), add_tip=t("add_meal"))
        self.c_meals.add_clicked.connect(lambda: edit_item(win, "meals"))
        self.row(self.c_food, self.c_meals)

        self.c_log = Card(t("workout_log"), add_tip=t("add_workout"))
        self.c_log.add_clicked.connect(lambda: edit_item(win, "workouts"))
        self.c_focus = Card(t("what_trained"), t("last_30"))
        self.focus = HBars("text", fmt=lambda v: t("n_times", n=int(v)))
        self.c_focus.layout().addWidget(self.focus)
        self.c_plan = Card(t("sport_plan"), add_tip=t("add_routine"))
        self.c_plan.add_clicked.connect(lambda: edit_item(win, "routine", preset={"category": "sport"}))
        right_col = QWidget()
        rv = QVBoxLayout(right_col)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(16)
        rv.addWidget(self.c_focus)
        rv.addWidget(self.c_plan)
        rv.addStretch(1)
        self.row(self.c_log, right_col, stretches=[3, 2])

    def _add_meal(self, m):
        keep = {k: m.get(k) for k in ("name", "kcal", "protein", "carbs", "fat")}
        self.store.add("meals", keep | {"date": day_today().isoformat()})
        self.win.toast(t("meal_added", x=m.get("name", "")))

    def _fill_food(self):
        s, win, td = self.store, self.win, day_today()
        tot = s.meal_totals(td)
        c = self.c_food
        c.clear()
        # halkalar: yedikçe dolar; hedefin ±%10'u yeşil, %10'dan fazla aşınca kırmızı
        rings = QWidget()
        rl = QHBoxLayout(rings)
        rl.setContentsMargins(6, 6, 6, 4)
        rl.setSpacing(14)
        self.food_rings = {}
        for key, unit in (("kcal", "kcal"), ("protein", "g"), ("carbs", "g"), ("fat", "g")):
            goal = float(prefs.get("goal_" + key) or 0) or 1.0
            v = tot[key]
            over = v > goal * 1.1
            done = goal * 0.9 <= v <= goal * 1.1
            role = "bad" if over else "good" if done else "text"
            big = key == "kcal"
            ring = Ring(150 if big else 86, thick=12 if big else 7)
            ring.set(v / goal, fmt_num(v, 0), f"/ {fmt_num(goal, 0)} {unit}" if big else
                     f"%{int(round(100 * v / goal))}", role)
            ring.setToolTip(t("macro_val", v=fmt_num(v, 0), g=fmt_num(goal, 0), u=unit))
            self.food_rings[key] = ring
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(ring, 0, Qt.AlignmentFlag.AlignHCenter)
            name = QLabel(t("macro_" + key))
            name.setObjectName("RowTitle")
            name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(name)
            rest = goal - v
            hint = QLabel(t("macro_left", v=fmt_num(rest, 0), u=unit) if rest >= 0
                          else t("macro_over", v=fmt_num(-rest, 0), u=unit))
            hint.setObjectName("RowSub")
            hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(hint)
            if big:
                rl.addLayout(col)
                rl.addSpacing(6)
                mac = QHBoxLayout()
                mac.setSpacing(10)
                rl.addLayout(mac, 1)
            else:
                col.addStretch(1)
                mac.addLayout(col, 1)
        c.add(rings)
        # 7 günlük ortalama (öğün girilen günler)
        logged = [td - timedelta(days=k) for k in range(1, 8) if s.meals_on(td - timedelta(days=k))]
        if logged:
            kc = sum(s.meal_totals(d)["kcal"] for d in logged) / len(logged)
            pr = sum(s.meal_totals(d)["protein"] for d in logged) / len(logged)
            c.set_sub(t("nutrition_sub", k=fmt_num(kc, 0), p=fmt_num(pr, 0)))
        else:
            c.set_sub("")
        # sık yenenler: tıkla, bugüne ekle
        cnt = Counter()
        last = {}
        for m in sorted(s.all("meals"), key=lambda m: m.get("created") or ""):
            nm = (m.get("name") or "").strip()
            if nm:
                cnt[nm.lower()] += 1
                last[nm.lower()] = m
        top = [last[k] for k, _ in cnt.most_common(8)]
        if top:
            lbl = QLabel(t("frequent_meals"))
            lbl.setObjectName("FieldLabel")
            lbl.setContentsMargins(6, 10, 0, 4)
            c.add(lbl)
            box = QWidget()
            fl = FlowLayout(box, spacing=8)
            fl.setContentsMargins(6, 0, 0, 0)
            for m in top:
                b = QPushButton(f"{m.get('name', '')}  ·  {fmt_num(m.get('kcal') or 0, 0)}".replace("&", "&&"))
                b.setObjectName("Chip")
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(lambda _=False, m=m: self._add_meal(m))
                fl.addWidget(b)
            c.add(box)

        mc = self.c_meals
        mc.clear()
        meals = sorted(s.meals_on(td), key=lambda m: m.get("created") or "")
        for m in meals:
            r = Row(m.get("name", ""), t("meal_macros", p=fmt_num(m.get("protein") or 0, 0),
                                         c=fmt_num(m.get("carbs") or 0, 0), f=fmt_num(m.get("fat") or 0, 0)),
                    value=f"{fmt_num(m.get('kcal') or 0, 0)} kcal")
            mc.add(bind_row(win, r, "meals", m, [(t("repeat_today"), lambda m=m: self._add_meal(m))]))
        if not meals:
            mc.empty(t("no_meals"))
        mc.title_lbl.setText(t("todays_meals"))
        mc.set_sub(t("n_items", n=len(meals)) if meals else "")

    # ------------------------------------------------------------ spora ara
    def _edit_break(self):
        s, td = self.store, day_today()
        br = s.sport_break()
        dlg = QDialog(self.win)
        dlg.setWindowTitle(t("sport_break"))
        dlg.setMinimumWidth(420)
        v = QVBoxLayout(dlg)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        info = QLabel(t("sport_break_info"))
        info.setObjectName("RowSub")
        info.setWordWrap(True)
        v.addWidget(info)
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        edits = []
        for i, (key, d0) in enumerate((("f_from", br[0] if br else td), ("f_until", br[1] if br else td + timedelta(days=6)))):
            lbl = QLabel(t(key))
            lbl.setObjectName("FieldLabel")
            de = QDateEdit(QDate(d0.year, d0.month, d0.day))
            de.setCalendarPopup(True)
            de.setDisplayFormat("d MMMM yyyy, dddd")
            g.addWidget(lbl, i, 0)
            g.addWidget(de, i, 1)
            edits.append(de)
        note = QLineEdit((prefs.get("sport_break") or {}).get("note", "") if br else "")
        note.setPlaceholderText(t("sport_break_note"))
        lbl = QLabel(t("f_note"))
        lbl.setObjectName("FieldLabel")
        g.addWidget(lbl, 2, 0)
        g.addWidget(note, 2, 1)
        v.addLayout(g)
        quick = QHBoxLayout()
        quick.setSpacing(6)
        for n in (3, 7, 14, 30):
            b = QPushButton(t("n_days_short", n=n))
            b.setObjectName("Chip")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, n=n: edits[1].setDate(edits[0].date().addDays(n - 1)))
            quick.addWidget(b)
        quick.addStretch(1)
        v.addLayout(quick)
        bar = QHBoxLayout()
        result = {}
        if br:
            end = QPushButton(t("sport_break_end"))
            end.clicked.connect(lambda: (result.update(op="end"), dlg.accept()))
            bar.addWidget(end)
        bar.addStretch(1)
        cancel = QPushButton(t("cancel"))
        cancel.clicked.connect(dlg.reject)
        ok = QPushButton(t("save"))
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(lambda: (result.update(op="save"), dlg.accept()))
        bar.addWidget(cancel)
        bar.addWidget(ok)
        v.addLayout(bar)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if result.get("op") == "end":
            # bugün bitir (geçmiş ara günleri seride korunsun); henüz başlamadıysa tamamen kaldır
            if br[0] >= td:
                prefs.set("sport_break", {})
            else:
                prefs.set("sport_break", {"from": br[0].isoformat(), "until": (td - timedelta(days=1)).isoformat(),
                                          "note": (prefs.get("sport_break") or {}).get("note", "")})
        else:
            a, z = (e.date().toPyDate() for e in edits)
            if z < a:
                a, z = z, a
            prefs.set("sport_break", {"from": a.isoformat(), "until": z.isoformat(), "note": note.text().strip()})
        self.refresh()
        self.win.pages["today"].mark_dirty()

    def _goal(self, v):
        prefs.set("sport_weekly_goal", int(v))
        self.refresh()
        self.win.pages["today"].mark_dirty()

    def refresh(self):
        s, win = self.store, self.win
        td = day_today()
        ws = week_start(td)
        base = max(1, int(prefs.get("sport_weekly_goal", 4)))
        if self.goal.value() != base:
            self.goal.blockSignals(True)
            self.goal.setValue(base)
            self.goal.blockSignals(False)
        goal = s.sport_goal(ws)
        days = s.sport_days(ws, ws + timedelta(days=6))
        n = len(days)
        left = goal - n
        br = s.sport_break()
        on_break = br is not None and br[0] <= td <= br[1]
        if goal == 0:
            self.ring.set(1.0 if n else 0.0, t("sport_break_short"), t("n_days_short", n=n) if n else "", "text3")
        else:
            self.ring.set(n / goal, f"{n}/{goal}", t("days"), "good" if n >= goal else "text")
        self.strip.set([(ws + timedelta(days=i)) in days for i in range(7)], td.weekday())
        if on_break:
            sub = t("sport_break_until", d=fmt_day_month(br[1]))
        elif br is not None and br[0] > td:
            sub = t("sport_break_from", a=fmt_day_month(br[0]), z=fmt_day_month(br[1]))
        else:
            sub = t("goal_reached") if left <= 0 else t("goal_left", n=left, d=7 - td.weekday())
        if goal and goal != base and not on_break and not (br is not None and br[0] > td):
            sub += " · " + t("sport_goal_scaled", g=goal)
        self.c_week.set_sub(sub)
        self.break_btn.setText(t("sport_break_edit") if br and br[1] >= td else t("sport_break"))
        self.break_btn.setProperty("checked", bool(on_break))
        self.break_btn.setCheckable(True)
        self.break_btn.setChecked(bool(on_break))
        self.t_week.set(f"{n}/{goal}" if goal else t("sport_break_short"), t("days") if goal else "",
                        "good" if goal and n >= goal else None)

        m0 = td.replace(day=1)
        month_w = s.workouts_between(m0, td)
        self.t_month.set(str(len({w.get('date') for w in month_w})), t("days"))
        self.t_minutes.set(str(int(sum(num(w.get("minutes")) for w in month_w))), t("minutes"))

        # seri: hedefi tutturan ardışık haftalar (bu hafta henüz bitmediyse geçen haftadan say)
        # ara haftaları (hedef 0) seriyi ne artırır ne bozar
        streak = 0
        k = 0 if n >= goal else 1
        while k <= 520:
            a = ws - timedelta(weeks=k)
            g = s.sport_goal(a)
            if g == 0:
                k += 1
                continue
            if len(s.sport_days(a, a + timedelta(days=6))) >= g:
                streak += 1
                k += 1
            else:
                break
        self.t_streak.set(str(streak), t("weeks"), "good" if streak else None)

        data = []
        for i in range(7, -1, -1):
            a = ws - timedelta(weeks=i)
            data.append((fmt_day_month(a, short=True), [len(s.sport_days(a, a + timedelta(days=6)))]))
        self.chart.set_data(data)

        cnt = Counter()
        for w in s.workouts_between(td - timedelta(days=30), td):
            for f in (w.get("focus") or w.get("kind") or "").split(","):
                f = f.strip()
                if f:
                    cnt[f] += 1
        self.focus.set_data(cnt.most_common(8), t("no_workouts"))

        self.c_log.clear()
        ws_all = sorted(s.all("workouts"), key=lambda w: (w.get("date") or "", w.get("created") or ""), reverse=True)
        for w in ws_all[:25]:
            d = parse_date(w.get("date"))
            sub = [fmt_day(d) if d else ""]
            if w.get("minutes"):
                sub.append(t("n_min", n=int(num(w["minutes"]))))
            if w.get("note"):
                sub.append(w["note"].splitlines()[0][:60])
            title = " · ".join(x for x in (w.get("kind"), w.get("focus")) if x) or t("workout")
            r = Row(title, " · ".join(x for x in sub if x), icon="cat_sport")
            self.c_log.add(bind_row(win, r, "workouts", w, [(t("repeat_today"), lambda w=w: s.add("workouts", {
                k: v for k, v in w.items() if k not in ("id", "created", "date")} | {"date": td.isoformat()}))]))
        if not ws_all:
            self.c_log.empty(t("no_workouts_hint"))
        self.c_log.set_sub(t("n_total", n=len(ws_all)) if ws_all else "")

        self._fill_food()

        self.c_plan.clear()
        rt = sorted((r for r in s.all("routine") if r.get("category") == "sport"),
                    key=lambda r: (min(r.get("days") or [9]), r.get("start") or ""))
        names = WEEKDAYS_SHORT()
        for r in rt:
            dd = ", ".join(names[i] for i in sorted(r.get("days") or []))
            st = r.get("start") or ""
            row = Row(r.get("title", ""), " · ".join(x for x in (dd, st, r.get("place")) if x), icon="clock")
            self.c_plan.add(bind_row(win, row, "routine", r))
        for tk in s.open_tasks("sport")[:5]:
            self.c_plan.add(task_row(win, tk, show_cat=False))
        if not rt and not s.open_tasks("sport"):
            self.c_plan.empty(t("no_sport_plan"))

