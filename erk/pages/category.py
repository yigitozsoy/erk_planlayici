"""Genel kategori sayfası: Kişisel ve kullanıcının eklediği kategoriler (navmenu.custom_cats).
Yapılacaklar (hızlı ekle), önümüzdeki 30 gün, haftalık program."""
from ..components import Page, Card
from ..forms import edit_item
from ..i18n import t, WEEKDAYS_SHORT
from . import task_row, deadline_row, routine_row, QuickTask


class CategoryPage(Page):
    def __init__(self, store, win, cat):
        from .. import navmenu
        self.cat = cat
        super().__init__(store, win, navmenu.label(cat), t("cat_page_sub"))
        self.action(t("add_task"), lambda: edit_item(win, "tasks", preset={"category": cat}), primary=True, icon="add")

        self.c_tasks = Card(t("todo"), add_tip=t("add_task"))
        self.c_tasks.add_clicked.connect(lambda: edit_item(win, "tasks", preset={"category": cat}))
        self.c_tasks.layout().addSpacing(6)
        self.c_tasks.layout().addWidget(QuickTask(win, cat, due_today=False, placeholder=t("quick_task_ph2")))
        self.c_up = Card(t("upcoming"))
        self.row(self.c_tasks, self.c_up)
        self.c_routine = Card(t("cat_routine"), add_tip=t("cat_routine"))
        self.c_routine.add_clicked.connect(lambda: edit_item(win, "routine", preset={"category": cat}))
        self.add(self.c_routine)

    def refresh(self):
        from .. import navmenu
        s, win, cat = self.store, self.win, self.cat
        self.title_lbl.setText(navmenu.label(cat))

        self.c_tasks.clear()
        tasks = s.open_tasks(cat)
        for tk in tasks[:15]:
            self.c_tasks.add(task_row(win, tk, show_cat=False))
        if not tasks:
            self.c_tasks.empty(t("no_tasks"))

        self.c_up.clear()
        ups = [d for d in s.deadlines(30, cat) if d["coll"] != "tasks"]
        for d in ups[:10]:
            self.c_up.add(deadline_row(win, d, show_cat=False))
        if not ups:
            self.c_up.empty(t("no_upcoming_cat"))

        self.c_routine.clear()
        wd = WEEKDAYS_SHORT()
        rs = sorted((r for r in s.all("routine") if r.get("category") == cat),
                    key=lambda r: (min(r.get("days") or [7]), r.get("start") or ""))
        for r in rs:
            row = routine_row(win, r)
            days = " ".join(wd[d] for d in sorted(r.get("days") or []))
            if days:
                row.setToolTip(days)
            self.c_routine.add(row)
        if not rs:
            self.c_routine.empty(t("no_routine_cat"))
