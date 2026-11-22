"""Bütçe: gider kategorileri gruplar halinde + grup başına aylık tavan (prefs "budgets" {grup: TL}).

Kayıtta kategori alt başlığın adı durur ("Akaryakıt"); grubu group_of() bulur. Eski / elle yazılmış adlar da bir
gruba düşer (ör. "Yemek" → food, "Ulaşım" → transport), bulunamayan → other.
Abonelikler sabit giderlerden (recurring, kategori "Abonelik") okunur: aylık toplam + yıllık karşılık + yenilenme günü.
"""
from datetime import date

from .config import prefs
from .store import parse_date, num

# (anahtar, alt kategoriler) — formdaki gider kategorisi listesi bu sırayla
GROUPS = (
    ("food", ("Market", "Dışarıda yemek", "Kahve")),
    ("transport", ("Akaryakıt", "Otopark", "Toplu taşıma", "Araç bakımı")),
    ("home", ("Kira", "Faturalar", "Ev eşyası")),
    ("subs", ("Abonelik",)),
    ("fun", ("Hobi", "Eğlence", "Seyahat")),
    ("shopping", ("Giyim", "Elektronik", "Kişisel bakım")),
    ("health", ("Sağlık", "Spor", "Takviye")),
    ("edu", ("Eğitim", "Kitap")),
    ("other", ("Hediye", "Diğer")),
)
EXPENSE_CATS = tuple(c for _g, cats in GROUPS for c in cats)
# eski / serbest yazılmış adlar → grup
_ALIAS = {"yemek": "food", "ulaşım": "transport", "araba": "transport", "benzin": "transport", "ev": "home",
          "kafe": "food", "restoran": "food", "fatura": "home", "oyun": "fun", "tatil": "fun", "otel": "fun"}
WARN = 0.8          # tavanın %80'i → uyarı


def group_of(cat):
    c = (cat or "").strip().casefold()
    for g, cats in GROUPS:
        if any(c == x.casefold() for x in cats):
            return g
    for k, g in _ALIAS.items():
        if k in c:
            return g
    return "other"


def caps():
    """{grup: aylık tavan} (yalnızca > 0 olanlar)."""
    raw = prefs.get("budgets") or {}
    return {g: num(v) for g, v in raw.items() if num(v) > 0}


def set_cap(group, value):
    raw = dict(prefs.get("budgets") or {})
    if value and num(value) > 0:
        raw[group] = round(num(value), 2)
    else:
        raw.pop(group, None)
    prefs.set("budgets", raw)


def spent(store, y, m):
    """{grup: bu ay harcanan} — yalnızca gider hareketleri."""
    out = {}
    for tr in store.all("transactions"):
        if tr.get("kind") == "income":
            continue
        d = parse_date(tr.get("date"))
        if d and (d.year, d.month) == (y, m):
            g = group_of(tr.get("category"))
            out[g] = out.get(g, 0.0) + num(tr.get("amount"))
    return out


def status(store, td):
    """[(grup, harcanan, tavan, oran, beklenen_oran)] — tavanı ya da harcaması olan gruplar, GROUPS sırasıyla.
    beklenen_oran = ayın geçen kısmı (bugün 15/30 → 0.5): çizginin önündeysen hızlı harcıyorsun."""
    import calendar
    sp, cp = spent(store, td.year, td.month), caps()
    days = calendar.monthrange(td.year, td.month)[1]
    pace = td.day / days
    out = []
    for g, _cats in GROUPS:
        if g == "subs":
            continue                      # abonelikler ayrı kartta (sabit gider)
        s, c = sp.get(g, 0.0), cp.get(g, 0.0)
        if s or c:
            out.append((g, s, c, (s / c) if c else None, pace))
    return out


def alerts(store, td):
    """Tavanın %80'ini geçen gruplar: [(grup, harcanan, tavan, oran)]."""
    return [(g, s, c, r) for g, s, c, r, _p in status(store, td) if r is not None and r >= WARN]


def subscriptions(store):
    """Etkin abonelikler: [(kayıt, aylık tutar)], tutara göre azalan."""
    out = [(r, num(r.get("amount"))) for r in store.all("recurring")
           if r.get("kind") != "income" and r.get("active") is not False and group_of(r.get("category")) == "subs"]
    return sorted(out, key=lambda x: -x[1])


def next_renewal(r, td):
    """Aboneliğin bir sonraki yenilenme günü (ayın day'i; yoksa 1)."""
    import calendar
    day = int(num(r.get("day")) or 1)
    y, m = td.year, td.month
    for _ in range(2):
        d = date(y, m, min(day, calendar.monthrange(y, m)[1]))
        if d >= td:
            return d
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return d
