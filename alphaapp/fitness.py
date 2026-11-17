"""Ağırlık antrenmanı: hareket kataloğu (çalıştırdığı kaslar), set / tekrar / kilo hesapları, kas yükü, rekorlar.

Veri (store):
  workouts.exercises  [{"name": hareket, "sets": [{"r": tekrar, "w": kg}]}]   (eski kayıtlarda yok)
  templates           antrenman şablonu: name, exercises [{"name", "sets": n, "reps": "6-8", "rir": "1"}], note
  body                vücut ölçüsü: date, weight, fat, waist, chest, arm, thigh, note   (prefs goal_weight)
  lifts               tek başına girilen rekor (PR): date, name, w, r, note — antrenman günlüğüne girmez
Hareket adları kullanıcının uygulamasındaki gibi İngilizce tutulur; kas adları i18n "mus_<anahtar>".
"""
from collections import defaultdict
from datetime import date, timedelta

from .store import parse_date, num

MUSCLES = ("chest", "front_delts", "side_delts", "rear_delts", "biceps", "triceps", "forearms", "abs", "obliques",
           "traps", "lats", "upper_back", "lower_back", "glutes", "quads", "hamstrings", "adductors", "calves")
FRONT = ("chest", "front_delts", "side_delts", "biceps", "forearms", "abs", "obliques", "quads", "adductors",
         "calves", "traps")
BACK = ("traps", "rear_delts", "side_delts", "triceps", "forearms", "lats", "upper_back", "lower_back", "glutes",
        "hamstrings", "calves")

