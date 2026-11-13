"""Uçtan uca duman testi: geçici veri klasörü + örnek veri, tüm sayfalar ve formlar, ekran görüntüleri.

python tests/smoke_test.py                 # test
python tests/smoke_test.py --shots DIR     # ayrıca her sayfanın PNG'sini DIR'e kaydet (açık + koyu tema)
"""
import os
import re
import sys
import glob
import tempfile
from datetime import date, timedelta

# gerçek tercihlere / verilere ASLA dokunma
_tmp = tempfile.mkdtemp(prefix="alpha-test-")
os.environ["LOCALAPPDATA"] = _tmp
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication  # noqa: E402

STEPS = []


def step(name):
    def deco(fn):
        STEPS.append((name, fn))
        return fn
    return deco


def seed(store):
    td = date.today()
    D = lambda k: (td + timedelta(days=k)).isoformat()  # noqa: E731
    wd = td.weekday()
    store.add("routine", {"title": "Akışkanlar Mekaniği", "category": "education", "days": [wd, (wd + 2) % 7],
                          "start": "09:00", "end": "10:50", "place": "B-201"})
    store.add("routine", {"title": "Gym", "category": "sport", "days": [0, 2, 4], "start": "18:00", "end": "19:30"})
    store.add("routine", {"title": "Staj", "category": "work", "days": [wd], "start": "13:00", "end": "17:00"})
    c1 = store.add("courses", {"name": "Akışkanlar Mekaniği", "code": "MAK301", "credits": 6, "target": "BA"})
    c2 = store.add("courses", {"name": "Isı Transferi", "code": "MAK305", "credits": 5, "target": "BB"})
    store.add("exams", {"course": c1["id"], "name": "Vize", "date": D(-20), "weight": 40, "target": 80, "score": 72})
    store.add("exams", {"course": c1["id"], "name": "Final", "date": D(9), "weight": 60, "target": 85, "score": None})
    store.add("exams", {"course": c2["id"], "name": "Quiz", "date": D(-5), "weight": 10, "target": 70, "score": 90})
    store.add("exams", {"course": c2["id"], "name": "Vize", "date": D(2), "weight": 40, "target": 75, "score": None})
    store.add("tasks", {"title": "Bitirme raporunu gönder", "category": "education", "due": D(0), "priority": "high"})
    store.add("tasks", {"title": "Kirayı öde", "category": "finance", "due": D(-1)})
    store.add("tasks", {"title": "Toplantı notlarını düzenle", "category": "work", "due": D(3), "time": "10:00"})
    store.add("tasks", {"title": "Spor ayakkabısı bak", "category": "personal"})
    store.add("tasks", {"title": "Dedemi ara", "category": "social"})
    store.add("projects", {"name": "Hava emiş rezonatörü", "status": "doing", "due": D(12), "progress": 45})
    store.add("projects", {"name": "Web sitesi", "status": "waiting", "progress": 70})
    for k, (kind, focus) in enumerate([("Gym", "Göğüs"), ("Gym", "Sırt"), ("Koşu", "Kardiyo"), ("Gym", "Bacak")]):
        store.add("workouts", {"date": D(-k * 2), "kind": kind, "focus": focus, "minutes": 60 + k * 5})
    store.add("events", {"title": "Akşam yemeği", "date": D(1), "time": "20:00", "people": "Ece, Can", "place": "Moda"})
    store.add("events", {"title": "Halı saha", "date": D(-3), "time": "21:00"})
    store.add("birthdays", {"name": "Annem", "date": (td + timedelta(days=6)).replace(year=1970).isoformat()})
    for k in range(6):
        m = td.replace(day=1) - timedelta(days=30 * k)
        store.add("transactions", {"kind": "income", "amount": 30000 + k * 1000, "category": "Maaş",
                                   "date": m.isoformat()})
        store.add("transactions", {"kind": "expense", "amount": 12000 + k * 800, "category": "Kira",
                                   "date": m.isoformat()})
    store.add("transactions", {"kind": "expense", "amount": 845.5, "category": "Market", "date": D(0)})
    store.add("transactions", {"kind": "expense", "amount": 320, "category": "Yemek", "date": D(0), "note": "öğle"})
    store.add("debts", {"direction": "owe", "person": "Mert", "amount": 1500, "due": D(4)})
    store.add("debts", {"direction": "owed", "person": "Zeynep", "amount": 600})
    store.add("investments", {"name": "Altın (gr)", "kind": "Altın", "invested": 20000, "value": 23400, "date": D(-90)})
    store.add("investments", {"name": "BIST fon", "kind": "Fon", "invested": 15000, "value": 14100, "date": D(-60)})
    store.add("notes", {"title": "Bu dönem hedefleri", "body": "- Ortalama 3,2\n- Haftada 4 gün spor", "pinned": True,
                        "category": "personal", "updated": D(0) + "T08:00:00"})
    c1["study_days"] = [D(-k) for k in (1, 2, 3, 5, 8, 9, 15, 22, 40)]
    store.add("habits", {"name": "Kitap oku", "category": "personal", "goal": 5,
                         "days": [D(-k) for k in range(1, 6)] + [D(-k) for k in (9, 10, 30, 31, 32, 60)]})
    store.add("habits", {"name": "Su iç (2 L)", "category": "sport", "goal": 7, "days": [D(0), D(-1), D(-3)]})
    for k, (nm, kc, pr, cb, ft) in enumerate([("Yulaf + süt", 420, 20, 60, 10), ("Tavuk pilav", 650, 45, 70, 15),
                                              ("Protein shake", 180, 30, 5, 3)]):
        store.add("meals", {"date": D(0), "name": nm, "kcal": kc, "protein": pr, "carbs": cb, "fat": ft})
        store.add("meals", {"date": D(-1), "name": nm, "kcal": kc, "protein": pr, "carbs": cb, "fat": ft})
    store.add("notes", {"title": "Staj fikirleri", "body": "Rezonatör ölçümleri", "category": "work",
                        "updated": D(-2) + "T12:00:00"})


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    shots = None
    if "--shots" in sys.argv:
        shots = sys.argv[sys.argv.index("--shots") + 1]
        os.makedirs(shots, exist_ok=True)
    app = QApplication(sys.argv)
    # PyQt slot içindeki yakalanmamış hatada süreci kapatır; burada toplayıp test hatası say
    slot_errors = []

    def hook(tp, val, tb):
        import traceback
        slot_errors.append("".join(traceback.format_exception(tp, val, tb)))
    sys.excepthook = hook
    from alphaapp.config import prefs, DATA_DIR
    assert DATA_DIR.startswith(_tmp), DATA_DIR
    prefs.set("name", "Test")
    prefs.set("last_plan", date.today().isoformat())   # plan ekranı kendi adımında test edilir
    from alphaapp.i18n import apply_locale
    apply_locale()
    from alphaapp.theme import theme
    theme.apply("amoled")
    from alphaapp.store import Store
    from alphaapp.window import MainWindow
    store = Store()
    seed(store)
    win = MainWindow(store)
    win.resize(1400, 900)
    win.show()
    app.processEvents()
    ctx = {"app": app, "store": store, "win": win, "shots": shots}
    failed = 0
    for i, (name, fn) in enumerate(STEPS, 1):
        try:
            fn(ctx)
            print(f"[{i:2}/{len(STEPS)}] ok   {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            import traceback
            traceback.print_exc()
            print(f"[{i:2}/{len(STEPS)}] FAIL {name}: {e}")
    win.close()
    if slot_errors:
        failed += 1
        print("\nArka planda yakalanan hatalar:")
        for e in slot_errors[:5]:
            print(e)
    print("\n" + ("HEPSİ GEÇTİ" if not failed else f"{failed} ADIM BAŞARISIZ"))
    return 1 if failed else 0


def _pump(app, n=3):
    for _ in range(n):
        app.processEvents()


@step("i18n: koddaki tüm anahtarlar tanımlı")
def _i18n(ctx):
    from alphaapp.i18n import S
    missing = set()
    for f in glob.glob(os.path.join(ROOT, "alphaapp", "**", "*.py"), recursive=True):
        s = open(f, encoding="utf-8").read()
        for k in re.findall(r'\bt\(\s*"([a-z0-9_]+)"\s*[,)]', s):
            if k not in S and k != "anahtar":   # i18n.py belge metnindeki örnek
                missing.add(k)
        for k in re.findall(r'"((?:f|qa)_[a-z_]+)"', s):
            if k not in S:
                missing.add(k)
    from alphaapp.store import CATEGORIES, COLLECTIONS
    from alphaapp.forms import TASK_PRIORITIES, PROJECT_STATUS
    from alphaapp.window import NAV
    missing |= {e[2] for e in NAV if e} - set(S)
    for c in CATEGORIES:
        missing |= {"cat_" + c} - set(S)
    for p in TASK_PRIORITIES:
        missing |= {"prio_" + p} - set(S)
    for p in PROJECT_STATUS:
        missing |= {"status_" + p} - set(S)
    from alphaapp.pages.plan import STEPS as PSTEPS, CHOICES
    for k in PSTEPS:
        missing |= {"plan_step_" + k, "plan_lead_" + k} - set(S)
    for k in CHOICES:
        missing |= {"plan_ch_" + k} - set(S)
    missing |= {"plan_all_" + k for k in ("today", "tomorrow", "someday")} - set(S)
    for c in COLLECTIONS:
        if c not in ("notes", "days"):
            missing |= {"new_" + c, "edit_" + c} - set(S)
    assert not missing, sorted(missing)


@step("tüm sayfalar açılıyor ve yenileniyor")
def _pages(ctx):
    win, app = ctx["win"], ctx["app"]
    for key in win.pages:
        win.show_page(key)
        _pump(app)
        assert win.stack.currentWidget() is win.pages[key]


@step("Bugün: program, yapılacaklar, yaklaşanlar dolu")
def _today(ctx):
    win, app = ctx["win"], ctx["app"]
    from alphaapp.components import Row
    win.show_page("today")
    _pump(app)
    p = win.pages["today"]
    assert p.c_prog.findChildren(Row), "program boş"
    assert p.c_todo.findChildren(Row), "yapılacaklar boş"
    assert p.c_dead.findChildren(Row), "yaklaşanlar boş"
    assert "Test" in p.title_lbl.text()


@step("görev tamamla + geri al")
def _task_done(ctx):
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    from alphaapp.pages import toggle_task
    tk = [x for x in store.all("tasks") if x["title"] == "Kirayı öde"][0]
    toggle_task(win, tk, True)
    assert store.get("tasks", tk["id"])["done"]
    win.toast_w._clicked()   # geri al
    assert not store.get("tasks", tk["id"])["done"]
    _pump(app)


@step("silme + geri al (ders silinince sınavları da gider ve geri gelir)")
def _delete_undo(ctx):
    store = ctx["store"]
    c = store.all("courses")[0]
    n_ex = len(store.all("exams"))
    removed = store.delete("courses", c["id"])
    assert len(store.all("exams")) < n_ex
    store.restore(removed)
    assert store.get("courses", c["id"]) and len(store.all("exams")) == n_ex


@step("ders ortalaması ve gereken not")
def _course_avg(ctx):
    store = ctx["store"]
    c = [x for x in store.all("courses") if x["code"] == "MAK301"][0]
    avg, w, tavg = store.course_average(c["id"])
    assert avg == 72 and w == 40 and abs(tavg - 83) < 1e-9, (avg, w, tavg)


@step("tüm formlar açılıyor, değer okuyor, kaydediyor")
def _forms(ctx):
    store, win = ctx["store"], ctx["win"]
    from alphaapp.forms import FormDialog
    from alphaapp.store import COLLECTIONS
    for coll in COLLECTIONS:
        if coll in ("notes", "days"):
            continue
        item = store.all(coll)[0] if store.all(coll) else None
        before = dict(item) if item else None
        d = FormDialog(win, store, coll, item)
        v = d.values()
        assert isinstance(v, dict) and v, coll
        if item:
            d._save()
            assert d.result() == 1, coll
            after = store.get(coll, item["id"])
            for k in ("days", "study_days"):   # form kaydı kareleri silmemeli
                if before.get(k):
                    assert after.get(k) == before[k], (coll, k)
        d.deleteLater()


@step("form: sayı ayrıştırma (1.250,50 → 1250.5)")
def _num(ctx):
    from alphaapp.forms import _parse_num
    assert _parse_num("1.250,50") == 1250.5
    assert _parse_num("12,5") == 12.5
    assert _parse_num("12.5") == 12.5
    assert _parse_num("") is None
    assert _parse_num("abc") is None


@step("biçimler: para, tarih")
def _fmt(ctx):
    from alphaapp.i18n import fmt_money, fmt_day, due_badge
    assert fmt_money(1250.5) == "1.250,50 ₺", fmt_money(1250.5)
    assert fmt_money(1000) == "1.000 ₺", fmt_money(1000)
    assert fmt_money(-20, sign=True) == "−20 ₺"
    assert fmt_day(date.today()) == "Bugün"
    assert due_badge(date.today() - timedelta(days=2))[1] == "bad"


@step("notlar: yeni not, yaz, kaydet, sil + geri al")
def _notes(ctx):
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    win.show_page("notes")
    _pump(app)
    p = win.pages["notes"]
    n0 = len(store.all("notes"))
    p.new_note()
    p.ed_title.setText("Deneme")
    p.ed_body.setPlainText("gövde")
    p.commit()
    assert store.get("notes", p.cur)["title"] == "Deneme"
    nid = p.cur
    p._delete()
    assert store.get("notes", nid) is None
    win.toast_w._clicked()
    assert store.get("notes", nid) is not None and len(store.all("notes")) == n0 + 1


@step("veri dosyaya yazılıyor ve geri okunuyor")
def _persist(ctx):
    store = ctx["store"]
    from alphaapp.store import Store
    store.flush()
    s2 = Store()
    for c in ("tasks", "courses", "transactions", "notes"):
        assert len(s2.all(c)) == len(store.all(c)), c


@step("tema değişimi (aydınlık ↔ karanlık)")
def _theme(ctx):
    from alphaapp.theme import theme
    theme.apply("white")
    _pump(ctx["app"])
    theme.apply("amoled")
    _pump(ctx["app"])


@step("dar pencere (tek sütun) bozulmuyor")
def _narrow(ctx):
    win, app = ctx["win"], ctx["app"]
    win.resize(800, 700)
    for key in win.pages:
        win.show_page(key)
        _pump(app)
    win.resize(1400, 900)
    _pump(app)


@step("sabah planı: kalanlar taşınıyor/siliniyor + geri al, hızlı ekle, odak (en fazla 3), hedef, bitir")
def _plan(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from datetime import datetime
    from alphaapp.config import prefs
    from alphaapp.components import Row
    td = date.today()
    D = lambda k: (td + timedelta(days=k)).isoformat()  # noqa: E731
    page = win.pages["plan"]
    # otomatik açılış: yalnızca öğleden önce ve plan yapılmadıysa
    prefs.set("last_plan", None)
    win.show_page("today")
    win.maybe_plan()
    assert (win.current == "plan") == (datetime.now().hour < 12), win.current
    win.show_page("today")
    win.refresh_all()   # gün dönümü gibi
    _pump(app)
    assert win.pages["today"].c_plan.isVisible(), "plan daveti görünmüyor"

    win.open_plan()
    _pump(app)
    assert win.current == "plan" and page.step == 0
    assert not any(b.isChecked() for b in win.nav.btns.values()), "menüde bir şey seçili kaldı"
    kira = [x for x in store.all("tasks") if x["title"] == "Kirayı öde"][0]
    fat = store.add("tasks", {"title": "Faturayı yatır", "category": "finance", "due": D(-2)})
    old = store.add("tasks", {"title": "Eski bir iş", "category": "personal", "due": D(-6)})
    _pump(app, 4)
    assert set(page.carry_rows) >= {kira["id"], fat["id"], old["id"]}, page.carry_rows
    page.carry_rows[kira["id"]].btns["tomorrow"].click()
    page.carry_rows[fat["id"]].btns["delete"].click()
    page.carry_rows[old["id"]].btns["someday"].click()
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "plan_1_carry.png"))
    page.next()
    _pump(app)
    assert store.get("tasks", kira["id"])["due"] == D(1)
    assert store.get("tasks", fat["id"]) is None
    assert store.get("tasks", old["id"])["due"] is None
    # geri al: hepsi eski haline
    win.toast_w._cb()
    _pump(app)
    assert store.get("tasks", kira["id"])["due"] == D(-1)
    assert store.get("tasks", fat["id"])["due"] == D(-2)
    assert store.get("tasks", old["id"])["due"] == D(-6)
    page.go(0)
    _pump(app)
    page._pick_all("today")
    page.next()
    _pump(app)
    assert all(store.get("tasks", i)["due"] == D(0) for i in (kira["id"], fat["id"], old["id"]))

    # adım 2: hızlı ekle bugüne yazar
    assert page.step == 1
    page.quick.setText("Su iç")
    page.quick._add()
    _pump(app, 4)
    su = [x for x in store.all("tasks") if x["title"] == "Su iç"][0]
    assert su["due"] == D(0)
    assert any(r.title_lbl.text() == "Su iç" for r in page.c_tasks.findChildren(Row))
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "plan_2_today.png"))

    # adım 3: odak en fazla 3; tarihsiz iş odak olunca bugüne yazılır
    page.next()
    _pump(app)
    undated = [x for x in store.open_tasks() if not x.get("due")][0]
    for tk in (undated, kira, fat, su):
        page.toggle_focus(store.get("tasks", tk["id"]))
        _pump(app)
    foc = store.focus_tasks(td)
    assert len(foc) == 3 and su not in foc, [x["title"] for x in foc]
    assert store.get("tasks", undated["id"])["due"] == D(0)
    page.intent.setText("Raporu bitir, spora git")
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "plan_3_focus.png"))
    page.next()
    _pump(app)
    assert store.day(td)["intention"] == "Raporu bitir, spora git"
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "plan_4_ready.png"))
    page.next()   # Güne başla
    _pump(app, 4)
    assert win.current == "today" and prefs.get("last_plan") == td.isoformat()
    assert store.day(td).get("planned_at")
    today = win.pages["today"]
    assert not today.c_plan.isVisible()
    assert "Raporu bitir" in today.sub_lbl.text()
    titles = [r.title_lbl.text() for r in today.c_todo.findChildren(Row)]
    assert set(titles[:3]) == {x["title"] for x in foc}, titles
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "plan_5_today_after.png"))
    # plan yapıldıysa bir daha kendiliğinden açılmaz; "last_page" plan olmaz
    win.maybe_plan()
    assert win.current == "today" and prefs.get("last_page") != "plan"
    # sonraki adımlar için örnek veriyi eski haline getir
    store.update("tasks", kira["id"], due=D(-1), focus=None)
    store.delete("tasks", fat["id"])
    store.delete("tasks", old["id"])
    store.delete("tasks", su["id"])
    _pump(app)


