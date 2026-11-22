"""Beden > Antrenmanlar: antrenman hedefleri kartı + rekorlar kartındaki progressive overload parçaları
(sonraki oturum önerisi, hedef çizgisi, haftalık hacim). Hesap erk/overload.py."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from .. import overload
from ..components import Card, Row, BarChart
from ..components.charts import ProgressBar
from ..config import day_today
from ..forms import edit_item, bind_row
from ..i18n import t, fmt_num, fmt_day_month
from ..store import parse_date, num


def kg(v):
    return f"{fmt_num(v, 1)} kg"


def goal_text(g):
    r = int(num(g.get("r")) or 1)
    return f"{fmt_num(num(g.get('w')), 1)} kg × {r}" if r > 1 else kg(num(g.get("w")))


def suggest_row(store, name):
    """"Sonraki sefer: 82,5 kg × 8" satırı (ipucunda kural) ya da None."""
    s = overload.suggest(store, name)
    if not s:
        return None
    last = ", ".join(f"{fmt_num(w, 1)}×{r}" if w else f"{r}" for w, r in s["last"])
    what = (f"{kg(s['w'])} × {s['reps']}" if s["w"] else t("ov_reps", r=s["reps"]))
    r = Row(t("ov_next", x=what), t("ov_last", x=last), icon="trending_up",
            icon_role="good" if s["kind"] == "up" else "text2",
            badges=[(t("ov_up"), "good")] if s["kind"] == "up" else [])
    r.setToolTip(t("ov_tip", lo=s["lo"], hi=s["hi"], st=fmt_num(overload.step_of(name), 1)))
    return r


def goal_rows(win, name):
    """Seçili hareketin hedef satırları (çubuklu) ya da "Hedef koy" satırı."""
    s, td = win.store, day_today()
    out = []
    for g in overload.goals_for(s, name):
        out.append(goal_widget(win, g, td))
    if not out:
        r = Row(t("lg_add_for", n=name), t("lg_add_hint"), value="+", value_role="text3", icon="flag",
                icon_role="text3")
        r.clicked.connect(lambda: edit_item(win, "lift_goals", preset={"name": name}))
        out.append(r)
    return out


def goal_widget(win, g, td, show_name=False):
    s = win.store
    cur, tgt, ratio = overload.progress(s, g)
    per_week, n = overload.trend(s, g.get("name"), td)
    eta = overload.eta(s, g, td)
    bits = [t("lg_now", c=kg(cur), p=fmt_num(min(ratio, 9.99) * 100, 0))]
    if per_week is not None:
        bits.append(t("lg_trend", v=("+" if per_week >= 0 else "−") + fmt_num(abs(per_week), 1)))
    if ratio >= 1:
        bits.append(t("lg_reached"))
    elif eta:
        bits.append(t("lg_eta", d=fmt_day_month(eta, short=True)))
    by = parse_date(g.get("by"))
    badges = []
    if by and ratio < 1:
        late = eta is None or eta > by
        badges.append((t("lg_by", d=fmt_day_month(by, short=True)), "bad" if late else None))
    if show_name:                               # hedefler kartı: başlık hareket, hedef alt satırın başında
        title = g.get("name", "")
        bits.insert(0, t("lg_goal", g=goal_text(g)))
    else:
        title = t("lg_goal", g=goal_text(g))
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 6)
    lay.setSpacing(0)
    r = Row(title, " · ".join(bits), value=kg(tgt) if int(num(g.get("r")) or 1) > 1 else "",
            value_role="text3", icon="flag", icon_role="good" if ratio >= 1 else "text2", badges=badges)
    tip = t("lg_tip", g=goal_text(g), e=fmt_num(tgt, 1), c=fmt_num(cur, 1), w=overload.TREND_WEEKS, n=n)
    r.setToolTip(tip)
    lay.addWidget(bind_row(win, r, "lift_goals", g))
    bar = ProgressBar(min(ratio, 1.0), "good" if ratio >= 1 else "text", height=5)
    bar.setToolTip(tip)
    wrap = QWidget()
    wl = QVBoxLayout(wrap)
    wl.setContentsMargins(46, 0, 10, 0)
    wl.addWidget(bar)
    lay.addWidget(wrap)
    return box


def volume_chart(store, name):
    td = day_today()
    data = overload.weekly_volume(store, name, td)
    if sum(v for _d, v in data) <= 0:
        return None
    ch = BarChart(roles=("text",), names=(t("ov_volume"),), fmt=lambda v: f"{fmt_num(v, 0)} kg", height=110)
    ch.set_data([(fmt_day_month(d, short=True), [v]) for d, v in data])
    ch.setToolTip(t("ov_volume_tip"))
    return ch


class LiftGoalsCard(Card):
    """Tüm antrenman hedefleri: ilerleme çubuğu, haftalık artış, tahmini varış."""

    def __init__(self, win):
        super().__init__(t("lg_title"), t("lg_sub"), add_tip=t("lg_new"))
        self.win = win
        self.add_clicked.connect(lambda: edit_item(win, "lift_goals"))

    def refresh(self):
        s, td = self.win.store, day_today()
        self.clear()
        goals = s.all("lift_goals")
        goals = sorted(goals, key=lambda g: -overload.progress(s, g)[2])
        for g in goals:
            self.add(goal_widget(self.win, g, td, show_name=True))
        if not goals:
            self.empty(t("lg_empty"))
        done = sum(1 for g in goals if overload.progress(s, g)[2] >= 1)
        self.set_sub(t("lg_sub_n", n=len(goals), d=done) if goals else t("lg_sub"))