# hareket → (ana kaslar, yardımcı kaslar)
EXERCISES = {
    "Bench Press": (("chest",), ("front_delts", "triceps")),
    "Incline Bench Press": (("chest",), ("front_delts", "triceps")),
    "Smith Machine Incline Bench Press": (("chest",), ("front_delts", "triceps")),
    "Dumbbell Bench Press": (("chest",), ("front_delts", "triceps")),
    "Dumbbell Incline Chest Press": (("chest",), ("front_delts", "triceps")),
    "Chest Press Machine": (("chest",), ("front_delts", "triceps")),
    "Cable Fly": (("chest",), ("front_delts",)),
    "Pec Deck": (("chest",), ("front_delts",)),
    "Dips": (("chest", "triceps"), ("front_delts",)),
    "Push Up": (("chest",), ("triceps", "front_delts", "abs")),
    "Barbell Overhead Press": (("front_delts",), ("side_delts", "triceps", "traps")),
    "Dumbbell Shoulder Press": (("front_delts",), ("side_delts", "triceps")),
    "Shoulder Press Machine": (("front_delts",), ("side_delts", "triceps")),
    "Dumbbell Lateral Raise": (("side_delts",), ("traps",)),
    "Cable Lateral Raise": (("side_delts",), ()),
    "Cable Reverse Fly": (("rear_delts",), ("upper_back",)),
    "Reverse Pec Deck": (("rear_delts",), ("upper_back",)),
    "Face Pull": (("rear_delts",), ("upper_back", "traps")),
    "Barbell Shrug": (("traps",), ("forearms",)),
    "Lat Pulldown": (("lats",), ("biceps", "rear_delts")),
    "Lat Pulldown Wide Grip": (("lats",), ("biceps", "rear_delts")),
    "Pull Up": (("lats",), ("biceps", "upper_back")),
    "Chin Up": (("lats", "biceps"), ("upper_back",)),
    "Chest Supported Machine Row": (("upper_back", "lats"), ("rear_delts", "biceps")),
    "Seated Cable Row": (("upper_back", "lats"), ("biceps", "rear_delts")),
    "Barbell Row": (("upper_back", "lats"), ("biceps", "lower_back", "rear_delts")),
    "Dumbbell Row": (("lats", "upper_back"), ("biceps", "rear_delts")),
    "T-Bar Row": (("upper_back", "lats"), ("biceps", "lower_back")),
    "Deadlift": (("lower_back", "glutes", "hamstrings"), ("traps", "forearms", "quads", "upper_back")),
    "Romanian Deadlift": (("hamstrings", "glutes"), ("lower_back",)),
    "Back Extension": (("lower_back",), ("glutes", "hamstrings")),
    "Barbell Curl": (("biceps",), ("forearms",)),
    "EZ Bar Curl": (("biceps",), ("forearms",)),
    "Dumbbell Curl": (("biceps",), ("forearms",)),
    "Dumbbell Hammer Curl": (("biceps", "forearms"), ()),
    "Preacher Curl": (("biceps",), ()),
    "Cable Curl": (("biceps",), ("forearms",)),
    "Triceps Pushdown": (("triceps",), ()),
    "Overhead Triceps Extension": (("triceps",), ()),
    "Skull Crusher": (("triceps",), ()),
    "Close Grip Bench Press": (("triceps",), ("chest", "front_delts")),
    "Wrist Curl": (("forearms",), ()),
    "Squat": (("quads", "glutes"), ("adductors", "lower_back", "hamstrings")),
    "Front Squat": (("quads",), ("glutes", "abs")),
    "Hack Squat": (("quads",), ("glutes",)),
    "Leg Press": (("quads", "glutes"), ("adductors", "hamstrings")),
    "Bulgarian Split Squat": (("quads", "glutes"), ("adductors", "hamstrings")),
    "Lunge": (("quads", "glutes"), ("hamstrings", "adductors")),
    "Leg Extension": (("quads",), ()),
    "Seated Leg Curl": (("hamstrings",), ("calves",)),
    "Lying Leg Curl": (("hamstrings",), ("calves",)),
    "Hip Thrust": (("glutes",), ("hamstrings",)),
    "Hip Adduction Machine": (("adductors",), ()),
    "Hip Abduction Machine": (("glutes",), ()),
    "Seated Calf Raise": (("calves",), ()),
    "Standing Calf Raise": (("calves",), ()),
    "Crunch": (("abs",), ()),
    "Cable Crunch": (("abs",), ()),
    "Hanging Leg Raise": (("abs",), ("obliques",)),
    "Plank": (("abs",), ("obliques",)),
    "Russian Twist": (("obliques",), ("abs",)),
}
# katalogda olmayan adlar için anahtar kelime tahmini (sıra önemli)
_GUESS = (("calf", ("calves",)), ("leg curl", ("hamstrings",)), ("leg extension", ("quads",)),
          ("squat", ("quads", "glutes")), ("leg press", ("quads", "glutes")), ("lunge", ("quads", "glutes")),
          ("deadlift", ("hamstrings", "glutes", "lower_back")), ("hip thrust", ("glutes",)),
          ("glute", ("glutes",)), ("adduct", ("adductors",)), ("hammer", ("biceps", "forearms")),
          ("curl", ("biceps",)), ("tricep", ("triceps",)), ("pushdown", ("triceps",)), ("dip", ("triceps", "chest")),
          ("lateral", ("side_delts",)), ("reverse fly", ("rear_delts",)), ("rear delt", ("rear_delts",)),
          ("face pull", ("rear_delts",)), ("shrug", ("traps",)), ("overhead press", ("front_delts",)),
          ("shoulder", ("front_delts",)), ("pulldown", ("lats",)), ("pull up", ("lats",)), ("row", ("upper_back", "lats")),
          ("fly", ("chest",)), ("bench", ("chest",)), ("chest", ("chest",)), ("press", ("chest",)),
          ("crunch", ("abs",)), ("plank", ("abs",)), ("twist", ("obliques",)), ("wrist", ("forearms",)))


def muscles_of(name):
    """(ana, yardımcı) kas listesi; katalogda yoksa addaki kelimelerden tahmin."""
    key = (name or "").strip()
    for k, v in EXERCISES.items():
        if k.casefold() == key.casefold():
            return v
    low = key.casefold()
    for word, prim in _GUESS:
        if word in low:
            return prim, ()
    return (), ()


def exercise_names(store):
    """Seçilebilecek hareketler: katalog + kayıtlarda / şablonlarda geçenler (sık kullanılan önce)."""
    used = defaultdict(int)
    for w in store.all("workouts"):
        for e in w.get("exercises") or []:
            used[e.get("name") or ""] += 1
    for tp in store.all("templates"):
        for e in tp.get("exercises") or []:
            used[e.get("name") or ""] += 1
    used.pop("", None)
    names = sorted(used, key=lambda n: -used[n])
    names += [n for n in sorted(EXERCISES) if n not in used]
    return names


