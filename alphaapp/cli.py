"""Komut satırı kapısı: kayıt ekle / oku / güncelle. Claude'un alpha'yı az token'la kullanması için yazıldı.

Uygulama açıksa istek çalışan alpha'ya gider (tek örnek sunucusu, aynı veri klasörü) ve onun deposunda çalışır:
açık pencerenin kaydı ezilmez, ekran hemen yenilenir. Kapalıysa data.json doğrudan açılıp kaydedilir.

    python -m alphaapp.cli <komut> ...          (proje klasöründen; çıktı UTF-8, kısa)

  ping                               alpha açık mı (açıksa istekler ona gider)
  colls                              koleksiyonlar ve alanları
  day [T]                            günün özeti: öğünler / hedef, antrenman, uyku, kilo, görevler, alışkanlıklar
  list <coll> [--date T] [--from T] [--to T] [--where k=v]... [--q metin] [--fields a,b] [--limit N]
  get <coll> <id>
  add <coll> k=v ...  |  add <coll> --json '{...}'
  set <coll> <id> k=v ...            alanları günceller (id yerine benzersiz ad / başlık da olur)
  del <coll> <id>
  meal "besin:miktar" ... [--date T] besin kütüphanesinden: "pirinç:200" "tavuk göğsü:400" "protein tozu:2 ölçek"
  food list [metin]
  food add "<ad>" kcal= protein= carbs= fat= [unit= unit_g= aliases= note= src=]   (100 g değerleri)
  food set <ad|id> k=v ...  |  food del <ad|id>
  habit <ad> [T] [--off] [--half]    alışkanlığı işaretle (varsayılan: bugün, tam)

T (tarih): bugün / today, dün, yarın, -1, +3, 2026-11-17, 17.11.2026. Değerler: sayı, true/false, null, [..] / {..} JSON;
days / aliases / links / people alanlarında "a,b" listeye çevrilir.
"""
import json
import re
import sys
from datetime import date, timedelta

DATE_KEYS = {"date", "due", "start", "until", "from", "started", "finished", "done_date", "bought_at"}
LIST_KEYS = {"days", "aliases", "links", "people", "half", "slips", "genres"}
HIDE = {"created"}


class CliError(Exception):
    pass


# ============================================================ değer ayrıştırma
def parse_day(s, today=None):
    from .config import day_today
    td = today or day_today()
    w = str(s or "").strip().casefold()
    if w in ("", "bugün", "bugun", "today"):
        return td
    if w in ("dün", "dun", "yesterday"):
        return td - timedelta(days=1)
    if w in ("yarın", "yarin", "tomorrow"):
        return td + timedelta(days=1)
    if re.fullmatch(r"[+-]\d+", w):
        return td + timedelta(days=int(w))
    m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", w)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    try:
        return date.fromisoformat(w)
    except ValueError:
        raise CliError(f"tarih okunamadı: {s!r}")


def parse_value(key, v):
    if key in DATE_KEYS:
        return None if v.lower() in ("", "null", "none") else parse_day(v).isoformat()
    lv = v.strip().lower()
    if lv in ("true", "evet"):
        return True
    if lv in ("false", "hayır", "hayir"):
        return False
    if lv in ("null", "none"):
        return None
    if v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            raise CliError(f"{key}: JSON okunamadı")
    if key in LIST_KEYS:
        return [x.strip() for x in v.split(",") if x.strip()]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+[.,]\d+", v):
        return float(v.replace(",", "."))
    return v


