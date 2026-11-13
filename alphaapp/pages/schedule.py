"""Haftalık program: tekrar eden ders / iş / spor saatleri + o haftanın tarihli işleri, gün gün."""
from datetime import date, timedelta

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from ..components import Page, Card, ResponsiveRow
from ..forms import edit_item, item_menu
from ..i18n import t, WEEKDAYS_LONG, fmt_day_month, fmt_money
from ..store import parse_date, week_start
from ..widgets import IconButton


class Block(QWidget):
    """Gün sütunundaki küçük kutu: saat + başlık + alt satır."""
    clicked = pyqtSignal()
    menu = pyqtSignal(object)

    def __init__(self, time, title, sub="", done=False):
        super().__init__()
        self.setObjectName("Row")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(1)
        if time:
            a = QLabel(time)
            a.setObjectName("RowSub")
            v.addWidget(a)
        b = QLabel(title)
        b.setObjectName("RowTitleDone" if done else "RowTitle")
        b.setWordWrap(True)
        b.setTextFormat(Qt.TextFormat.PlainText)
        v.addWidget(b)
        if sub:
            c = QLabel(sub)
            c.setObjectName("RowSub")
            c.setWordWrap(True)
            v.addWidget(c)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.menu.emit(e.globalPos())


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
        self.action(t("add_routine"), lambda: edit_item(win, "routine"), icon="add")

        hint = QLabel(t("schedule_hint"))
        hint.setObjectName("Secondary")
        hint.setWordWrap(True)
        self.add(hint)
        self.row_w = ResponsiveRow(980)
        self.cols = []
        for i in range(7):
            c = Card("")
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            c.layout().setContentsMargins(8, 10, 8, 10)
            c.title_lbl.setContentsMargins(6, 0, 0, 0)
            c.sub_lbl.setContentsMargins(6, 0, 0, 0)
            c.body.addStretch(1)
            self.cols.append(c)
            self.row_w.add(c, 1)
        self.row_w.lay.setSpacing(8)
        self.add(self.row_w)

    def _shift(self, d, reset=False):
        self.offset = 0 if reset else self.offset + d
        self.refresh()

    def refresh(self):
        s, win = self.store, self.win
        td = date.today()
        ws = week_start(td) + timedelta(weeks=self.offset)
        we = ws + timedelta(days=6)
        self.set_sub(f"{fmt_day_month(ws)} – {fmt_day_month(we)}")
        self.btn_this.setVisible(self.offset != 0)
        names = WEEKDAYS_LONG()
        courses = {c["id"]: c for c in s.all("courses")}
        for i, col in enumerate(self.cols):
            d = ws + timedelta(days=i)
            col.clear()
            col.title_lbl.setText(names[i])
            col.set_sub(fmt_day_month(d) + ("  ·  " + t("today") if d == td else ""))
            col.setProperty("today", d == td)
            items = []
            for r in s.routine_for(d):
                st, en = r.get("start") or "", r.get("end") or ""
                items.append((st or "99", Block(f"{st}–{en}" if st and en else st, r.get("title", ""),
                                                r.get("place") or ""), "routine", r))
            for tk in s.all("tasks"):
                if parse_date(tk.get("due")) == d:
                    items.append((tk.get("time") or "99:90", Block(tk.get("time") or "", "☐ " + tk.get("title", "")
                                                                   if not tk.get("done") else "☑ " + tk.get("title", ""),
                                                                   done=bool(tk.get("done"))), "tasks", tk))
            for ev in s.all("events"):
                if parse_date(ev.get("date")) == d:
                    items.append((ev.get("time") or "99:80", Block(ev.get("time") or "", ev.get("title", ""),
                                                                   ev.get("place") or ""), "events", ev))
            for ex in s.all("exams"):
                if parse_date(ex.get("date")) == d:
                    c = courses.get(ex.get("course"), {})
                    items.append(("00", Block(t("exam"), f"{c.get('name', '')} · {ex.get('name', '')}"), "exams", ex))
            for p in s.all("projects"):
                if parse_date(p.get("due")) == d and p.get("status") != "done":
                    items.append(("99:95", Block(t("deadline"), p.get("name", "")), "projects", p))
            for db in s.all("debts"):
                if parse_date(db.get("due")) == d and not db.get("settled"):
                    items.append(("99:96", Block(t("dir_" + (db.get("direction") or "owe")),
                                                 f"{db.get('person', '')} · {fmt_money(db.get('amount'))}"),
                                  "debts", db))
            items.sort(key=lambda x: x[0])
            for _, blk, coll, it in items:
                blk.clicked.connect(lambda c=coll, x=it: edit_item(win, c, x))
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
