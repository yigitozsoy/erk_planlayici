"""Hızlı ekle komutu (İngilizce, Todoist tarzı): tek satırdan görev ya da harcama.

  call mom tomorrow 6pm #social !          → görev: yarın 18:00, Sosyal, önemli
  report fri 14:00-15:30 #work +Thesis     → cuma 14:00–15:30, İş, Thesis projesi
  gym every mon,wed,fri 7am #sport         → her Pzt / Çar / Cum tekrarlayan görev (repeat "w:0,2,4")
  pay rent every month 1.12                → 1 Aralık'tan başlayıp her ay
  spent 120 coffee with ali                → harcama: 120 ₺, kategori Kahve, not "with ali"

Tarih: today / tonight / tomorrow (tmr) / mon..sun (bir sonraki) / next week / next month / in 3 days / in 2 weeks /
21.11 / 21.11.2026 / 2026-11-21 / nov 21 / 21 nov. Saat: 14:30, 9am, 9:30pm, "at 9", aralık 14-16 / 14:00-15:30.
Tekrar: every day | daily | every weekday | every week | weekly | every month | monthly | every mon,wed.
Öncelik: ! ya da !! ya da !high → high, !low → low. Kategori: #work #school #sport #social #finance #personal (+ Türkçe
ve özel kategori adları). Proje: +ad (adın başı yeter). Tanınmayan sözcükler başlıkta kalır.
parse() saf fonksiyon; next_due() tekrarlayan görevin bir sonraki tarihi (store.update görev bitince kullanır).
"""
import calendar
import re
from datetime import date, timedelta

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_DAY_FULL = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
CAT_TAGS = {
    "work": "work", "job": "work", "iş": "work", "is": "work", "office": "work",
    "school": "education", "edu": "education", "education": "education", "uni": "education", "class": "education",
    "study": "education", "okul": "education", "ders": "education", "eğitim": "education",
    "sport": "sport", "gym": "sport", "fitness": "sport", "spor": "sport", "health": "sport",
    "social": "social", "friends": "social", "family": "social", "sosyal": "social",
    "finance": "finance", "money": "finance", "ekonomi": "finance", "para": "finance",
    "personal": "personal", "home": "personal", "kişisel": "personal", "me": "personal",
}
REPEATS = ("daily", "weekdays", "weekly", "monthly")


def _weekday(tok):
    tok = tok.lower().rstrip(".,")
    for i, (a, b) in enumerate(zip(DAYS, _DAY_FULL)):
        if tok == a or tok == b or (len(tok) >= 3 and b.startswith(tok)):
            return i
    return None


def _month(tok):
    tok = tok.lower().rstrip(".,")
    for i, m in enumerate(MONTHS):
        if len(tok) >= 3 and tok.startswith(m):
            return i + 1
    return None


def _next_wd(today, wd, strictly=True):
    k = (wd - today.weekday()) % 7
    if k == 0 and strictly:
        k = 7
    return today + timedelta(days=k)


def _safe_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _future(today, m, d):
    """Yılsız gün.ay: geçtiyse gelecek yıl."""
    x = _safe_date(today.year, m, d)
    if x and x < today:
        x = _safe_date(today.year + 1, m, d)
    return x


_TIME = re.compile(r"^(\d{1,2})(?::(\d{2}))?(am|pm)?$", re.I)
_RANGE = re.compile(r"^(\d{1,2}(?::\d{2})?(?:am|pm)?)-(\d{1,2}(?::\d{2})?(?:am|pm)?)$", re.I)


