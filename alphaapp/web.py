"""Web görünümü: günün programı / yapılacaklar / takvimin anlık görüntüsünü kişisel sunucuya gönderir.

Yalnızca "yapmam gerekenler" gider: program, görevler, planlar, sınavlar, teslimler, borç/alacak tarihleri, doğum
günleri. Hedefler, vision board, notlar, ekonomi kayıtları, beslenme GİTMEZ.

Sunucu: api/alpha.php (yigitozsoy.net). Anahtar (prefs web_key) X-Alpha-Key başlığında gider; sunucuda yalnızca
sha256'sı durur (api/_alpha_key.php, key_file_text() üretir). Telefondaki sayfa anahtarı bağlantının #k= kısmından alır.
"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, QTimer, QUrl, QByteArray, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from .config import prefs, day_today, day_end_hour
from .i18n import t, fmt_money
from .store import parse_date, day_set, CATEGORIES

DAYS_BACK, DAYS_AHEAD = 7, 30         # haftalık program için geçen hafta da
MAX_AGE_MIN = 60                     # içerik değişmese de en geç bu kadar dakikada bir gönder ("son güncelleme")


def page_url(api_url):
    """https://site/api/alpha.php → https://site/alpha/"""
    u = (api_url or "").strip()
    if "/api/" in u:
        return u.split("/api/")[0] + "/alpha/"
    return u.rsplit("/", 1)[0] + "/alpha/" if u else ""


def url_ok(u):
    """Anahtar düz HTTP'de gitmesin: yalnızca https (ya da bu bilgisayardaki deneme sunucusu)."""
    u = (u or "").strip()
    return u.startswith("https://") or u.startswith("http://127.0.0.1:") or u.startswith("http://localhost:")


def new_key():
    return secrets.token_urlsafe(24)


def key_hash(key):
    return hashlib.sha256((key or "").encode("utf-8")).hexdigest()


def key_file_text(key):
    """Sunucudaki api/_alpha_key.php içeriği (anahtarın kendisi değil, yalnızca özeti)."""
    return ("<?php\n// alpha web anahtarının sha256 özeti (alpha > Seçenekler > Web'den üretildi)\n"
            f"return '{key_hash(key)}';\n")


def _span(a, b):
    return f"{a}–{b}" if a and b else (a or "")


def _cat(c):
    return c if c in CATEGORIES else "personal"


def day_blocks(store, d, show_place=True, show_habits=False, courses=None):
    """Haftalık programdaki kutular (pages/schedule.py ile aynı kaynak, sıra ve metin)."""
    courses = courses if courses is not None else {c["id"]: c for c in store.all("courses")}
    out = []

    def add(sort, kind, time, title, sub="", cat=None, important=False, done=False):
        out.append((sort, dict(kind=kind, time=time or "", title=title or "", sub=sub or "", cat=_cat(cat),
                               important=bool(important), done=bool(done))))

    for r in store.routine_for(d):
        st, en = r.get("start") or "", r.get("end") or ""
        add(st or "99", "routine", f"{st}–{en}" if st and en else st, r.get("title", ""),
            (r.get("place") or "") if show_place else "", r.get("category"), r.get("important"))
    for tk in store.all("tasks"):
        if parse_date(tk.get("due")) == d:
            done = bool(tk.get("done"))
            add(tk.get("time") or "99:90", "task", _span(tk.get("time"), tk.get("end")),
                ("☑ " if done else "☐ ") + tk.get("title", ""), "", tk.get("category"),
                tk.get("priority") == "high" and not done, done)
    for ev in store.all("events"):
        if parse_date(ev.get("date")) == d:
            add(ev.get("time") or "99:80", "event", ev.get("time") or "", ev.get("title", ""),
                (ev.get("place") or "") if show_place else "", "social", ev.get("important"))
    for ex in store.all("exams"):
        if parse_date(ex.get("date")) == d:
            c = courses.get(ex.get("course"), {})
            add(ex.get("time") or "00", "exam", t("exam") + (f" · {ex['time']}" if ex.get("time") else ""),
                f"{c.get('name', '')} · {ex.get('name', '')}", "", "education",
                ex.get("score") in (None, ""))
    for p in store.all("projects"):
        if parse_date(p.get("due")) == d and p.get("status") != "done":
            add("99:95", "project", t("deadline"), p.get("name", ""), "", "work", True)
    for db in store.all("debts"):
        if parse_date(db.get("due")) == d and not db.get("settled"):
            add("99:96", "debt", t("dir_" + (db.get("direction") or "owe")),
                f"{db.get('person', '')} · {fmt_money(db.get('amount'))}", "", "finance")
    if show_habits:
        for h in store.all("habits"):
            wds = h.get("weekdays") or []
            if wds and d.weekday() not in wds:
                continue
            done = d in day_set(h.get("days"))
            add(h.get("time") or "99:97", "habit", h.get("time") or t("habit"),
                ("☑ " if done else "☐ ") + h.get("name", ""), "", h.get("category") or "personal", done=done)
    out.sort(key=lambda x: x[0])
    return [x for _s, x in out]


