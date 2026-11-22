"""Besin kütüphanesi (foods koleksiyonu) ve gramdan öğün hesabı. Arayüzden bağımsız: komut satırı (cli.py) ve
Spor sayfası aynı fonksiyonları kullanır.

foods kaydı: name, kcal, protein, carbs, fat (100 g başına), unit (ör. "ölçek", "adet", "dilim"), unit_g (bir birim kaç
gram), aliases [başka adlar], note (ör. "çiğ ağırlık"), src (değerin kaynağı, ör. diyetkolik bağlantısı).
Öğün kaydı (meals): name ("Pirinç (çiğ) · 200 g"), date, kcal, protein, carbs, fat, food (besin id), grams.
"""
import re

MACROS = ("kcal", "protein", "carbs", "fat")


def _key(s):
    return " ".join((s or "").replace("İ", "i").casefold().replace("ı", "i").split())


def aliases(f):
    a = f.get("aliases") or []
    return [x.strip() for x in (a.split(",") if isinstance(a, str) else a) if str(x).strip()]


def find_food(store, name):
    """Ad / takma adla besin. → (besin | None, adaylar). Tam eşleşme önce; yoksa adı içeren tek besin."""
    k = _key(name)
    if not k:
        return None, []
    foods = store.all("foods")
    for f in foods:
        if _key(f.get("name")) == k or k in (_key(a) for a in aliases(f)):
            return f, [f]
    cands = [f for f in foods if k in _key(f.get("name")) or any(k in _key(a) for a in aliases(f))]
    if len(cands) == 1:
        return cands[0], cands
    words = k.split()
    if not cands and len(words) > 1:
        cands = [f for f in foods if all(w in _key(f.get("name")) for w in words)]
        if len(cands) == 1:
            return cands[0], cands
    return None, cands


_AMOUNT = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*([^\d\s][\w.]*)?\s*$")


def parse_amount(text, food):
    """ "200", "200g", "200 gr", "2 ölçek", "1,5" (birim tanımlıysa birim, değilse gram) → (gram, etiket).
    Tanınmayan birim ValueError."""
    m = _AMOUNT.match(str(text or ""))
    if not m:
        raise ValueError(f"miktar okunamadı: {text!r}")
    qty = float(m.group(1).replace(",", "."))
    unit = (m.group(2) or "").casefold().rstrip(".")
    fu = (food.get("unit") or "").casefold()
    if unit in ("g", "gr", "gram"):
        return qty, f"{_n(qty)} g"
    if unit in ("kg",):
        return qty * 1000, f"{_n(qty)} kg"
    if unit in ("ml",):
        return qty, f"{_n(qty)} ml"
    if not unit:
        if fu and food.get("unit_g") and qty < 20:        # "2" → 2 ölçek (birim tanımlıysa küçük sayılar birimdir)
            return qty * float(food["unit_g"]), f"{_n(qty)} {food['unit']}"
        return qty, f"{_n(qty)} g"
    if fu and (unit == fu or fu.startswith(unit) or unit.startswith(fu)) and food.get("unit_g"):
        return qty * float(food["unit_g"]), f"{_n(qty)} {food['unit']}"
    raise ValueError(f"birim tanınmadı: {unit!r} (besinin birimi: {food.get('unit') or 'yok, gram yaz'})")


def _n(v):
    return str(int(v)) if float(v).is_integer() else str(round(v, 2)).replace(".", ",")


def macros_for(food, grams):
    """grams gram besinin kalori / makroları (100 g değerlerinden)."""
    r = grams / 100.0
    return {k: round(float(food.get(k) or 0) * r, 1) for k in MACROS}


def meal_from(food, amount_text, date_iso):
    grams, label = parse_amount(amount_text, food)
    m = {"name": f"{food['name']} · {label}", "date": date_iso, "food": food["id"], "grams": round(grams, 1)}
    m.update(macros_for(food, grams))
    return m


def totals(meals):
    out = {k: 0.0 for k in MACROS}
    for m in meals:
        for k in MACROS:
            try:
                out[k] += float(m.get(k) or 0)
            except (TypeError, ValueError):
                pass
    return {k: round(v, 1) for k, v in out.items()}
