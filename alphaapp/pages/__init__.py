"""Sayfalar ve sayfalar arası ortak satır yardımcıları."""
from datetime import date, datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QLineEdit

from ..components import Row
from ..forms import bind_row, edit_item
from ..i18n import t, due_badge, fmt_day, fmt_money
from ..store import parse_date

CAT_ICON = {"education": "cat_education", "work": "cat_work", "sport": "cat_sport", "social": "group", "finance": "wallet",
            "personal": "person"}
KIND_ICON = {"task": None, "exam": "cat_education", "project": "cat_work", "debt_owe": "wallet", "debt_owed": "wallet",
             "event": "group", "birthday": "cake", "workout": "cat_sport"}


def build_pages(store, win):
    from .today import TodayPage
    from .schedule import SchedulePage
    from .education import EducationPage
    from .work import WorkPage
    from .sport import SportPage
    from .social import SocialPage
    from .finance import FinancePage
    from .notes import NotesPage
    from .plan import PlanPage
    from .habits import HabitsPage
    return {
        "today": TodayPage(store, win),
        "schedule": SchedulePage(store, win),
        "habits": HabitsPage(store, win),
        "education": EducationPage(store, win),
        "work": WorkPage(store, win),
        "sport": SportPage(store, win),
        "social": SocialPage(store, win),
        "finance": FinancePage(store, win),
        "notes": NotesPage(store, win),
        "plan": PlanPage(store, win),
    }


def time_lead(text, width=86):
    lbl = QLabel(text)
    lbl.setObjectName("TimeLbl")
    lbl.setFixedWidth(width)
    return lbl


def toggle_task(win, task, done):
    win.store.update("tasks", task["id"], done=done,
                     done_at=datetime.now().isoformat(timespec="seconds") if done else None)
    if done:
        win.toast(t("task_done"), t("undo"),
                  lambda: win.store.update("tasks", task["id"], done=False, done_at=None))


def task_row(win, task, show_cat=True):
    d = parse_date(task.get("due"))
    sub = []
    if show_cat:
        sub.append(t("cat_" + (task.get("category") or "personal")))
    if d and task.get("time"):
        sub.append(task["time"])
    if task.get("note"):
        sub.append(task["note"].splitlines()[0][:60])
    badges = []
    if task.get("focus") == date.today().isoformat() and not task.get("done"):
        badges.append((t("focus"), None))
    if task.get("priority") == "high" and not task.get("done"):
        badges.append((t("prio_high"), "warn"))
    if d and not task.get("done"):
        badges.append(due_badge(d))
    r = Row(task.get("title", ""), " · ".join(sub), check=bool(task.get("done")), badges=badges)
    r.check_toggled.connect(lambda v: toggle_task(win, task, v))
    extra = []
    if not task.get("done"):
        extra = [(t("move_today"), lambda: win.store.update("tasks", task["id"], due=date.today().isoformat())),
                 (t("move_tomorrow"), lambda: win.store.update(
                     "tasks", task["id"], due=date.fromordinal(date.today().toordinal() + 1).isoformat()))]
    return bind_row(win, r, "tasks", task, extra)


def deadline_row(win, d, show_cat=True):
    """store.deadlines() kaydı için satır."""
    item = win.store.get(d["coll"], d["id"])
    sub = []
    if show_cat:
        sub.append(t("cat_" + d["category"]))
    kind = d["kind"]
    if kind.startswith("debt_"):
        sub.append(t("dir_" + kind[5:]) + " · " + fmt_money(d["sub"]))
    elif kind == "birthday":
        sub.append(t("birthday"))
    elif kind == "exam":
        sub.append(t("exam"))
    elif d["sub"]:
        sub.append(str(d["sub"]))
    sub.append(fmt_day(d["date"]))
    icon = KIND_ICON.get(kind) or CAT_ICON.get(d["category"], "flag")
    r = Row(d["title"], " · ".join(sub), icon=icon, badges=[due_badge(d["date"])])
    if item is not None:
        if d["coll"] == "tasks":
            r.check_btn = None
            bind_row(win, r, "tasks", item, [(t("mark_done"), lambda: toggle_task(win, item, True))])
        else:
            bind_row(win, r, d["coll"], item)
    return r


def routine_row(win, r_item, now_hm=None):
    st, en = r_item.get("start") or "", r_item.get("end") or ""
    lead = time_lead(f"{st}–{en}" if st and en else st or "—")
    sub = [t("cat_" + (r_item.get("category") or "personal"))]
    if r_item.get("place"):
        sub.append(r_item["place"])
    badges = []
    if now_hm and st and en and st <= now_hm < en:
        badges.append((t("now"), "good"))
    r = Row(r_item.get("title", ""), " · ".join(sub), lead=lead, badges=badges)
    return bind_row(win, r, "routine", r_item)


class QuickTask(QLineEdit):
    """Kart altında "görev ekle" satırı: yaz, Enter."""

    def __init__(self, win, category="personal", due_today=True, placeholder=None):
        super().__init__()
        self.win, self.category, self.due_today = win, category, due_today
        self.setPlaceholderText(placeholder or t("quick_task_ph"))
        self.setObjectName("Search")
        self.returnPressed.connect(self._add)

    def _add(self):
        text = self.text().strip()
        if not text:
            return
        self.win.store.add("tasks", {"title": text, "category": self.category, "priority": "normal", "done": False,
                                     "due": date.today().isoformat() if self.due_today else None})
        self.clear()


def add_button_for(card, win, coll, preset=None):
    card.add_clicked.connect(lambda: edit_item(win, coll, preset=preset() if callable(preset) else preset))


ALIGN_TOP = Qt.AlignmentFlag.AlignTop