def parse_fields(pairs):
    out = {}
    for p in pairs:
        if "=" not in p:
            raise CliError(f"k=v bekleniyordu: {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = parse_value(k.strip(), v)
    return out


def take_opts(args, flags=("--off", "--half", "--all"), valued=("--date", "--from", "--to", "--q", "--fields",
                                                                  "--limit", "--json")):
    """--x değer / --bayrak seçeneklerini ayırır; --where tekrarlanabilir. → (konumsal, seçenekler)"""
    pos, opt = [], {"where": []}
    i = 0
    while i < len(args):
        a = args[i]
        if a in flags:
            opt[a[2:]] = True
        elif a == "--where" and i + 1 < len(args):
            opt["where"].append(args[i + 1])
            i += 1
        elif a in valued and i + 1 < len(args):
            opt[a[2:]] = args[i + 1]
            i += 1
        elif a.startswith("--") and "=" in a and a.split("=", 1)[0] in valued:
            k, v = a[2:].split("=", 1)
            opt[k] = v
        else:
            pos.append(a)
        i += 1
    return pos, opt


# ============================================================ çıktı
def dump(x):
    if isinstance(x, dict):
        x = {k: v for k, v in x.items() if k not in HIDE and v not in (None, "", [], {})}
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def _coll(store, name):
    if name not in store.data:
        raise CliError(f"koleksiyon yok: {name!r} (colls ile listele)")
    return name


def _resolve(store, coll, ref):
    """id ya da benzersiz ad / başlık → kayıt."""
    x = store.get(coll, ref)
    if x is not None:
        return x
    k = ref.casefold().strip()
    hits = [i for i in store.all(coll) if any(str(i.get(f) or "").casefold().strip() == k
                                              for f in ("name", "title", "person"))]
    if not hits:
        hits = [i for i in store.all(coll) if any(k in str(i.get(f) or "").casefold()
                                                  for f in ("name", "title", "person"))]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise CliError(f"{coll}: bulunamadı: {ref!r}")
    raise CliError(f"{coll}: birden çok eşleşme: " + "; ".join(f"{h['id']} {h.get('name') or h.get('title')}"
                                                                for h in hits[:8]))


def _date_of(x):
    return str(x.get("date") or x.get("due") or "")


# ============================================================ komutlar
def cmd_colls(store, args):
    from . import store as st
    doc = st.__doc__ or ""
    lines = [l for l in doc.splitlines() if re.match(r"^  \w", l) or re.match(r"^\s{15,}\S", l)]
    return "\n".join(l.rstrip() for l in lines)


def cmd_list(store, args):
    pos, opt = take_opts(args)
    if not pos:
        raise CliError("list <coll>")
    coll = _coll(store, pos[0])
    items = list(store.all(coll))
    if "date" in opt:
        d = parse_day(opt["date"]).isoformat()
        items = [x for x in items if _date_of(x)[:10] == d]
    if "from" in opt:
        a = parse_day(opt["from"]).isoformat()
        items = [x for x in items if _date_of(x)[:10] >= a]
    if "to" in opt:
        b = parse_day(opt["to"]).isoformat()
        items = [x for x in items if _date_of(x)[:10] and _date_of(x)[:10] <= b]
    for w in opt["where"]:
        k, _, v = w.partition("=")
        want = parse_value(k, v)
        items = [x for x in items if x.get(k) == want or str(x.get(k)) == v]
    if opt.get("q"):
        q = opt["q"].casefold()
        items = [x for x in items if q in json.dumps(x, ensure_ascii=False).casefold()]
    if any(_date_of(x) for x in items):
        items.sort(key=_date_of)
    lim = int(opt.get("limit") or 50)
    more = len(items) - lim
    items = items[-lim:] if lim > 0 else items
    if opt.get("fields"):
        fs = ["id"] + [f for f in opt["fields"].split(",") if f != "id"]
        items = [{f: x.get(f) for f in fs} for x in items]
    out = [dump(x) for x in items]
    if more > 0:
        out.insert(0, f"# {more} eski kayıt gizli (--limit / --from)")
    return "\n".join(out) or "# boş"


def cmd_get(store, args):
    if len(args) < 2:
        raise CliError("get <coll> <id>")
    return dump(_resolve(store, _coll(store, args[0]), args[1]))


def cmd_add(store, args):
    pos, opt = take_opts(args)
    if not pos:
        raise CliError("add <coll> k=v ...")
    coll = _coll(store, pos[0])
    data = json.loads(opt["json"]) if opt.get("json") else {}
    data.update(parse_fields(pos[1:]))
    if not data:
        raise CliError("boş kayıt")
    if coll in ("meals", "body", "sleep", "workouts", "lifts", "transactions", "sessions") and not data.get("date"):
        data["date"] = parse_day("").isoformat()
    if coll == "exams":
        x, _before = store.add_exam(data)
    else:
        x = store.add(coll, data)
    return "+ " + dump(x)


def cmd_set(store, args):
    if len(args) < 3:
        raise CliError("set <coll> <id> k=v ...")
    coll = _coll(store, args[0])
    x = _resolve(store, coll, args[1])
    store.update(coll, x["id"], **parse_fields(args[2:]))
    return "~ " + dump(store.get(coll, x["id"]))


def cmd_del(store, args):
    if len(args) < 2:
        raise CliError("del <coll> <id>")
    coll = _coll(store, args[0])
    x = _resolve(store, coll, args[1])
    store.delete(coll, x["id"])
    return "- " + dump({"id": x["id"], "name": x.get("name") or x.get("title")})


def cmd_meal(store, args):
    from . import nutrition as nu
    pos, opt = take_opts(args)
    if not pos:
        raise CliError('meal "besin:miktar" ...')
    d = parse_day(opt.get("date", "")).isoformat()
    made, errs = [], []
    plan = []
    for p in pos:
        name, sep, amt = p.rpartition(":")
        if not sep:
            m = re.match(r"^(.*?)\s+(\d+(?:[.,]\d+)?\s*\S*)$", p.strip())
            if not m:
                errs.append(f"{p!r}: 'besin:miktar' yaz")
                continue
            name, amt = m.group(1), m.group(2)
        f, cands = nu.find_food(store, name)
        if f is None:
            errs.append(f"{name!r}: kütüphanede yok" if not cands else
                        f"{name!r}: belirsiz → " + ", ".join(c["name"] for c in cands[:6]))
            continue
        try:
            plan.append(nu.meal_from(f, amt, d))
        except ValueError as e:
            errs.append(f"{name!r}: {e}")
    if errs:                                   # yarım öğün yazma: önce hepsi doğru olsun
        raise CliError("öğün eklenmedi:\n  " + "\n  ".join(errs))
    for m in plan:
        made.append(store.add("meals", m))
    tot = nu.totals(store.meals_on(parse_day(d)))
    lines = [f"+ {m['name']}: {m['kcal']:g} kcal P{m['protein']:g} K{m['carbs']:g} Y{m['fat']:g}" for m in made]
    lines.append(_food_line(tot))
    return "\n".join(lines)


def _food_line(tot):
    from .config import prefs

    def g(k):
        v = prefs.get("goal_" + k)
        return f"/{float(v):g}" if v else ""
    return (f"gün: {tot['kcal']:g}{g('kcal')} kcal · P {tot['protein']:g}{g('protein')} · "
            f"K {tot['carbs']:g}{g('carbs')} · Y {tot['fat']:g}{g('fat')}")


def cmd_food(store, args):
    from . import nutrition as nu
    if not args or args[0] == "list":
        q = " ".join(args[1:]).casefold()
        rows = [f for f in store.all("foods") if not q or q in nu._key(f.get("name")) or
                any(q in nu._key(a) for a in nu.aliases(f))]
        rows.sort(key=lambda f: nu._key(f.get("name")))
        return "\n".join(f"{f['id']} {f['name']}: {float(f.get('kcal') or 0):g} kcal P{float(f.get('protein') or 0):g} "
                         f"K{float(f.get('carbs') or 0):g} Y{float(f.get('fat') or 0):g} /100g"
                         + (f" · 1 {f['unit']}={float(f['unit_g']):g}g" if f.get("unit") and f.get("unit_g") else "")
                         + (f" · ({', '.join(nu.aliases(f))})" if nu.aliases(f) else "")
                         for f in rows) or "# besin yok"
    op = args[0]
    if op == "add":
        if len(args) < 2:
            raise CliError('food add "<ad>" kcal= protein= carbs= fat=')
        name = args[1]
        f0, _c = nu.find_food(store, name)
        if f0 is not None and nu._key(f0["name"]) == nu._key(name):
            raise CliError(f"zaten var: {f0['id']} {f0['name']} (food set ile güncelle)")
        data = {"name": name} | parse_fields(args[2:])
        for k in ("kcal", "protein", "carbs", "fat"):
            if not isinstance(data.get(k), (int, float)):
                raise CliError(f"{k}= (100 g başına sayı) gerekli")
        return "+ " + dump(store.add("foods", data))
    if op in ("set", "del"):
        if len(args) < 2:
            raise CliError(f"food {op} <ad|id>")
        f = store.get("foods", args[1]) or nu.find_food(store, args[1])[0]
        if f is None:
            raise CliError(f"besin bulunamadı: {args[1]!r}")
        if op == "del":
            store.delete("foods", f["id"])
            return f"- {f['id']} {f['name']}"
        store.update("foods", f["id"], **parse_fields(args[2:]))
        return "~ " + dump(store.get("foods", f["id"]))
    raise CliError("food list | add | set | del")


def cmd_habit(store, args):
    from . import habits_core as hc
    pos, opt = take_opts(args)
    if not pos:
        return "\n".join(f"{h['id']} {h.get('name')}" for h in store.all("habits")) or "# alışkanlık yok"
    h = _resolve(store, "habits", pos[0])
    d = parse_day(pos[1] if len(pos) > 1 else "")
    iso = d.isoformat()
    if opt.get("half") and not hc.is_quit(h):
        days = [x for x in (h.get("days") or []) if x != iso]
        half = sorted(set(h.get("half") or []) | {iso})
        store.update("habits", h["id"], days=days, half=half)
    else:
        hc.set_today(store, h, d, not opt.get("off"))
    v = hc.state(store.get("habits", h["id"]), d, store) or 0
    return f"{h.get('name')} {iso}: " + ("tam" if v >= 1 else "yarım" if v > 0 else "boş")


def cmd_day(store, args):
    from . import habits_core as hc
    from . import nutrition as nu
    from .store import num
    d = parse_day(args[0] if args else "")
    iso = d.isoformat()
    out = [f"# {iso}"]
    meals = store.meals_on(d)
    if meals:
        out.append(_food_line(nu.totals(meals)))
        out.append("öğünler: " + " | ".join(m.get("name", "") for m in meals))
    else:
        out.append("öğün yok")
    for w in [w for w in store.all("workouts") if w.get("date") == iso]:
        ex = w.get("exercises") or []
        out.append(f"antrenman: {w.get('kind') or w.get('focus') or ''} {w.get('name') or ''} · {len(ex)} hareket"
                   + (f" · {w['minutes']} dk" if w.get("minutes") else ""))
    for s in [s for s in store.all("sleep") if s.get("date") == iso]:
        out.append(f"uyku: {s.get('bed')}–{s.get('wake')}" + (f" · kalite {s['quality']}" if s.get("quality") else ""))
    for b in [b for b in store.all("body") if b.get("date") == iso]:
        out.append("vücut: " + " · ".join(f"{k} {b[k]}" for k in ("weight", "fat", "waist") if b.get(k)))
    rt = store.routine_for(d)
    if rt:
        out.append("program: " + " | ".join(f"{r.get('start') or ''} {r.get('title', '')}".strip() for r in rt))
    tasks = [t for t in store.all("tasks") if not t.get("done") and t.get("due") and t["due"] <= iso]
    if tasks:
        out.append("görevler: " + " | ".join(("! " if t["due"] < iso else "") + t.get("title", "") for t in tasks[:15]))
    hs = store.all("habits")
    if hs:
        marks = []
        for h in hs:
            v = hc.state(h, d, store) or 0
            marks.append(f"{h.get('name')} {'✓' if v >= 1 else '½' if v > 0 else '·'}")
        out.append("alışkanlıklar: " + " | ".join(marks))
    sess = [s for s in store.all("sessions") if s.get("date") == iso]
    if sess:
        mins = sum(num(s.get("minutes")) for s in sess if s.get("kind") == "study")
        if mins:
            out.append(f"ders çalışma: {mins / 60:.1f} sa")
    return "\n".join(out)


def cmd_ping(store, args):
    import os
    from . import __version__
    from PyQt6.QtWidgets import QApplication
    where = "açık uygulama" if isinstance(QApplication.instance(), QApplication) else "dosya (alpha kapalı)"
    return f"alpha {__version__} · {where} · pid {os.getpid()}"


COMMANDS = {"ping": cmd_ping, "colls": cmd_colls, "list": cmd_list, "get": cmd_get, "add": cmd_add, "set": cmd_set, "del": cmd_del,
            "meal": cmd_meal, "food": cmd_food, "habit": cmd_habit, "day": cmd_day}


def run(store, argv):
    """Komutu verilen depoda çalıştırır → (çıkış kodu, metin). Uygulama içinden de çağrılır."""
    if not argv or argv[0] in ("-h", "--help", "help"):
        return 0, __doc__.strip()
    fn = COMMANDS.get(argv[0])
    if fn is None:
        return 2, f"bilinmeyen komut: {argv[0]!r} (help)"
    try:
        return 0, fn(store, list(argv[1:]))
    except CliError as e:
        return 1, f"hata: {e}"
    except (KeyError, ValueError, TypeError) as e:
        return 1, f"hata: {type(e).__name__}: {e}"


# ============================================================ çalışan uygulamayla konuşma
def handle_request(store, raw: bytes) -> bytes:
    """app.py sunucusu: {"cli": [...]} → {"code": n, "out": "..."} (tek satır JSON)."""
    try:
        req = json.loads(raw.decode("utf-8"))
        code, text = run(store, req.get("cli") or [])
    except Exception as e:  # noqa: BLE001  (sunucu asla düşmesin)
        code, text = 1, f"hata: {type(e).__name__}: {e}"
    return (json.dumps({"code": code, "out": text}, ensure_ascii=False) + "\n").encode("utf-8")


def _via_running(argv):
    """Açık alpha'ya gönder. → (kod, metin) ya da bağlanamazsa None."""
    from PyQt6.QtNetwork import QLocalSocket
    from .app import SERVER_NAME
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if not sock.waitForConnected(400):
        return None
    sock.write((json.dumps({"cli": argv}, ensure_ascii=False) + "\n").encode("utf-8"))
    sock.flush()
    buf = b""
    for _ in range(100):                       # en fazla ~10 sn
        if sock.waitForReadyRead(100):
            buf += bytes(sock.readAll())
            if buf.endswith(b"\n"):
                break
        elif sock.state() != QLocalSocket.LocalSocketState.ConnectedState:
            buf += bytes(sock.readAll())
            break
    sock.disconnectFromServer()
    if not buf.strip():
        return 1, "hata: açık alpha komutu tanımadı (eski sürüm). Uygulamayı kapatıp yeniden dene ya da güncelle."
    try:
        r = json.loads(buf.decode("utf-8"))
        return int(r.get("code", 1)), r.get("out", "")
    except ValueError:
        return 1, "hata: yanıt okunamadı"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    from PyQt6.QtCore import QCoreApplication
    main.app = QCoreApplication.instance() or QCoreApplication([sys.argv[0]])   # Qt soketleri / zamanlayıcıları için
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    r = _via_running(argv)
    if r is None:                              # alpha kapalı: dosyayı kendimiz açıp kaydederiz
        from .store import Store
        store = Store()
        r = run(store, argv)
        store.flush()
    code, text = r
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