def _time(tok, need_colon=True):
    m = _TIME.match(tok)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if need_colon and not m.group(2) and not ap:
        return None
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def parse(text, today, default_cat="personal", projects=(), custom_cats=()):
    """→ ("tasks" | "transactions", alanlar). projects: [(id, ad)], custom_cats: [(id, ad)]."""
    raw = (text or "").strip()
    toks = raw.split()
    low = [x.lower() for x in toks]
    if low and low[0] in ("spent", "spend", "paid", "pay$", "expense") and len(toks) > 1:
        return _expense(toks[1:], today)
    used = [False] * len(toks)
    out = {"category": default_cat, "priority": "normal", "done": False}
    due = time = end = repeat = None

    def take(*idx):
        for i in idx:
            used[i] = True

    i = 0
    while i < len(toks):
        w = low[i].rstrip(",")
        nxt = low[i + 1].rstrip(",") if i + 1 < len(toks) else ""
        nxt2 = low[i + 2].rstrip(",") if i + 2 < len(toks) else ""
        # --- tekrar
        if w == "every" and nxt:
            if nxt in ("day", "night"):
                repeat = "daily"
            elif nxt in ("weekday", "weekdays", "workday"):
                repeat = "weekdays"
            elif nxt == "week":
                repeat = "weekly"
            elif nxt == "month":
                repeat = "monthly"
            else:
                wds = [_weekday(p) for p in nxt.split(",") if p]
                if wds and None not in wds:
                    repeat = "w:" + ",".join(str(x) for x in sorted(set(wds)))
                    if due is None:
                        due = min(_next_wd(today, x, strictly=False) for x in wds)
            if repeat:
                take(i, i + 1)
                i += 2
                continue
        if w in ("daily", "weekly", "monthly"):
            repeat = w
            take(i)
            i += 1
            continue
        # --- tarih
        if w in ("today", "tod", "tonight"):
            due = today
            if w == "tonight" and time is None:
                time = "20:00"
            take(i)
        elif w in ("tomorrow", "tmr", "tmrw"):
            due = today + timedelta(days=1)
            take(i)
        elif w == "next" and nxt in ("week", "month") + DAYS + _DAY_FULL:
            if nxt == "week":
                due = _next_wd(today, 0)
            elif nxt == "month":
                y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
                due = date(y, m, 1)
            else:
                due = _next_wd(today, _weekday(nxt))
            take(i, i + 1)
            i += 2
            continue
        elif w == "in" and nxt.isdigit() and nxt2.rstrip("s") in ("day", "week", "month"):
            n = int(nxt)
            unit = nxt2.rstrip("s")
            due = today + timedelta(days=n * (7 if unit == "week" else 30 if unit == "month" else 1))
            take(i, i + 1, i + 2)
            i += 3
            continue
        elif _weekday(w) is not None and len(w) >= 3:
            due = _next_wd(today, _weekday(w))
            take(i)
        elif re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", w):
            y, m, d = (int(x) for x in w.split("-"))
            due = _safe_date(y, m, d) or due
            take(i)
        elif re.match(r"^\d{1,2}[./]\d{1,2}([./]\d{2,4})?$", w):
            parts = [int(x) for x in re.split(r"[./]", w)]
            if len(parts) == 3:
                y = parts[2] + (2000 if parts[2] < 100 else 0)
                due = _safe_date(y, parts[1], parts[0]) or due
            else:
                due = _future(today, parts[1], parts[0]) or due
            take(i)
        elif _month(w) and nxt.isdigit() and 1 <= int(nxt) <= 31:
            due = _future(today, _month(w), int(nxt)) or due
            take(i, i + 1)
            i += 2
            continue
        elif w.isdigit() and 1 <= int(w) <= 31 and _month(nxt):
            due = _future(today, _month(nxt), int(w)) or due
            take(i, i + 1)
            i += 2
            continue
        # --- saat
        elif w == "at" and nxt and (_time(nxt, need_colon=False) or _RANGE.match(nxt)):
            take(i)
        elif _RANGE.match(w):
            a, b = _RANGE.match(w).groups()
            ta, tb = _time(a, need_colon=False), _time(b, need_colon=False)
            # "5-10 pushups" başlıkta kalsın: iki nokta, am/pm ya da önünde "at" gerekir
            if ta and tb and ta < tb and (":" in w or "m" in w or (i > 0 and low[i - 1] == "at")):
                time, end = ta, tb
                take(i)
        elif _time(w) or (i > 0 and low[i - 1] == "at" and _time(w, need_colon=False)):
            time = _time(w, need_colon=False)
            take(i)
        # --- öncelik / kategori / proje
        elif re.match(r"^!+(high|h|low|l)?$", w) or w in ("p1", "p2", "p3"):
            out["priority"] = "low" if w.endswith(("low", "l")) or w == "p3" else \
                "normal" if w == "p2" else "high"
            take(i)
        elif w.startswith("#") and len(w) > 1:
            tag = w[1:]
            cat = CAT_TAGS.get(tag) or next((cid for cid, name in custom_cats if name.casefold() == tag), None)
            if cat:
                out["category"] = cat
                take(i)
        elif w.startswith("+") and len(w) > 1 and projects:
            p = next((pid for pid, name in projects if name.casefold().startswith(w[1:])), None)
            if p:
                out["project"] = p
                take(i)
        i += 1

    title = " ".join(tok for tok, u in zip(toks, used) if not u).strip(" ,-")
    out["title"] = title or raw
    if repeat and due is None:
        due = today
    if time and due is None:
        due = today
    out["due"] = due.isoformat() if due else None
    if time:
        out["time"] = time
    if end:
        out["end"] = end
    if repeat:
        out["repeat"] = repeat
    return "tasks", out


