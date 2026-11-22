"""İş: projeler (durum + ilerleme), iş görevleri, iş deadline'ları, bugünkü iş programı."""
from datetime import date, datetime

from ..config import day_today, day_of
from ..components import Page, Card, StatTile, TileGrid
from ..forms import edit_item
from ..i18n import t
from ..store import week_start
from . import task_row, deadline_row, routine_row, QuickTask
from .projects import project_row, sorted_projects

STATUS_ORDER = {"doing": 0, "waiting": 1, "todo": 2, "done": 3}


class WorkPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_work"), t("work_sub"))
        self.action(t("add_task"), lambda: edit_item(win, "tasks", preset={"category": "work"}))
        self.action(t("add_project"), lambda: edit_item(win, "projects", preset={"category": "work"}), primary=True,
                    icon="add")

        self.t_active = StatTile(t("active_projects"))
        self.t_open = StatTile(t("open_tasks"))
        self.t_week = StatTile(t("due_this_week"))
        self.t_done = StatTile(t("done_this_week"))
        self.add(TileGrid([self.t_active, self.t_open, self.t_week, self.t_done]))

        self.c_proj = Card(t("projects"), add_tip=t("add_project"))
        self.c_proj.add_clicked.connect(lambda: edit_item(win, "projects", preset={"category": "work"}))
        self.c_tasks = Card(t("work_tasks"), add_tip=t("add_task"))
        self.c_tasks.add_clicked.connect(lambda: edit_item(win, "tasks", preset={"category": "work"}))
        self.c_tasks.layout().addSpacing(6)
        self.c_tasks.layout().addWidget(QuickTask(win, "work", due_today=False, placeholder=t("quick_task_ph2")))
        self.row(self.c_proj, self.c_tasks)

        self.c_dead = Card(t("upcoming"))
        self.c_today = Card(t("today_work"), add_tip=t("add_routine"))
        self.c_today.add_clicked.connect(lambda: edit_item(win, "routine", preset={"category": "work"}))
        self.row(self.c_dead, self.c_today)

    def refresh(self):
        s, win = self.store, self.win
        td = day_today()
        ws = week_start(td)
        projects = sorted_projects(s, "work")
        active = [p for p in projects if p.get("status") != "done"]
        tasks = s.open_tasks("work")
        self.t_active.set(str(len(active)), t("n_total", n=len(projects)) if projects else "")
        self.t_open.set(str(len(tasks)))
        dl = s.deadlines(6 - td.weekday(), "work")
        self.t_week.set(str(len(dl)), t("n_overdue", n=sum(1 for d in dl if d["date"] < td)) if any(
            d["date"] < td for d in dl) else "", "bad" if any(d["date"] < td for d in dl) else None)
        done = [x for x in s.all("tasks") if x.get("category") == "work" and x.get("done")
                and (day_of(x.get("done_at")) or date.min) >= ws]
        self.t_done.set(str(len(done)))

        self.c_proj.clear()
        for p in projects:
            self.c_proj.add(project_row(win, p))
        if not projects:
            self.c_proj.empty(t("no_projects"))

        self.c_tasks.clear()
        for tk in tasks[:12]:
            self.c_tasks.add(task_row(win, tk, show_cat=False))
        if not tasks:
            self.c_tasks.empty(t("no_tasks"))

        self.c_dead.clear()
        dl = s.deadlines(30, "work")
        for d in dl[:10]:
            self.c_dead.add(deadline_row(win, d, show_cat=False))
        if not dl:
            self.c_dead.empty(t("no_deadlines", n=30))
        self.c_dead.set_sub(t("next_n_days", n=30))

        self.c_today.clear()
        rt = s.routine_for(td, "work")
        hm = datetime.now().strftime("%H:%M")
        for r in rt:
            self.c_today.add(routine_row(win, r, hm))
        if not rt:
            self.c_today.empty(t("no_work_today"))
