"""Ekonomi: bu ayın bütçesi (grup başına tavan + ayın akışına göre hız çizgisi) ve abonelikler kartı."""
import calendar

from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu, QInputDialog

from .. import budget
from ..components import Card, Row
from ..components.charts import ProgressBar
from ..config import day_today
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_money, fmt_day_month, fmt_num

GROUP_ICONS = {"food": "restaurant", "transport": "map", "home": "home", "subs": "tv", "fun": "sports_esports",
               "shopping": "shopping_bag", "health": "fitness", "edu": "school", "other": "more_horiz"}


def group_name(g):
    return t("bgrp_" + g)


def role_of(ratio):
    if ratio is None:
        return "text3"
    return "bad" if ratio > 1 else "warn" if ratio >= budget.WARN else "good"


class BudgetCard(Card):
    """Grup başına: harcanan / tavan, çubuk (çizgi = ayın geçen kısmı). Tıkla = tavanı değiştir."""

    def __init__(self, win):
        super().__init__(t("budget_title"), add_tip=t("budget_add"))
        self.win = win
        self.add_clicked.connect(self._add_menu)

    def _add_menu(self):
        m = QMenu(self)
        have = budget.caps()
        for g, _cats in budget.GROUPS:
            if g == "subs":
                continue
            a = m.addAction(group_name(g) + ("  ·  " + fmt_money(have[g]) if g in have else ""))
            a.triggered.connect(lambda _=False, g=g: self.ask_cap(g))
        m.exec(QCursor.pos())

    def ask_cap(self, g):
        cur = budget.caps().get(g, 0.0)
        v, ok = QInputDialog.getDouble(self, t("budget_add"), t("budget_cap_q", g=group_name(g)), cur, 0, 10_000_000,
                                       0)
        if ok:
            budget.set_cap(g, v)
            self.refresh()

    def refresh(self):
        s = self.win.store
        td = day_today()
        self.clear()
        rows = budget.status(s, td)
        days = calendar.monthrange(td.year, td.month)[1]
        left_days = days - td.day + 1
        tot_s = sum(x[1] for x in rows)
        tot_c = sum(x[2] for x in rows if x[2])
        cap_s = sum(x[1] for x in rows if x[2])          # yalnızca tavanlı grupların harcaması
        for g, sp, cap, ratio, pace in rows:
            if cap:
                left = cap - sp
                sub = (t("budget_left", v=fmt_money(left), d=fmt_money(left / left_days)) if left >= 0
                       else t("budget_over", v=fmt_money(-left)))
                value = f"{fmt_money(sp)} / {fmt_money(cap)}"
            else:
                sub, value = t("budget_nocap"), fmt_money(sp)
            box = QWidget()
            lay = QVBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 6)
            lay.setSpacing(0)
            r = Row(group_name(g), sub, value=value, value_role=role_of(ratio) if ratio is not None and ratio > 1
                    else None, icon=GROUP_ICONS.get(g, "wallet"), icon_role=role_of(ratio))
            r.clicked.connect(lambda g=g: self.ask_cap(g))
            r.menu_requested.connect(lambda pos, g=g: self._row_menu(g, pos))
            lay.addWidget(r)
            if cap:
                bar = ProgressBar(min(ratio, 1.0), role_of(ratio), marker=pace, height=5)
                bar.setContentsMargins(0, 0, 0, 0)
                tip = t("budget_tip", p=fmt_num(pace * 100, 0), r=fmt_num(ratio * 100, 0))
                bar.setToolTip(tip)
                r.setToolTip(tip)
                wrap = QWidget()
                wl = QVBoxLayout(wrap)
                wl.setContentsMargins(46, 0, 10, 0)
                wl.addWidget(bar)
                lay.addWidget(wrap)
            self.add(box)
        if not rows:
            self.empty(t("budget_empty"))
        self.set_sub(t("budget_sub", s=fmt_money(cap_s), c=fmt_money(tot_c)) if tot_c else
                     (fmt_money(tot_s) if tot_s else ""))

    def _row_menu(self, g, pos):
        m = QMenu(self)
        m.addAction(t("budget_set")).triggered.connect(lambda: self.ask_cap(g))
        if g in budget.caps():
            m.addAction(t("budget_remove")).triggered.connect(lambda: (budget.set_cap(g, 0), self.refresh()))
        m.exec(pos)


class SubsCard(Card):
    """Abonelikler (sabit gider, kategori Abonelik): yenilenme günü, aylık / yıllık toplam."""

    def __init__(self, win):
        super().__init__(t("subs_title"), add_tip=t("subs_add"))
        self.win = win
        self.add_clicked.connect(lambda: edit_item(win, "recurring", preset={"kind": "expense",
                                                                             "category": "Abonelik"}))

    def refresh(self):
        s, win = self.win.store, self.win
        td = day_today()
        self.clear()
        subs = budget.subscriptions(s)
        subs.sort(key=lambda x: (budget.next_renewal(x[0], td), -x[1]))
        total = sum(a for _r, a in subs)
        for r, amount in subs:
            d = budget.next_renewal(r, td)
            when = t("subs_today") if d == td else t("subs_renew", d=fmt_day_month(d))
            sub = " · ".join(x for x in (when, r.get("note") or "") if x)
            row = Row(r.get("name", ""), sub, value=fmt_money(amount) if amount else t("subs_noprice"),
                      value_role=None if amount else "text3", icon="tv", icon_role="text2")
            self.add(bind_row(win, row, "recurring", r))
        if not subs:
            self.empty(t("subs_empty"))
        self.set_sub(t("subs_sub", m=fmt_money(total), y=fmt_money(total * 12)) if total else "")