def day_program(store, d, courses):
    """Bugün sayfasındaki "Bugünün programı" satırları (pages/today.py ile aynı)."""
    items = []
    for r in store.routine_for(d):
        st, en = r.get("start") or "", r.get("end") or ""
        sub = [t("cat_" + _cat(r.get("category")))]
        if r.get("place"):
            sub.append(r["place"])
        items.append((st or "99:99", dict(kind="routine", lead=f"{st}–{en}" if st and en else st or "—",
                                          title=r.get("title", ""), sub=" · ".join(sub), start=st, end=en)))
    for tk in store.all("tasks"):
        if not tk.get("done") and parse_date(tk.get("due")) == d and tk.get("time"):
            items.append((tk["time"], dict(kind="task", lead=tk["time"], title=tk.get("title", ""),
                                           sub=t("cat_" + _cat(tk.get("category"))))))
    for ev in store.all("events"):
        if parse_date(ev.get("date")) == d:
            sub = " · ".join(x for x in (ev.get("people"), ev.get("place")) if x) or t("cat_social")
            items.append((ev.get("time") or "99:98", dict(kind="event", lead=ev.get("time") or t("all_day"),
                                                          title=ev.get("title", ""), sub=sub)))
    for ex in store.all("exams"):
        if parse_date(ex.get("date")) == d:
            c = courses.get(ex.get("course"), {})
            items.append((ex.get("time") or "99:97", dict(kind="exam", lead=ex.get("time") or t("exam_short"),
                                        title=f"{c.get('name', '')} · {ex.get('name', '')}", sub=t("exam"))))
    items.sort(key=lambda x: x[0])
    return [x for _s, x in items]


def _sub_parts(kind, category, sub):
    """components.deadline_row / takvim satırının alt yazısı (tarih hariç)."""
    out = [t("cat_" + _cat(category))]
    if kind.startswith("debt_"):
        out.append(t("dir_" + kind[5:]) + " · " + fmt_money(sub))
    elif kind == "birthday":
        out.append(t("birthday"))
    elif kind == "exam":
        out.append(t("exam"))
    elif sub:
        out.append(str(sub))
    return " · ".join(out)


KIND_ICON = {"exam": "cat_education", "project": "cat_work", "debt_owe": "wallet", "debt_owed": "wallet",
             "event": "group", "birthday": "cake", "workout": "cat_sport"}
CAT_ICON = {"education": "cat_education", "work": "cat_work", "sport": "cat_sport", "social": "group",
            "finance": "wallet", "personal": "person"}
DOT_ROLE = {"exam": "bad", "task": "text", "project": "text", "debt_owe": "text", "debt_owed": "text",
            "event": "text2", "birthday": "text2", "workout": "good"}
ICONS = ("menu", "today", "schedule_week", "sun", "moon", "chevron_left", "chevron_right", "box", "box_checked",
         "cat_education", "cat_work", "cat_sport", "group", "wallet", "person", "cake", "flag", "clock")
