"""Antrenman hedefleri + progressive overload (antrenman sırasında değil, önce / sonra bakmak için).

lift_goals koleksiyonu: name (hareket), w (kg), r (tekrar, varsayılan 1), by (tarih, isteğe bağlı), note.
Hedef "w × r" Epley ile tahmini 1RM'e çevrilir; ilerleme = şu anki en iyi e1RM / hedef e1RM.
trend(): son 10 haftadaki oturum başına en iyi e1RM'e doğru çizer (en küçük kareler) → kg / hafta + hedefe tahmini
varış. weekly_volume(): hareket başına haftalık hacim (kg × tekrar). suggest(): çift ilerleme (double progression):
son oturumda tüm setler aralığın üstüne ulaştıysa ağırlık artar, yoksa aynı ağırlıkta tekrar artar.
"""
from datetime import timedelta

from . import fitness
from .store import num

TREND_WEEKS = 10
# ağırlık artışı: halter / makine bileşik hareketleri 2.5, bacak itişleri 5, dambıl / izole 1-2
_BIG = ("Squat", "Deadlift", "Leg Press", "Hack Squat", "Hip Thrust", "Romanian Deadlift")


def goal_e1rm(g):
    return fitness.e1rm(g.get("w"), int(num(g.get("r")) or 1))


def goals_for(store, name):
    key = fitness.canonical(name or "").casefold()
    return [g for g in store.all("lift_goals") if fitness.canonical(g.get("name") or "").casefold() == key]


def current(store, name):
    b = fitness.best(store, name)
    return b["e1rm"] if b else 0.0


def progress(store, g):
    """(şu anki e1RM, hedef e1RM, oran 0..1+)."""
    cur, tgt = current(store, g.get("name")), goal_e1rm(g)
    return cur, tgt, (cur / tgt) if tgt else 0.0


def trend(store, name, today):
    """(kg / hafta, nokta sayısı) — son TREND_WEEKS haftanın oturum en iyileri; < 3 oturumda None."""
    a = today - timedelta(weeks=TREND_WEEKS)
    pts = [(d, v) for d, v in fitness.progress_series(store, name) if d >= a and v > 0]
    if len(pts) < 3:
        return None, len(pts)
    xs = [(d - a).days for d, _v in pts]
    ys = [v for _d, v in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if not den:
        return None, len(pts)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return slope * 7, len(pts)


def eta(store, g, today):
    """Bu hızla hedefe tahmini varış günü; ulaşıldıysa today, düşüş / veri yoksa None."""
    cur, tgt, _r = progress(store, g)
    if cur >= tgt > 0:
        return today
    per_week, _n = trend(store, g.get("name"), today)
    if not per_week or per_week <= 0.05:
        return None
    weeks = (tgt - cur) / per_week
    if weeks > 104:
        return None
    return today + timedelta(days=round(weeks * 7))


def weekly_volume(store, name, today, weeks=8):
    """[(hafta başı, hacim kg×tekrar)] eskiden yeniye, boş haftalar 0."""
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    out = {start + timedelta(weeks=i): 0.0 for i in range(weeks)}
    for d, sets in fitness.history(store, name):
        if d < start or d > today:
            continue
        ws = d - timedelta(days=d.weekday())
        out[ws] = out.get(ws, 0.0) + sum(num(s.get("w")) * num(s.get("r")) for s in sets)
    return sorted(out.items())


def rep_range(store, name):
    """Programlardaki tekrar aralığı ("8-12" → (8, 12)); yoksa (6, 10)."""
    key = fitness.canonical(name or "").casefold()
    for tp in store.all("templates"):
        for e in tp.get("exercises") or []:
            if fitness.canonical(e.get("name") or "").casefold() == key and e.get("reps"):
                txt = str(e["reps"]).replace("–", "-")
                parts = [fitness.first_int(p, 0) for p in txt.split("-")]
                parts = [p for p in parts if p > 0]
                if parts:
                    return parts[0], parts[-1] if len(parts) > 1 else parts[0]
    return 6, 10


def step_of(name):
    n = fitness.canonical(name or "")
    if any(b.casefold() == n.casefold() for b in _BIG):
        return 5.0
    if "Dumbbell" in n or n.startswith("Lateral") or "Curl" in n or "Raise" in n or "Fly" in n:
        return 1.0 if "Lateral" in n else 2.0
    return 2.5


def suggest(store, name, today=None):
    """Sonraki oturum önerisi: dict(w, reps, kind "up" | "reps" | "start", last [(w, r)]) ya da None."""
    sets = fitness.last_sets(store, name)
    sets = [s for s in sets if num(s.get("r")) > 0]
    if not sets:
        return None
    lo, hi = rep_range(store, name)
    top = max(num(s.get("w")) for s in sets)
    work = [s for s in sets if num(s.get("w")) >= top * 0.97] or sets
    last = [(num(s.get("w")), int(num(s.get("r")))) for s in sets]
    if top <= 0:                                            # vücut ağırlığı: tekrar artır
        return dict(w=0.0, reps=f"{min(r for _w, r in last) + 1}+", kind="reps", last=last, lo=lo, hi=hi)
    if all(int(num(s.get("r"))) >= hi for s in work):
        return dict(w=top + step_of(name), reps=f"{lo}", kind="up", last=last, lo=lo, hi=hi)
    low = min(int(num(s.get("r"))) for s in work)
    return dict(w=top, reps=f"{min(low + 1, hi)}", kind="reps", last=last, lo=lo, hi=hi)
