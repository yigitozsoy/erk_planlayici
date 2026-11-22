"""Bugün: sabah açınca her şey hazır — bugünün programı, yapılacaklar, yaklaşan deadline'lar, haftanın özeti."""
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QWidget, QPushButton

from ..config import day_today, day_of
from ..components import Page, Card, Row, WeekStrip, Ring, MonthCalendar
from ..widgets import IconButton
from ..config import prefs
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_day_month, fmt_long_date, fmt_money, fmt_month, fmt_num, WEEKDAYS_SHORT
from ..store import parse_date, week_start
from . import task_row, deadline_row, routine_row, time_lead, QuickTask, CAT_ICON, KIND_ICON

# takvim noktalarının rengi (tür → tema rolü), soldan sağa öncelik sırası
DOT_ROLE = {"exam": "bad", "task": "text", "project": "text", "debt_owe": "text", "debt_owed": "text",
            "event": "text2", "birthday": "text2", "workout": "good"}
DOT_ORDER = ("bad", "text", "text2", "good")


class TodayPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, "", "")
        self.title_lbl.setObjectName("Greeting")
        self.action(t("add_task"), lambda: edit_item(win, "tasks", preset={"due": day_today().isoformat()}),
                    icon="add")
        self.action(t("plan_day"), win.open_plan, icon="sunrise")
        self.action(t("sd_open"), win.open_shutdown, icon="moon")

        # sabah planı yapılmadıysa üstte davet
        self.c_plan = Card(t("plan_banner_title"), t("plan_banner_sub"))
        self.c_plan.setObjectName("CardToday")
        bl = QHBoxLayout()
        bl.setSpacing(8)
        for text, role, cb in ((t("plan_banner_go"), "Primary", win.open_plan),
                               (t("plan_banner_not_today"), "Flat", self._plan_not_today)):
            b = QPushButton(text)
            b.setObjectName(role)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(cb)
            bl.addWidget(b)
        bl.addStretch(1)
        self.c_plan.layout().addSpacing(4)
        self.c_plan.layout().addLayout(bl)
        self.add(self.c_plan)

        # akşam: kapanış yapılmadıysa davet (prefs shutdown_hour sonrası)
        self.c_shut = Card(t("sd_banner_title"), t("sd_banner_sub"))
        self.c_shut.setObjectName("CardToday")
        bl = QHBoxLayout()
        bl.setSpacing(8)
        for text, role, cb in ((t("sd_banner_go"), "Primary", win.open_shutdown),
                               (t("plan_banner_not_today"), "Flat", self._shut_not_today)):
            b = QPushButton(text)
            b.setObjectName(role)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(cb)
            bl.addWidget(b)
        bl.addStretch(1)
        self.c_shut.layout().addSpacing(4)
        self.c_shut.layout().addLayout(bl)
        self.add(self.c_shut)

        self.c_prog = Card(t("today_program"), add_tip=t("add_routine"))
        self.c_prog.add_clicked.connect(lambda: edit_item(win, "routine"))
        self.c_todo = Card(t("todo"), add_tip=t("add_task"))
        self.c_todo.add_clicked.connect(lambda: edit_item(win, "tasks", preset={"due": day_today().isoformat()}))
        self.c_todo.layout().addSpacing(6)
        self.c_todo.layout().addWidget(QuickTask(win))

        # sağ üst: bu ayın takvimi
        self.c_cal = Card("", add_tip=t("add_task"))
        self.c_cal.add_clicked.connect(self._cal_new_task)
        self.cal_today_btn = QPushButton(t("today"))
        self.cal_today_btn.setObjectName("SmallPill")
        self.cal_today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cal_today_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cal_today_btn.clicked.connect(self._cal_today)
        self.c_cal.head_widget(self.cal_today_btn)
        for ic, tip, step in (("chevron_left", t("cal_prev"), -1), ("chevron_right", t("cal_next"), 1)):
            b = IconButton(ic, tip, 32, 20)
            b.clicked.connect(lambda _=False, k=step: self._cal_shift(k))
            self.c_cal.head_widget(b)
        self.cal = MonthCalendar(WEEKDAYS_SHORT())
        self.cal.setToolTip(t("cal_tip"))
        self.cal.day_clicked.connect(self._cal_click)
        self.cal.day_activated.connect(lambda d: edit_item(win, "tasks", preset={"due": d.isoformat()}))
        self.c_cal.layout().insertWidget(1, self.cal)
        self.cal_sel = None
        self.row(self.c_prog, self.c_todo, self.c_cal, stretches=[4, 5, 4])

        self.c_dead = Card(t("upcoming"))
        self.c_habits = Card(t("today_habits"), add_tip=t("add_habit"))
        self.c_habits.add_clicked.connect(lambda: edit_item(win, "habits"))
        self.c_week = Card(t("week_summary"))
        self.row(self.c_dead, self.c_habits, self.c_week, stretches=[3, 3, 2])

        from .library import now_card
        self.c_now = now_card(win)          # kütüphane: şu an okunan / izlenen (boşsa gizli)
        self.add(self.c_now)
        self.c_pinned = Card(t("pinned_notes"))
        self.add(self.c_pinned)

        # haftanın özeti: sabit parçalar
        wk = QHBoxLayout()
        wk.setSpacing(16)
        self.ring = Ring(92)
        wk.addWidget(self.ring)
        right = QVBoxLayout()
        right.setSpacing(4)
        self.sport_lbl = QLabel()
        self.sport_lbl.setObjectName("RowTitle")
        self.strip = WeekStrip(WEEKDAYS_SHORT())
        right.addWidget(self.sport_lbl)
        right.addWidget(self.strip)
        wk.addLayout(right, 1)
        self.week_top = QWidget()
        self.week_top.setLayout(wk)
        self.c_week.layout().insertWidget(1, self.week_top)

    # ------------------------------------------------------------ takvim
    def _cal_shift(self, k):
        y, m = self.cal.year, self.cal.month + k
        if m < 1:
            y, m = y - 1, 12
        elif m > 12:
            y, m = y + 1, 1
        self.cal.set_month(y, m)
        self._fill_cal()

    def _cal_today(self):
        td = day_today()
        self.cal_sel = None
        self.cal.set_selected(None)
        self.cal.set_month(td.year, td.month)
        self._fill_cal()

    def _cal_click(self, d):
        self.cal_sel = None if d == self.cal_sel else d
        if d.month != self.cal.month or d.year != self.cal.year:
            self.cal.set_month(d.year, d.month)
        self.cal.set_selected(self.cal_sel)
        self._fill_cal()

    def _cal_new_task(self):
        d = self.cal_sel or day_today()
        edit_item(self.win, "tasks", preset={"due": d.isoformat()})

    def _fill_cal(self):
        s, win, td = self.store, self.win, day_today()
        cal, c = self.cal, self.c_cal
        a, b = cal.visible_range()
        items = s.items_between(a, b)
        marks = {}
        for d, lst in items.items():
            roles = {DOT_ROLE.get(x["kind"], "text2") for x in lst}
            marks[d] = [r for r in DOT_ORDER if r in roles]
        cal.set_marks(marks)
        c.title_lbl.setText(fmt_month(cal.year, cal.month))
        self.cal_today_btn.setVisible((cal.year, cal.month) != (td.year, td.month) or self.cal_sel is not None)
        c.clear()
        sel = self.cal_sel
        if sel is None:
            n = sum(len(v) for d, v in items.items() if d.month == cal.month and d.year == cal.year)
            c.set_sub(t("cal_hint", n=n) if n else t("cal_hint_empty"))
            return
        lst = items.get(sel, [])
        c.set_sub(fmt_long_date(sel) + (f" · {t('n_items', n=len(lst))}" if lst else ""))
        for x in lst:
            sub = [t("cat_" + x["category"])]
            kind = x["kind"]
            if kind.startswith("debt_"):
                sub.append(t("dir_" + kind[5:]) + " · " + fmt_money(x["sub"]))
            elif kind == "birthday":
                sub.append(t("birthday"))
            elif kind == "exam":
                sub.append(t("exam"))
            elif x["sub"]:
                sub.append(str(x["sub"]))
            r = Row(x["title"], " · ".join(sub), icon=KIND_ICON.get(kind) or CAT_ICON.get(x["category"], "flag"),
                    icon_role=DOT_ROLE.get(kind, "text2") if kind in ("exam", "workout") else "text2")
            item = s.get(x["coll"], x["id"])
            c.add(bind_row(win, r, x["coll"], item) if item is not None else r)
        if not lst:
            c.empty(t("cal_empty"))

    def _shut_not_today(self):
        prefs.set("last_shutdown", day_today().isoformat())
        self.c_shut.hide()

    def _plan_not_today(self):
        prefs.set("last_plan", day_today().isoformat())
        self.c_plan.hide()

    def refresh(self):
        s, win = self.store, self.win
        self.c_now.fill()
        now = datetime.now()
        td = day_today()
        name = (prefs.get("name") or "").strip()
        h = now.hour
        greet = t("greet_morning") if 5 <= h < 12 else t("greet_day") if h < 18 else t("greet_evening")
        self.title_lbl.setText(f"{greet}, {name}" if name else greet)

        # --- bugünün programı (rutin + saatli görev + plan + sınav)
        self.c_prog.clear()
        hm = now.strftime("%H:%M")
        items = []
        for r in s.routine_for(td):
            items.append((r.get("start") or "99:99", "r", r))
        for tk in s.all("tasks"):
            if not tk.get("done") and parse_date(tk.get("due")) == td and tk.get("time"):
                items.append((tk["time"], "t", tk))
        for ev in s.all("events"):
            if parse_date(ev.get("date")) == td:
                items.append((ev.get("time") or "99:98", "e", ev))
        courses = {c["id"]: c for c in s.all("courses")}
        for ex in s.all("exams"):
            if parse_date(ex.get("date")) == td:
                items.append((ex.get("time") or "99:97", "x", ex))
        items.sort(key=lambda x: x[0])
        for _, kind, it in items:
            if kind == "r":
                self.c_prog.add(routine_row(win, it, hm))
            elif kind == "t":
                r = Row(it.get("title", ""), t("cat_" + (it.get("category") or "personal")),
                        lead=time_lead(it["time"]))
                self.c_prog.add(bind_row(win, r, "tasks", it))
            elif kind == "e":
                sub = " · ".join(x for x in (it.get("people"), it.get("place")) if x) or t("cat_social")
                r = Row(it.get("title", ""), sub, lead=time_lead(it.get("time") or t("all_day")))
                self.c_prog.add(bind_row(win, r, "events", it))
            else:
                c = courses.get(it.get("course"), {})
                r = Row(f"{c.get('name', '')} · {it.get('name', '')}", t("exam"), lead=time_lead(it.get("time") or t("exam_short")),
                        badges=[(t("today"), "bad")])
                self.c_prog.add(bind_row(win, r, "exams", it))
        if not items:
            self.c_prog.empty(t("no_program"))
        self.c_prog.set_sub(t("n_items", n=len(items)) if items else "")

        # --- yapılacaklar: geciken + bugün + tarihsiz
        self.c_todo.clear()
        opens = s.open_tasks()
        due_now = [x for x in opens if parse_date(x.get("due")) and parse_date(x.get("due")) <= td]
        due_now.sort(key=lambda x: x.get("focus") != td.isoformat())   # odak işler üstte
        undated = [x for x in opens if not parse_date(x.get("due"))]
        for tk in due_now:
            self.c_todo.add(task_row(win, tk))
        if undated:
            if due_now:
                lbl = QLabel(t("undated"))
                lbl.setObjectName("FieldLabel")
                lbl.setContentsMargins(6, 10, 0, 2)
                self.c_todo.add(lbl)
            for tk in undated[:8]:
                self.c_todo.add(task_row(win, tk))
            if len(undated) > 8:
                self.c_todo.empty(t("and_more", n=len(undated) - 8))
        done_today = [x for x in s.all("tasks") if x.get("done") and day_of(x.get("done_at")) == td]
        if not due_now and not undated:
            self.c_todo.empty(t("no_todo"))
        n_over = sum(1 for x in due_now if parse_date(x.get("due")) < td)
        bits = [t("n_open", n=len(due_now))] if due_now else []
        if n_over:
            bits.append(t("n_overdue", n=n_over))
        if done_today:
            bits.append(t("n_done_today", n=len(done_today)))
        self.c_todo.set_sub(" · ".join(bits))

        # --- yaklaşanlar
        self.c_dead.clear()
        days = int(prefs.get("deadline_days", 14))
        dl = [d for d in s.deadlines(days) if not (d["coll"] == "tasks" and d["date"] <= td)]
        for d in dl[:12]:
            self.c_dead.add(deadline_row(win, d))
        if not dl:
            self.c_dead.empty(t("no_deadlines", n=days))
        elif len(dl) > 12:
            self.c_dead.empty(t("and_more", n=len(dl) - 12))
        self.c_dead.set_sub(t("next_n_days", n=days))

        # --- haftanın özeti
        ws = week_start(td)
        goal = s.sport_goal(ws)
        sdays = s.sport_days(ws, ws + timedelta(days=6))
        n = len(sdays)
        if goal:
            self.ring.set(n / goal, f"{n}/{goal}", t("days"), "good" if n >= goal else "text")
            self.sport_lbl.setText(t("sport_week", n=n, g=goal))
        else:
            self.ring.set(0, t("sport_break_short"), "", "text3")
            self.sport_lbl.setText(t("sport_break_until", d=fmt_day_month(s.sport_break()[1])))
        self.strip.set([(ws + timedelta(days=i)) in sdays for i in range(7)], td.weekday())
        self.week_top.setVisible(bool(prefs.get("show_sport_on_today", True)))
        self.c_week.clear()
        if prefs.get("show_finance_on_today", True):
            inc, exp = s.month_totals(td.year, td.month)
            self.c_week.add(Row(t("month_income"), value=fmt_money(inc), value_role="good", icon="arrow_down"))
            self.c_week.add(Row(t("month_expense"), value=fmt_money(exp), value_role="bad", icon="arrow_up"))
            owe, owed = s.debt_totals()
            if owe:
                self.c_week.add(Row(t("total_owe"), value=fmt_money(owe), icon="wallet"))
            if owed:
                self.c_week.add(Row(t("total_owed"), value=fmt_money(owed), icon="wallet"))
            for r in self.c_week.findChildren(Row):
                r.clicked.connect(lambda: win.show_page("finance"))
        n_courses = len(s.all("courses"))
        if n_courses:
            below = 0
            for c in s.all("courses"):
                avg, _, tgt = s.course_average(c["id"])
                if avg is not None and tgt is not None and avg < tgt:
                    below += 1
            r = Row(t("courses_status"), t("courses_below", n=below) if below else t("courses_ok"), icon="cat_education",
                    badges=[(str(below), "warn")] if below else [])
            r.clicked.connect(lambda: win.show_page("education"))
            self.c_week.add(r)

        # --- bugünün alışkanlıkları (işaretle; tamamı Alışkanlıklar'da)
        from .habits import habit_row
        from .. import habits_core as hc
        self.c_habits.clear()
        habits = sorted(s.all("habits"), key=lambda h: (h.get("created") or "", h.get("name") or ""))
        tot = 0.0
        for h in habits:
            tot += hc.state(h, td, s) or 0
            self.c_habits.add(habit_row(win, s, h, td, show_cat=False))
        if not habits:
            self.c_habits.empty(t("no_habits"))
        self.c_habits.set_sub(t("habits_today_sub", d=fmt_num(tot, 1) if tot % 1 else int(tot), n=len(habits))
                              if habits else "")
        self.c_habits.setVisible(bool(prefs.get("show_habits_on_today", True)))

        # --- bu ayın takvimi
        self._fill_cal()

        # --- sabitlenmiş notlar
        self.c_pinned.clear()
        pins = [x for x in s.all("notes") if x.get("pinned")]
        pins.sort(key=lambda x: x.get("updated") or "", reverse=True)
        self.c_pinned.setVisible(bool(pins))
        for nt in pins[:6]:
            body = (nt.get("body") or "").strip().replace("\n", "  ·  ")
            r = Row(nt.get("title") or t("untitled"), body[:140], icon="pin")
            r.clicked.connect(lambda nid=nt["id"]: (win.show_page("notes"), win.pages["notes"].open_note(nid)))
            self.c_pinned.add(r)

        # alt başlık + günün hedefi
        from .shutdown import is_due
        shut = is_due(now)
        self.c_shut.setVisible(shut)
        self.c_plan.setVisible(not shut and bool(prefs.get("morning_plan", True))
                               and prefs.get("last_plan") != td.isoformat())
        intention = (s.day(td) or {}).get("intention", "")
        self.set_sub(fmt_long_date(td) + (f"   ·   “{intention}”" if intention else ""))
