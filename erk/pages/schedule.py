"""Haftalık program: tekrar eden ders / iş / spor saatleri + o haftanın tarihli işleri (+ isteğe bağlı alışkanlıklar),
gün gün. Her kayıt kendi kutusunda; önemli olanlar kırmızı."""
from datetime import timedelta

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QMimeData, QTimer, QPoint
from PyQt6.QtGui import QDrag, QAction, QCursor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QApplication, QMenu

from ..config import day_today
from ..components import Page, Card, ResponsiveRow, sub_label
from ..config import prefs
from ..forms import edit_item, item_menu
from ..i18n import t, WEEKDAYS_LONG, fmt_day_month, fmt_money
from ..store import parse_date, week_start
from ..widgets import IconButton
from . import CAT_ICON


def _span(a, b):
    return f"{a}–{b}" if a and b else (a or "")


MIME = "application/x-erk-block"
# sürüklenince hangi alan yeni tarihe yazılır (routine ayrı ele alınır)
DATE_FIELD = {"tasks": "due", "events": "date", "exams": "date", "projects": "due", "debts": "due"}


class Block(QWidget):
    """Gün sütunundaki ayrı kutu: saat [ikon] + başlık + alt satır. important=True → kırmızı.
    drag_info verilmişse sürüklenip başka güne bırakılabilir (drag_requested yayılır, sürüklemeyi sayfa yürütür)."""
    clicked = pyqtSignal()
    menu = pyqtSignal(object)
    drag_requested = pyqtSignal(object)    # Block

    def __init__(self, time, title, sub="", done=False, important=False, cat=None, kind=None):
        super().__init__()
        self.drag_info = None      # (koleksiyon, kayıt, kaynak gün)
        self._press = None
        self.setObjectName("BlockImportant" if important else "Block")
        if kind and not important:
            self.setProperty("kind", kind)      # theme.BLOCK_KINDS: renkli kutu
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 6, 7)
        v.setSpacing(1)
        if time or cat:
            top = QHBoxLayout()
            top.setSpacing(4)
            a = QLabel(time or "")
            a.setObjectName("BlockTimeImportant" if important else "RowSub")
            top.addWidget(a, 1)
            if cat:
                ic = IconButton(CAT_ICON.get(cat, "person"), t("cat_" + cat), 18, 14,
                                role="bad" if important else "text3")
                ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                top.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
            v.addLayout(top)
        b = QLabel(title)
        b.setObjectName("RowTitleDone" if done else ("BlockTitleImportant" if important else "RowTitle"))
        b.setWordWrap(True)
        b.setTextFormat(Qt.TextFormat.PlainText)
        v.addWidget(b)
        if sub:
            c = sub_label(sub, wrap=True)
            v.addWidget(c)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if (self._press is not None and self.drag_info and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position().toPoint() - self._press).manhattanLength() >= QApplication.startDragDistance()):
            self._press = None
            self.drag_requested.emit(self)

    def mouseReleaseEvent(self, e):
        was = self._press is not None
        self._press = None
        if was and e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.menu.emit(e.globalPos())


WEEKS = 2   # programda alt alta kaç hafta görünür
KIND_OF_CAT = {"education": "lesson", "sport": "sport", "work": "meeting", "social": "meeting"}


def kind_of(cat):
    """Kutu rengi (theme.BLOCK_KINDS): ders / spor / toplantı-etkinlik; görevler her zaman "task"."""
    return KIND_OF_CAT.get(cat)


