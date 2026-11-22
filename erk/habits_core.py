"""Alışkanlık mantığı: gün değerleri (tam / yarım / yok), bırakma türü, ders çalışmadan otomatik, seri kuralları.

habits kaydı:
  kind      "build" (yap, varsayılan) | "quit" (bırak: NoFap, ekran süresi …). Bırakmada her gün kendiliğinden
            "temiz" sayılır; yalnızca kayma işaretlenir (slips). start = bırakmanın başladığı gün.
  days      tam işaretli günler (build) · half: yarım işaretli günler (iki türde de)
  slips     bırakmada kayılan günler
  source    "study" → değer sessions'tan gelir: o gün ders çalışma ≥ target_h saat = tam, ≥ yarısı = yarım
            "workout" → antrenman (workouts) girilen gün tam. İkisinde de elle işaret geçerli; büyük olan alınır.
  goal      haftalık ideal gün (ör. 4) · week_min: haftalık en az (ör. 3.5; yarım gün 0.5 sayılır)
  gap       üst üste kaç gün kaçırınca seri bozulur (varsayılan 1 = her gün; spor için 3)
Seri: bozulmadan geçen gün sayısı (dinlenme günleri dahil) + bu süredeki işaretli gün sayısı.
Bozulma: gap kadar üst üste boş gün, ya da biten bir haftada toplam < week_min. Bugün henüz bitmedi: bugünün
boşluğu sayılmaz.
"""
from datetime import timedelta

from .store import day_set, parse_date, num, week_start


def is_quit(h):
    return h.get("kind") == "quit"


def study_minutes(store):
    """{gün: dakika} — ders çalışma oturumları."""
    out = {}
    for s in store.all("sessions"):
        if s.get("kind") != "study":
            continue
        d = parse_date(s.get("date"))
        if d:
            out[d] = out.get(d, 0.0) + num(s.get("minutes"))
    return out


def start_of(h, store=None):
    """Değerlendirmenin başladığı gün: bırakmada start, yoksa ilk işaret / oluşturulma."""
    s = parse_date(h.get("start"))
    if s:
        return s
    cands = [d for d in (day_set(h.get("days")) | day_set(h.get("half")) | day_set(h.get("slips")))]
    c = parse_date((h.get("created") or "")[:10])
    if c:
        cands.append(c)
    if h.get("source") == "study" and store is not None:
        cands += [d for d, m in study_minutes(store).items() if m > 0]
    if h.get("source") == "workout" and store is not None:
        cands += list(workout_days(store))
    return min(cands) if cands else None


def workout_days(store):
    return {d for d in (parse_date(w.get("date")) for w in store.all("workouts")) if d}


def auto_source(store):
    """Antrenmandan dolan alışkanlık (Spor sayfası serisi için) ya da None."""
    return next((h for h in store.all("habits") if h.get("source") == "workout"), None)


def values(h, td, store=None, a=None):
    """{gün: 0 | 0.5 | 1} a..td arası (a yoksa başlangıçtan). Bırakmada başlangıçtan önce değer yok."""
    st = start_of(h, store)
    if st is None:
        return {}
    a = max(a or st, st) if is_quit(h) else (a or st)
    full, half = day_set(h.get("days")), day_set(h.get("half"))
    out = {}
    if is_quit(h):
        slips = day_set(h.get("slips"))
        d = a
        while d <= td:
            out[d] = 0.0 if d in slips else 0.5 if d in half else 1.0
            d += timedelta(days=1)
        return out
    mins = study_minutes(store) if h.get("source") == "study" and store is not None else {}
    wdays = workout_days(store) if h.get("source") == "workout" and store is not None else set()
    thr = (num(h.get("target_h")) or 3.0) * 60
    d = a
    while d <= td:
        v = 1.0 if d in full else 0.5 if d in half else 0.0
        if d in wdays:
            v = 1.0
        m = mins.get(d, 0.0)
        if m >= thr:
            v = 1.0
        elif m >= thr / 2:
            v = max(v, 0.5)
        out[d] = v
        d += timedelta(days=1)
    return out


def rules(h):
    goal = num(h.get("goal")) or 7.0
    wmin = h.get("week_min")
    wmin = num(wmin) if wmin not in (None, "") else None
    gap = int(num(h.get("gap")) or 1)
    return max(0.5, min(7.0, goal)), wmin, max(1, gap)