def first_int(text, default=8):
    """"6-8" → 6, "10" → 10."""
    digits = ""
    for ch in str(text or ""):
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else default


def e1rm(w, r):
    """Tahmini tek tekrar maksimum (Epley). r = 1 ise ağırlığın kendisi."""
    w, r = num(w), int(num(r))
    if w <= 0 or r <= 0:
        return 0.0
    return w if r == 1 else w * (1 + r / 30.0)


def valid_sets(ex):
    return [s for s in ex.get("sets") or [] if num(s.get("r")) > 0]


def history(store, name):
    """Bir hareketin oturumları: [(tarih, setler)] eskiden yeniye."""
    out = []
    key = (name or "").casefold()
    for x in store.all("lifts"):
        d = parse_date(x.get("date"))
        if d and (x.get("name") or "").casefold() == key and num(x.get("r")) > 0:
            out.append((d, [{"r": x.get("r"), "w": x.get("w")}]))
    for w in store.all("workouts"):
        d = parse_date(w.get("date"))
        if d is None:
            continue
        for e in w.get("exercises") or []:
            if (e.get("name") or "").casefold() == key and valid_sets(e):
                out.append((d, valid_sets(e)))
    out.sort(key=lambda x: x[0])
    return out


def last_sets(store, name, before=None):
    """Bu hareketin en son yapılan setleri (before tarihinden önce) ya da []."""
    h = [x for x in history(store, name) if before is None or x[0] < before]
    return h[-1][1] if h else []


def best(store, name):
    """dict(e1rm, w, r, date) — en yüksek tahmini maksimumlu set; yoksa None."""
    top = None
    for d, sets in history(store, name):
        for s in sets:
            v = e1rm(s.get("w"), s.get("r"))
            if v and (top is None or v > top["e1rm"]):
                top = {"e1rm": v, "w": num(s.get("w")), "r": int(num(s.get("r"))), "date": d}
    return top


def progress_series(store, name):
    """Oturum başına en iyi tahmini maksimum: [(tarih, e1rm)]."""
    return [(d, max(e1rm(s.get("w"), s.get("r")) for s in sets)) for d, sets in history(store, name)
            if any(num(s.get("w")) > 0 for s in sets)]


def logged_exercises(store):
    """Set girilmiş hareketler (rekorlar dahil), en son yapılan önce."""
    last = {}
    for x in store.all("lifts"):
        d, n = parse_date(x.get("date")), x.get("name") or ""
        if d and n and num(x.get("r")) > 0 and (n not in last or d > last[n]):
            last[n] = d
    for w in store.all("workouts"):
        d = parse_date(w.get("date"))
        for e in w.get("exercises") or []:
            if d and valid_sets(e):
                n = e.get("name") or ""
                if n and (n not in last or d > last[n]):
                    last[n] = d
    return sorted(last, key=lambda n: last[n], reverse=True)


def muscle_load(exercises, sets_key="sets"):
    """Kas → set sayısı (ana kas 1, yardımcı 0.5). exercises: kayıt ya da şablon hareketleri."""
    load = defaultdict(float)
    for e in exercises:
        n = e.get(sets_key)
        n = len(valid_sets(e)) if isinstance(n, list) else int(num(n))
        prim, sec = muscles_of(e.get("name"))
        for m in prim:
            load[m] += n
        for m in sec:
            load[m] += n * 0.5
    return dict(load)


def recent_load(store, days=7, today=None):
    """Son `days` günde kaslara düşen set ve her kasın en son çalıştığı gün."""
    today = today or date.today()
    a = today - timedelta(days=days - 1)
    load, last = defaultdict(float), {}
    for w in store.all("workouts"):
        d = parse_date(w.get("date"))
        if d is None or not (a <= d <= today):
            continue
        for m, v in muscle_load(w.get("exercises") or []).items():
            load[m] += v
            if v >= 1 and (m not in last or d > last[m]):
                last[m] = d
    return dict(load), last


def template_sets(tp):
    return sum(int(num(e.get("sets"))) for e in tp.get("exercises") or [])


