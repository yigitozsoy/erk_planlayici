"""Veri deposu: tüm kayıtlar tek JSON dosyasında (config.DATA_FILE: Documents\\alpha\\data.json).

Koleksiyonlar (her kayıt bir dict, "id" alanı otomatik):
  tasks        yapılacaklar   title, category, due, time, end, priority, done, done_at, note, project (proje id)
  routine      haftalık program title, category, days[0-6], start, end, place, from, until (tarih aralığı), skip[iso] (o gün yok)
  courses      dersler        name, code, credits, target (harf), note, study_days[iso] (çalışma kareleri)
  exams        sınav/ödev     course, name, date, weight, target, score
  workouts     antrenman      date, kind, focus, minutes, note, exercises [{name, sets [{r, w}]}] (fitness.py)
  templates    program        name, exercises [{name, sets, reps, rir}], note
  body         vücut ölçüsü   date, weight, fat, waist, chest, arm, thigh, note
  mood         ruh hali       date, mood, energy, stress (1-5), note — günde bir (pages/mind.check_in)
  sleep        uyku           date (uyanılan gün), bed, wake ("HH:MM"), quality (1-5), note
  sessions     sayaç oturumu  date, kind (study | meditation), minutes, course, start, mode (clock.py)
  lifts        rekor (PR)     date, name, w, r, note (antrenman günlüğüne girmez; fitness.history okur)
  projects     projeler       name, category (work / education / ...), status, start, due, progress (görev yoksa),
               logo (DATA_DIR\\images içindeki dosya adı), note. Görevler task.project ile bağlanır.
  events       sosyal plan    title, date, time, people, place, note
  birthdays    doğum günü     name, date (yıl önemsiz)
  transactions gelir/gider    date, kind(income|expense), amount, category, note
  debts        borç/alacak    person, direction(owe|owed), amount, due, settled, note
  investments  yatırım        name, kind, invested, value, date, note, asset (markets kodu), qty (adet / gram)
  notes        notlar         title, body, category, pinned, updated
  days         günlük plan    date, intention, planned_at
  habits       alışkanlık     name, category, goal (haftada gün), note, days[iso]
  meals        beslenme       date, name, kcal, protein, carbs, fat
  accounts     nakit / hesap  name, balance, note
  recurring    sabit gelir/gider name, kind(income|expense), amount, day (ayın kaçı, boşsa 1), category, active, note
  goals        hayat hedefleri title, area (LIFE_AREAS; eski kategori değerleri life_area ile eşlenir), horizon (life|y10|y3|year|term|action), parent (goal id),
               due, progress (%; boşsa alt hedeflerden), image (DATA_DIR\\images içindeki dosya adı),
               links["habits:id" | "courses:id" | "projects:id"], days[iso] (elle "bugün çalıştım"), done, note,
               order, sample (örnek veri)
  transcript   transkript     term ("3.2"), code, name, lang, credits (AKTS), letter, target, old_letter, order
               (hesap: grades.py; dersler: letter gerçek, guess ihtimal, target hedef harf, retake)
  media        kütüphane      type, title, creator, year, cover, genres, status, rating, progress, total, started,
               finished, link, links, source, note (library.py; telefon sayfasına gitmez)
  cv           özgeçmiş       side (now | dream), section, title, org, when, detail, note, done, goal, now_id
               (pages/cv.py; Hedefler > CV sekmesi; telefona gitmez)
  bucket       bucket list    title, category, image, year, place, link, note, done, done_date (pages/bucket.py)
  places       harita         kind (province | country | city), key (plaka / iso3 / şehir adı), name, iso, lon, lat,
               status (been | want), date, note (pages/places.py; Kütüphane > Harita; telefona gitmez)
  wishlist     alınacaklar    name, price, category, link, bought, bought_at, note, source ("notion" = içe alındı)
  wheel        hayat çarkı   month (YYYY-MM), scores {hayat alanı: 1-10}, sample
"""
import copy
import json
import os
import shutil
import time
import uuid
from datetime import date, datetime, timedelta

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .config import day_today
from .config import DATA_FILE, BACKUP_DIR

COLLECTIONS = ("tasks", "routine", "courses", "exams", "workouts", "projects", "events", "birthdays",
               "transactions", "debts", "investments", "notes", "days", "habits", "meals", "accounts",
               "recurring", "goals", "wheel", "transcript", "media", "templates", "body", "lifts",
               "mood", "sleep", "sessions", "wishlist", "cv", "bucket", "places")

