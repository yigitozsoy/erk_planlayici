"""Veri deposu: tüm kayıtlar tek JSON dosyasında (%LOCALAPPDATA%\\alpha\\data.json).

Koleksiyonlar (her kayıt bir dict, "id" alanı otomatik):
  tasks        yapılacaklar   title, category, due, time, priority, done, done_at, note
  routine      haftalık program title, category, days[0-6], start, end, place
  courses      dersler        name, code, credits, target (harf), note, study_days[iso] (çalışma kareleri)
  exams        sınav/ödev     course, name, date, weight, target, score
  workouts     antrenman      date, kind, focus, minutes, note
  projects     iş projeleri   name, status, due, progress, note
  events       sosyal plan    title, date, time, people, place, note
  birthdays    doğum günü     name, date (yıl önemsiz)
  transactions gelir/gider    date, kind(income|expense), amount, category, note
  debts        borç/alacak    person, direction(owe|owed), amount, due, settled, note
  investments  yatırım        name, kind, invested, value, date, note
  notes        notlar         title, body, category, pinned, updated
  days         günlük plan    date, intention, planned_at
  habits       alışkanlık     name, category, goal (haftada gün), note, days[iso]
  meals        beslenme       date, name, kcal, protein, carbs, fat
"""
import copy
import json
import os
import shutil
import uuid
from datetime import date, datetime, timedelta

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .config import DATA_FILE, BACKUP_DIR

COLLECTIONS = ("tasks", "routine", "courses", "exams", "workouts", "projects", "events", "birthdays",
               "transactions", "debts", "investments", "notes", "days", "habits", "meals")

CATEGORIES = ("education", "work", "sport", "social", "finance", "personal")


def today() -> date:
    return date.today()


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


