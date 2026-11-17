"""Türkçe / İngilizce metinler ve tarih / para biçimleri. t("anahtar", **biçim) ile kullanılır."""
import json
import os
from datetime import date, datetime

from .config import day_today
from .config import prefs

# Metinler alphaapp/locales/<dil>.json'da (anahtar → metin). Türkçede olup İngilizcede olmayan anahtar Türkçe görünür.
# Yeni dil: locales/xx.json ekle (tr.json'un kopyası) + t() içindeki dil seçimi.
_LOCALES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")


def _load(lang):
    try:
        with open(os.path.join(_LOCALES, lang + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


_TR, _EN = _load("tr"), _load("en")
S = {k: (v, _EN.get(k, v)) for k, v in _TR.items()}


def apply_locale():
    """Tarih seçicilerde ay / gün adları seçilen dilde olsun (pencereler oluşmadan çağır)."""
    from PyQt6.QtCore import QLocale
    if _tr():
        QLocale.setDefault(QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey))
    else:
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))


def t(key, **kw):
    v = S.get(key)
    # Menüyü düzenle: kullanıcının verdiği adlar (nav_names) menüde, sayfa başlığında ve kategori adlarında kullanılır;
    # eklenen kategoriler (custom_cats) yalnızca adla gelir.
    if not kw and key[:4] in ("nav_", "cat_"):
        name = (prefs.get("nav_names") or {}).get(key[4:])
        if name:
            return name
        if v is None:
            for c in prefs.get("custom_cats") or []:
                if c.get("id") == key[4:]:
                    return c.get("name") or key
            if key[:4] == "cat_":
                v = S["cat_personal"]
    if v is None:
        return key
    s = v[0] if prefs.get("language", "tr") == "tr" else v[1]
    return s.format(**kw) if kw else s


def _tr():
    return prefs.get("language", "tr") == "tr"


def WEEKDAYS_SHORT():
    return ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if _tr() else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
                                                                          "Sun"]


def WEEKDAYS_LONG():
    return (["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"] if _tr() else
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])


def MONTHS_SHORT():
    return (["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"] if _tr() else
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])


def MONTHS_LONG():
    return (["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
             "Aralık"] if _tr() else
            ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"])


# ------------------------------------------------------------ biçimler
def fmt_num(v, digits=2):
    """Türkçe ondalık (virgül), gereksiz sıfırlar atılır."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{f:,.{digits}f}"
    if digits:
        s = s.rstrip("0").rstrip(".")
    if _tr():
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def fmt_money(v, sign=False):
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        f = 0.0
    cur = prefs.get("currency", "₺") or ""
    body = fmt_num(abs(f), 2)
    if "," in body and _tr():
        a, b = body.split(",")
        body = a + "," + b.ljust(2, "0")
    elif "." in body and not _tr():
        a, b = body.split(".")
        body = a + "." + b.ljust(2, "0")
    pre = ("+" if f > 0 else "−" if f < 0 else "") if sign else ("−" if f < 0 else "")
    if cur in ("₺", "TL"):
        return f"{pre}{body} {cur}"
    return f"{pre}{cur}{body}"


def fmt_day_month(d: date, short=False):
    if short:
        return f"{d.day} {MONTHS_SHORT()[d.month - 1]}"
    return f"{d.day} {MONTHS_SHORT()[d.month - 1]}"


def fmt_month(y, m):
    return f"{MONTHS_LONG()[m - 1]} {y}"


def fmt_long_date(d: date):
    return f"{d.day} {MONTHS_LONG()[d.month - 1]} {d.year}, {WEEKDAYS_LONG()[d.weekday()]}"


def fmt_day(d: date):
    """Göreli kısa tarih: Bugün · Yarın · Dün · Cuma (bu hafta içi) · 14 Kas · 14 Kas 2027."""
    if d is None:
        return ""
    td = day_today()
    diff = (d - td).days
    if diff == 0:
        return t("today")
    if diff == 1:
        return t("tomorrow")
    if diff == -1:
        return t("yesterday")
    if 1 < diff < 7:
        return WEEKDAYS_LONG()[d.weekday()]
    s = f"{d.day} {MONTHS_SHORT()[d.month - 1]}"
    if d.year != td.year:
        s += f" {d.year}"
    return s


def due_badge(d: date):
    """(metin, tür) — geciken kırmızı, bugün/yarın kırmızı-turuncu, 3 güne kadar turuncu."""
    diff = (d - day_today()).days
    if diff < 0:
        return t("overdue_n", n=-diff), "bad"
    if diff == 0:
        return t("today"), "bad"
    if diff == 1:
        return t("tomorrow"), "warn"
    if diff <= 3:
        return t("in_n_days", n=diff), "warn"
    return t("in_n_days", n=diff), None


def fmt_stamp(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    d = dt.date()
    hm = dt.strftime("%H:%M")
    diff = (day_today() - d).days
    if diff == 0:
        return f"{t('today')} {hm}"
    if diff == 1:
        return f"{t('yesterday')} {hm}"
    return fmt_day(d)


def is_tr():
    return _tr()