@step("Bugün takvimi: işaretler, gün seçimi, ay değiştirme · kategori ikonları")
def _calendar(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp import icons
    from alphaapp.components import Row
    from alphaapp.pages import CAT_ICON
    assert all(v in icons.P for v in CAT_ICON.values())
    td = date.today()
    win.show_page("today")
    _pump(app)
    page = win.pages["today"]
    cal = page.cal
    assert (cal.year, cal.month) == (td.year, td.month)
    a, b = cal.visible_range()
    assert a.weekday() == 0 and (b - a).days + 1 == cal.rows * 7
    final = [x for x in store.all("exams") if x["name"] == "Final"][0]
    fd = date.fromisoformat(final["date"])
    items = store.items_between(fd, fd)
    assert any(x["id"] == final["id"] for x in items.get(fd, [])), items
    # antrenman günleri yeşil nokta
    wd = date.fromisoformat(store.all("workouts")[0]["date"])
    page._cal_click(wd)
    _pump(app)
    assert "good" in cal.marks.get(wd, []), cal.marks.get(wd)
    # sınav gününe tıkla: ay gerekirse değişir, satır listelenir
    page._cal_click(fd)
    _pump(app)
    assert (cal.year, cal.month) == (fd.year, fd.month) and cal.selected == fd
    assert "bad" in cal.marks.get(fd, [])
    titles = [r.title_lbl.text() for r in page.c_cal.findChildren(Row)]
    assert any("Final" in x for x in titles), titles
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "today_calendar_selected.png"))
    page._cal_shift(1)
    page._cal_shift(-13)
    page._cal_shift(12)
    page._cal_today()
    _pump(app)
    assert (cal.year, cal.month) == (td.year, td.month) and cal.selected is None
    assert not page.cal_today_btn.isVisible()