def intensity(total_sets):
    """Şablonun yoğunluğu 1-5 (set sayısına göre)."""
    for lim, lvl in ((10, 1), (15, 2), (20, 3), (25, 4)):
        if total_sets <= lim:
            return lvl
    return 5


def volume(w):
    """Kayıttaki toplam hacim (kg × tekrar)."""
    return sum(num(s.get("w")) * num(s.get("r")) for e in w.get("exercises") or [] for s in valid_sets(e))


# ---------------------------------------------------------------- gelişim (kas başına güç seviyesi)
# Orta seviye bir erkek için tahmini 1RM / vücut ağırlığı oranı (dambıllarda tek dambıl). Yaygın güç
# standartlarından yuvarlanmış kaba değerler; amaç kasları kıyaslamak, kesin seviye değil.
STANDARDS = {
    "Bench Press": 1.0, "Incline Bench Press": 0.85, "Smith Machine Incline Bench Press": 0.85,
    "Dumbbell Bench Press": 0.37, "Dumbbell Incline Chest Press": 0.32, "Chest Press Machine": 0.9,
    "Cable Fly": 0.25, "Pec Deck": 0.6, "Barbell Overhead Press": 0.65, "Dumbbell Shoulder Press": 0.27,
    "Shoulder Press Machine": 0.6, "Dumbbell Lateral Raise": 0.13, "Cable Lateral Raise": 0.08,
    "Cable Reverse Fly": 0.1, "Reverse Pec Deck": 0.45, "Face Pull": 0.35, "Barbell Shrug": 1.3,
    "Lat Pulldown": 0.85, "Lat Pulldown Wide Grip": 0.8, "Chest Supported Machine Row": 0.75,
    "Seated Cable Row": 0.85, "Barbell Row": 0.85, "Dumbbell Row": 0.4, "T-Bar Row": 0.9, "Deadlift": 1.5,
    "Romanian Deadlift": 1.1, "Back Extension": 0.3, "Barbell Curl": 0.45, "EZ Bar Curl": 0.45,
    "Dumbbell Curl": 0.18, "Dumbbell Hammer Curl": 0.2, "Preacher Curl": 0.35, "Cable Curl": 0.4,
    "Triceps Pushdown": 0.5, "Overhead Triceps Extension": 0.4, "Skull Crusher": 0.4,
    "Close Grip Bench Press": 0.85, "Wrist Curl": 0.3, "Squat": 1.25, "Front Squat": 1.0, "Hack Squat": 1.5,
    "Leg Press": 2.5, "Bulgarian Split Squat": 0.35, "Lunge": 0.35, "Leg Extension": 0.9,
    "Seated Leg Curl": 0.7, "Lying Leg Curl": 0.6, "Hip Thrust": 1.5, "Hip Adduction Machine": 0.9,
    "Hip Abduction Machine": 0.9, "Seated Calf Raise": 1.0, "Standing Calf Raise": 1.4, "Cable Crunch": 0.6,
}
LEVELS = (0.45, 0.75, 1.05, 1.35)     # oran / standart → 0 yeni başlayan · 1 acemi · 2 orta · 3 ileri · 4 elit


def standard(name):
    key = (name or "").casefold()
    for k, v in STANDARDS.items():
        if k.casefold() == key:
            return v
    return None


def body_weight(store):
    """En son girilen kilo ya da None."""
    rows = sorted((b for b in store.all("body") if parse_date(b.get("date")) and num(b.get("weight")) > 0),
                  key=lambda b: (b["date"], b.get("created") or ""))
    return num(rows[-1]["weight"]) if rows else None


def level_of(q):
    return sum(1 for x in LEVELS if q >= x)


def development(store, bw=None):
    """Kas → dict(q, level, ex, e1rm, date, main). q = 1RM / vücut ağırlığı / standart (1 ≈ orta seviye).
    Ana kas tam, yardımcı kas %50 sayılır; her kas için en iyi hareket alınır."""
    bw = bw or body_weight(store) or 75.0
    out = {}
    for name in logged_exercises(store):
        std = standard(name)
        b = best(store, name)
        if not std or not b or b["e1rm"] <= 0:
            continue
        q = b["e1rm"] / bw / std
        prim, sec = muscles_of(name)
        for m, wgt in [(m, 1.0) for m in prim] + [(m, 0.5) for m in sec]:
            v = q * wgt
            if m not in out or v > out[m]["q"]:
                out[m] = {"q": v, "level": level_of(v), "ex": name, "e1rm": b["e1rm"], "date": b["date"],
                          "main": wgt == 1.0}
    return out