STRINGS = ("nav_today", "nav_schedule", "today", "tomorrow", "yesterday", "now", "focus", "prio_high", "undated",
           "today_program", "todo", "upcoming", "n_items", "n_open", "n_overdue", "no_program", "no_todo",
           "no_deadlines", "next_n_days", "and_more", "cal_hint", "cal_hint_empty", "cal_empty", "cal_prev",
           "cal_next", "greet_morning", "greet_day", "greet_evening", "overdue_n", "in_n_days", "this_week")


def _icon_for(kind, cat):
    return KIND_ICON.get(kind) or CAT_ICON.get(_cat(cat), "flag")


def build_snapshot(store, now=None):
    """Sunucuya giden JSON (dict): Bugün + Haftalık program sayfalarını çizmeye yetecek kadar.
    Hedef, vision board, not, ekonomi kaydı İÇERMEZ."""
    from . import __version__
    from .i18n import WEEKDAYS_LONG, WEEKDAYS_SHORT, MONTHS_LONG, MONTHS_SHORT
    from .icons import P
    now = now or datetime.now()
    td = day_today()
    show_place = prefs.get("show_place", True)
    show_habits = bool(prefs.get("habits_in_schedule", False))
    courses = {c["id"]: c for c in store.all("courses")}
    days = []
    for i in range(-DAYS_BACK, DAYS_AHEAD + 1):
        d = td + timedelta(days=i)
        days.append(dict(date=d.isoformat(), intention=(store.day(d) or {}).get("intention", "") or "",
                         blocks=day_blocks(store, d, show_place, show_habits, courses),
                         prog=day_program(store, d, courses)))
    tasks = []
    limit = td + timedelta(days=DAYS_AHEAD)
    for x in store.open_tasks():
        due = parse_date(x.get("due"))
        if due and due > limit:
            continue
        note = (x.get("note") or "").strip()
        tasks.append(dict(title=x.get("title", ""), cat=_cat(x.get("category")), due=due.isoformat() if due else "",
                          time=x.get("time") or "", note=note.splitlines()[0][:60] if note else "",
                          focus=x.get("focus") or "", high=x.get("priority") == "high"))
    dl_days = int(prefs.get("deadline_days", 14))
    deadlines = []
    for x in store.deadlines(DAYS_AHEAD):
        deadlines.append(dict(kind=x["kind"], date=x["date"].isoformat(), title=x["title"],
                              sub=_sub_parts(x["kind"], x["category"], x["sub"]), task=x["coll"] == "tasks",
                              icon=_icon_for(x["kind"], x["category"])))
    a = td.replace(day=1)
    b = (a + timedelta(days=95)).replace(day=1) - timedelta(days=1)     # bu ay + 2 ay
    cal = {}
    for d, lst in store.items_between(a - timedelta(days=7), b + timedelta(days=14)).items():
        cal[d.isoformat()] = [dict(title=x["title"], sub=_sub_parts(x["kind"], x["category"], x["sub"]),
                                   icon=_icon_for(x["kind"], x["category"]),
                                   role=DOT_ROLE.get(x["kind"], "text2") if x["kind"] in ("exam", "workout") else "text2",
                                   dot=DOT_ROLE.get(x["kind"], "text2")) for x in lst]
    return {
        "v": 2, "app": "alpha", "version": __version__,
        "lang": prefs.get("language", "tr"),
        "generated": now.isoformat(timespec="seconds"),
        "today": td.isoformat(), "day_end_hour": day_end_hour(),
        "name": (prefs.get("name") or "").strip(),
        "deadline_days": dl_days,
        "cats": {c: t("cat_" + c) for c in CATEGORIES},
        "cal_range": [a.isoformat(), b.isoformat()],
        "str": {k: t(k) for k in STRINGS},
        "wd_long": WEEKDAYS_LONG(), "wd_short": WEEKDAYS_SHORT(),
        "mon_long": MONTHS_LONG(), "mon_short": MONTHS_SHORT(),
        "icons": {k: P[k] for k in ICONS if k in P},
        "days": days,
        "tasks": tasks,
        "deadlines": deadlines,
        "cal": cal,
    }


