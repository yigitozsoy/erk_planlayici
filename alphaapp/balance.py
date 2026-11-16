"""Hayat alanlarının puanı (0-10) — elle değil, alpha'daki verilerden.

Her alan birkaç parçadan oluşur; her parça 0-1 arası bir oran ve "nereden geldi" metni verir. Puan = parçaların
ortalaması × 10. Verisi olmayan parça hesaba girmez; hiç parça yoksa puan None ("veri yok").

  education  ders çalışma günleri (haftada 5 = tam) · notların hedefe oranı · eğitim hedeflerine emek
  career     biten iş görevleri (30 günde 8 = tam) · kariyer hedeflerine emek
  venture    kendi iş hedeflerine emek
  body       spor günleri / haftalık hedef · protein hedefini tutturduğun günler · beden hedeflerine emek
  mind       zihin hedeflerine (ve bağlı alışkanlıklara) emek
  finance    birikim oranı (gelirin %20'si = tam) · açık borç (yalnızca bugünkü dönem) · ekonomi hedeflerine emek
  growth     alışkanlık karelerinin doluluğu (%80 = tam) · günü planladığın günler · gelişim hedeflerine emek

"Emek" = hedefin (ve bağlı alışkanlık / ders kayıtlarının) etkin günleri; 30 günde 15 gün = tam.
"""
from datetime import timedelta

from .config import day_of, day_today, prefs
from .i18n import t, fmt_money
from .store import LIFE_AREAS, life_area, day_set, parse_date, num

WINDOW = 30


def _clip(x):
    return max(0.0, min(1.0, x))


def _fmt(x, nd=1):
    s = f"{x:.{nd}f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


def area_report(store, end=None, window=WINDOW):
    """{alan: {"score": 0-10 | None, "parts": [(metin, oran 0-1)]}} — [end - window + 1, end] aralığı için."""
    end = end or day_today()
    a = end - timedelta(days=window - 1)
    weeks = window / 7.0
    parts = {k: [] for k in LIFE_AREAS}
    inside = lambda d: d is not None and a <= d <= end  # noqa: E731

    # --- hedeflere emek (tüm alanlar)
    goal_days = {k: set() for k in LIFE_AREAS}
    has_goal = set()
    for g in store.all("goals"):
        ar = life_area(g.get("area"))
        has_goal.add(ar)
        goal_days[ar] |= {d for d in store.goal_days(g, deep=False) if inside(d)}

    # --- eğitim
    courses = store.all("courses")
    if courses:
        study = set()
        for c in courses:
            study |= {d for d in day_set(c.get("study_days")) if inside(d)}
        per_w = len(study) / weeks
        parts["education"].append((t("bal_study", n=_fmt(per_w)), _clip(per_w / 5.0)))
        got = tgt = 0.0
        for e in store.all("exams"):
            d = parse_date(e.get("date"))
            if e.get("score") in (None, "") or e.get("target") in (None, "") or (d and d > end):
                continue
            w = num(e.get("weight")) or 1.0
            got += num(e.get("score")) * w
            tgt += num(e.get("target")) * w
        if tgt > 0:
            r = got / tgt
            parts["education"].append((t("bal_grades", p=int(round(r * 100))), _clip((r - 0.6) / 0.4)))

    # --- kariyer: biten iş görevleri
    done_work = [x for x in store.all("tasks") if x.get("done") and (x.get("category") == "work")
                 and inside(day_of(x.get("done_at")))]
    if any(x.get("category") == "work" for x in store.all("tasks")):
        parts["career"].append((t("bal_work_tasks", n=len(done_work)), _clip(len(done_work) / 8.0)))

    # --- beden: spor + protein
    goal_w = max(1, min(7, int(num(prefs.get("sport_weekly_goal", 4)) or 4)))
    if store.all("workouts"):
        sd ={d for d in store.sport_days(a, end) if d}
        per_w = len(sd) / weeks
        parts["body"].append((t("bal_sport", n=_fmt(per_w), g=goal_w), _clip(per_w / goal_w)))
    meal_days = sorted({parse_date(m.get("date")) for m in store.all("meals")} - {None})
    meal_days = [d for d in meal_days if inside(d)]
    if meal_days:
        gp = num(prefs.get("goal_protein", 140)) or 140
        hit = sum(1 for d in meal_days if store.meal_totals(d)["protein"] >= gp * 0.9)
        parts["body"].append((t("bal_protein", n=hit, m=len(meal_days)), _clip(hit / len(meal_days))))

    # --- ekonomi: birikim oranı, açık borç
    inc = exp = 0.0
    for tr in store.all("transactions"):
        if inside(parse_date(tr.get("date"))):
            if tr.get("kind") == "income":
                inc += num(tr.get("amount"))
            else:
                exp += num(tr.get("amount"))
    if inc > 0 or exp > 0:
        rate = (inc - exp) / inc if inc > 0 else -1.0
        parts["finance"].append((t("bal_saving", p=int(round(rate * 100))) if inc > 0 else t("bal_no_income"),
                                 _clip(rate / 0.2)))
    if end >= day_today() - timedelta(days=1):
        owe, _owed = store.debt_totals()
        if owe > 0 or store.all("debts"):
            parts["finance"].append((t("bal_debt", v=fmt_money(owe)) if owe > 0 else t("bal_no_debt"),
                                     1.0 if owe <= 0 else 0.4))

    # --- kişisel gelişim: alışkanlıklar, plan
    slots = filled = 0
    for h in store.all("habits"):
        created = parse_date(h.get("created")) or a
        start = max(a, created)
        if start > end:
            continue
        span = (end - start).days + 1
        slots += span
        filled += sum(1 for d in day_set(h.get("days")) if start <= d <= end)
    if slots:
        r = filled / slots
        parts["growth"].append((t("bal_habits", p=int(round(r * 100))), _clip(r / 0.8)))
    planned = {parse_date(x.get("date")) for x in store.all("days") if x.get("planned_at")}
    n_plan = sum(1 for d in planned if inside(d))
    if store.all("days"):
        parts["growth"].append((t("bal_plans", n=n_plan, m=window), _clip(n_plan / (window * 0.8))))

    # --- hedeflere emek (son parça)
    for ar in LIFE_AREAS:
        if ar in has_goal:
            n = len(goal_days[ar])
            parts[ar].append((t("bal_goal_days", n=n), _clip(n / 15.0)))

    out = {}
    for ar in LIFE_AREAS:
        ps = parts[ar]
        score = round(10 * sum(f for _s, f in ps) / len(ps), 1) if ps else None
        out[ar] = {"score": score, "parts": ps}
    return out


def month_ends(td=None, n=6):
    """Son n ayın değerlendirme günleri (eskiden yeniye): geçmiş aylar için ayın son günü, bu ay için bugün."""
    td = td or day_today()
    out = [td]
    d = td.replace(day=1) - timedelta(days=1)
    while len(out) < n:
        out.append(d)
        d = d.replace(day=1) - timedelta(days=1)
    return list(reversed(out))


def history(store, td=None, n=6):
    """{alan: [puan | None, ...]} (eskiden yeniye) + o ayların bitiş günleri."""
    ends = month_ends(td, n)
    reps = [area_report(store, e) for e in ends]
    return {ar: [r[ar]["score"] for r in reps] for ar in LIFE_AREAS}, ends