def _expense(toks, today):
    from .budget import EXPENSE_CATS
    amount, rest = None, []
    for tk in toks:
        v = tk.replace("₺", "").replace("tl", "").replace("TL", "").replace(",", ".")
        if amount is None and re.match(r"^\d+(\.\d+)?$", v):
            amount = float(v)
        else:
            rest.append(tk)
    cat = "Diğer"
    note = rest
    if rest:
        first = rest[0].casefold()
        hit = next((c for c in EXPENSE_CATS if c.casefold().startswith(first) or first in _EXP_WORDS.get(c, ())),
                   None)
        if hit:
            cat, note = hit, rest[1:]
    return "transactions", {"kind": "expense", "amount": amount or 0.0, "category": cat, "date": today.isoformat(),
                            "note": " ".join(note)}


_EXP_WORDS = {
    "Market": ("grocery", "groceries", "market", "supermarket"), "Dışarıda yemek": ("food", "lunch", "dinner",
    "restaurant", "breakfast", "eat"), "Kahve": ("coffee", "cafe", "tea"), "Akaryakıt": ("fuel", "gas", "petrol"),
    "Otopark": ("parking",), "Toplu taşıma": ("bus", "metro", "taxi", "transit", "uber"), "Kira": ("rent",),
    "Faturalar": ("bill", "bills", "electricity", "water", "internet", "phone"), "Abonelik": ("subscription",),
    "Eğlence": ("movie", "cinema", "concert", "fun", "bar", "game"), "Seyahat": ("travel", "trip", "hotel",
    "flight"), "Giyim": ("clothes", "shoes"), "Elektronik": ("electronics", "tech"), "Sağlık": ("pharmacy",
    "doctor", "medicine"), "Spor": ("gym",), "Kitap": ("book", "books"), "Hediye": ("gift",),
    "Kişisel bakım": ("haircut", "barber", "cosmetics"), "Eğitim": ("course", "tuition"),
}


def next_due(repeat, due, today):
    """Tekrarlayan görevin bir sonraki tarihi: due'dan ileri adım at, bugünü geçene dek."""
    d = due or today

    def step(x):
        if repeat == "daily":
            return x + timedelta(days=1)
        if repeat == "weekdays":
            x += timedelta(days=1)
            while x.weekday() > 4:
                x += timedelta(days=1)
            return x
        if repeat == "weekly":
            return x + timedelta(days=7)
        if repeat == "monthly":
            y, m = (x.year + 1, 1) if x.month == 12 else (x.year, x.month + 1)
            return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
        if repeat and repeat.startswith("w:"):
            wds = {int(c) for c in repeat[2:].split(",") if c.isdigit()}
            if not wds:
                return x + timedelta(days=7)
            x += timedelta(days=1)
            while x.weekday() not in wds:
                x += timedelta(days=1)
            return x
        return None
    nd = step(d)
    while nd is not None and nd <= today:
        nd = step(nd)
    return nd


def repeat_label(repeat, t):
    """"her gün" / "her Pzt, Çar" … (t = i18n.t)."""
    if not repeat:
        return ""
    if repeat in REPEATS:
        return t("rep_" + repeat)
    if repeat.startswith("w:"):
        from .i18n import WEEKDAYS_SHORT
        names = WEEKDAYS_SHORT()
        return t("rep_days", d=", ".join(names[int(c)] for c in repeat[2:].split(",") if c.isdigit()))
    return repeat


def parse_for(store, text, default_cat="personal"):
    """parse() + kullanıcının projeleri ve özel kategorileri."""
    from .config import day_today, prefs
    projects = [(p["id"], p.get("name") or "") for p in store.all("projects") if p.get("status") != "done"]
    cats = [(c["id"], c.get("name") or "") for c in (prefs.get("custom_cats") or []) if c.get("id")]
    return parse(text, day_today(), default_cat, projects, cats)