def content_hash(snap):
    s = {k: v for k, v in snap.items() if k != "generated"}
    return hashlib.sha1(json.dumps(s, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class WebSync(QObject):
    """Kayıt değişince (birkaç sn sonra) ve saatte bir anlık görüntüyü gönderir. Ağ hatası uygulamayı etkilemez."""
    status = pyqtSignal(str)          # "ok" | "error" | "sending" | "off"

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.net = QNetworkAccessManager(self)
        self._reply = None
        self._pending = False
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(8000)
        self._debounce.timeout.connect(self.push)
        self._tick = QTimer(self)
        self._tick.setInterval(5 * 60_000)
        self._tick.timeout.connect(lambda: self.push(force=False))
        self._tick.start()
        store.changed.connect(lambda _c: self.schedule())
        QTimer.singleShot(4000, self.push)

    @staticmethod
    def enabled():
        return bool(prefs.get("web_on", False) and url_ok(prefs.get("web_url")) and prefs.get("web_key"))

    def schedule(self):
        if self.enabled():
            self._debounce.start()

    def push(self, force=True):
        """force=False: yalnızca içerik değiştiyse ya da son gönderim MAX_AGE_MIN'den eskiyse."""
        if not self.enabled():
            return False
        if self._reply is not None:
            self._pending = True
            return False
        snap = build_snapshot(self.store)
        h = content_hash(snap)
        last = prefs.get("web_last_ok")
        if not force and h == prefs.get("web_last_hash") and last:
            try:
                if datetime.now() - datetime.fromisoformat(last) < timedelta(minutes=MAX_AGE_MIN):
                    return False
            except ValueError:
                pass
        body = json.dumps(snap, ensure_ascii=False).encode("utf-8")
        req = QNetworkRequest(QUrl(prefs.get("web_url").strip() + "?action=push"))
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json; charset=utf-8")
        req.setRawHeader(b"X-Alpha-Key", prefs.get("web_key").encode("ascii", "ignore"))
        req.setTransferTimeout(20_000)
        # Qt yönlendirmeyi kendisi izlerse POST'u GET'e çevirir: elle izle (_done)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        self._reply = self.net.post(req, QByteArray(body))
        self._reply.finished.connect(lambda r=self._reply, hh=h: self._done(r, hh))
        self.status.emit("sending")
        return True

    def _done(self, reply, h):
        self._reply = None
        code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll())
        ok = reply.error() == QNetworkReply.NetworkError.NoError and code == 200
        msg = ""
        loc = reply.attribute(QNetworkRequest.Attribute.RedirectionTargetAttribute)
        if code in (301, 302, 307, 308) and loc is not None:
            # site başka adrese yönlendiriyor (ör. www.): POST yönlendirmede kaybolur → adresi güncelle, yeniden gönder
            new = reply.url().resolved(loc).toString().split("?")[0]
            if url_ok(new) and new != prefs.get("web_url"):
                prefs.set("web_url", new)
                reply.deleteLater()
                QTimer.singleShot(0, self.push)
                return
        if ok:
            try:
                ok = bool(json.loads(data.decode("utf-8")).get("ok"))
            except (ValueError, AttributeError):
                ok = False
                msg = "geçersiz yanıt"
        if ok:
            prefs.set("web_last_ok", datetime.now().isoformat(timespec="seconds"))
            prefs.set("web_last_hash", h)
            prefs.set("web_error", "")
        else:
            if not msg:
                try:
                    msg = json.loads(data.decode("utf-8")).get("error") or ""
                except (ValueError, AttributeError):
                    msg = ""
                msg = msg or (f"HTTP {code}" if code else reply.errorString())
            prefs.set("web_error", msg[:200])
        reply.deleteLater()
        self.status.emit("ok" if ok else "error")
        if self._pending:
            self._pending = False
            QTimer.singleShot(500, self.push)