@step("kareler: ders çalışma günü, alışkanlık işaretle + seri, beslenme toplamı / sık yenen / form doldurma")
def _squares(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.store import streaks
    from alphaapp.components import DayGrid, Row
    from alphaapp.forms import FormDialog
    td = date.today()
    D = lambda k: td - timedelta(days=k)  # noqa: E731
    assert streaks({D(0), D(1), D(2)}, td) == (3, 3)
    assert streaks({D(1), D(2)}, td) == (2, 2)          # bugün henüz yok: dünden say
    assert streaks({D(0), D(5), D(6), D(7)}, td) == (1, 3)
    assert streaks(set(), td) == (0, 0)

    # ders: kareye tıkla → çalışma günü eklenir / kalkar
    win.show_page("education")
    _pump(app)
    course = [c for c in store.all("courses") if c["name"] == "Akışkanlar Mekaniği"][0]
    grids = win.pages["education"].findChildren(DayGrid)
    assert len(grids) == len(store.all("courses")), len(grids)
    assert td.isoformat() not in course.get("study_days", [])
    store.toggle_day("courses", course["id"], td, "study_days")
    _pump(app)
    assert td.isoformat() in store.get("courses", course["id"])["study_days"]
    g = win.pages["education"].findChildren(DayGrid)[0]
    assert g.weeks() >= 10, g.weeks()
    g.day_toggled.emit(td)   # aynı ders ilk sırada (isim sırası) → geri al
    _pump(app)
    assert td.isoformat() not in store.get("courses", course["id"])["study_days"]

    # alışkanlık: bugün listesinden işaretle
    win.show_page("habits")
    _pump(app)
    page = win.pages["habits"]
    kitap = [h for h in store.all("habits") if h["name"] == "Kitap oku"][0]
    rows = [r for r in page.c_today.findChildren(Row) if r.title_lbl.text() == "Kitap oku"]
    assert rows
    rows[0]._toggle()
    _pump(app)
    assert td.isoformat() in store.get("habits", kitap["id"])["days"]
    assert page.t_today.findChildren(type(page.title_lbl))  # kutu dolu
    assert len(page.findChildren(DayGrid)) == 2
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "habits_after_check.png"))

    # beslenme
    win.show_page("sport")
    _pump(app)
    sp = win.pages["sport"]
    tot = store.meal_totals(td)
    assert tot["kcal"] == 1250 and tot["protein"] == 95, tot
    from PyQt6.QtWidgets import QPushButton
    chips = [b for b in sp.c_food.findChildren(QPushButton) if b.objectName() == "Chip"]
    assert len(chips) == 3, len(chips)
    chips[0].click()
    _pump(app)
    assert len(store.meals_on(td)) == 4
    meal_rows = sp.c_meals.findChildren(Row)
    assert len(meal_rows) == 4, len(meal_rows)
    d = FormDialog(win, store, "meals")
    d.fields["name"][1].setCurrentText("Tavuk pilav")
    assert d.fields["kcal"][1].text() == "650", d.fields["kcal"][1].text()
    assert d.fields["protein"][1].text() == "45"
    d.deleteLater()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "sport_nutrition.png"))


