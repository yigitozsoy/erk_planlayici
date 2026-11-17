"""Alışkanlıklar: bugünün işaret listesi, hazır alışkanlıklar, her alışkanlık için kareler (son 2 ay + önümüzdeki
1 ay) ve seri. Mantık habits_core.py'de: yap / bırak türü, yarım işaret, ders çalışmadan otomatik, seri kuralları.
Ders çalışma kareleri Eğitim'deki ders kartlarında."""
from datetime import timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget

from .. import habits_core as hc
from ..config import day_today
from ..components import Page, Card, Row, StatTile, TileGrid, DayGrid, FlowLayout, ResponsiveRow, clear_layout
from ..forms import edit_item, bind_row, item_menu
from ..i18n import t, fmt_num, WEEKDAYS_SHORT, MONTHS_SHORT
from ..widgets import IconButton
from . import CAT_ICON


def _n(v):
    """3 → "3", 3.5 → "3,5"."""
    return fmt_num(v, 1) if v % 1 else str(int(v))


def habit_stats(h, td, store=None):
    """Geriye uyum: (işaretli günler, seri, en uzun, bu hafta, haftalık ideal)."""
    info = hc.streak_info(h, td, store)
    goal, _wmin, _gap = hc.rules(h)
    return hc.done_days(h, td, store), info["cur"], info["best"], hc.week_total(h, td, store), goal


def rule_text(h):
    if hc.is_quit(h):
        return t("habit_rule_quit")
    goal, wmin, gap = hc.rules(h)
    bits = []
    if h.get("source") == "study":
        bits.append(t("habit_rule_study", h=_n(hc.num(h.get("target_h")) or 3)))
    elif h.get("source") == "workout":
        bits.append(t("habit_rule_workout"))
    if wmin is not None:
        bits.append(t("habit_rule_min", m=_n(wmin), g=_n(goal)))
    elif goal < 7:
        bits.append(t("habit_rule_goal", g=_n(goal)))
    bits.append(t("habit_rule_gap", n=gap) if gap > 1 else t("habit_rule_daily"))
    return " · ".join(bits)


