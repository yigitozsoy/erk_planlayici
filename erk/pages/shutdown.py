"""Akşam kapanışı (sabah planının karşılığı, "shutdown" anahtarı, menüde yok): 4 adımda günü kapat.

1. Bugün — biten işler, alışkanlıklar, çalışma süresi, spor, harcama; sabahki günün hedefi oldu mu?
2. Kalanlar — bugüne / geçmişe yazılı açık işler: yarın / tarihsiz / bitti / sil (İleri'de uygulanır, geri alınır)
   + henüz işaretlenmemiş alışkanlıklar
3. Yarın — yarının programı, 3 gün içindeki deadline'lar, yarının en fazla 3 odak işi (task.focus = yarının iso'su;
   sabah planı bunları seçili bulur), bütçe uyarıları
4. Kapat — tek satırlık kapanış notu (days.shutdown_note; sabah planında "Dün akşamki notun" olarak görünür)
Bitince days.closed_at + prefs last_shutdown = bugün. Bugün sayfası akşam (prefs shutdown_hour, varsayılan 18)
kapanış yapılmadıysa davet kartı gösterir (prefs evening_shutdown).
"""
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget, QVBoxLayout

from .. import budget, habits_core as hc
from ..components import Page, Card, Row, ResponsiveRow, StatTile, TileGrid
from ..config import day_today, day_of, prefs
from ..forms import bind_row
from ..i18n import t, fmt_long_date, fmt_day, fmt_money, fmt_num
from ..store import parse_date, num
from ..theme import theme
from ..timeline import fmt_dur
from . import task_row, deadline_row, time_lead
from .habits import habit_row
from .plan import CarryRow, _button

STEPS = ("review", "left", "tomorrow", "close")
CHOICES = ("tomorrow", "someday", "done", "delete")
MAX_FOCUS = 3
OUTCOMES = ("yes", "partly", "no")


def is_due(now=None):
    """Akşam kapanışı zamanı mı (ayar açık, saat geçti, bugün kapatılmadı)?"""
    now = now or datetime.now()
    td = day_today()
    if not prefs.get("evening_shutdown", True) or prefs.get("last_shutdown") == td.isoformat():
        return False
    h = int(prefs.get("shutdown_hour", 18) or 18)
    return now.hour >= h or now.date() != td        # gece yarısını geçtiysek hâlâ "bugün"


class ShutdownPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, "", "")
        self.title_lbl.setObjectName("Greeting")
        self.step = 0
        self.choices = {}
        self.action(t("plan_skip"), self.skip)

        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        self.step_btns = []
        for i, key in enumerate(STEPS):
            b = _button(f"{i + 1}   {t('sd_step_' + key)}", "Chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            bl.addWidget(b)
            self.step_btns.append(b)
        bl.addStretch(1)
        self.add(bar)

        prog = QWidget()
        pl = QHBoxLayout(prog)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)
        self.prog_fill = QWidget()
        self.prog_fill.setObjectName("ProgFill")
        self.prog_rest = QWidget()
        self.prog_rest.setObjectName("ProgTrack")
        for w in (self.prog_fill, self.prog_rest):
            w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            w.setFixedHeight(4)
            pl.addWidget(w)
        self.prog_lay = pl
        self.add(prog)

        self.lead = QLabel()
        self.lead.setObjectName("PageSub")
        self.lead.setWordWrap(True)
        self.add(self.lead)

        # --- 1: bugün
        self.t_tasks = StatTile(t("plan_y_tasks"))
        self.t_habits = StatTile(t("plan_y_habits"))
        self.t_study = StatTile(t("sd_study"))
        self.t_sport = StatTile(t("plan_y_sport"))
        self.t_spent = StatTile(t("sd_spent"))
        self.c_intent = Card(t("sd_intent_title"))
        self.intent_lbl = QLabel()
        self.intent_lbl.setObjectName("Intention")
        self.intent_lbl.setWordWrap(True)
        self.intent_lbl.setContentsMargins(0, 2, 0, 6)
        self.c_intent.layout().addWidget(self.intent_lbl)
        ib = QWidget()
        il = QHBoxLayout(ib)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(6)
        self.out_btns = {}
        for k in OUTCOMES:
            b = _button(t("sd_out_" + k), "Chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=k: self._outcome(k))
            il.addWidget(b)
            self.out_btns[k] = b
        il.addStretch(1)
        self.c_intent.layout().addWidget(ib)
        self.c_done = Card(t("sd_done_title"))
        self.s_review = self._wrap(TileGrid([self.t_tasks, self.t_habits, self.t_study, self.t_sport, self.t_spent]),
                                   self.c_intent, self.c_done)

        # --- 2: kalanlar
        self.c_left = Card(t("sd_left_title"))
        bulk = QWidget()
        hb = QHBoxLayout(bulk)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(6)
        for c in ("tomorrow", "someday"):
            hb.addWidget(_button(t("plan_all_" + c), "SmallPill", lambda _=False, k=c: self._pick_all(k)))
        self.left_bulk = self.c_left.head_widget(bulk)
        self.left_rows = {}
        self.c_hab = Card(t("sd_habits_title"))
        self.s_left = self._wrap(self.c_left, self.c_hab)

        # --- 3: yarın
        self.c_tm_prog = Card(t("sd_tomorrow_prog"))
        self.c_tm_focus = Card(t("sd_tomorrow_focus"))
        rr = ResponsiveRow()
        rr.add(self.c_tm_prog)
        rr.add(self.c_tm_focus)
        self.c_soon = Card(t("plan_soon"))
        self.c_money = Card(t("budget_title"))
        self.s_tomorrow = self._wrap(rr, self.c_soon, self.c_money)

        # --- 4: kapat
        self.c_note = Card(t("sd_note_title"), t("sd_note_sub"))
        self.note = QLineEdit()
        self.note.setObjectName("Search")
        self.note.setPlaceholderText(t("sd_note_ph"))
        self.note.setMaxLength(200)
        self.note.returnPressed.connect(self.next)
        self.c_note.layout().addWidget(self.note)
        self.c_sum = Card(t("sd_sum_title"))
        self.s_close = self._wrap(self.c_note, self.c_sum)
        self.sections = [self.s_review, self.s_left, self.s_tomorrow, self.s_close]

        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 4, 0, 0)
        fl.setSpacing(8)
        self.btn_back = _button(t("plan_back"), "Flat", self.back, "chevron_left")
        fl.addWidget(self.btn_back)
        fl.addStretch(1)
        self.btn_next = _button(t("plan_next"), "Primary", self.next)
        fl.addWidget(self.btn_next)
        self.add(foot)

    def _wrap(self, *widgets):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        for x in widgets:
            v.addWidget(x)
        self.add(w)
        return w

    # ============================================================ akış
    def start(self):
        self.step = 0
        self.choices = {}
        self.note.setText((self.store.day(day_today()) or {}).get("shutdown_note", ""))
        self.mark_dirty()

    def go(self, i):
        i = max(0, min(len(STEPS) - 1, i))
        if self.step == 1 and i > 1:
            self._apply_left()
        if self.step == 3:
            self._save_note()
        self.step = i
        self.mark_dirty()
        self.verticalScrollBar().setValue(0)
        if i == 3:
            self.note.setFocus()

    def next(self):
        if self.step >= len(STEPS) - 1:
            self.finish()
        else:
            self.go(self.step + 1)

    def back(self):
        self.go(self.step - 1)

    def skip(self):
        prefs.set("last_shutdown", day_today().isoformat())
        self.win.pages["today"].mark_dirty()
        self.win.show_page("today")

    def finish(self):
        self._save_note()
        td = day_today()
        self.store.set_day(td, closed_at=datetime.now().isoformat(timespec="seconds"))
        prefs.set("last_shutdown", td.isoformat())
        self.win.pages["today"].mark_dirty()
        self.win.show_page("today")
        self.win.toast(t("sd_done_toast"))

    def _save_note(self):
        text = self.note.text().strip()
        if (self.store.day(day_today()) or {}).get("shutdown_note", "") != text:
            self.store.set_day(day_today(), shutdown_note=text)

    # ============================================================ 1: bugün
    def _outcome(self, k):
        cur = (self.store.day(day_today()) or {}).get("intention_met")
        self.store.set_day(day_today(), intention_met=None if cur == k else k)

    def _fill_review(self):
        s, td, win = self.store, day_today(), self.win
        tasks = s.all("tasks")
        done = [x for x in tasks if x.get("done") and day_of(x.get("done_at")) == td]
        left = [x for x in tasks if not x.get("done") and parse_date(x.get("due")) == td]
        total = len(done) + len(left)
        self.t_tasks.set(f"{len(done)}/{total}" if total else str(len(done)),
                         t("plan_y_tasks_note", n=len(left)) if left else (t("plan_y_all_done") if total else ""),
                         "good" if total and not left else None)
        habits = s.all("habits")
        hd = sum(1 for h in habits if (hc.state(h, td, s) or 0) >= 1)
        self.t_habits.set(f"{hd}/{len(habits)}" if habits else "—", "",
                          "good" if habits and hd == len(habits) else None)
        mins = sum(num(x.get("minutes")) for x in s.all("sessions")
                   if x.get("kind", "study") == "study" and parse_date(x.get("date")) == td)
        self.t_study.set(fmt_dur(int(mins)) if mins else "—", "")
        ws = [w for w in s.all("workouts") if parse_date(w.get("date")) == td]
        if ws:
            m = sum(int(num(w.get("minutes")) or 0) for w in ws)
            self.t_sport.set("✓", " · ".join(x for x in (ws[0].get("kind") or "", t("dur_m", m=m) if m else "") if x),
                             "good")
        else:
            self.t_sport.set("—", t("plan_y_rest"))
        spent = sum(num(x.get("amount")) for x in s.all("transactions")
                    if x.get("kind") != "income" and parse_date(x.get("date")) == td)
        self.t_spent.set(fmt_money(spent) if spent else "—", "")

        day = s.day(td) or {}
        intention = day.get("intention", "")
        self.c_intent.setVisible(bool(intention))
        self.intent_lbl.setText(f"“{intention}”")
        for k, b in self.out_btns.items():
            b.setChecked(day.get("intention_met") == k)

        c = self.c_done
        c.clear()
        for tk in done:
            c.add(task_row(win, tk))
        if not done:
            c.empty(t("sd_done_none"))
        c.set_sub(t("n_items", n=len(done)) if done else "")

    # ============================================================ 2: kalanlar
    def _left_tasks(self):
        td = day_today()
        return [x for x in self.store.open_tasks() if parse_date(x.get("due")) and parse_date(x.get("due")) <= td]

    def _pick(self, tid, key):
        self.choices[tid] = key

    def _pick_all(self, key):
        for tid, r in self.left_rows.items():
            self.choices[tid] = key
            r.select(key)

    def _apply_left(self):
        s, td = self.store, day_today()
        tasks = self._left_tasks()
        if not tasks:
            return
        undo_fields, removed = [], []
        tm = (td + timedelta(days=1)).isoformat()
        for tk in tasks:
            ch = self.choices.get(tk["id"], "tomorrow")
            old = {k: tk.get(k) for k in ("due", "done", "done_at", "time", "focus")}
            if ch == "delete":
                removed += s.delete("tasks", tk["id"])
                continue
            undo_fields.append((tk["id"], old))
            if ch == "tomorrow":
                s.update("tasks", tk["id"], due=tm)
            elif ch == "someday":
                s.update("tasks", tk["id"], due=None, time=None, focus=None)
            elif ch == "done":
                s.update("tasks", tk["id"], done=True, done_at=datetime.now().isoformat(timespec="seconds"))
        self.choices = {}

        def undo():
            s.restore(removed)
            for tid, old in undo_fields:
                s.update("tasks", tid, **old)
        self.win.toast(t("plan_carried", n=len(tasks)), t("undo"), undo)

    def _fill_left(self):
        s, td, win = self.store, day_today(), self.win
        c = self.c_left
        c.clear()
        self.left_rows = {}
        tasks = self._left_tasks()
        for tk in tasks:
            r = CarryRow(tk, self.choices.setdefault(tk["id"], "tomorrow"), self._pick, CHOICES, keys=False)
            bind_row(win, r.row, "tasks", tk)
            self.left_rows[tk["id"]] = r
            c.add(r)
        self.left_bulk.setVisible(len(tasks) > 1)
        if not tasks:
            c.empty(t("sd_left_none"))
        c.set_sub(t("n_open", n=len(tasks)) if tasks else "")

        h = self.c_hab
        h.clear()
        open_h = [x for x in s.all("habits") if (hc.state(x, td, s) or 0) < 1 and not x.get("source")]
        for x in open_h:
            h.add(habit_row(win, s, x, td))
        h.setVisible(bool(open_h))
        h.set_sub(t("sd_habits_sub", n=len(open_h)))

    # ============================================================ 3: yarın
    def toggle_focus(self, task):
        tm = day_today() + timedelta(days=1)
        key = tm.isoformat()
        if task.get("focus") == key:
            self.store.update("tasks", task["id"], focus=None)
            return
        if len(self.store.focus_tasks(tm)) >= MAX_FOCUS:
            self.win.toast(t("plan_focus_max", n=MAX_FOCUS))
            return
        fields = {"focus": key}
        d = parse_date(task.get("due"))
        if not d or d <= day_today():
            fields["due"] = key           # yarının odağı yarına yazılır
        self.store.update("tasks", task["id"], **fields)

    def _fill_tomorrow(self):
        from ..desk_widget import today_agenda
        s, td, win = self.store, day_today(), self.win
        tm = td + timedelta(days=1)
        c = self.c_tm_prog
        c.clear()
        agenda = today_agenda(s, tm)
        for a in agenda:
            tmx = f"{a['start']}–{a['end']}" if a["start"] and a["end"] else (a["start"] or t("all_day"))
            c.add(bind_row(win, Row(a["title"], a["sub"], lead=time_lead(tmx)), a["coll"], a["item"]))
        if not agenda:
            c.empty(t("sd_tomorrow_free"))
        c.set_sub(fmt_day(tm))

        f = self.c_tm_focus
        f.clear()
        key = tm.isoformat()
        cands = [x for x in s.open_tasks() if not parse_date(x.get("due")) or parse_date(x.get("due")) <= tm]
        cands.sort(key=lambda x: (x.get("focus") != key, parse_date(x.get("due")) is None))
        n_sel = 0
        for tk in cands[:15]:
            on = tk.get("focus") == key
            n_sel += on
            d = parse_date(tk.get("due"))
            sub = [t("cat_" + (tk.get("category") or "personal"))] + ([fmt_day(d)] if d else [])
            r = Row(tk.get("title", ""), " · ".join(sub), icon="star" if on else "star_outline",
                    icon_role="text" if on else "text3", badges=[(t("focus"), None)] if on else [])
            r.clicked.connect(lambda tk=tk: self.toggle_focus(tk))
            r.menu_requested.connect(lambda pos, tk=tk: self.toggle_focus(tk))
            f.add(r)
        if not cands:
            f.empty(t("plan_focus_none"))
        f.set_sub(t("plan_focus_sub", n=n_sel, m=MAX_FOCUS))

        so = self.c_soon
        so.clear()
        soon = [d for d in s.deadlines(4) if d["date"] > td]
        for d in soon:
            so.add(deadline_row(win, d))
        so.setVisible(bool(soon))
        so.set_sub(t("next_n_days", n=3))

        m = self.c_money
        m.clear()
        al = budget.alerts(s, td)
        for g, sp, cap, r in al:
            m.add(Row(t("budget_alert", g=t("bgrp_" + g), p=fmt_num(r * 100, 0)),
                      f"{fmt_money(sp)} / {fmt_money(cap)}", icon="wallet", icon_role="bad" if r > 1 else "warn"))
        m.setVisible(bool(al))

    # ============================================================ 4: kapat
    def _fill_close(self):
        s, td = self.store, day_today()
        tm = td + timedelta(days=1)
        c = self.c_sum
        c.clear()
        foc = s.focus_tasks(tm)
        for tk in foc:
            c.add(Row(tk.get("title", ""), t("sd_focus_tm"), icon="star", icon_role="text"))
        if not foc:
            c.add(Row(t("focus"), t("plan_focus_empty"), icon="star_outline", icon_role="text3"))
        n_tm = sum(1 for x in s.open_tasks() if parse_date(x.get("due")) == tm)
        c.add(Row(t("sd_tm_tasks"), t("n_open", n=n_tm) if n_tm else t("plan_no_today_tasks"), icon="check_circle"))
        hint = QLabel(t("sd_close_hint"))
        hint.setObjectName("Empty")
        hint.setWordWrap(True)
        c.add(hint)

    # ============================================================ yenile
    def refresh(self):
        td = day_today()
        name = (prefs.get("name") or "").strip()
        self.title_lbl.setText(t("sd_greet_n", n=name) if name else t("sd_greet"))
        self.set_sub(t("sd_sub", d=fmt_long_date(td)))
        for i, b in enumerate(self.step_btns):
            b.setChecked(i == self.step)
        for i, w in enumerate(self.sections):
            w.setVisible(i == self.step)
        self.prog_lay.setStretch(0, self.step + 1)
        self.prog_lay.setStretch(1, len(STEPS) - self.step - 1)
        self.prog_rest.setVisible(self.step < len(STEPS) - 1)
        self.lead.setText(t("sd_lead_" + STEPS[self.step]))
        self.btn_back.setVisible(self.step > 0)
        last = self.step == len(STEPS) - 1
        self.btn_next.setText(t("sd_finish") if last else t("plan_next"))
        theme.icon(self.btn_next, "moon" if last else "chevron_right", "button_fg", 18)
        self.btn_next.setLayoutDirection(Qt.LayoutDirection.LeftToRight if last else Qt.LayoutDirection.RightToLeft)
        [self._fill_review, self._fill_left, self._fill_tomorrow, self._fill_close][self.step]()