class Store(QObject):
    changed = pyqtSignal(str)   # koleksiyon adı

    def __init__(self, path=DATA_FILE):
        super().__init__()
        self.path = path
        self.data = {c: [] for c in COLLECTIONS}
        self._load()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self.flush)
        self._dirty = False

    # ------------------------------------------------------------ dosya
    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            # bozuk dosyayı kenara al, boş başla
            try:
                shutil.copy2(self.path, self.path + f".broken-{datetime.now():%Y%m%d-%H%M%S}")
            except OSError:
                pass
            return
        if isinstance(loaded, dict):
            for c in COLLECTIONS:
                v = loaded.get(c)
                if isinstance(v, list):
                    self.data[c] = [x for x in v if isinstance(x, dict)]
        self._daily_backup()

    def _daily_backup(self):
        """Günde bir kez data.json'un kopyası (son 14 gün tutulur)."""
        try:
            name = f"data-{date.today():%Y-%m-%d}.json"
            dst = os.path.join(BACKUP_DIR, name)
            if not os.path.exists(dst) and os.path.exists(self.path):
                shutil.copy2(self.path, dst)
            olds = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("data-") and f.endswith(".json"))
            for f in olds[:-14]:
                os.remove(os.path.join(BACKUP_DIR, f))
        except OSError:
            pass

    def flush(self):
        if not self._dirty:
            return
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            self._dirty = False
        except OSError:
            pass

    def _touch(self, coll):
        self._dirty = True
        self._timer.start()
        self.changed.emit(coll)

    # ------------------------------------------------------------ CRUD
    def all(self, coll):
        return self.data[coll]

    def get(self, coll, item_id):
        for x in self.data[coll]:
            if x.get("id") == item_id:
                return x
        return None

    def add(self, coll, item):
        item = dict(item)
        item.setdefault("id", uuid.uuid4().hex[:12])
        item.setdefault("created", datetime.now().isoformat(timespec="seconds"))
        self.data[coll].append(item)
        self._touch(coll)
        return item

    def update(self, coll, item_id, **fields):
        x = self.get(coll, item_id)
        if x is None:
            return None
        x.update(fields)
        self._touch(coll)
        return x

    def delete(self, coll, item_id):
        """Silinen kaydı (ve dizindeki yerini) döndürür; restore() ile geri alınır."""
        lst = self.data[coll]
        for i, x in enumerate(lst):
            if x.get("id") == item_id:
                lst.pop(i)
                removed = [(coll, i, x)]
                if coll == "courses":   # dersin sınavları da gider
                    for j in range(len(self.data["exams"]) - 1, -1, -1):
                        e = self.data["exams"][j]
                        if e.get("course") == item_id:
                            self.data["exams"].pop(j)
                            removed.append(("exams", j, e))
                    self._touch("exams")
                self._touch(coll)
                return removed
        return []

    def restore(self, removed):
        for coll, i, x in reversed(removed):
            self.data[coll].insert(min(i, len(self.data[coll])), x)
            self._touch(coll)

    def snapshot(self):
        return copy.deepcopy(self.data)

    # ------------------------------------------------------------ sorgular
    # ------------------------------------------------------------ kareler (alışkanlık / ders çalışma)
    def toggle_day(self, coll, item_id, d, field="days"):
        """Kaydın gün listesinde d'yi açar/kapatır; yeni durumu (True = işaretli) döndürür."""
        x = self.get(coll, item_id)
        if x is None:
            return None
        key = d.isoformat()
        days = list(x.get(field) or [])
        on = key not in days
        if on:
            days.append(key)
            days.sort()
        else:
            days.remove(key)
        self.update(coll, item_id, **{field: days})
        return on

    def meals_on(self, d):
        key = d.isoformat()
        return [m for m in self.data["meals"] if m.get("date") == key]

    def meal_totals(self, d):
        out = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for m in self.meals_on(d):
            for k in out:
                out[k] += num(m.get(k))
        return out

    # ------------------------------------------------------------ günlük plan
    def day(self, d):
        """O günün plan kaydı ({date, intention, planned_at}) ya da None."""
        key = d.isoformat()
        for x in self.data["days"]:
            if x.get("date") == key:
                return x
        return None

    def set_day(self, d, **fields):
        x = self.day(d)
        if x is None:
            return self.add("days", dict(date=d.isoformat(), **fields))
        return self.update("days", x["id"], **fields)

    def focus_tasks(self, d):
        key = d.isoformat()
        return [x for x in self.data["tasks"] if x.get("focus") == key and not x.get("done")]

    def open_tasks(self, category=None):
        out = [t for t in self.data["tasks"] if not t.get("done")]
        if category:
            out = [t for t in out if t.get("category") == category]
        return sorted(out, key=_task_key)

    def routine_for(self, d: date, category=None):
        wd = d.weekday()
        out = [r for r in self.data["routine"] if wd in (r.get("days") or [])]
        if category:
            out = [r for r in out if r.get("category") == category]
        return sorted(out, key=lambda r: r.get("start") or "99:99")

    def deadlines(self, days=14, category=None):
        """Yaklaşan (ve geciken) her şey: görev, sınav, proje, borç/alacak, plan, doğum günü.
        Her biri: dict(kind, date, title, sub, category, coll, id)."""
        t0 = today()
        limit = t0 + timedelta(days=days)
        out = []

        def add(kind, d, title, sub, cat, coll, iid, overdue_ok=True):
            if d is None or d > limit:
                return
            if d < t0 and not overdue_ok:
                return
            out.append(dict(kind=kind, date=d, title=title, sub=sub, category=cat, coll=coll, id=iid))

        for t in self.data["tasks"]:
            if not t.get("done"):
                add("task", parse_date(t.get("due")), t.get("title", ""), t.get("time") or "",
                    t.get("category") or "personal", "tasks", t["id"])
        courses = {c["id"]: c for c in self.data["courses"]}
        for e in self.data["exams"]:
            if e.get("score") in (None, ""):
                c = courses.get(e.get("course"))
                add("exam", parse_date(e.get("date")), f"{c.get('name', '') if c else ''} · {e.get('name', '')}".strip(" ·"),
                    "", "education", "exams", e["id"], overdue_ok=False)
        for p in self.data["projects"]:
            if p.get("status") != "done":
                add("project", parse_date(p.get("due")), p.get("name", ""), f"%{int(p.get('progress') or 0)}",
                    "work", "projects", p["id"])
        for d in self.data["debts"]:
            if not d.get("settled"):
                add("debt_" + (d.get("direction") or "owe"), parse_date(d.get("due")), d.get("person", ""),
                    d.get("amount"), "finance", "debts", d["id"])
        for e in self.data["events"]:
            add("event", parse_date(e.get("date")), e.get("title", ""), e.get("time") or "", "social", "events",
                e["id"], overdue_ok=False)
        for b in self.data["birthdays"]:
            bd = parse_date(b.get("date"))
            if bd:
                nxt = _next_anniversary(bd, t0)
                add("birthday", nxt, b.get("name", ""), "", "social", "birthdays", b["id"], overdue_ok=False)
        if category:
            out = [x for x in out if x["category"] == category]
        out.sort(key=lambda x: (x["date"], x["title"].lower()))
        return out

    def items_between(self, a: date, b: date):
        """Takvim için [a, b] aralığındaki her şey: {tarih: [dict(kind, date, title, sub, category, coll, id)]}.
        Açık görevler, sınavlar, projeler, borç/alacak, planlar, doğum günleri ve antrenmanlar."""
        out = {}

        def add(kind, d, title, sub, cat, coll, iid):
            if d is not None and a <= d <= b:
                out.setdefault(d, []).append(dict(kind=kind, date=d, title=title, sub=sub, category=cat,
                                                  coll=coll, id=iid))

        for t in self.data["tasks"]:
            if not t.get("done"):
                add("task", parse_date(t.get("due")), t.get("title", ""), t.get("time") or "",
                    t.get("category") or "personal", "tasks", t["id"])
        courses = {c["id"]: c for c in self.data["courses"]}
        for e in self.data["exams"]:
            c = courses.get(e.get("course"))
            add("exam", parse_date(e.get("date")), f"{c.get('name', '') if c else ''} · {e.get('name', '')}".strip(" ·"),
                "", "education", "exams", e["id"])
        for p in self.data["projects"]:
            if p.get("status") != "done":
                add("project", parse_date(p.get("due")), p.get("name", ""), f"%{int(p.get('progress') or 0)}",
                    "work", "projects", p["id"])
        for d in self.data["debts"]:
            if not d.get("settled"):
                add("debt_" + (d.get("direction") or "owe"), parse_date(d.get("due")), d.get("person", ""),
                    d.get("amount"), "finance", "debts", d["id"])
        for e in self.data["events"]:
            add("event", parse_date(e.get("date")), e.get("title", ""), e.get("time") or "", "social", "events", e["id"])
        for bd_item in self.data["birthdays"]:
            bd = parse_date(bd_item.get("date"))
            if bd:
                for y in range(a.year, b.year + 1):
                    try:
                        d = bd.replace(year=y)
                    except ValueError:      # 29 Şubat
                        d = date(y, 2, 28)
                    add("birthday", d, bd_item.get("name", ""), "", "social", "birthdays", bd_item["id"])
        for w in self.data["workouts"]:
            add("workout", parse_date(w.get("date")), w.get("kind") or "", w.get("focus") or "", "sport",
                "workouts", w["id"])
        for lst in out.values():
            lst.sort(key=lambda x: (x["kind"] == "workout", x["title"].lower()))
        return out

    def workouts_between(self, a: date, b: date):
        out = []
        for w in self.data["workouts"]:
            d = parse_date(w.get("date"))
            if d and a <= d <= b:
                out.append(w)
        return out

    def sport_days(self, a: date, b: date):
        return {parse_date(w.get("date")) for w in self.workouts_between(a, b)}

    def month_totals(self, year, month):
        inc = exp = 0.0
        for tr in self.data["transactions"]:
            d = parse_date(tr.get("date"))
            if d and d.year == year and d.month == month:
                a = _num(tr.get("amount"))
                if tr.get("kind") == "income":
                    inc += a
                else:
                    exp += a
        return inc, exp

    def debt_totals(self):
        owe = owed = 0.0
        for d in self.data["debts"]:
            if d.get("settled"):
                continue
            if d.get("direction") == "owed":
                owed += _num(d.get("amount"))
            else:
                owe += _num(d.get("amount"))
        return owe, owed

    def investment_totals(self):
        inv = val = 0.0
        for x in self.data["investments"]:
            i = _num(x.get("invested"))
            v = x.get("value")
            inv += i
            val += _num(v) if v not in (None, "") else i
        return inv, val

    def course_average(self, course_id):
        """Notu girilmiş sınavların ağırlıklı ortalaması, girilen ağırlık toplamı, hedeflerin ağırlıklı ortalaması."""
        tot_w = tot = 0.0
        tw = tt = 0.0
        for e in self.data["exams"]:
            if e.get("course") != course_id:
                continue
            w = _num(e.get("weight")) or 0.0
            if e.get("score") not in (None, ""):
                tot += _num(e.get("score")) * w
                tot_w += w
            if e.get("target") not in (None, ""):
                tt += _num(e.get("target")) * w
                tw += w
        avg = tot / tot_w if tot_w else None
        tavg = tt / tw if tw else None
        return avg, tot_w, tavg


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def day_set(items):
    """["2026-11-13", ...] → {date, ...} (bozuk değerler atlanır)."""
    out = set()
    for x in items or []:
        d = parse_date(x)
        if d:
            out.add(d)
    return out


def streaks(days, td=None):
    """(şu anki seri, en uzun seri). Bugün henüz işaretlenmediyse seri dünden sayılır."""
    td = td or today()
    cur = 0
    d = td if td in days else td - timedelta(days=1)
    while d in days:
        cur += 1
        d -= timedelta(days=1)
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    return cur, best


def _task_key(t):
    d = parse_date(t.get("due"))
    pr = {"high": 0, "normal": 1, "low": 2}.get(t.get("priority") or "normal", 1)
    return (d is None, d or date.max, t.get("time") or "99:99", pr, (t.get("title") or "").lower())


def _next_anniversary(bd: date, ref: date) -> date:
    for y in (ref.year, ref.year + 1):
        try:
            d = bd.replace(year=y)
        except ValueError:   # 29 Şubat
            d = date(y, 2, 28)
        if d >= ref:
            return d
    return bd


num = _num
