"""Sabah planı: 4 adımda güne hazırlık (Sunsama / Akiflow tarzı).

1. Dünden kalanlar — geciken her iş için karar: bugün / yarın / tarihsiz / bitti / sil
2. Bugün neler var — program, bugünün işleri, 3 gün içindeki deadline'lar (+ hızlı ekle)
3. Odak — en önemli en fazla 3 iş + tek cümlelik günün hedefi
4. Hazırsın — özet, "Güne başla"
Planı bitirince prefs["last_plan"] = bugün; hedef "days" koleksiyonuna yazılır.
"""
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget, QVBoxLayout, QMenu

from ..config import day_today, day_of
from ..components import Page, Card, Row, ResponsiveRow, ElideLabel, StatTile, TileGrid
from ..config import prefs
from ..forms import bind_row, edit_item
from ..i18n import t, fmt_long_date, fmt_day
from ..store import parse_date, num
from ..theme import theme
from ..timeline import DayTimeline, to_min, hhmm, fmt_dur, now_minutes
from . import task_row, deadline_row, time_lead, QuickTask

STEPS = ("carry", "today", "focus", "ready")
CHOICES = ("today", "tomorrow", "someday", "done", "delete")
MAX_FOCUS = 3


def _button(text, role="Pill", cb=None, icon=None):
    b = QPushButton(text.replace("&", "&&"))
    b.setObjectName(role)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if icon:
        theme.icon(b, icon, "button_fg" if role == "Primary" else "text", 18)
    if cb:
        b.clicked.connect(cb)
    return b


class CarryRow(QWidget):
    """Geciken iş + karar çipleri."""

    def __init__(self, task, current, on_pick):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        d = parse_date(task.get("due"))
        sub = [t("cat_" + (task.get("category") or "personal"))]
        if d:
            sub.append(fmt_day(d))
        self.setObjectName("CarryRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay.setContentsMargins(0, 2, 6, 2)
        self.row = Row(task.get("title", ""), " · ".join(sub), icon="flag",
                       icon_role="bad" if task.get("priority") == "high" else "text2")
        lay.addWidget(self.row, 1)
        self.btns = {}
        for i, c in enumerate(CHOICES):
            b = _button(f"{i + 1}  {t('plan_ch_' + c)}", "Chip")
            b.setToolTip(t("plan_key_tip", k=i + 1))
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=c: (self.select(k), on_pick(task["id"], k)))
            lay.addWidget(b)
            self.btns[c] = b
        self.select(current)

    def select(self, key):
        for k, b in self.btns.items():
            b.setChecked(k == key)

    def set_current(self, on):
        name = "CarryRowCurrent" if on else "CarryRow"
        if self.objectName() != name:
            self.setObjectName(name)
            self.style().unpolish(self)
            self.style().polish(self)


class PlanPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, "", "")
        self.title_lbl.setObjectName("Greeting")
        self.step = 0
        self.choices = {}          # görev id → karar (adım 1)
        self.carry_rows = {}
        self.action(t("plan_skip"), self.skip)

        # adım göstergesi: tıklanabilir çipler
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        self.step_btns = []
        for i, key in enumerate(STEPS):
            b = _button(f"{i + 1}   {t('plan_step_' + key)}", "Chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            bl.addWidget(b)
            self.step_btns.append(b)
        bl.addStretch(1)
        self.add(bar)

        # ilerleme çubuğu (adım / toplam)
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

        # açıklama satırı (her adımın ne istediği)
        self.lead = QLabel()
        self.lead.setObjectName("PageSub")
        self.lead.setWordWrap(True)
        self.add(self.lead)

        # --- 1: dünden kalanlar
        self.c_carry = Card(t("plan_carry_title"))
        bulk = QWidget()
        hb = QHBoxLayout(bulk)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(6)
        for c in ("today", "tomorrow", "someday"):
            hb.addWidget(_button(t("plan_all_" + c), "SmallPill", lambda _=False, k=c: self._pick_all(k)))
        self.carry_bulk = self.c_carry.head_widget(bulk)
        self.y_tasks = StatTile(t("plan_y_tasks"))
        self.y_habits = StatTile(t("plan_y_habits"))
        self.y_streak = StatTile(t("plan_y_streak"))
        self.y_sport = StatTile(t("plan_y_sport"))
        self.y_grid = TileGrid([self.y_tasks, self.y_habits, self.y_streak, self.y_sport])
        y_title = QLabel(t("plan_yesterday"))
        y_title.setObjectName("SubTitle")
        self.carry_keys = QLabel(t("plan_keys_hint"))
        self.carry_keys.setObjectName("Secondary")
        self.s_carry = self._wrap(y_title, self.y_grid, self.c_carry, self.carry_keys)
        self.s_carry.layout().setSpacing(10)
        self.carry_order = []
        self.cur = 0
        self.shortcuts = []
        for i in range(len(CHOICES)):
            self._shortcut(str(i + 1), lambda i=i: self._key_pick(CHOICES[i]))
        self._shortcut("Delete", lambda: self._key_pick("delete"))
        self._shortcut("Down", lambda: self._move(1))
        self._shortcut("Up", lambda: self._move(-1))
        self._shortcut("Return", self.next)
        self._shortcut("Enter", self.next)

        # --- 2: bugün neler var
        self.c_flow = Card(t("plan_flow"), t("plan_flow_sub"))
        self.timeline = DayTimeline()
        self.timeline.item_clicked.connect(lambda x: edit_item(win, x["coll"], x["item"]))
        self.timeline.gap_clicked.connect(self._gap_menu)
        self.c_flow.layout().addWidget(self.timeline)
        self.c_agenda = Card(t("today_program"))
        self.c_tasks = Card(t("plan_today_tasks"), add_tip=t("add_task"))
        self.c_tasks.add_clicked.connect(self._new_task)
        self.c_tasks.layout().addSpacing(6)
        self.quick = QuickTask(win)
        self.c_tasks.layout().addWidget(self.quick)
        self.c_soon = Card(t("plan_soon"))
        rr = ResponsiveRow()
        rr.add(self.c_agenda)
        rr.add(self.c_tasks)
        self.s_today = self._wrap(self.c_flow, rr, self.c_soon)

        # --- 3: odak + hedef
        self.c_focus = Card(t("plan_focus_title"))
        self.c_intent = Card(t("plan_intention"), t("plan_intention_sub"))
        self.intent = QLineEdit()
        self.intent.setObjectName("Search")
        self.intent.setPlaceholderText(t("plan_intention_ph"))
        self.intent.setMaxLength(140)
        self.intent.returnPressed.connect(self.next)
        self.c_intent.layout().addWidget(self.intent)
        self.s_focus = self._wrap(self.c_intent, self.c_focus)

        # --- 4: hazırsın
        self.c_ready = Card(t("plan_ready_title"))
        self.s_ready = self._wrap(self.c_ready)
        self.sections = [self.s_carry, self.s_today, self.s_focus, self.s_ready]

        # alt çubuk: geri / ileri
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

    def _shortcut(self, key, fn):
        sc = QShortcut(QKeySequence(key), self)
        sc.setContext(Qt.ShortcutContext.WindowShortcut)
        sc.activated.connect(fn)
        sc.setEnabled(False)
        self.shortcuts.append(sc)

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
        """Plan ekranını baştan aç (pencere çağırır)."""
        self.step = 0
        self.cur = 0
        self.choices = {}
        x = self.store.day(day_today())
        self.intent.setText((x or {}).get("intention", ""))
        self.mark_dirty()

    def go(self, i):
        i = max(0, min(len(STEPS) - 1, i))
        if self.step == 0 and i > 0:
            self._apply_carry()
        if self.step == 2:
            self._save_intention()
        self.step = i
        self.mark_dirty()
        self.verticalScrollBar().setValue(0)
        if i == 2:
            self.intent.setFocus()

    def next(self):
        if self.step >= len(STEPS) - 1:
            self.finish()
        else:
            self.go(self.step + 1)

    def back(self):
        self.go(self.step - 1)

    def skip(self):
        prefs.set("plan_skipped", day_today().isoformat())
        self.win.pages["today"].mark_dirty()
        self.win.show_page("today")

    def finish(self):
        self._save_intention()
        td = day_today()
        self.store.set_day(td, planned_at=datetime.now().isoformat(timespec="seconds"))
        prefs.set("last_plan", td.isoformat())
        self.win.pages["today"].mark_dirty()
        self.win.show_page("today")
        self.win.toast(t("plan_done_toast"))

    # ============================================================ adım 1
    def _overdue(self):
        td = day_today()
        return [x for x in self.store.open_tasks() if parse_date(x.get("due")) and parse_date(x.get("due")) < td]

    def _pick(self, tid, key):
        self.choices[tid] = key
        if tid in self.carry_order:      # tıklanan satırdan sonrakine geç
            self._set_cur(self.carry_order.index(tid) + 1)

    def _set_cur(self, i):
        if not self.carry_order:
            return
        self.cur = max(0, min(len(self.carry_order) - 1, i))
        for k, tid in enumerate(self.carry_order):
            self.carry_rows[tid].set_current(k == self.cur)
        self.ensureWidgetVisible(self.carry_rows[self.carry_order[self.cur]], 0, 80)

    def _move(self, d):
        self._set_cur(self.cur + d)

    def _key_pick(self, key):
        """Klavye: 1 bugün · 2 yarın · 3 tarihsiz · 4 bitti · 5 / Del sil — seçili satıra uygulanır."""
        if self.step != 0 or not self.carry_order:
            return
        tid = self.carry_order[self.cur]
        self.carry_rows[tid].select(key)
        self._pick(tid, key)

    def _pick_all(self, key):
        for tid, r in self.carry_rows.items():
            self.choices[tid] = key
            r.select(key)

    def _apply_carry(self):
        s, td = self.store, day_today()
        tasks = self._overdue()
        if not tasks:
            return
        undo_fields, removed, n = [], [], 0
        for tk in tasks:
            ch = self.choices.get(tk["id"], "today")
            old = {k: tk.get(k) for k in ("due", "done", "done_at", "time")}
            if ch == "delete":
                removed += s.delete("tasks", tk["id"])
            else:
                undo_fields.append((tk["id"], old))
                if ch == "today":
                    s.update("tasks", tk["id"], due=td.isoformat())
                elif ch == "tomorrow":
                    s.update("tasks", tk["id"], due=(td + timedelta(days=1)).isoformat())
                elif ch == "someday":
                    s.update("tasks", tk["id"], due=None, time=None)
                elif ch == "done":
                    s.update("tasks", tk["id"], done=True, done_at=datetime.now().isoformat(timespec="seconds"))
            n += 1
        self.choices = {}

        def undo():
            s.restore(removed)
            for tid, old in undo_fields:
                s.update("tasks", tid, **old)
        self.win.toast(t("plan_carried", n=n), t("undo"), undo)

    def _fill_carry(self):
        c = self.c_carry
        c.clear()
        self.carry_rows = {}
        tasks = self._overdue()
        for tk in tasks:
            r = CarryRow(tk, self.choices.setdefault(tk["id"], "today"), self._pick)
            bind_row(self.win, r.row, "tasks", tk)
            self.carry_rows[tk["id"]] = r
            c.add(r)
        self.carry_bulk.setVisible(len(tasks) > 1)
        self.carry_order = [tk["id"] for tk in tasks]
        self.carry_keys.setVisible(bool(tasks))
        if not tasks:
            c.empty(t("plan_carry_none"))
        else:
            self._set_cur(self.cur)
        c.set_sub(t("n_overdue", n=len(tasks)) if tasks else "")
        self._fill_yesterday()

    def _fill_yesterday(self):
        """Dünün özeti: biten işler, alışkanlıklar, en uzun süren seri, spor."""
        s, td = self.store, day_today()
        yd = td - timedelta(days=1)
        tasks = s.all("tasks")
        done_y = sum(1 for x in tasks if x.get("done") and day_of(x.get("done_at")) == yd)
        left_y = sum(1 for x in tasks if not x.get("done") and parse_date(x.get("due")) == yd)
        total = done_y + left_y
        self.y_tasks.set(f"{done_y}/{total}" if total else str(done_y),
                         t("plan_y_tasks_note", n=left_y) if left_y else (t("plan_y_all_done") if total else ""),
                         "good" if total and not left_y else None)
        habits = s.all("habits")
        from .. import habits_core as hc
        hd = sum(1 for h in habits if (hc.state(h, yd, s) or 0) >= 1)
        self.y_habits.set(f"{hd}/{len(habits)}" if habits else "—", "",
                          "good" if habits and hd == len(habits) else None)
        best, best_name = 0, ""
        for h in habits:
            cur = hc.streak_info(h, td, s)["cur"]
            if cur > best:
                best, best_name = cur, h.get("name", "")
        self.y_streak.set(t("n_days", n=best) if best else "—", best_name)
        ws = [w for w in s.all("workouts") if parse_date(w.get("date")) == yd]
        if ws:
            mins = sum(int(num(w.get("minutes")) or 0) for w in ws)
            self.y_sport.set("✓", " · ".join(x for x in (ws[0].get("kind") or "", t("dur_m", m=mins) if mins else "")
                                            if x), "good")
        else:
            self.y_sport.set("—", t("plan_y_rest"))

    # ============================================================ adım 2
    def _today_tasks(self):
        td = day_today()
        return [x for x in self.store.open_tasks() if parse_date(x.get("due")) == td]

    def _new_task(self):
        from ..forms import edit_item
        edit_item(self.win, "tasks", preset={"due": day_today().isoformat()})

    def _fill_today(self):
        from ..desk_widget import today_agenda
        s, win, td = self.store, self.win, day_today()
        self.c_agenda.clear()
        agenda = today_agenda(s, td)
        for a in agenda:
            tm = f"{a['start']}–{a['end']}" if a["start"] and a["end"] else (a["start"] or t("all_day"))
            r = Row(a["title"], a["sub"], lead=time_lead(tm))
            self.c_agenda.add(bind_row(win, r, a["coll"], a["item"]))
        if not agenda:
            self.c_agenda.empty(t("no_program"))
        self.c_agenda.set_sub(t("n_items", n=len(agenda)) if agenda else "")

        self._fill_flow(agenda)

        self.c_tasks.clear()
        tasks = self._today_tasks()
        for tk in tasks:
            self.c_tasks.add(task_row(win, tk))
        if not tasks:
            self.c_tasks.empty(t("plan_no_today_tasks"))
        self.c_tasks.set_sub(t("n_open", n=len(tasks)) if tasks else "")

        self.c_soon.clear()
        soon = [d for d in s.deadlines(3) if d["date"] > td]
        for d in soon:
            self.c_soon.add(deadline_row(win, d))
        self.c_soon.setVisible(bool(soon))
        self.c_soon.set_sub(t("next_n_days", n=3))

    def _fill_flow(self, agenda):
        """Zaman şeridi: saatli kayıtlar kutu, aralar boş zaman."""
        items = []
        for a in agenda:
            st = to_min(a["start"])
            if st is None:
                continue
            en = to_min(a["end"])
            if en is None or en <= st:
                en = st + (30 if a["coll"] == "tasks" else 60)
            it = a["item"]
            imp = bool(it.get("important")) or (a["coll"] == "tasks" and it.get("priority") == "high")
            items.append(dict(start=st, end=min(en, 24 * 60), title=a["title"], important=imp,
                              coll=a["coll"], item=it))
        # gece yarısını geçtiysek (gün bitişinden önce) bugünün saatleri çoktan geçti sayılır
        late = 24 * 60 if datetime.now().date() != day_today() else 0
        self.timeline.set_items(items, now_minutes() + late)
        free = sum(b - a for a, b in self.timeline.gaps)
        self.c_flow.set_sub(t("plan_flow_sub_n", d=fmt_dur(free)) if free else t("plan_flow_full"))

    def _gap_menu(self, a, b, pos):
        """Boş aralık: bugünün saatsiz işlerinden birini (ya da yeni bir görevi) bu saate koy."""
        s, td = self.store, day_today()
        m = QMenu(self)
        head = QAction(f"{hhmm(a)}–{hhmm(b)} · {t('tl_free', d=fmt_dur(b - a))}", m)
        head.setEnabled(False)
        m.addAction(head)
        m.addSeparator()
        cands = [x for x in s.open_tasks() if not x.get("time")
                 and (parse_date(x.get("due")) == td or not parse_date(x.get("due")))]
        cands.sort(key=lambda x: (parse_date(x.get("due")) != td, x.get("focus") != td.isoformat()))
        for tk in cands[:10]:
            ac = QAction(("★ " if tk.get("focus") == td.isoformat() else "") + tk.get("title", ""), m)
            ac.triggered.connect(lambda _=False, tid=tk["id"]: s.update("tasks", tid, due=td.isoformat(),
                                                                       time=hhmm(a)))
            m.addAction(ac)
        if cands:
            m.addSeparator()
        ac = QAction(t("plan_gap_new"), m)
        ac.triggered.connect(lambda: edit_item(self.win, "tasks", preset={"due": td.isoformat(), "time": hhmm(a)}))
        m.addAction(ac)
        m.exec(pos)

    # ============================================================ adım 3
    def _focus_candidates(self):
        td = day_today()
        out = [x for x in self.store.open_tasks()
               if not parse_date(x.get("due")) or parse_date(x.get("due")) <= td]
        key = td.isoformat()
        out.sort(key=lambda x: x.get("focus") != key)   # seçilenler üstte (sıralama kararlı)
        return out

    def toggle_focus(self, task):
        key = day_today().isoformat()
        if task.get("focus") == key:
            self.store.update("tasks", task["id"], focus=None)
            return
        if len(self.store.focus_tasks(day_today())) >= MAX_FOCUS:
            self.win.toast(t("plan_focus_max", n=MAX_FOCUS))
            return
        fields = {"focus": key}
        if not parse_date(task.get("due")):
            fields["due"] = key          # odak iş bugüne yazılır
        self.store.update("tasks", task["id"], **fields)

    def _fill_focus(self):
        c, key = self.c_focus, day_today().isoformat()
        c.clear()
        tasks = self._focus_candidates()
        n_sel = sum(1 for x in tasks if x.get("focus") == key)
        for tk in tasks[:20]:
            on = tk.get("focus") == key
            d = parse_date(tk.get("due"))
            sub = [t("cat_" + (tk.get("category") or "personal"))]
            if d:
                sub.append(fmt_day(d))
            r = Row(tk.get("title", ""), " · ".join(sub), icon="star" if on else "star_outline",
                    icon_role="text" if on else "text3",
                    badges=[(t("focus"), None)] if on else [])
            r.clicked.connect(lambda tk=tk: self.toggle_focus(tk))
            r.menu_requested.connect(lambda pos, tk=tk: self.toggle_focus(tk))
            c.add(r)
        if not tasks:
            c.empty(t("plan_focus_none"))
        c.set_sub(t("plan_focus_sub", n=n_sel, m=MAX_FOCUS))

    def _save_intention(self):
        text = self.intent.text().strip()
        x = self.store.day(day_today())
        if (x or {}).get("intention", "") != text:
            self.store.set_day(day_today(), intention=text)

    # ============================================================ adım 4
    def _fill_ready(self):
        from ..desk_widget import today_agenda
        s, td, c = self.store, day_today(), self.c_ready
        c.clear()
        text = self.intent.text().strip()
        if text:
            lbl = QLabel(f"“{text}”")
            lbl.setObjectName("Intention")
            lbl.setWordWrap(True)
            lbl.setContentsMargins(6, 4, 6, 10)
            c.add(lbl)
        agenda = today_agenda(s, td)
        timed = [a for a in agenda if a["start"]]
        first = f" · {t('plan_first', s=timed[0]['start'], x=timed[0]['title'])}" if timed else ""
        c.add(Row(t("today_program"), (t("n_items", n=len(agenda)) if agenda else t("no_program")) + first,
                  icon="schedule_week"))
        tasks = self._today_tasks()
        c.add(Row(t("todo"), t("n_open", n=len(tasks)) if tasks else t("plan_no_today_tasks"), icon="check_circle"))
        foc = s.focus_tasks(td)
        for tk in foc:
            c.add(Row(tk.get("title", ""), t("focus"), icon="star", icon_role="text"))
        if not foc:
            c.add(Row(t("focus"), t("plan_focus_empty"), icon="star_outline", icon_role="text3"))
        soon = [d for d in s.deadlines(3) if d["date"] > td]
        if soon:
            c.add(Row(t("plan_soon"), " · ".join(d["title"] for d in soon[:3]), icon="flag",
                      badges=[(str(len(soon)), "warn")]))
        done_l = ElideLabel(t("plan_ready_hint"))
        done_l.setObjectName("Empty")
        c.add(done_l)

    # ============================================================ yenile
    def refresh(self):
        td = day_today()
        name = (prefs.get("name") or "").strip()
        h = datetime.now().hour
        greet = t("greet_morning") if 5 <= h < 12 else t("greet_day") if h < 18 else t("greet_evening")
        self.title_lbl.setText(f"{greet}, {name}" if name else greet)
        self.set_sub(t("plan_sub", d=fmt_long_date(td)))
        for i, b in enumerate(self.step_btns):
            b.setChecked(i == self.step)
        for i, w in enumerate(self.sections):
            w.setVisible(i == self.step)
        for sc in self.shortcuts:
            sc.setEnabled(self.step == 0)
        self.prog_lay.setStretch(0, self.step + 1)
        self.prog_lay.setStretch(1, len(STEPS) - self.step - 1)
        self.prog_rest.setVisible(self.step < len(STEPS) - 1)
        self.lead.setText(t("plan_lead_" + STEPS[self.step]))
        self.btn_back.setVisible(self.step > 0)
        last = self.step == len(STEPS) - 1
        self.btn_next.setText(t("plan_start_day") if last else t("plan_next"))
        theme.icon(self.btn_next, "check" if last else "chevron_right", "button_fg", 18)
        self.btn_next.setLayoutDirection(Qt.LayoutDirection.LeftToRight if last else Qt.LayoutDirection.RightToLeft)
        [self._fill_carry, self._fill_today, self._fill_focus, self._fill_ready][self.step]()