def dev_heat(q):
    """Gelişim oranı → 0..1 kırmızılık (elit ≈ 1)."""
    return max(0.0, min(1.0, q / LEVELS[-1]))


# ---------------------------------------------------------------- en yaygın 10 program (haftalık toplam set)
def _p(key, name, days, ex):
    return {"key": key, "name": name, "days": days,
            "exercises": [{"name": n, "sets": s, "reps": r} for n, s, r in ex]}


POPULAR = [
    _p("ppl", "Push / Pull / Legs", 6, [
        ("Bench Press", 8, "5-8"), ("Barbell Overhead Press", 6, "8"), ("Dumbbell Incline Chest Press", 6, "10"),
        ("Triceps Pushdown", 6, "12"), ("Dumbbell Lateral Raise", 8, "15"), ("Deadlift", 3, "5"),
        ("Barbell Row", 8, "8"), ("Lat Pulldown", 6, "10"), ("Face Pull", 6, "15"), ("Barbell Curl", 6, "10"),
        ("Dumbbell Hammer Curl", 4, "12"), ("Squat", 8, "5-8"), ("Romanian Deadlift", 6, "10"),
        ("Leg Press", 6, "10"), ("Seated Leg Curl", 6, "12"), ("Standing Calf Raise", 8, "12")]),
    _p("ul", "Upper / Lower", 4, [
        ("Bench Press", 6, "6"), ("Barbell Row", 6, "8"), ("Barbell Overhead Press", 4, "8"),
        ("Lat Pulldown", 6, "10"), ("Dumbbell Incline Chest Press", 4, "10"), ("Seated Cable Row", 4, "10"),
        ("Dumbbell Lateral Raise", 6, "15"), ("Barbell Curl", 4, "10"), ("Triceps Pushdown", 4, "12"),
        ("Squat", 6, "6"), ("Romanian Deadlift", 6, "8"), ("Leg Press", 4, "10"), ("Seated Leg Curl", 4, "12"),
        ("Standing Calf Raise", 6, "12"), ("Cable Crunch", 4, "15")]),
    _p("fb", "Full Body", 3, [
        ("Squat", 9, "5"), ("Bench Press", 9, "5"), ("Barbell Row", 9, "8"), ("Barbell Overhead Press", 3, "8"),
        ("Romanian Deadlift", 3, "8"), ("Lat Pulldown", 3, "10"), ("Dumbbell Lateral Raise", 6, "15"),
        ("Barbell Curl", 3, "10"), ("Triceps Pushdown", 3, "12"), ("Standing Calf Raise", 3, "12"),
        ("Plank", 3, "45 sn")]),
    _p("sl5", "StrongLifts 5×5", 3, [
        ("Squat", 15, "5"), ("Bench Press", 8, "5"), ("Barbell Row", 8, "5"), ("Barbell Overhead Press", 7, "5"),
        ("Deadlift", 2, "5")]),
    _p("ss", "Starting Strength", 3, [
        ("Squat", 9, "5"), ("Bench Press", 5, "5"), ("Barbell Overhead Press", 4, "5"), ("Deadlift", 2, "5"),
        ("Chin Up", 3, "8")]),
    _p("531", "5/3/1 Boring But Big", 4, [
        ("Barbell Overhead Press", 8, "5/3/1 + 5×10"), ("Bench Press", 8, "5/3/1 + 5×10"),
        ("Squat", 8, "5/3/1 + 5×10"), ("Deadlift", 8, "5/3/1 + 5×10"), ("Chin Up", 10, "10"),
        ("Dumbbell Row", 5, "10"), ("Hanging Leg Raise", 10, "10")]),
    _p("phul", "PHUL", 4, [
        ("Bench Press", 7, "3-5"), ("Dumbbell Incline Chest Press", 4, "8-12"), ("Barbell Row", 7, "3-5"),
        ("Lat Pulldown", 4, "6-10"), ("Barbell Overhead Press", 3, "5-8"), ("Cable Fly", 3, "10-12"),
        ("Seated Cable Row", 4, "8-12"), ("Dumbbell Lateral Raise", 4, "10-12"), ("Barbell Curl", 6, "6-12"),
        ("Skull Crusher", 6, "6-12"), ("Squat", 4, "3-5"), ("Deadlift", 3, "3-5"), ("Leg Press", 5, "10-15"),
        ("Seated Leg Curl", 7, "6-12"), ("Standing Calf Raise", 8, "6-15"), ("Front Squat", 4, "8-12"),
        ("Lunge", 3, "8-12"), ("Leg Extension", 4, "10-15")]),
    _p("phat", "PHAT", 5, [
        ("Bench Press", 6, "3-5"), ("Dumbbell Incline Chest Press", 6, "8-12"), ("Cable Fly", 3, "12-15"),
        ("Barbell Row", 6, "3-5"), ("Pull Up", 5, "6-10"), ("Seated Cable Row", 3, "12-15"),
        ("Dumbbell Shoulder Press", 5, "6-10"), ("Dumbbell Lateral Raise", 6, "12-20"), ("Barbell Curl", 5, "6-10"),
        ("Preacher Curl", 3, "8-12"), ("Skull Crusher", 5, "6-10"), ("Triceps Pushdown", 3, "12-15"),
        ("Squat", 9, "3-5 / 8-12"), ("Hack Squat", 3, "8-12"), ("Leg Extension", 3, "12-20"),
        ("Romanian Deadlift", 6, "5-8"), ("Seated Leg Curl", 6, "8-12"), ("Standing Calf Raise", 8, "8-15"),
        ("Barbell Shrug", 3, "8-12")]),
    _p("arnold", "Arnold Split", 6, [
        ("Bench Press", 8, "6-10"), ("Dumbbell Incline Chest Press", 8, "8-12"), ("Cable Fly", 6, "12"),
        ("Pull Up", 8, "8-10"), ("Barbell Row", 8, "8-10"), ("T-Bar Row", 6, "10"),
        ("Barbell Overhead Press", 8, "8"), ("Dumbbell Lateral Raise", 8, "12"), ("Reverse Pec Deck", 6, "12"),
        ("Barbell Curl", 8, "8-10"), ("Dumbbell Curl", 6, "10"), ("Close Grip Bench Press", 8, "8-10"),
        ("Overhead Triceps Extension", 6, "10"), ("Squat", 8, "8-10"), ("Leg Press", 6, "10"),
        ("Seated Leg Curl", 8, "10"), ("Standing Calf Raise", 10, "15"), ("Crunch", 8, "20")]),
    _p("bro", "Bro Split", 5, [
        ("Bench Press", 4, "8"), ("Dumbbell Incline Chest Press", 4, "10"), ("Cable Fly", 3, "12"),
        ("Pec Deck", 3, "12"), ("Deadlift", 3, "5"), ("Lat Pulldown", 4, "10"), ("Barbell Row", 4, "8"),
        ("Seated Cable Row", 3, "10"), ("Dumbbell Shoulder Press", 4, "10"), ("Dumbbell Lateral Raise", 4, "15"),
        ("Reverse Pec Deck", 3, "15"), ("Barbell Shrug", 3, "12"), ("Barbell Curl", 3, "10"),
        ("Dumbbell Hammer Curl", 3, "12"), ("Preacher Curl", 3, "12"), ("Triceps Pushdown", 3, "12"),
        ("Skull Crusher", 3, "10"), ("Overhead Triceps Extension", 3, "12"), ("Squat", 4, "8"),
        ("Leg Press", 4, "10"), ("Leg Extension", 3, "12"), ("Seated Leg Curl", 4, "12"),
        ("Standing Calf Raise", 4, "15")]),
]


def weekly_intensity(weekly_sets):
    """Haftalık toplam sete göre 1-5 (programlar arası kıyas)."""
    for lim, lvl in ((40, 1), (60, 2), (80, 3), (100, 4)):
        if weekly_sets <= lim:
            return lvl
    return 5