CATEGORIES = ("education", "work", "sport", "social", "finance", "personal")

# hayat alanları (hedefler + hayat çarkı): görev kategorilerinden ayrı, daha ince
#   education  dersler, notlar, sınavlar, CAD, İngilizce, Almanca
#   career     staj, iş bulma, aday mühendislik, bağlantılar
#   venture    kendi işini kurma
#   body · mind · finance · growth (kişisel gelişim ve keyif)
LIFE_AREAS = ("education", "career", "venture", "body", "mind", "finance", "growth")
# eski (kategori anahtarlı) kayıtlar okunurken eşlenir; veri yeniden yazılmaz
AREA_ALIAS = {"work": "career", "sport": "body", "social": "growth", "personal": "growth"}


def life_area(v):
    v = v or "growth"
    v = AREA_ALIAS.get(v, v)
    return v if v in LIFE_AREAS else "growth"


def life_scores(scores):
    """Çark puanları: eski anahtarlar yeni alana (aynı alana iki eski anahtar düşerse büyüğü)."""
    exact, old = {}, {}
    for k, v in (scores or {}).items():
        if not v:
            continue
        a = life_area(k)
        if k == a:
            exact[a] = v                       # yeni anahtarla verilmiş puan her zaman geçerli
        else:
            old[a] = max(old.get(a, 0), v)
    return {**old, **exact}


def today() -> date:
    return day_today()          # mantıksal gün (config.day_end_hour)


