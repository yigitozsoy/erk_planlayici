"""Ekonomik durum: aylık gelir/gider, son 6 ay, gider kategorileri, borç & alacak, yatırımlar."""
from collections import Counter
from datetime import date

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..components import Page, Card, Row, StatTile, TileGrid, BarChart, HBars, ChipBar
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_money, fmt_day, fmt_month, due_badge, MONTHS_SHORT, fmt_num
from ..store import parse_date, num
from ..widgets import IconButton


def _add_months(y, m, k):
    m0 = y * 12 + (m - 1) + k
    return m0 // 12, m0 % 12 + 1


class FinancePage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_finance"), t("finance_sub"))
        self.action(t("add_debt"), lambda: edit_item(win, "debts"))
        self.action(t("add_income"), lambda: edit_item(win, "transactions", preset={"kind": "income",
                                                                                   "category": "Maaş"}))
        self.action(t("add_expense"), lambda: edit_item(win, "transactions"), primary=True, icon="add")
        td = date.today()
        self.ym = (td.year, td.month)

        self.t_inc = StatTile(t("month_income"))
        self.t_exp = StatTile(t("month_expense"))
        self.t_net = StatTile(t("month_net"))
        self.t_owe = StatTile(t("total_owe"))
        self.t_owed = StatTile(t("total_owed"))
        self.t_inv = StatTile(t("portfolio"))
        self.add(TileGrid([self.t_inc, self.t_exp, self.t_net, self.t_owe, self.t_owed, self.t_inv]))

        self.c_chart = Card(t("last_6_months"))
        leg = QLabel(f"<span style='color:#2ba640'>●</span> {t('income')} &nbsp;&nbsp; "
                     f"<span style='color:#ff4e45'>●</span> {t('expense')}")
        leg.setObjectName("RowSub")
        self.c_chart.head_widget(leg)
        self.chart = BarChart(roles=("good", "bad"), names=(t("income"), t("expense")), fmt=fmt_money, height=190)
        self.c_chart.layout().addWidget(self.chart)
        self.c_cats = Card(t("expense_by_cat"))
        self.cats = HBars("bad", fmt=fmt_money)
        self.c_cats.layout().addWidget(self.cats)
        self.row(self.c_chart, self.c_cats, stretches=[3, 2])

        # sekmeler: hareketler / borç & alacak / yatırımlar
        self.tabs = ChipBar([("tx", t("tab_tx")), ("debts", t("tab_debts")), ("inv", t("tab_inv"))], "tx")
        self.tabs.changed.connect(self._tab)
        self.add(self.tabs)

        # hareketler (ay gezinmeli)
        self.c_tx = Card("", add_tip=t("add_tx"))
        self.c_tx.add_clicked.connect(self._add_tx_in_month)
        nav = QWidget()
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(2)
        bp = IconButton("chevron_left", t("prev_month"), 32, 20)
        bp.clicked.connect(lambda: self._month(-1))
        bn = IconButton("chevron_right", t("next_month"), 32, 20)
        bn.clicked.connect(lambda: self._month(1))
        nl.addWidget(bp)
        nl.addWidget(bn)
        self.c_tx.head_widget(nav)
        self.c_debts = Card(t("tab_debts"), add_tip=t("add_debt"))
        self.c_debts.add_clicked.connect(lambda: edit_item(win, "debts"))
        self.c_inv = Card(t("tab_inv"), add_tip=t("add_investment"))
        self.c_inv.add_clicked.connect(lambda: edit_item(win, "investments"))
        self.tab_cards = {"tx": self.c_tx, "debts": self.c_debts, "inv": self.c_inv}
        for c in self.tab_cards.values():
            self.add(c)

    def _tab(self, key):
        for k, c in self.tab_cards.items():
            c.setVisible(k == key)

    def _month(self, k):
        self.ym = _add_months(*self.ym, k)
        self.refresh()

    def _add_tx_in_month(self):
        td = date.today()
        y, m = self.ym
        d = td if (y, m) == (td.year, td.month) else date(y, m, 1)
        edit_item(self.win, "transactions", preset={"date": d.isoformat()})

    def refresh(self):
        s, win = self.store, self.win
        td = date.today()
        inc, exp = s.month_totals(td.year, td.month)
        py, pm = _add_months(td.year, td.month, -1)
        pinc, pexp = s.month_totals(py, pm)
        self.t_inc.set(fmt_money(inc), self._vs(inc, pinc))
        self.t_exp.set(fmt_money(exp), self._vs(exp, pexp))
        net = inc - exp
        self.t_net.set(fmt_money(net, sign=True), t("saved") if net > 0 else t("overspent") if net < 0 else "",
                       "good" if net > 0 else "bad" if net < 0 else None)
        owe, owed = s.debt_totals()
        n_owe = sum(1 for d in s.all("debts") if not d.get("settled") and d.get("direction") != "owed")
        n_owed = sum(1 for d in s.all("debts") if not d.get("settled") and d.get("direction") == "owed")
        self.t_owe.set(fmt_money(owe), t("n_people", n=n_owe) if n_owe else "")
        self.t_owed.set(fmt_money(owed), t("n_people", n=n_owed) if n_owed else "")
        inv, val = s.investment_totals()
        pl = val - inv
        pct = (pl / inv * 100) if inv else 0
        self.t_inv.set(fmt_money(val), (fmt_money(pl, sign=True) + f" (%{fmt_num(pct, 1)})") if inv else "",
                       "good" if pl > 0 else "bad" if pl < 0 else None)

        data = []
        ms = MONTHS_SHORT()
        for k in range(-5, 1):
            y, m = _add_months(td.year, td.month, k)
            a, b = s.month_totals(y, m)
            data.append((ms[m - 1], [a, b]))
        self.chart.set_data(data)

        cnt = Counter()
        for tr in s.all("transactions"):
            d = parse_date(tr.get("date"))
            if d and d.year == td.year and d.month == td.month and tr.get("kind") != "income":
                cnt[tr.get("category") or t("other")] += num(tr.get("amount"))
        self.cats.set_data(cnt.most_common(8), t("no_expense_month"))
        self.c_cats.set_sub(fmt_month(td.year, td.month))

        # --- hareketler
        y, m = self.ym
        self.c_tx.title_lbl.setText(fmt_month(y, m))
        mi, me = s.month_totals(y, m)
        self.c_tx.set_sub(f"{t('income')} {fmt_money(mi)} · {t('expense')} {fmt_money(me)} · "
                          f"{t('net')} {fmt_money(mi - me, sign=True)}")
        self.c_tx.clear()
        txs = [x for x in s.all("transactions") if (parse_date(x.get("date")) or date.min).timetuple()[:2] == (y, m)]
        txs.sort(key=lambda x: (x.get("date") or "", x.get("created") or ""), reverse=True)
        for tr in txs:
            income = tr.get("kind") == "income"
            d = parse_date(tr.get("date"))
            sub = " · ".join(x for x in (fmt_day(d) if d else "", tr.get("note") or "") if x)
            r = Row(tr.get("category") or (t("income") if income else t("expense")), sub,
                    value=fmt_money(num(tr.get("amount")) * (1 if income else -1), sign=True),
                    value_role="good" if income else None, icon="arrow_down" if income else "arrow_up",
                    icon_role="good" if income else "text2")
            self.c_tx.add(bind_row(win, r, "transactions", tr, [(t("duplicate_today"), lambda tr=tr: s.add(
                "transactions", {k: v for k, v in tr.items() if k not in ("id", "created", "date")}
                | {"date": td.isoformat()}))]))
        if not txs:
            self.c_tx.empty(t("no_tx"))

        # --- borç & alacak
        self.c_debts.clear()
        debts = sorted(s.all("debts"), key=lambda d: (bool(d.get("settled")), parse_date(d.get("due")) or date.max))
        for db in debts:
            owed_dir = db.get("direction") == "owed"
            d = parse_date(db.get("due"))
            sub = [t("dir_" + ("owed" if owed_dir else "owe"))]
            if d:
                sub.append(fmt_day(d))
            if db.get("note"):
                sub.append(db["note"])
            badges = []
            if db.get("settled"):
                badges.append((t("settled"), "good"))
            elif d:
                badges.append(due_badge(d))
            r = Row(db.get("person", ""), " · ".join(sub), value=fmt_money(db.get("amount")),
                    value_role=("text3" if db.get("settled") else "good" if owed_dir else "bad"),
                    icon="swap", badges=badges)
            extra = [(t("mark_settled") if not db.get("settled") else t("mark_unsettled"),
                      lambda db=db: s.update("debts", db["id"], settled=not db.get("settled")))]
            self.c_debts.add(bind_row(win, r, "debts", db, extra))
        if not debts:
            self.c_debts.empty(t("no_debts"))
        self.c_debts.set_sub(f"{t('total_owe')} {fmt_money(owe)} · {t('total_owed')} {fmt_money(owed)} · "
                             f"{t('net')} {fmt_money(owed - owe, sign=True)}")

        # --- yatırımlar
        self.c_inv.clear()
        invs = sorted(s.all("investments"), key=lambda x: -num(x.get("value") if x.get("value") not in (None, "")
                                                               else x.get("invested")))
        for x in invs:
            i = num(x.get("invested"))
            v = num(x.get("value")) if x.get("value") not in (None, "") else i
            p = v - i
            pc = (p / i * 100) if i else 0
            sub = [x.get("kind") or "", t("invested_amt", v=fmt_money(i))]
            if x.get("note"):
                sub.append(x["note"])
            r = Row(x.get("name", ""), " · ".join(y for y in sub if y), value=fmt_money(v), icon="trending_up",
                    badges=[(f"{'+' if p >= 0 else '−'}%{fmt_num(abs(pc), 1)}", "good" if p > 0 else "bad" if p < 0
                             else None)] if i else [])
            self.c_inv.add(bind_row(win, r, "investments", x))
        if not invs:
            self.c_inv.empty(t("no_inv"))
        self.c_inv.set_sub(t("inv_sub", i=fmt_money(inv), v=fmt_money(val)) if invs else t("inv_hint"))

        self._tab(self.tabs.current)

    def _vs(self, cur, prev):
        if not prev:
            return ""
        d = (cur - prev) / prev * 100
        return t("vs_last_month", p=("+" if d >= 0 else "−") + "%" + fmt_num(abs(d), 0))
