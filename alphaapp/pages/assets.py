"""Ekonomi > Varlıklarım: anlık net varlık, kur / altın / kripto şeridi, sembollü yatırımların canlı değeri.
Fiyatlar markets.py ile arka planda çekilir (sayfa görünürken 5 dk'da bir, ya da yenile düğmesiyle)."""
import os
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from .. import markets
from ..components import Card
from ..forms import edit_item
from ..i18n import t, fmt_money, fmt_num, is_tr
from ..library import Job
from ..widgets import IconButton

STALE_S = 300


def offline():
    """Testte / ekransız çizimde ağa çıkma."""
    return os.environ.get("ALPHA_OFFLINE") == "1" or os.environ.get("QT_QPA_PLATFORM") == "offscreen"


def _pct(a, b):
    return (a - b) / b * 100 if b else 0.0


def _box(title, value, sub, kind=None):
    w = QWidget()
    w.setObjectName("CardToday")
    w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    v = QVBoxLayout(w)
    v.setContentsMargins(12, 8, 12, 8)
    v.setSpacing(1)
    a = QLabel(title)
    a.setObjectName("StatLabel")
    b = QLabel(value)
    b.setObjectName("RowTitle")
    c = QLabel(sub)
    c.setObjectName({"good": "StatGood", "bad": "StatBad"}.get(kind, "RowSub"))
    for x in (a, b, c):
        v.addWidget(x)
    return w


class AssetsCard(Card):
    def __init__(self, win, on_prices=None):
        super().__init__(t("assets_title"), t("assets_sub"), add_tip=t("add_investment"))
        self.win, self.store = win, win.store
        self.add_clicked.connect(lambda: edit_item(win, "investments"))
        self.when = QLabel("")
        self.when.setObjectName("RowSub")
        self.head_widget(self.when)
        self.btn = IconButton("swap", t("assets_refresh"), 32, 20)
        self.btn.clicked.connect(lambda: self.fetch(force=True))
        self.head_widget(self.btn)
        self.job = None
        self.err = ""
        self.on_prices = on_prices or self.refresh
        self._timer = QTimer(self)
        self._timer.setInterval(STALE_S * 1000)
        self._timer.timeout.connect(lambda: self.isVisible() and self.fetch())
        self._timer.start()

    # ---------------------------------------------------------------- fiyatlar
    def fetch(self, force=False, get=None):
        if self.job is not None or (offline() and get is None):
            return
        ct = markets.cache_time()
        if not force and ct and (datetime.now() - ct).total_seconds() < STALE_S:
            return
        self.when.setText(t("assets_loading"))
        codes = markets.wanted(self.store)
        fn = (lambda: markets.fetch(codes, get)) if get else (lambda: markets.fetch(codes))
        self.job = Job(fn, parent=self)
        self.job.done.connect(self._done)
        self.job.failed.connect(self._failed)
        self.job.start()

    def _done(self, res):
        quotes, errs = res
        self.job = None
        if quotes:
            markets.remember(quotes)
        self.err = ", ".join(sorted(errs)) if errs else ""
        self.on_prices()

    def _failed(self, name):
        self.job = None
        self.err = name
        self.on_prices()

    # ---------------------------------------------------------------- içerik
    def refresh(self):
        self.clear()
        q = markets.cached()
        ct = markets.cache_time()
        txt = t("assets_updated", t=ct.strftime("%H:%M" if ct.date() == datetime.now().date() else "%d.%m %H:%M")) \
            if ct else t("assets_never")
        if self.err:
            txt += " · " + t("assets_failed", x=self.err)
        if self.job is None:
            self.when.setText(txt)
        nw = markets.net_worth(self.store, q)

        top = QWidget()
        h = QHBoxLayout(top)
        h.setContentsMargins(0, 0, 0, 6)
        h.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(0)
        a = QLabel(t("assets_net"))
        a.setObjectName("StatLabel")
        b = QLabel(fmt_money(nw["total"]))
        b.setObjectName("StatValue")
        left.addWidget(a)
        left.addWidget(b)
        if nw["day"]:
            c = QLabel(t("assets_today", v=fmt_money(nw["day"], sign=True)))
            c.setObjectName("StatGood" if nw["day"] > 0 else "StatBad")
            left.addWidget(c)
        parts = QLabel(t("assets_parts", c=fmt_money(nw["cash"]), i=fmt_money(nw["invest"]), o=fmt_money(nw["owed"]),
                         d=fmt_money(nw["owe"])))
        parts.setObjectName("RowSub")
        parts.setWordWrap(True)
        left.addWidget(parts)
        h.addLayout(left, 2)
        tr = is_tr()
        for code in markets.TICKER:
            x = q.get(code)
            if x:
                ch = _pct(x["p"], x["prev"])
                h.addWidget(_box(markets.label(code, tr), fmt_money(x["p"]),
                                 ("+" if ch >= 0 else "−") + "%" + fmt_num(abs(ch), 2),
                                 "good" if ch > 0.005 else "bad" if ch < -0.005 else None), 1)
            else:
                h.addWidget(_box(markets.label(code, tr), "—", ""), 1)
        self.add(top)
        if not any(markets.live_value(x, q) is not None for x in self.store.all("investments")):
            hint = QLabel(t("assets_empty"))
            hint.setObjectName("RowSub")
            hint.setWordWrap(True)
            self.add(hint)

        if not offline():
            QTimer.singleShot(0, self.fetch)