def habit_row(win, s, h, td, info=None, show_cat=True):
    """Bugün listesi satırı (Alışkanlıklar ve Bugün sayfası): onay = bugün yaptım / bırakmada temiz."""
    info = info or hc.streak_info(h, td, s)
    v = hc.state(h, td, s) or 0
    quit_ = hc.is_quit(h)
    done = v >= 1
    sub = [t("cat_" + (h.get("category") or "personal"))] if show_cat else []
    if quit_:
        sub.append(t("habit_clean_days", n=info["cur"]) if v > 0 else t("habit_slipped_today"))
    else:
        goal, _wmin, _gap = hc.rules(h)
        sub.append(t("habit_week2", w=_n(hc.week_total(h, td, s)), g=_n(goal)))
    badges = []
    if 0 < v < 1:
        badges.append((t("habit_half"), None))
    if info["cur"] >= 2 and not quit_:
        badges.append((t("habit_streak", n=info["cur"]), "good" if done else None))
    r = Row(h.get("name", ""), " · ".join(sub), check=done, badges=badges)
    r.check_toggled.connect(lambda on, h=h: hc.set_today(s, h, td, on))
    return bind_row(win, r, "habits", h)


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

        # hazır alışkanlıklar (eklenmemiş olanlar)
        self.c_suggest = Card(t("habit_templates"), t("habit_templates_sub"))
        self.sug_host = QWidget()
        self.sug = FlowLayout(self.sug_host, 8)
        self.c_suggest.layout().addWidget(self.sug_host)
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
        n_done = 0.0
        best_all = 0
        rate_sum = rate_n = 0.0
        for h in habits:
            info = hc.streak_info(h, td, s)
            v = hc.state(h, td, s) or 0
            n_done += v
            best_all = max(best_all, info["cur"])
            vals = hc.values(h, td, s, a=td - timedelta(days=29))
            rate_sum += sum(vals.values())
            rate_n += len(vals)
            self.c_today.add(habit_row(win, s, h, td, info))
        if not habits:
            self.c_today.empty(t("no_habits"))
        self.c_today.set_sub(t("habits_today_sub", d=_n(n_done), n=len(habits)) if habits else "")

        # --- hazır alışkanlıklar
        clear_layout(self.sug)
        names = {(h.get("name") or "").strip().lower() for h in habits}
        free = [tp for tp in hc.TEMPLATES if tp["name"].lower() not in names and
                not (tp.get("source") == "study" and any(h.get("source") == "study" for h in habits))]
        for tp in free:
            b = QPushButton("+ " + tp["name"] + ("  ·  " + t("habit_kind_quit") if tp.get("kind") == "quit" else ""))
            b.setObjectName("Chip")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setToolTip(rule_text(tp))
            b.clicked.connect(lambda _=False, tp=tp: hc.from_template(s, tp, day_today()))
            self.sug.addWidget(b)
        self.c_suggest.setVisible(bool(free))

        # --- kutular
        self.t_active.set(str(len(habits)))
        self.t_today.set(f"{_n(n_done)}/{len(habits)}" if habits else "—", "",
                         "good" if habits and n_done >= len(habits) else None)
        self.t_best.set(str(best_all), t("days"))
        rate = rate_sum / rate_n if rate_n else 0
        self.t_rate.set(f"%{int(round(rate * 100))}" if habits else "—", t("habit_rate_note"))

        # --- her alışkanlık: kareler
        clear_layout(self.cards_v)
        cards = [self._habit_card(h, td) for h in habits]
        for i in range(0, len(cards), 2):        # iki sütun (dar pencerede alt alta)
            r = ResponsiveRow(900)
            r.add(cards[i], 1)
            r.add(cards[i + 1] if i + 1 < len(cards) else QWidget(), 1)
            self.cards_v.addWidget(r)

    def _habit_card(self, h, td):
        s, win = self.store, self.win
        info = hc.streak_info(h, td, s)
        quit_ = hc.is_quit(h)
        if quit_:
            n_slip = sum(1 for _d, v in hc.values(h, td, s, a=td - timedelta(days=29)).items() if v == 0)
            sub = t("habit_quit_stats", s=info["cur"], b=info["best"], k=n_slip)
        else:
            goal, _wmin, _gap = hc.rules(h)
            sub = t("habit_stats2", s=info["cur"], d=_n(info["cur_done"]), b=info["best"],
                    w=_n(hc.week_total(h, td, s)), g=_n(goal))
        card = Card(h.get("name") or "—", sub)
        ic = CAT_ICON.get(h.get("category") or "personal", "person")
        icon_btn = IconButton(ic, t("cat_" + (h.get("category") or "personal")), 32, 20, role="text2")
        icon_btn.setEnabled(False)
        card.head.insertWidget(0, icon_btn, 0, Qt.AlignmentFlag.AlignTop)
        v = hc.state(h, td, s) or 0
        if quit_:
            slipped = v == 0
            b = QPushButton(t("habit_unslip") if slipped else t("habit_slip"))
            b.setCheckable(True)
            b.setChecked(slipped)
            b.clicked.connect(lambda _=False, h=h, sl=slipped: hc.set_today(s, h, td, sl))
        else:
            b = QPushButton(t("habit_done_today") if v >= 1 else (t("habit_half") + " ✓") if v > 0 else t("today"))
            b.setCheckable(True)
            b.setChecked(v > 0)
            b.clicked.connect(lambda _=False, h=h: hc.cycle(s, h, td))
        b.setObjectName("Chip")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setToolTip(t("habit_cycle_tip_quit") if quit_ else t("habit_cycle_tip"))
        card.head_widget(b)
        card.today_btn = b
        more = IconButton("more_vert", t("habit_menu"), 32, 20)
        more.clicked.connect(lambda _=False, m=more: item_menu(win, "habits", h, m.mapToGlobal(m.rect().bottomLeft())))
        card.head_widget(more)
        grid = DayGrid(WEEKDAYS_SHORT(), MONTHS_SHORT(), span=(2, 1), role="good" if quit_ else "text")
        grid.set_values(hc.values(h, td, s), [] if quit_ else info["ranges"], quit=quit_)
        grid.day_toggled.connect(lambda d, h=h: hc.cycle(s, h, d))
        card.add(grid)
        card.grid = grid
        foot = QLabel(rule_text(h) + "  ·  " + (t("habit_cycle_tip_quit") if quit_ else t("habit_cycle_tip")) +
                      ("  ·  " + h["note"] if h.get("note") else ""))
        foot.setObjectName("RowSub")
        foot.setWordWrap(True)
        foot.setContentsMargins(6, 6, 0, 0)
        card.add(foot)
        return card