def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _exam_label(name):
    from . import grades
    from .i18n import is_tr
    return grades.exam_label(name, is_tr())


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
        # dosya dışarıdan değişirse (elle düzenleme, başka bir alpha) kaydedilmemiş değişiklik yoksa yeniden oku
        self._watch = QTimer(self)
        self._watch.setInterval(3000)
        self._watch.timeout.connect(self.check_external)
        self._watch.start()

    # ------------------------------------------------------------ dosya
    def _disk_mtime(self):
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return None

    def check_external(self):
        """Disktaki data.json bizim son okuduğumuz / yazdığımızdan farklıysa ve bekleyen kayıt yoksa yeniden yükle."""
        m = self._disk_mtime()
        if m is None or m == self._mtime or self._dirty:
            return False
        self.data = {c: [] for c in COLLECTIONS}
        self._load()
        for c in COLLECTIONS:
            self.changed.emit(c)
        return True

    def _load(self):
        self._mtime = self._disk_mtime()
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
            # bu sürümün tanımadığı bölümler (daha yeni bir alpha yazmış olabilir) olduğu gibi korunur
            self._extra = {k: v for k, v in loaded.items() if k not in COLLECTIONS}
        self._daily_backup()

    def _daily_backup(self):
        """Günde bir kez data.json'un kopyası (son 14 gün tutulur)."""
        try:
            name = f"data-{day_today():%Y-%m-%d}.json"
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
        # Belgeler OneDrive'daysa eşitleme dosyayı bir anlığına kilitleyebilir: birkaç kez dene, olmazsa sonra yine dene
        for attempt in range(4):
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump({**getattr(self, "_extra", {}), **self.data}, f, ensure_ascii=False, indent=1)
                os.replace(tmp, self.path)
                self._mtime = self._disk_mtime()
                self._dirty = False
                return
            except OSError:
                time.sleep(0.15 * (attempt + 1))
        self._timer.start(2000)

    def _touch(self, coll):
        self._dirty = True
        self._timer.start(400)
        self.changed.emit(coll)

    # ------------------------------------------------------------ CRUD
    def all(self, coll):
        return self.data[coll]

    def project_task_counts(self, pid):
        """(açık, toplam) görev sayısı."""
        ts = [x for x in self.data["tasks"] if x.get("project") == pid]
        return sum(1 for x in ts if not x.get("done")), len(ts)

    def project_progress(self, p):
        """İlerleme (0-100): projeye görev atanmışsa biten oranı, yoksa elle girilen; bitti → 100."""
        if p.get("status") == "done":
            return 100.0
        n_open, n_all = self.project_task_counts(p["id"])
        if n_all:
            return 100.0 * (n_all - n_open) / n_all
        return max(0.0, min(100.0, num(p.get("progress"))))

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

    def add_exam(self, ex):
        """Sınav ekler; aynı derste aynı türde (Vize 2, Final …) tarihi boş ya da aynı olan bir sınav varsa
        yenisini açmaz, boş olmayan alanları ona yazar (ağırlık / hedef korunur). (kayıt, önceki hâli | None)."""
        from . import grades
        ex = dict(ex)
        ex["name"] = grades.exam_canon(ex.get("name")) or ex.get("name")
        kind = grades.exam_kind(ex.get("name"))
        for e in self.data["exams"]:
            if e.get("course") != ex.get("course") or e.get("score") not in (None, ""):
                continue
            same = (grades.exam_kind(e.get("name")) == kind) if kind else \
                (e.get("name") or "").strip().casefold() == (ex.get("name") or "").strip().casefold()
            if same and (not e.get("date") or e.get("date") == ex.get("date")):
                before = dict(e)
                fields = {k: v for k, v in ex.items() if v not in (None, "") and k not in ("id", "created")}
                if e.get("note") and fields.get("note") and fields["note"] not in e["note"]:
                    fields["note"] = e["note"] + "\n" + fields["note"]
                self.update("exams", e["id"], **fields)
                return e, before
        return self.add("exams", ex), None

    def undo_exam(self, item, before):
        """add_exam'i geri alır."""
        if before is None:
            self.delete("exams", item["id"])
        else:
            self.update("exams", item["id"], **{k: before.get(k) for k in set(item) | set(before)})

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
                if coll == "goals":     # alt hedefler de gider (geri al hepsini döndürür)
                    kill = {item_id}
                    grew = True
                    while grew:
                        grew = False
                        for g in lst:
                            if g.get("parent") in kill and g.get("id") not in kill:
                                kill.add(g.get("id"))
                                grew = True
                    for j in range(len(lst) - 1, -1, -1):
                        if lst[j].get("id") in kill:
                            removed.append((coll, j, lst.pop(j)))   # silme sırası: restore tersten ekler
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
        """O gün tekrar eden saatler. "from" / "until" (isteğe bağlı tarih) dışındaki günlerde yok."""
        wd = d.weekday()
        out = [r for r in self.data["routine"] if wd in (r.get("days") or [])
               and not (parse_date(r.get("from")) and d < parse_date(r.get("from")))
               and not (parse_date(r.get("until")) and d > parse_date(r.get("until")))
               and d.isoformat() not in (r.get("skip") or [])]
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
                add("exam", parse_date(e.get("date")), f"{c.get('name', '') if c else ''} · {_exam_label(e.get('name'))}".strip(" ·"),
                    "", "education", "exams", e["id"], overdue_ok=False)
        for p in self.data["projects"]:
            if p.get("status") != "done":
                add("project", parse_date(p.get("due")), p.get("name", ""), f"%{int(self.project_progress(p))}",
                    p.get("category") or "work", "projects", p["id"])
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
            add("exam", parse_date(e.get("date")), f"{c.get('name', '') if c else ''} · {_exam_label(e.get('name'))}".strip(" ·"),
                "", "education", "exams", e["id"])
        for p in self.data["projects"]:
            if p.get("status") != "done":
                add("project", parse_date(p.get("due")), p.get("name", ""), f"%{int(self.project_progress(p))}",
                    p.get("category") or "work", "projects", p["id"])
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

    def sport_break(self):
        """Spora ara: (başlangıç, bitiş) ya da None. prefs sport_break = {"from", "until", "note"}."""
        from .config import prefs
        br = prefs.get("sport_break") or {}
        a, z = parse_date(br.get("from")), parse_date(br.get("until"))
        if a is None or z is None or z < a:
            return None
        return a, z

    def sport_goal(self, ws):
        """O haftanın hedefi: aradaki günler kadar orantılı düşer; 0 = ara haftası (seriyi bozmaz)."""
        from .config import prefs
        goal = max(1, min(7, int(_num(prefs.get("sport_weekly_goal", 4)) or 4)))
        br = self.sport_break()
        if not br:
            return goal
        off = sum(1 for i in range(7) if br[0] <= ws + timedelta(days=i) <= br[1])
        return int(round(goal * (7 - off) / 7)) if off else goal

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

    def cash_total(self):
        return sum(_num(a.get("balance")) for a in self.data["accounts"])

    def recurring_between(self, a, b):
        """(a, b] aralığına düşen sabit gelir / giderler: [(tarih, kayıt)], sıralı. Gün boşsa ayın 1'i."""
        import calendar
        out = []
        for r in self.data["recurring"]:
            if r.get("active") is False:
                continue
            try:
                day = int(_num(r.get("day")) or 1)
            except (TypeError, ValueError):
                day = 1
            y, m = a.year, a.month
            while (y, m) <= (b.year, b.month):
                d = date(y, m, max(1, min(day, calendar.monthrange(y, m)[1])))
                if a < d <= b:
                    out.append((d, r))
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return sorted(out, key=lambda x: x[0])

    def investment_totals(self):
        """(yatırılan, şu anki değer) — sembol + miktar varsa değer anlık fiyattan (markets önbelleği)."""
        from .markets import value_of
        inv = val = 0.0
        for x in self.data["investments"]:
            inv += _num(x.get("invested"))
            val += value_of(x)
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

    # ------------------------------------------------------------ hayat hedefleri
    def goal_children(self, parent_id):
        out = [g for g in self.data["goals"] if (g.get("parent") or None) == (parent_id or None)]
        return sorted(out, key=lambda g: (_num(g.get("order")), g.get("created") or ""))

    def goal_roots(self):
        ids = {g.get("id") for g in self.data["goals"]}
        out = [g for g in self.data["goals"] if not g.get("parent") or g.get("parent") not in ids]
        return sorted(out, key=lambda g: (_num(g.get("order")), g.get("created") or ""))

    def goal_descendants(self, goal_id):
        out, stack, seen = [], [goal_id], {goal_id}
        while stack:
            for c in self.goal_children(stack.pop()):
                if c["id"] not in seen:
                    seen.add(c["id"])
                    out.append(c)
                    stack.append(c["id"])
        return out

    def link_item(self, link):
        """"habits:abc" → (koleksiyon, kayıt) ya da (None, None)."""
        coll, _, iid = str(link or "").partition(":")
        if coll not in ("habits", "courses", "projects"):
            return None, None
        x = self.get(coll, iid)
        return (coll, x) if x is not None else (None, None)

    def link_days(self, link):
        """Bağlı kaydın etkinlik günleri: alışkanlık kareleri, ders çalışma günleri, projenin biten görevleri yok."""
        coll, x = self.link_item(link)
        if x is None:
            return set()
        if coll == "habits":
            return day_set(x.get("days"))
        if coll == "courses":
            return day_set(x.get("study_days"))
        return set()

    def goal_days(self, goal, deep=True):
        """Hedefin (ve alt hedeflerinin) etkinlik günleri: elle işaretlenenler + bağlı kayıtlar."""
        goals = [goal] + (self.goal_descendants(goal["id"]) if deep else [])
        out = set()
        for g in goals:
            out |= day_set(g.get("days"))
            for ln in g.get("links") or []:
                out |= self.link_days(ln)
        return out

    def goal_activity(self, goal, td=None, window=30):
        """(son `window` gündeki etkin gün sayısı, son etkin gün ya da None)."""
        td = td or today()
        days = self.goal_days(goal)
        a = td - timedelta(days=window - 1)
        n = sum(1 for d in days if a <= d <= td)
        past = [d for d in days if d <= td]
        return n, (max(past) if past else None)

    def goal_progress(self, goal, _depth=0):
        """0-1 arası: bitti → 1; elle girilen % varsa o; yoksa alt hedeflerin / bağlı projelerin ortalaması."""
        if goal.get("done"):
            return 1.0
        p = goal.get("progress")
        if p not in (None, ""):
            return max(0.0, min(1.0, _num(p) / 100.0))
        parts = []
        if _depth < 8:
            parts += [self.goal_progress(c, _depth + 1) for c in self.goal_children(goal["id"])]
        for ln in goal.get("links") or []:
            coll, x = self.link_item(ln)
            if coll == "projects":
                parts.append(1.0 if x.get("status") == "done" else max(0.0, min(1.0, _num(x.get("progress")) / 100)))
        return sum(parts) / len(parts) if parts else 0.0

    def wheel_for(self, month):
        for w in self.data["wheel"]:
            if w.get("month") == month:
                return w
        return None

    def set_wheel(self, month, area, score):
        w = self.wheel_for(month)
        if w is None:
            w = self.add("wheel", {"month": month, "scores": {}})
        scores = life_scores(w.get("scores"))
        if score:
            scores[area] = int(score)
        else:
            scores.pop(area, None)
        self.update("wheel", w["id"], scores=scores)


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
