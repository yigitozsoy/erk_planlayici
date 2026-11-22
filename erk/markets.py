"""Anlık piyasa fiyatları (TL): döviz, altın / gümüş, kripto, BIST ve yabancı hisseler.

Kaynak: Yahoo Finance grafik uç noktası (anahtarsız, ~anlık). Kurlar alınamazsa ECB (frankfurter.app, günlük).
Fiyatlar prefs "prices"ta önbelleklenir {"t": iso, "q": {kod: {p, prev, ccy, raw, t}}}: internet yokken son
değerler gösterilir. Yalnızca sembol adları gönderilir; kişisel veri / miktar ASLA gitmez.

Yatırım kaydı (investments): asset (kod) + qty (adet / gram) varsa değeri = qty × anlık fiyat; yoksa elle girilen
value kullanılır. Kodlar: USD, EUR, GBP, CHF, GA (gram altın), CEYREK, GAG (gram gümüş), BTC, ETH ya da
herhangi bir Yahoo sembolü (THYAO.IS, AAPL …; nokta yoksa önce olduğu gibi, olmazsa .IS ile denenir).
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime

from .config import prefs
from .store import num

UA = "Mozilla/5.0 (erk)"
TIMEOUT = 10
OZ = 31.1034768                 # bir ons, gram
CEYREK_G = 1.6036               # çeyrek altın ≈ 1,75 g × 22 ayar (0,9163) saf altın

# kod → (tr ad, en ad, yahoo sembolü, çarpan, ons mu (USD/ons → TL/gram))
PRESETS = {
    "USD": ("Dolar", "US dollar", "USDTRY=X", 1.0, False),
    "EUR": ("Euro", "Euro", "EURTRY=X", 1.0, False),
    "GBP": ("Sterlin", "Pound", "GBPTRY=X", 1.0, False),
    "CHF": ("İsviçre frangı", "Swiss franc", "CHFTRY=X", 1.0, False),
    "GA": ("Gram altın", "Gold (gram)", "GC=F", 1.0, True),
    "CEYREK": ("Çeyrek altın", "Quarter gold", "GC=F", CEYREK_G, True),
    "GAG": ("Gram gümüş", "Silver (gram)", "SI=F", 1.0, True),
    "BTC": ("Bitcoin", "Bitcoin", "BTC-USD", 1.0, False),
    "ETH": ("Ethereum", "Ethereum", "ETH-USD", 1.0, False),
}
TICKER = ("USD", "EUR", "GA", "BTC")          # Ekonomi'deki fiyat şeridi


def label(code, tr=True):
    p = PRESETS.get((code or "").upper())
    return (p[0] if tr else p[1]) if p else (code or "")


def options(tr=True):
    """Formdaki seçenekler: "Gram altın (GA)" …"""
    return [f"{label(k, tr)} ({k})" for k in PRESETS]


def parse_code(text):
    """"Gram altın (GA)" → "GA", " thyao.is " → "THYAO.IS"."""
    s = (text or "").strip()
    if s.endswith(")") and "(" in s:
        s = s[s.rindex("(") + 1:-1]
    return s.strip().upper()


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def yahoo(symbol):
    """(fiyat, önceki kapanış, para birimi, zaman) ya da hata."""
    d = _get_json("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol)
                  + "?range=5d&interval=1d")
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        raise ValueError("no data")
    m = res[0]["meta"]
    p = m.get("regularMarketPrice")
    if p is None:
        raise ValueError("no price")
    return float(p), float(m.get("chartPreviousClose") or m.get("previousClose") or p), \
        (m.get("currency") or "USD").upper(), int(m.get("regularMarketTime") or time.time())


def _ecb_try(ccy):
    d = _get_json(f"https://api.frankfurter.app/latest?from={ccy}&to=TRY")
    v = float(d["rates"]["TRY"])
    return v, v, "TRY", int(time.time())


def fetch(codes, get=yahoo):
    """{kod: {p, prev, ccy, raw, t}} (TL) ve {kod: hata}. get: test için değiştirilebilir."""
    out, errs, fx = {}, {}, {"TRY": (1.0, 1.0)}

    def rate(ccy):
        ccy = ccy.upper()
        if ccy not in fx:
            try:
                p, prev, _c, _t = get(f"{ccy}TRY=X")
            except Exception:
                p, prev, _c, _t = _ecb_try(ccy)
            fx[ccy] = (p, prev)
        return fx[ccy]

    for code in dict.fromkeys(c.upper() for c in codes if c):
        try:
            pre = PRESETS.get(code)
            if pre:
                sym, mult, per_oz = pre[2], pre[3], pre[4]
                try:
                    raw, prev, ccy, ts = get(sym)
                except Exception:
                    if sym.endswith("TRY=X"):
                        raw, prev, ccy, ts = _ecb_try(code)
                    else:
                        raise
            else:
                sym, mult, per_oz = code, 1.0, False
                try:
                    raw, prev, ccy, ts = get(sym)
                except Exception:
                    if "." in code or "=" in code or "-" in code:
                        raise
                    raw, prev, ccy, ts = get(code + ".IS")
            if ccy == "GBP" and sym.endswith(".L"):      # Londra pens
                raw, prev, ccy = raw / 100, prev / 100, "GBP"
            r, rprev = rate(ccy)
            k = mult / OZ if per_oz else mult
            out[code] = {"p": raw * r * k, "prev": prev * rprev * k, "ccy": ccy, "raw": raw, "t": ts}
        except Exception as e:
            errs[code] = type(e).__name__
    return out, errs


# ---------------------------------------------------------------- önbellek
def cached():
    return (prefs.get("prices") or {}).get("q") or {}


def cache_time():
    t = (prefs.get("prices") or {}).get("t")
    try:
        return datetime.fromisoformat(t) if t else None
    except ValueError:
        return None


def remember(quotes):
    q = dict(cached())
    q.update(quotes)
    prefs.set("prices", {"t": datetime.now().isoformat(timespec="seconds"), "q": q})


def wanted(store):
    """Fiyatı gereken kodlar: şerit + yatırımlardaki semboller."""
    codes = list(TICKER)
    for x in store.all("investments"):
        c = parse_code(x.get("asset"))
        if c and c not in codes:
            codes.append(c)
    return codes


# ---------------------------------------------------------------- değerler
def live_value(x, quotes=None):
    """Yatırımın anlık TL değeri (asset + qty ve fiyat varsa) ya da None."""
    q = (quotes if quotes is not None else cached()).get(parse_code(x.get("asset")))
    qty = num(x.get("qty"))
    if not q or qty <= 0:
        return None
    return qty * q["p"]


def value_of(x, quotes=None):
    v = live_value(x, quotes)
    if v is not None:
        return v
    return num(x.get("value")) if x.get("value") not in (None, "") else num(x.get("invested"))


def day_change(x, quotes=None):
    """Bugünkü değişim (TL) ya da None."""
    q = (quotes if quotes is not None else cached()).get(parse_code(x.get("asset")))
    qty = num(x.get("qty"))
    if not q or qty <= 0:
        return None
    return qty * (q["p"] - q["prev"])


def net_worth(store, quotes=None):
    """dict(cash, invest, invested, owed, owe, total, day) — nakit + yatırımlar (anlık) + alacak − borç."""
    cash = sum(num(a.get("balance")) for a in store.all("accounts"))
    invest = invested = day = 0.0
    for x in store.all("investments"):
        invest += value_of(x, quotes)
        invested += num(x.get("invested"))
        dc = day_change(x, quotes)
        day += dc or 0.0
    owe, owed = store.debt_totals()
    return {"cash": cash, "invest": invest, "invested": invested, "owed": owed, "owe": owe,
            "total": cash + invest + owed - owe, "day": day}
