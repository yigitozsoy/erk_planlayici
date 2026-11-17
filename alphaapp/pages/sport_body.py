"""Spor sayfasının girişi: döndürülebilir 3B vücut + yanında açıklama.

Kipler (ChipBar):
  dev   Gelişimim: kaslar rekorlarına göre kızarır (fitness.development: 1RM / vücut ağırlığı / standart)
  week  Son 7 gün: kaslara düşen set
  mine  Programlarım: seçilen programın bir antrenmanda kaslara düşen seti
  pop   Popüler programlar: hazır programların haftalık seti (fitness.POPULAR)
Model: body3d.body_view() — muscle-body paketi varsa gerçek anatomi, yoksa basit model.
"""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton

from .. import fitness
from ..body3d import body_view
from ..components import Card, Row, ChipBar, HBars, FlowLayout
from ..config import prefs, day_today
from ..forms import edit_item
from ..i18n import t, fmt_num, fmt_day_month
from ..theme import theme

MODES = ("dev", "week", "mine", "pop")


def mus(m):
    return t("mus_" + m)


def _clear(lay):
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()


class HeroCard(Card):
    def __init__(self, win):
        super().__init__(t("hero_title"), add_tip=t("add_lift"))
        self.win, self.store = win, win.store
        self.add_clicked.connect(lambda: edit_item(win, "lifts"))
        self.mode = prefs.get("hero_mode") if prefs.get("hero_mode") in MODES else "dev"
        self.sel = {"mine": None, "pop": "mine"}

        row = QHBoxLayout()
        row.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(6)
        self.model = body_view(460)
        self.model.setMinimumWidth(300)
        self.model.set_heat({}, names={m: mus(m) for m in fitness.MUSCLES})
        left.addWidget(self.model)
        turn = QHBoxLayout()
        turn.setSpacing(6)
        turn.addStretch(1)
        for text, deg in ((t("hero_front"), 0), (t("hero_back"), 180)):
            b = QPushButton(text)
            b.setObjectName("Chip")
            b.setStyleSheet("min-width: 0px; padding: 3px 14px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, d=deg: self.model.turn_to(d))
            turn.addWidget(b)
        turn.addStretch(1)
        left.addLayout(turn)
        hint = QLabel(t("hero_drag"))
        hint.setObjectName("RowSub")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(hint)
        row.addLayout(left, 5)

        right = QVBoxLayout()
        right.setSpacing(8)
        self.modes = ChipBar([(m, t("hero_" + m)) for m in MODES], self.mode)
        self.modes.changed.connect(self._set_mode)
        right.addWidget(self.modes)
        self.picks_host = QWidget()
        self.picks = FlowLayout(self.picks_host, 6)
        right.addWidget(self.picks_host)
        self.head_lbl = QLabel("")
        self.head_lbl.setObjectName("RowTitle")
        self.head_lbl.setWordWrap(True)
        right.addWidget(self.head_lbl)
        self.info = QLabel("")
        self.info.setObjectName("RowSub")
        self.info.setWordWrap(True)
        right.addWidget(self.info)
        self.legend = QWidget()
        lg = QHBoxLayout(self.legend)
        lg.setContentsMargins(0, 2, 0, 2)
        lg.setSpacing(10)
        self.legend_lbls = []
        for i in range(5):
            sw = QLabel()
            sw.setFixedSize(12, 12)
            lb = QLabel(t("dev_%d" % i))
            lb.setObjectName("RowSub")
            lg.addWidget(sw)
            lg.addWidget(lb)
            self.legend_lbls.append(sw)
        lg.addStretch(1)
        right.addWidget(self.legend)
        self.list_host = QWidget()
        self.list = QVBoxLayout(self.list_host)
        self.list.setContentsMargins(0, 0, 0, 0)
        self.list.setSpacing(0)
        right.addWidget(self.list_host)
        right.addStretch(1)
        row.addLayout(right, 6)
        self.body.addLayout(row)
        self._paint_legend()
        theme.bind(self, lambda c: c._paint_legend())

    # ---------------------------------------------------------------- yardımcılar
    def _paint_legend(self):
        for i, sw in enumerate(self.legend_lbls):
            q = (fitness.LEVELS[i - 1] if i else 0.25) + 0.05
            r, g, b = self._rgb(fitness.dev_heat(q))
            sw.setStyleSheet(f"background: rgb({int(r)},{int(g)},{int(b)}); border-radius: 6px;")

    def _rgb(self, h):
        a, b = (150, 150, 156), (229, 57, 53)
        if h <= 0:
            return a
        k = 0.22 + 0.78 * h
        return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))

    def _set_mode(self, m):
        self.mode = m
        if self.modes.current != m:
            self.modes.select(m, emit=False)
        prefs.set("hero_mode", m)
        QTimer.singleShot(0, self.refresh)

    def _pick(self, mode, key):
        self.sel[mode] = key
        QTimer.singleShot(0, self.refresh)

    def _chips(self, items, current, mode):
        _clear(self.picks)
        for key, label in items:
            b = QPushButton(label.replace("&", "&&"))
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setChecked(key == current)
            b.setStyleSheet("min-width: 0px; padding: 3px 12px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, k=key: self._pick(mode, k))
            self.picks.addWidget(b)
        self.picks_host.setVisible(bool(items))

    def _bars(self, load, fmt=lambda v: t("hero_sets", n=fmt_num(v, 1))):
        bars = HBars("text", fmt=fmt)
        top = sorted((m for m in load if load[m] >= 0.5), key=lambda m: -load[m])[:10]
        bars.set_data([(mus(m), load[m]) for m in top], "")
        self.list.addWidget(bars)

    # ---------------------------------------------------------------- içerik
    def refresh(self):
        _clear(self.list)
        self.legend.setVisible(self.mode == "dev")
        getattr(self, "_fill_" + self.mode)()

    def _fill_dev(self):
        self._chips([], None, "dev")
        bw = fitness.body_weight(self.store)
        dev = fitness.development(self.store, bw)
        self.set_sub(t("hero_sub_dev", bw=fmt_num(bw or 75, 1)))
        heat = {m: fitness.dev_heat(d["q"]) for m, d in dev.items()}
        tips = {m: t("dev_%d" % d["level"]) + " · " + d["ex"] + f" · 1RM ≈ {fmt_num(d['e1rm'], 1)} kg"
                for m, d in dev.items()}
        self.model.set_heat(heat, tips)
        if not dev:
            self.head_lbl.setText("")
            self.info.setText(t("hero_dev_empty"))
            return
        lv = [d["level"] for d in dev.values() if d["main"]] or [0]
        self.head_lbl.setText(t("hero_overall", x=t("dev_%d" % round(sum(lv) / len(lv)))))
        missing = [mus(m) for m in fitness.MUSCLES if m not in dev]
        self.info.setText(t("hero_no_data_n", n=len(missing)) if missing else "")
        self.info.setToolTip(", ".join(missing))
        for m in sorted(dev, key=lambda m: -dev[m]["q"])[:9]:
            d = dev[m]
            sub = t("hero_dev_row" if d["main"] else "hero_dev_sec", ex=d["ex"], e=fmt_num(d["e1rm"], 1))
            r = Row(mus(m), sub, value=t("dev_%d" % d["level"]))
            r.setCursor(Qt.CursorShape.ArrowCursor)
            self.list.addWidget(r)

    def _fill_week(self):
        self._chips([], None, "week")
        self.set_sub(t("hero_sub_week"))
        load, last = fitness.recent_load(self.store, 7, day_today())
        td = day_today()
        self.model.set_heat({m: v / 10.0 for m, v in load.items()},
                            {m: t("hero_sets", n=fmt_num(v, 1)) + (f" · {fmt_day_month(last[m], short=True)}"
                                                                   if m in last else "") for m, v in load.items()})
        rest = [mus(m) for m in fitness.MUSCLES if m in last and (td - last[m]).days <= 1]
        self.head_lbl.setText(t("hero_sets", n=fmt_num(sum(v for v in load.values()), 0)) if load else "")
        self.info.setText(t("map_rest", x=", ".join(rest)) if rest else ("" if load else t("hero_week_empty")))
        if load:
            self._bars(load)

    def _fill_mine(self):
        self.set_sub(t("hero_sub_mine"))
        tps = sorted(self.store.all("templates"), key=lambda x: x.get("created") or "")
        ids = [tp["id"] for tp in tps]
        if self.sel["mine"] not in ids:
            self.sel["mine"] = ids[0] if ids else None
        self._chips([(tp["id"], tp.get("name", "")) for tp in tps], self.sel["mine"], "mine")
        if not tps:
            self.model.set_heat({})
            self.head_lbl.setText("")
            self.info.setText(t("hero_tpl_empty"))
            return
        tp = next(x for x in tps if x["id"] == self.sel["mine"])
        load = fitness.muscle_load(tp.get("exercises") or [])
        self.model.set_heat({m: v / 10.0 for m, v in load.items()},
                            {m: t("hero_sets", n=fmt_num(v, 1)) for m, v in load.items()})
        s = fitness.template_sets(tp)
        self.head_lbl.setText(tp.get("name", ""))
        self.info.setText(t("hero_mine_sub", n=len(tp.get("exercises") or []), s=s,
                            lvl=t("lvl_%d" % fitness.intensity(s))))
        self._bars(load)

    def _fill_pop(self):
        self.set_sub(t("hero_sub_pop"))
        keys = [p["key"] for p in fitness.POPULAR]
        if self.sel["pop"] not in keys:
            self.sel["pop"] = keys[0]
        self._chips([(p["key"], p["name"]) for p in fitness.POPULAR], self.sel["pop"], "pop")
        p = next(x for x in fitness.POPULAR if x["key"] == self.sel["pop"])
        load = fitness.muscle_load(p["exercises"])
        self.model.set_heat({m: v / 20.0 for m, v in load.items()},
                            {m: t("hero_sets", n=fmt_num(v, 1)) for m, v in load.items()})
        s = sum(e["sets"] for e in p["exercises"])
        self.head_lbl.setText(p["name"])
        self.info.setText(t("hero_pop_sub", d=p["days"], s=s, lvl=t("lvl_%d" % fitness.weekly_intensity(s))) +
                          ("\n" + p["split"] if p.get("split") else ""))
        self._bars(load)