class SchedulePage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_schedule"), "")
        self.offset = 0   # hafta kaydırma
        self.btn_prev = IconButton("chevron_left", t("prev_week"), 36, 22)
        self.btn_prev.clicked.connect(lambda: self._shift(-1))
        self.btn_next = IconButton("chevron_right", t("next_week"), 36, 22)
        self.btn_next.clicked.connect(lambda: self._shift(1))
        self.head_actions.addWidget(self.btn_prev)
        self.head_actions.addWidget(self.btn_next)
        self.btn_this = self.action(t("this_week"), lambda: self._shift(0, reset=True))
        self.btn_habit = self.action(t("add_habit"), lambda: edit_item(win, "habits"), icon="add")
        self.action(t("add_routine"), lambda: edit_item(win, "routine"), icon="add")

        # iki hafta alt alta: bu hafta + önümüzdeki hafta (her biri 7 sütun)
        self.weeks = WEEKS
        self.cols = []
        self.col_dates = [None] * (7 * WEEKS)
        self.week_lbls = []
        self.rows = []
        self._drop = None          # sürükleme sırasında üzerinde durulan sütun
        self._drop_date = None
        for i in range(7 * WEEKS):
            if i % 7 == 0:
                lb = QLabel("")
                lb.setStyleSheet("font-size: 15px; font-weight: 700;")
                lb.setContentsMargins(4, 10 if i else 0, 0, 0)
                self.week_lbls.append(lb)
                if i:
                    self.add(lb)
                else:                        # ilk haftanın başlığı + renk açıklaması aynı satırda
                    top = QWidget()
                    th = QHBoxLayout(top)
                    th.setContentsMargins(0, 0, 0, 0)
                    th.setSpacing(8)
                    th.addWidget(lb)
                    th.addStretch(1)
                    from ..theme import BLOCK_KINDS
                    for k, hx in BLOCK_KINDS.items():
                        sw = QLabel()
                        sw.setFixedSize(10, 10)
                        sw.setStyleSheet(f"background: {hx}; border-radius: 5px;")
                        kl = sub_label(t("bk_kind_" + k))
                        th.addWidget(sw)
                        th.addWidget(kl)
                        th.addSpacing(6)
                    self.add(top)
                self.row_w = ResponsiveRow(980)
                self.row_w.lay.setSpacing(8)
                self.rows.append(self.row_w)
                self.add(self.row_w)
            c = Card("")
            c.setAcceptDrops(True)
            c.installEventFilter(self)
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            c.layout().setContentsMargins(8, 10, 8, 10)
            c.title_lbl.setContentsMargins(6, 0, 0, 0)
            c.sub_lbl.setContentsMargins(6, 0, 0, 0)
            c.body.setSpacing(6)
            c.body.setContentsMargins(0, 6, 0, 0)
            c.body.addStretch(1)
            c.setMinimumHeight(180)      # boş günde de sağ tıklanacak yer olsun
            self.cols.append(c)
            self.row_w.add(c, 1)
            self.row_w.lay.setAlignment(c, Qt.AlignmentFlag(0))   # sütunlar en uzunu kadar uzasın

    # ============================================================ sürükle-bırak
    def eventFilter(self, obj, e):
        if obj in getattr(self, "cols", ()):    # Page kurulurken de çağrılır
            et = e.type()
            if et == QEvent.Type.ContextMenu:
                self.day_menu(self.col_dates[self.cols.index(obj)], e.globalPos())
                return True
            if et in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if e.mimeData().hasFormat(MIME):
                    e.acceptProposedAction()
                    self._set_drop(obj)
                    return True
            elif et == QEvent.Type.DragLeave:
                self._set_drop(None)
                return True
            elif et == QEvent.Type.Drop:
                if e.mimeData().hasFormat(MIME):
                    e.acceptProposedAction()
                    self._drop_date = self.col_dates[self.cols.index(obj)]
                    self._set_drop(None)
                    return True
        return super().eventFilter(obj, e)

    # ============================================================ güne sağ tık: hızlı ekle
    def day_actions(self, d):
        """(metin, koleksiyon, ön değerler) — o güne eklenebilecekler."""
        iso, wd = d.isoformat(), d.weekday()
        out = [(t("dm_task"), "tasks", {"due": iso}),
               (t("dm_important"), "tasks", {"due": iso, "priority": "high"}),
               (t("dm_once"), "routine", {"days": [wd], "from": iso, "until": iso}),
               (t("dm_weekly", d=WEEKDAYS_LONG()[wd]), "routine", {"days": [wd]}),
               (t("dm_event"), "events", {"date": iso})]
        if self.store.all("courses"):
            out.append((t("dm_exam"), "exams", {"date": iso}))
        return out

    def day_menu(self, d, pos):
        m = QMenu(self)
        head = QAction(f"{WEEKDAYS_LONG()[d.weekday()]}, {fmt_day_month(d)}", m)
        head.setEnabled(False)
        m.addAction(head)
        m.addSeparator()
        for text, coll, preset in self.day_actions(d):
            a = QAction(text, m)
            a.triggered.connect(lambda _=False, c=coll, p=preset: edit_item(self.win, c, preset=dict(p)))
            m.addAction(a)
        m.exec(pos)

    def _col_name(self, c):
        if c is self._drop:
            return "CardDrop"
        return "CardToday" if self.col_dates[self.cols.index(c)] == day_today() else "Card"

    def _set_drop(self, col):
        if col is self._drop:
            return
        old, self._drop = self._drop, col
        for c in (old, col):
            if c is not None and c.objectName() != self._col_name(c):
                c.setObjectName(self._col_name(c))
                c.style().unpolish(c)
                c.style().polish(c)

    def _start_drag(self, blk):
        coll, item, src = blk.drag_info
        drag = QDrag(self)                 # sayfaya ait: kaynak kutu yenilemede silinse de sorun olmaz
        md = QMimeData()
        md.setData(MIME, f"{coll}:{item['id']}".encode())
        drag.setMimeData(md)
        pm = blk.grab()
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(pm.width() // 2, 12))
        self._drop_date = None
        blk.setVisible(False)
        drag.exec(Qt.DropAction.MoveAction)
        self._set_drop(None)
        target = self._drop_date
        if target is None or target == src:
            blk.setVisible(True)
            return
        # sürükleme döngüsünden çıktıktan sonra uygula (kutular o sırada yeniden kurulur)
        QTimer.singleShot(0, lambda: self.move_item(coll, item["id"], src, target))

    def move_item(self, coll, iid, src, target, mode=None):
        """Kaydı başka güne taşır. Haftalık derste mode: "week" (her hafta) | "once" (yalnızca bu hafta) | None (sor)."""
        s, win = self.store, self.win
        it = s.get(coll, iid)
        if it is None:
            return
        if coll == "routine":
            if mode is None:
                mode = self._ask_routine(src, target)
                if mode is None:
                    self.refresh()
                    return
            old = {"days": list(it.get("days") or []), "skip": list(it.get("skip") or [])}
            created = None
            if mode == "week":
                days = [d for d in old["days"] if d != src.weekday()]
                if target.weekday() not in days:
                    days.append(target.weekday())
                s.update("routine", iid, days=sorted(days))
            else:
                s.update("routine", iid, skip=sorted(set(old["skip"]) | {src.isoformat()}))
                one = {k: v for k, v in it.items() if k not in ("id", "created", "skip", "days", "from", "until")}
                one.update({"days": [target.weekday()], "from": target.isoformat(), "until": target.isoformat()})
                created = s.add("routine", one)

            def undo():
                if created:
                    s.delete("routine", created["id"])
                s.update("routine", iid, **old)
        else:
            field = DATE_FIELD[coll]
            prev = it.get(field)
            s.update(coll, iid, **{field: target.isoformat()})

            def undo():
                s.update(coll, iid, **{field: prev})
        win.toast(t("moved_to", d=fmt_day_month(target)), t("undo"), undo)

    def _ask_routine(self, src, target):
        """Haftalık ders bırakılınca: yalnızca bu hafta mı, her hafta mı?"""
        m = QMenu(self)
        a_once = QAction(t("move_once", a=fmt_day_month(src), b=fmt_day_month(target)), m)
        a_week = QAction(t("move_every_week", d=WEEKDAYS_LONG()[target.weekday()]), m)
        m.addAction(a_once)
        m.addAction(a_week)
        m.addSeparator()
        m.addAction(QAction(t("cancel"), m))
        ch = m.exec(QCursor.pos())
        return "once" if ch is a_once else "week" if ch is a_week else None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit_weeks()

    def _fit_weeks(self):
        """Dar pencerede günler alt alta dizilir; iki hafta 14 uzun kart olmasın diye yalnızca ilk hafta görünür
        (öteki haftalara oklarla geçilir)."""
        narrow = self.viewport().width() - 56 < self.rows[0].bp
        for k in range(1, self.weeks):
            self.week_lbls[k].setVisible(not narrow)
            self.rows[k].setVisible(not narrow)

    def _shift(self, d, reset=False):
        self.offset = 0 if reset else self.offset + d
        self.refresh()

    def _habit_menu(self, habits, d, blk):
        """Günün alışkanlık kutusu: her alışkanlık işaretlenebilir satır (menü açık kalmaz, tıkla = tam / boş)."""
        from PyQt6.QtWidgets import QMenu
        from .. import habits_core as hc
        m = QMenu(self)
        m.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        for h in habits:
            v = hc.state(h, d, self.store) or 0
            a = m.addAction(("½  " if 0 < v < 1 else "") + h.get("name", ""))
            a.setCheckable(True)
            a.setChecked(v >= 1)
            a.triggered.connect(lambda on, hh=h: hc.set_today(self.store, hh, d, on))
        m.addSeparator()
        m.addAction(t("open_habits"), lambda: self.win.show_page("habits"))
        self.last_menu = m
        m.popup(blk.mapToGlobal(blk.rect().bottomLeft()))

    def refresh(self):
        s, win = self.store, self.win
        td = day_today()
        ws = week_start(td) + timedelta(weeks=self.offset)
        we = ws + timedelta(days=6)
        self.set_sub(f"{fmt_day_month(ws)} – {fmt_day_month(we)}")
        for k, lb in enumerate(self.week_lbls):
            a = ws + timedelta(weeks=k)
            o = self.offset + k
            name = t("this_week") if o == 0 else t("next_week_title") if o == 1 else ""
            lb.setText("  ·  ".join(x for x in (t("week_no", n=a.isocalendar()[1]), name,
                                                 f"{fmt_day_month(a)} – {fmt_day_month(a + timedelta(days=6))}") if x))
        self.btn_this.setVisible(self.offset != 0)
        show_place = prefs.get("show_place", True)
        show_habits = bool(prefs.get("habits_in_schedule", True))
        self.btn_habit.setVisible(show_habits)
        names = WEEKDAYS_LONG()
        courses = {c["id"]: c for c in s.all("courses")}
        from .. import habits_core as _hc
        habits = [h for h in s.all("habits") if _hc.is_sport(h)] if show_habits else []
        for i, col in enumerate(self.cols):
            d = ws + timedelta(days=i)
            self.col_dates[i] = d
            col.clear()
            col.title_lbl.setText(names[i % 7])
            col.set_sub(fmt_day_month(d) + ("  ·  " + t("today") if d == td else ""))
            items = []   # (sıra, blok, koleksiyon, kayıt, sol tık)
            for r in s.routine_for(d):
                st, en = r.get("start") or "", r.get("end") or ""
                items.append((st or "99", Block(f"{st}–{en}" if st and en else st, r.get("title", ""),
                                                (r.get("place") or "") if show_place else "",
                                                important=bool(r.get("important")), cat=r.get("category"),
                                                kind=kind_of(r.get("category"))),
                              "routine", r, None))
            for tk in s.all("tasks"):
                if parse_date(tk.get("due")) == d:
                    done = bool(tk.get("done"))
                    items.append((tk.get("time") or "99:90",
                                  Block(_span(tk.get("time"), tk.get("end")),
                                        ("☑ " if done else "☐ ") + tk.get("title", ""),
                                        done=done, important=tk.get("priority") == "high" and not done,
                                        cat=tk.get("category"), kind="task"), "tasks", tk, None))
            for ev in s.all("events"):
                if parse_date(ev.get("date")) == d:
                    items.append((ev.get("time") or "99:80",
                                  Block(ev.get("time") or "", ev.get("title", ""),
                                        (ev.get("place") or "") if show_place else "",
                                        important=bool(ev.get("important")), cat="social", kind="meeting"),
                                  "events", ev, None))
            for ex in s.all("exams"):
                if parse_date(ex.get("date")) == d:
                    c = courses.get(ex.get("course"), {})
                    items.append((ex.get("time") or "00", Block(t("exam") + (f" · {ex['time']}" if ex.get("time") else ""), f"{c.get('name', '')} · {ex.get('name', '')}",
                                              important=ex.get("score") in (None, ""), cat="education"),
                                  "exams", ex, None))
            for p in s.all("projects"):
                if parse_date(p.get("due")) == d and p.get("status") != "done":
                    items.append(("99:95", Block(t("deadline"), p.get("name", ""), important=True, cat="work"),
                                  "projects", p, None))
            for db in s.all("debts"):
                if parse_date(db.get("due")) == d and not db.get("settled"):
                    items.append(("99:96", Block(t("dir_" + (db.get("direction") or "owe")),
                                                 f"{db.get('person', '')} · {fmt_money(db.get('amount'))}",
                                                 cat="finance"), "debts", db, None))
            # alışkanlıklar: saatli olanlar ayrı kutu, ötekiler günde tek özet kutu (tıkla → işaretleme menüsü)
            from .. import habits_core as hc
            loose = []
            for h in habits:
                wds = h.get("weekdays") or []
                if hc.is_quit(h) or (wds and d.weekday() not in wds):
                    continue
                if h.get("time"):
                    done = (hc.state(h, d, s) or 0) >= 1
                    items.append((h["time"], Block(h["time"], ("☑ " if done else "☐ ") + h.get("name", ""),
                                                   done=done, cat=h.get("category") or "personal",
                                                   kind=kind_of(h.get("category"))), "habits", h,
                                  lambda hh=h, dd=d: hc.cycle(s, hh, dd)))
                else:
                    loose.append(h)
            if loose:
                vals = [hc.state(h, d, s) or 0 for h in loose]
                n_done = sum(1 for v in vals if v >= 1)
                left = [h.get("name", "") for h, v in zip(loose, vals) if v < 1]
                blk = Block(t("sport_habits_n", d=n_done, n=len(loose)),
                            ", ".join(left) if left else t("habits_all_done"),
                            done=not left, cat="sport", kind="sport")
                blk.setToolTip(chr(10).join(("☑ " if v >= 1 else "½ " if v > 0 else "☐ ") + h.get("name", "")
                                          for h, v in zip(loose, vals)))
                items.append(("99:97", blk, "habits_day", loose, None))
            items.sort(key=lambda x: x[0])
            for _, blk, coll, it, click in items:
                if coll == "habits_day":
                    blk.clicked.connect(lambda b=blk, hs=it, dd=d: self._habit_menu(hs, dd, b))
                    blk.menu.connect(lambda pos, b=blk, hs=it, dd=d: self._habit_menu(hs, dd, b))
                    col.add(blk)
                    continue
                if coll in DATE_FIELD or coll == "routine":
                    blk.drag_info = (coll, it, d)
                    blk.drag_requested.connect(self._start_drag)
                blk.clicked.connect(click or (lambda c=coll, x=it: edit_item(win, c, x)))
                blk.menu.connect(lambda pos, c=coll, x=it: item_menu(win, c, x, pos))
                col.add(blk)
            if not items:
                col.empty("—")
            col.body.addStretch(1)
            # bugünün sütunu biraz daha belirgin
            name = "CardToday" if d == td else "Card"
            if col.objectName() != name:
                col.setObjectName(name)
                col.style().unpolish(col)
                col.style().polish(col)
