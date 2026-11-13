"""Sosyal hayat: yaklaşan planlar, doğum günleri, sosyal görevler, geçmiş buluşmalar."""
from datetime import date

from ..components import Page, Card, Row, StatTile, TileGrid
from ..forms import edit_item, bind_row
from ..i18n import t, due_badge, fmt_day
from ..store import parse_date, _next_anniversary
from . import task_row, QuickTask


class SocialPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_social"), t("social_sub"))
        self.action(t("add_birthday"), lambda: edit_item(win, "birthdays"))
        self.action(t("add_event"), lambda: edit_item(win, "events"), primary=True, icon="add")

        self.t_up = StatTile(t("upcoming_plans"))
        self.t_month = StatTile(t("met_this_month"))
        self.t_bday = StatTile(t("next_birthday"))
        self.add(TileGrid([self.t_up, self.t_month, self.t_bday]))

        self.c_plans = Card(t("upcoming_plans"), add_tip=t("add_event"))
        self.c_plans.add_clicked.connect(lambda: edit_item(win, "events"))
        self.c_bdays = Card(t("birthdays"), add_tip=t("add_birthday"))
        self.c_bdays.add_clicked.connect(lambda: edit_item(win, "birthdays"))
        self.row(self.c_plans, self.c_bdays)

        self.c_tasks = Card(t("social_tasks"), add_tip=t("add_task"))
        self.c_tasks.add_clicked.connect(lambda: edit_item(win, "tasks", preset={"category": "social"}))
        self.c_tasks.layout().addSpacing(6)
        self.c_tasks.layout().addWidget(QuickTask(win, "social", due_today=False, placeholder=t("quick_social_ph")))
        self.c_past = Card(t("past_events"))
        self.row(self.c_tasks, self.c_past)

    def refresh(self):
        s, win = self.store, self.win
        td = date.today()
        evs = [(parse_date(e.get("date")), e) for e in s.all("events")]
        future = sorted([x for x in evs if x[0] and x[0] >= td], key=lambda x: (x[0], x[1].get("time") or ""))
        past = sorted([x for x in evs if x[0] and x[0] < td], key=lambda x: x[0], reverse=True)

        self.t_up.set(str(len(future)))
        self.t_month.set(str(sum(1 for d, _ in evs if d and d.year == td.year and d.month == td.month and d <= td)),
                         t("plans"))
        bd = sorted(((_next_anniversary(parse_date(b.get("date")), td), b) for b in s.all("birthdays")
                     if parse_date(b.get("date"))), key=lambda x: x[0])
        if bd:
            self.t_bday.set(due_badge(bd[0][0])[0], bd[0][1].get("name", ""))
        else:
            self.t_bday.set("—")

        self.c_plans.clear()
        for d, e in future[:12]:
            sub = [fmt_day(d)]
            if e.get("time"):
                sub.append(e["time"])
            for k in ("people", "place"):
                if e.get(k):
                    sub.append(e[k])
            r = Row(e.get("title", ""), " · ".join(sub), icon="group", badges=[due_badge(d)])
            self.c_plans.add(bind_row(win, r, "events", e))
        if not future:
            self.c_plans.empty(t("no_plans"))

        self.c_bdays.clear()
        for d, b in bd[:12]:
            born = parse_date(b.get("date"))
            age = d.year - born.year if born and born.year > 1900 else None
            r = Row(b.get("name", ""), fmt_day(d) + (f" · {t('turns', n=age)}" if age else ""), icon="cake",
                    badges=[due_badge(d)])
            self.c_bdays.add(bind_row(win, r, "birthdays", b))
        if not bd:
            self.c_bdays.empty(t("no_birthdays"))

        self.c_tasks.clear()
        tasks = s.open_tasks("social")
        for tk in tasks[:10]:
            self.c_tasks.add(task_row(win, tk, show_cat=False))
        if not tasks:
            self.c_tasks.empty(t("no_tasks"))

        self.c_past.clear()
        for d, e in past[:8]:
            sub = [fmt_day(d)] + [e[k] for k in ("people", "place") if e.get(k)]
            r = Row(e.get("title", ""), " · ".join(sub), icon="group", icon_role="text3")
            self.c_past.add(bind_row(win, r, "events", e))
        if not past:
            self.c_past.empty(t("no_past"))