def streak_info(h, td, store=None):
    """dict(cur, best, cur_done, start (aktif serinin ilk günü ya da None), ranges [(a, b)] geçmiş + aktif seriler)."""
    vals = values(h, td, store)
    if not vals:
        return {"cur": 0, "best": 0, "cur_done": 0, "start": None, "ranges": []}
    _goal, wmin, gap = rules(h)
    if is_quit(h):
        gap = 1                           # bırakmada her kayma seriyi sıfırlar
    days = sorted(vals)
    ranges = []
    run_a = None          # aktif seri başlangıcı
    last_hit = None       # serideki son işaretli gün
    miss = 0

    def close():
        nonlocal run_a, last_hit, miss
        if run_a is not None and last_hit is not None:
            ranges.append((run_a, last_hit))
        run_a, last_hit, miss = None, None, 0

    for d in days:
        v = vals[d]
        # biten hafta kontrolü (pazartesi başında, önceki tam hafta)
        # biten hafta (pazartesiye gelince önceki hafta): seri o haftanın tamamını kapsıyorsa toplam ≥ week_min
        if wmin is not None and d.weekday() == 0 and run_a is not None:
            ws = d - timedelta(days=7)
            if run_a <= ws:
                tot = sum(vals.get(ws + timedelta(days=i), 0.0) for i in range(7))
                if tot + 1e-9 < wmin:
                    close()
        if v > 0:
            if run_a is None:
                run_a = d
            last_hit = d
            miss = 0
        else:
            if d == td and not is_quit(h):
                continue                  # bugün bitmedi (bırakmada bugünkü kayma sayılır)
            if run_a is not None:
                miss += 1
                if miss >= gap:
                    close()
    alive = run_a is not None
    cur_range = (run_a, td) if alive else None
    if alive:
        ranges.append((run_a, last_hit))
    lens = [(b - a).days + 1 for a, b in ranges]
    cur = (td - run_a).days + 1 if alive else 0
    if alive and vals.get(td, 0) == 0:
        cur = (td - run_a).days           # bugün henüz işaretlenmedi: dünden say
    cur_done = sum(vals[d] for d in vals if alive and run_a <= d <= td)
    best = max(lens + [cur]) if lens else cur
    return {"cur": cur, "best": best, "cur_done": cur_done, "start": run_a if alive else None,
            "ranges": ranges, "cur_range": cur_range}


def week_total(h, td, store=None):
    ws = week_start(td)
    vals = values(h, td, store, a=ws)
    return sum(v for d, v in vals.items() if ws <= d <= td)


def state(h, d, store=None):
    """Grid / liste için o günün durumu: 1, 0.5, 0 (bırakmada 0 = kayma), None = başlangıçtan önce."""
    return values(h, d, store, a=d).get(d)


def cycle(store, h, d):
    """Tıklama: yap → boş → tam → yarım → boş · bırak → temiz → kayma → yarım → temiz. Yeni durumu döndürür."""
    iso = d.isoformat()
    days = [x for x in (h.get("days") or []) if x != iso]
    half = [x for x in (h.get("half") or []) if x != iso]
    slips = [x for x in (h.get("slips") or []) if x != iso]
    if is_quit(h):
        cur = 0 if iso in (h.get("slips") or []) else 0.5 if iso in (h.get("half") or []) else 1
        nxt = {1: 0, 0: 0.5, 0.5: 1}[cur]
        if nxt == 0:
            slips.append(iso)
        elif nxt == 0.5:
            half.append(iso)
        fields = {"slips": sorted(slips), "half": sorted(half)}
        st = parse_date(h.get("start"))
        if st is None or d < st:
            fields["start"] = iso
    else:
        cur = 1 if iso in (h.get("days") or []) else 0.5 if iso in (h.get("half") or []) else 0
        nxt = {0: 1, 1: 0.5, 0.5: 0}[cur]
        if nxt == 1:
            days.append(iso)
        elif nxt == 0.5:
            half.append(iso)
        fields = {"days": sorted(days), "half": sorted(half)}
    store.update("habits", h["id"], **fields)
    return nxt


def set_today(store, h, d, done):
    """"Bugün" listesindeki onay: yap → tam / boş, bırak → temiz / kayma."""
    iso = d.isoformat()
    days = [x for x in (h.get("days") or []) if x != iso]
    half = [x for x in (h.get("half") or []) if x != iso]
    slips = [x for x in (h.get("slips") or []) if x != iso]
    if is_quit(h):
        if not done:
            slips.append(iso)
        store.update("habits", h["id"], slips=sorted(slips), half=sorted(half))
    else:
        if done:
            days.append(iso)
        store.update("habits", h["id"], days=sorted(days), half=sorted(half))


def done_days(h, td, store=None):
    """Eski arayüzler için: tam ya da yarım işaretli günler kümesi (bırakmada temiz günler)."""
    return {d for d, v in values(h, td, store).items() if v > 0}


# hazır alışkanlıklar (Alışkanlıklar > öneriler)
TEMPLATES = (
    {"key": "nofap", "name": "NoFap", "kind": "quit", "category": "personal"},
    {"key": "screen", "name": "Ekran süresi (günde 3 saati aşma)", "kind": "quit", "category": "personal"},
    {"key": "gym", "name": "Spora git", "category": "sport", "source": "workout", "goal": 4, "week_min": 3.5,
     "gap": 3},
    {"key": "food", "name": "İyi beslen", "category": "sport", "goal": 7, "week_min": 5, "gap": 2},
    {"key": "book", "name": "Kitap oku", "category": "personal", "goal": 7, "week_min": 5, "gap": 2},
    {"key": "study", "name": "3+ saat ders çalışma", "category": "education", "source": "study", "target_h": 3,
     "goal": 5, "week_min": 4, "gap": 2},
)


def from_template(store, tpl, td):
    data = {k: v for k, v in tpl.items() if k != "key"}
    data.setdefault("days", [])
    if data.get("kind") == "quit":
        data["start"] = td.isoformat()
        data["slips"] = []
    return store.add("habits", data)


def is_sport(h):
    """Haftalık programa yalnızca spor alışkanlıkları girer (kategori spor ya da antrenmandan otomatik)."""
    return h.get("category") == "sport" or h.get("source") == "workout"
