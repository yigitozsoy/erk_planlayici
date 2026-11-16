"""Alışkanlıklar: her alışkanlık için GitHub tarzı kareler, bugünün işaret listesi, seri / haftalık hedef."""
from datetime import timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget

from ..config import day_today
from ..components import Page, Card, Row, StatTile, TileGrid, DayGrid
from ..forms import edit_item, bind_row, item_menu
from ..i18n import t, WEEKDAYS_SHORT, MONTHS_SHORT
from ..store import day_set, streaks, week_start, num
from ..widgets import IconButton
from . import CAT_ICON


def habit_stats(h, td):
    days = day_set(h.get("days"))
    ws = week_start(td)
    week = sum(1 for d in days if ws <= d <= ws + timedelta(days=6))
    cur, best = streaks(days, td)
    goal = int(num(h.get("goal")) or 7)
    return days, cur, best, week, max(1, min(7, goal))


class HabitsPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_habits"), t("habits_sub"))
        self.action(t("add_habit"), lambda: edit_item(win, "habits"), primary=True, icon="add")

        self.t_active = StatTile(t("habit_tiles_active"))
        self.t_today = StatTile(t("habit_tiles_today"))
        self.t_best = StatTile(t("habit_tiles_best"))
        self.t_rate = StatTile(t("habit_tiles_rate"))
        self.add(TileGrid([self.t_active, self.t_today, self.t_best, self.t_rate]))

        self.c_today = Card(t("habits_today"), add_tip=t("add_habit"))
        self.c_today.add_clicked.connect(lambda: edit_item(win, "habits"))
        self.add(self.c_today)

        # öneriler (alışkanlık yokken)
        self.c_suggest = Card(t("habit_suggest"))
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(8)
        for name in t("habit_suggestions").split("|"):
            b = QPushButton(name)
            b.setObjectName("Chip")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, n=name: store.add("habits", {"name": n, "category": "personal",
                                                                            "goal": 7, "days": []}))
            bl.addWidget(b)
        bl.addStretch(1)
        self.c_suggest.layout().addWidget(bar)
        self.add(self.c_suggest)

        self.cards_host = QWidget()
        self.cards_v = QVBoxLayout(self.cards_host)
        self.cards_v.setContentsMargins(0, 0, 0, 0)
        self.cards_v.setSpacing(16)
        self.add(self.cards_host)

    def refresh(self):
        s, win, td = self.store, self.win, day_today()
        habits = sorted(s.all("habits"), key=lambda h: (h.get("created") or "", h.get("name") or ""))

        # --- bugün: işaret listesi
        self.c_today.clear()
        n_done = 0
        best_all = 0
        filled = 0
        for h in habits:
            days, cur, best, week, goal = habit_stats(h, td)
            done = td in days
            n_done += done
            best_all = max(best_all, best)
            filled += sum(1 for k in range(30) if td - timedelta(days=k) in days)
            sub = [t("cat_" + (h.get("category") or "personal")), t("habit_week", w=week, g=goal)]
            badges = [(t("habit_streak", n=cur), "good" if done else None)] if cur >= 2 else []
            r = Row(h.get("name", ""), " · ".join(sub), check=done, badges=badges)
            r.check_toggled.connect(lambda _v, hid=h["id"]: s.toggle_day("habits", hid, td))
            self.c_today.add(bind_row(win, r, "habits", h))
        if not habits:
            self.c_today.empty(t("no_habits"))
        self.c_today.set_sub(t("habits_today_sub", d=n_done, n=len(habits)) if habits else "")
        self.c_suggest.setVisible(not habits)

        # --- kutular
        self.t_active.set(str(len(habits)))
        self.t_today.set(f"{n_done}/{len(habits)}" if habits else "—", "",
                         "good" if habits and n_done == len(habits) else None)
        self.t_best.set(str(best_all), t("days"))
        rate = filled / (30 * len(habits)) if habits else 0
        self.t_rate.set(f"%{int(round(rate * 100))}" if habits else "—", t("habit_rate_note"))

        # --- her alışkanlık: kareler
        while self.cards_v.count():
            it = self.cards_v.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for h in habits:
            self.cards_v.addWidget(self._habit_card(h, td))
        courses = sorted(s.all("courses"), key=lambda c: c.get("name") or "")
        if courses:
            title = QLabel(t("study_section"))
            title.setObjectName("SubTitle")
            title.setContentsMargins(4, 8, 0, 0)
            self.cards_v.addWidget(title)
            for c in courses:
                self.cards_v.addWidget(self._study_card(c, td))

    def _study_card(self, c, td):
        s, win = self.store, self.win
        days = day_set(c.get("study_days"))
        ws = week_start(td)
        week_n = sum(1 for d in days if ws <= d <= ws + timedelta(days=6))
        cur, best = streaks(days, td)
        card = Card(c.get("name") or "—", t("study_info", w=week_n, s=cur, n=len(days)))
        icon_btn = IconButton("cat_education", t("cat_education"), 32, 20, role="text2")
        icon_btn.setEnabled(False)
        card.head.insertWidget(0, icon_btn, 0, Qt.AlignmentFlag.AlignTop)
        done = td in days
        b = QPushButton(t("study_done_today") if done else t("study_today"))
        b.setObjectName("Chip")
        b.setCheckable(True)
        b.setChecked(done)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.clicked.connect(lambda _=False, cid=c["id"]: s.toggle_day("courses", cid, td, "study_days"))
        card.head_widget(b)
        more = IconButton("more_vert", t("course_menu"), 32, 20)
        more.clicked.connect(lambda _=False, m=more: item_menu(win, "courses", c, m.mapToGlobal(m.rect().bottomLeft())))
        card.head_widget(more)
        grid = DayGrid(WEEKDAYS_SHORT(), MONTHS_SHORT())
        grid.set_days(days)
        grid.day_toggled.connect(lambda d, cid=c["id"]: s.toggle_day("courses", cid, d, "study_days"))
        card.add(grid)
        card.grid = grid
        return card

    def _habit_card(self, h, td):
        s, win = self.store, self.win
        days, cur, best, week, goal = habit_stats(h, td)
        card = Card(h.get("name") or "—", t("habit_stats", s=cur, b=best, w=week, g=goal, n=len(days)))
        ic = CAT_ICON.get(h.get("category") or "personal", "person")
        icon_btn = IconButton(ic, t("cat_" + (h.get("category") or "personal")), 32, 20, role="text2")
        icon_btn.setEnabled(False)
        card.head.insertWidget(0, icon_btn, 0, Qt.AlignmentFlag.AlignTop)
        done = td in days
        b = QPushButton(t("habit_done_today") if done else t("today"))
        b.setObjectName("Chip")
        b.setCheckable(True)
        b.setChecked(done)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.clicked.connect(lambda _=False, hid=h["id"]: s.toggle_day("habits", hid, td))
        card.head_widget(b)
        more = IconButton("more_vert", t("habit_menu"), 32, 20)
        more.clicked.connect(lambda _=False, m=more: item_menu(win, "habits", h, m.mapToGlobal(m.rect().bottomLeft())))
        card.head_widget(more)
        grid = DayGrid(WEEKDAYS_SHORT(), MONTHS_SHORT())
        grid.set_days(days)
        grid.day_toggled.connect(lambda d, hid=h["id"]: s.toggle_day("habits", hid, d))
        card.add(grid)
        card.grid = grid
        if h.get("note"):
            lbl = QLabel(h["note"])
            lbl.setObjectName("RowSub")
            lbl.setWordWrap(True)
            lbl.setContentsMargins(6, 6, 0, 0)
            card.add(lbl)
        return card