@step("masaüstü widget'ı: açılıyor, içerik dolu, bölüm kapatılıyor, kaldırılıyor")
def _desk(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.config import prefs
    from alphaapp.components import Row
    from alphaapp.desk_widget import SECTIONS
    from alphaapp.i18n import S
    assert all("desk_sec_" + k in S for k in SECTIONS)
    win.set_desk(True)
    _pump(app)
    d = win.desk
    assert d.isVisible() and prefs.get("desk_widget") and win.titlebar.btn_desk.isChecked()
    n_rows = len(d.findChildren(Row))
    assert n_rows >= 3, n_rows
    # yapılacaklardan biri widget'tan işaretlenince veri güncellenir
    tk = [x for x in store.all("tasks") if x["title"] == "Kirayı öde"][0]
    rows = [r for r in d.findChildren(Row) if r.title_lbl.text() == "Kirayı öde"]
    assert rows, "görev widget'ta yok"
    rows[0]._toggle()
    _pump(app)
    assert store.get("tasks", tk["id"])["done"]
    store.update("tasks", tk["id"], done=False, done_at=None)
    _pump(app)
    d._toggle_section("program")
    _pump(app)
    assert "program" not in prefs.get("desk_sections")
    d._toggle_section("program")
    if ctx["shots"]:
        _pump(app, 6)
        d.grab().save(os.path.join(ctx["shots"], "desk_widget.png"))
    # ana pencere kapansa da widget açıkken uygulama yaşamalı: closeEvent quit planlamamalı
    d.set_mode("top")
    d.set_mode("bottom")
    assert d.isVisible()
    win.set_desk(False)
    _pump(app)
    assert not d.isVisible() and not prefs.get("desk_widget") and not win.titlebar.btn_desk.isChecked()


@step("ekran görüntüleri")
def _shots(ctx):
    shots, win, app = ctx["shots"], ctx["win"], ctx["app"]
    if not shots:
        return
    from alphaapp.theme import theme
    win.toast_w.hide()
    for th in ("amoled", "white"):
        theme.apply(th)
        for key in win.pages:
            win.show_page(key)
            _pump(app, 6)
            win.grab().save(os.path.join(shots, f"{th}_{key}.png"))
    theme.apply("amoled")
    from alphaapp.forms import FormDialog
    d = FormDialog(win, ctx["store"], "exams", ctx["store"].all("exams")[1])
    d.show()
    _pump(app, 6)
    d.grab().save(os.path.join(shots, "form_exam.png"))
    d.close()


if __name__ == "__main__":
    sys.exit(main())
