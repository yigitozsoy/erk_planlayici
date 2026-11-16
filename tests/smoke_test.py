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
os.environ["ALPHA_DATA_DIR"] = os.path.join(_tmp, "docs-alpha")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication, QLabel  # noqa: E402

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
    store.add("routine", {"title": "Akışkanlar Mekaniği", "category": "education", "days": sorted([wd, (wd + 2) % 7]),
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
    from alphaapp.config import prefs, DATA_DIR, APP_DIR, PREFS_FILE
    assert DATA_DIR.startswith(_tmp) and APP_DIR.startswith(_tmp) and PREFS_FILE.startswith(_tmp), DATA_DIR
    prefs.set("name", "Test")
    prefs.set("day_end_hour", 0)   # örnek veri takvim gününe göre; gece 00-04 arası da aynı sonuç
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
        if c not in ("notes", "days", "wheel"):
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


@step("web: anlık görüntü yalnızca gündem (hedef / not / ekonomi yok), kapalıyken gönderilmez")
def _web(ctx):
    import json
    from alphaapp import web
    from alphaapp.config import day_today
    store = ctx["store"]
    g = store.add("goals", {"title": "GIZLI_HEDEF_XYZ", "image": "gizli.png"})
    snap = web.build_snapshot(store)
    txt = json.dumps(snap, ensure_ascii=False)
    for bad in ("GIZLI_HEDEF_XYZ", "gizli.png", '"transactions"', '"notes"', '"goals"'):
        assert bad not in txt, bad
    td = day_today().isoformat()
    assert [d for d in snap["days"] if d["date"] == td][0]["blocks"], "bugün boş"
    assert len(snap["days"]) == web.DAYS_BACK + web.DAYS_AHEAD + 1
    assert web.page_url("https://ornek.net/api/alpha.php") == "https://ornek.net/alpha/"
    assert not web.url_ok("http://ornek.net/api/alpha.php") and web.url_ok("https://ornek.net/api/alpha.php")
    assert web.key_hash("a") in web.key_file_text("a") and "a'" not in web.key_file_text("a")
    assert not ctx["win"].web.enabled() and ctx["win"].web.push() is False
    store.delete("goals", g["id"])


@step("görev formu: Eğitim → sınav / teslim satırı, kaydedince Sınavlar'a gider (ders + tür tahmini)")
def _task_as_exam(ctx):
    from alphaapp.forms import FormDialog, guess_exam
    store, win = ctx["store"], ctx["win"]
    c = store.all("courses")[0]
    assert guess_exam(store, f"{c['name']}: Midterm 2 (D220)") == (c["id"], "Midterm 2")
    assert guess_exam(store, "Rapor teslim et")[1] == "Rapor teslimi"
    d = FormDialog(win, store, "tasks")
    assert d.exam_row is not None and d.exam_row[1].isHidden(), "kişisel kategoride görünmemeli"
    d.fields["category"][1].btns["education"].setChecked(True)
    assert not d.exam_row[1].isHidden()
    d.fields["title"][1].setText(f"{c['name']}: Quiz")
    d.exam_sw.setChecked(True)
    assert d.exam_course.currentData() == c["id"] and d.exam_kind.currentText() == "Quiz"
    n_ex, n_t = len(store.all("exams")), len(store.all("tasks"))
    d._save()
    assert len(store.all("exams")) == n_ex + 1 and len(store.all("tasks")) == n_t
    ex = store.all("exams")[-1]
    assert ex["course"] == c["id"] and ex["name"] == "Quiz" and d.coll == "exams"
    store.delete("exams", ex["id"])
    d2 = FormDialog(win, store, "tasks")          # anahtar kapalıyken normal görev
    d2.fields["category"][1].btns["education"].setChecked(True)
    d2.fields["title"][1].setText("Kitap oku")
    d2._save()
    assert len(store.all("tasks")) == n_t + 1
    store.delete("tasks", store.all("tasks")[-1]["id"])


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
        if coll in ("notes", "days", "wheel"):
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

    # ders: kareye tıkla → çalışma günü eklenir / kalkar (kareler Alışkanlıklar'da, alışkanlıkların altında)
    win.show_page("habits")
    _pump(app)
    course = [c for c in store.all("courses") if c["name"] == "Akışkanlar Mekaniği"][0]
    assert not win.pages["education"].findChildren(DayGrid)
    n_hab = len(store.all("habits"))
    grids = [g for g in win.pages["habits"].findChildren(DayGrid) if g.isVisible()]
    assert len(grids) == n_hab + len(store.all("courses")), len(grids)
    assert td.isoformat() not in course.get("study_days", [])
    store.toggle_day("courses", course["id"], td, "study_days")
    _pump(app)
    assert td.isoformat() in store.get("courses", course["id"])["study_days"]
    cards = [c for c in win.pages["habits"].cards_host.findChildren(type(win.pages["habits"].c_today))
             if getattr(c, "grid", None) is not None and c.title_lbl.text() == "Akışkanlar Mekaniği" and c.isVisible()]
    g = cards[0].grid
    assert g.weeks() >= 10, g.weeks()
    g.day_toggled.emit(td)   # geri al
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
    assert len([g for g in page.findChildren(DayGrid) if g.isVisible()]) == 2 + len(store.all("courses"))
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
    assert set(sp.food_rings) == {"kcal", "protein", "carbs", "fat"}
    assert abs(sp.food_rings["kcal"].value - 1250 / float(__import__("alphaapp.config").config.prefs.get("goal_kcal") or 1)) < 1e-6
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


@step("sürüm 2: önemliler kırmızı kutu, ikonlu kategori, konum kapatma, alışkanlıklar programda")
def _v2(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.config import prefs
    from alphaapp.forms import FormDialog, CategoryPicker
    from alphaapp.pages.schedule import Block
    td = date.today()
    # kategori ikonları: tek tıkla seçilir, değer kaydedilir
    d = FormDialog(win, store, "tasks")
    cp = d.fields["category"][1]
    assert isinstance(cp, CategoryPicker) and cp.value() == "personal"
    cp.btns["sport"].click()
    assert cp.value() == "sport"
    d.fields["title"][1].setText("Koşu ayakkabısı")
    d._save()
    assert d.item["category"] == "sport"
    d.deleteLater()
    # önemli program kaydı kırmızı kutu olur
    r = store.add("routine", {"title": "Önemli ders", "category": "education", "days": [td.weekday()],
                              "start": "08:00", "end": "09:00", "place": "Z-10", "important": True})
    page = win.pages["schedule"]
    win.show_page("schedule")
    _pump(app)
    page.refresh()
    imp = [b for b in page.findChildren(Block) if b.objectName() == "BlockImportant"]
    assert imp, "önemli kutu yok"
    texts = lambda: [lb.text() for lb in page.findChildren(QLabel)]  # noqa: E731
    assert "Z-10" in texts()
    # konum kapatılınca formda yer alanı yok, programda konum yazmaz
    prefs.set("show_place", False)
    page.refresh()
    assert "Z-10" not in texts()
    d = FormDialog(win, store, "routine", store.get("routine", r["id"]))
    assert "place" not in d.fields
    d._save()
    assert store.get("routine", r["id"])["place"] == "Z-10"   # gizli alan silinmez
    d.deleteLater()
    prefs.set("show_place", True)
    # alışkanlıklar programda: kutu çıkar, tıklayınca o gün işaretlenir
    h = store.add("habits", {"name": "Gitar çal", "category": "personal", "goal": 7, "days": [],
                             "weekdays": [td.weekday()]})
    page.refresh()
    assert not [b for b in page.findChildren(Block) if "Gitar çal" in " ".join(
        lb.text() for lb in b.findChildren(QLabel))]
    prefs.set("habits_in_schedule", True)
    page.refresh()
    hb = [b for b in page.findChildren(Block) if "Gitar çal" in " ".join(
        lb.text() for lb in b.findChildren(QLabel))]
    assert len(hb) == 1, len(hb)
    hb[0].clicked.emit()
    _pump(app)
    assert td.isoformat() in store.get("habits", h["id"])["days"]
    d = FormDialog(win, store, "habits", store.get("habits", h["id"]))
    assert "weekdays" in d.fields and d.fields["weekdays"][1].value() == [td.weekday()]
    d.deleteLater()


@step("veri taşıma: eski %LOCALAPPDATA%\\alpha\\data.json bir kez Belgeler\\alpha'ya kopyalanır")
def _migrate(ctx):
    import json
    import subprocess
    base = tempfile.mkdtemp(prefix="alpha-mig-")
    old = os.path.join(base, "local", "alpha")
    os.makedirs(os.path.join(old, "backups"))
    with open(os.path.join(old, "data.json"), "w", encoding="utf-8") as f:
        json.dump({"tasks": [{"id": "x", "title": "eski"}]}, f)
    open(os.path.join(old, "backups", "data-2026-01-01.json"), "w").close()
    new = os.path.join(base, "docs", "alpha")
    env = dict(os.environ, LOCALAPPDATA=os.path.join(base, "local"), ALPHA_DATA_DIR=new)
    import time

    def run(code="import alphaapp.config as c; c.migrate_old_data()"):
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr

    def title(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["tasks"][0]["title"]

    def write(path, text):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"tasks": [{"id": "x", "title": text}]}, f)

    run("import alphaapp.config")                       # yalnızca içe aktarmak hiçbir şey kopyalamaz
    assert not os.path.exists(os.path.join(new, "data.json"))
    run()
    assert title(os.path.join(new, "data.json")) == "eski"
    # eski 1.x uygulaması açık kaldı ve yazmaya devam etti, yenisine dokunulmadı → yeniden kopyala
    time.sleep(1.2)
    write(os.path.join(old, "data.json"), "eski-sonra")
    run()
    assert title(os.path.join(new, "data.json")) == "eski-sonra"
    # yeni sürümde değişiklik yapıldıysa eski dosya bir daha asla üzerine yazmaz
    time.sleep(1.2)
    write(os.path.join(new, "data.json"), "yeni")
    time.sleep(1.2)
    write(os.path.join(old, "data.json"), "eski-en-son")
    run()
    assert title(os.path.join(new, "data.json")) == "yeni"
    assert os.path.exists(os.path.join(new, "backups", "data-2026-01-01.json"))
    assert os.path.exists(os.path.join(old, "data.json"))   # eski kopya silinmez


@step("sabah planı 2: 1-5 tuşları, dünün özeti, ilerleme, zaman şeridi + boşluğa iş koyma")
def _plan2(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.timeline import find_gaps
    assert find_gaps([(540, 600), (580, 660), (720, 780)], 480, 840) == [(480, 540), (660, 720), (780, 840)]
    assert find_gaps([(500, 520)], 480, 540) == []          # 30 dk altı boşluk yok
    td = date.today()
    D = lambda k: (td + timedelta(days=k)).isoformat()  # noqa: E731
    a = store.add("tasks", {"title": "Gecikmiş A", "category": "work", "due": D(-1)})
    b = store.add("tasks", {"title": "Gecikmiş B", "category": "work", "due": D(-2)})
    page = win.pages["plan"]
    page.start()
    win.show_page("plan")
    _pump(app)
    assert all(sc.isEnabled() for sc in page.shortcuts)
    assert page.y_grid.isVisible() and page.y_tasks.val.text()
    order = list(page.carry_order)
    ia, ib = order.index(a["id"]), order.index(b["id"])
    page._set_cur(ia)
    page._key_pick("tomorrow")                      # "2"
    assert page.choices[a["id"]] == "tomorrow" and page.cur == min(ia + 1, len(order) - 1)
    page._set_cur(ib)
    page._key_pick("done")                          # "4"
    assert page.carry_rows[b["id"]].btns["done"].isChecked()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "plan_1_carry.png"))
    page.next()
    _pump(app)
    assert not any(sc.isEnabled() for sc in page.shortcuts)    # yazı alanlarında 1-5 yutulmasın
    assert store.get("tasks", a["id"])["due"] == D(1) and store.get("tasks", b["id"])["done"]
    tl = page.timeline
    assert tl.items, "şeritte kutu yok"
    # boşluğa iş koyma (menünün yaptığı güncelleme)
    c = store.add("tasks", {"title": "Saatsiz iş", "category": "personal", "due": D(0)})
    page.refresh()
    if tl.gaps:
        g = tl.gaps[0]
        from alphaapp.timeline import hhmm
        store.update("tasks", c["id"], time=hhmm(g[0]))
        _pump(app)
        page.refresh()
        assert any(x["item"]["id"] == c["id"] for x in tl.items if x["coll"] == "tasks")
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "plan_2_today.png"))
    for x in (a, b, c):
        store.delete("tasks", x["id"])
    prefs_today = date.today().isoformat()
    from alphaapp.config import prefs
    prefs.set("last_plan", prefs_today)
    win.show_page("today")
    _pump(app)


@step("program tarih aralığı (ilk hafta / son gün), görev bitiş saati, dosya dışarıdan değişince yeniden okuma")
def _range_reload(ctx):
    import json
    import time
    store, app = ctx["store"], ctx["app"]
    from alphaapp.forms import FormDialog
    td = date.today()
    wd = td.weekday()
    r = store.add("routine", {"title": "Dönemlik ders", "category": "education", "days": [wd], "start": "07:00",
                              "end": "07:50", "from": (td - timedelta(days=7)).isoformat(),
                              "until": (td + timedelta(days=7)).isoformat()})
    ids = lambda d: [x["id"] for x in store.routine_for(d)]  # noqa: E731
    assert r["id"] in ids(td) and r["id"] in ids(td + timedelta(days=7))
    assert r["id"] not in ids(td - timedelta(days=14)) and r["id"] not in ids(td + timedelta(days=14))
    d = FormDialog(ctx["win"], store, "routine", r)
    assert "from" in d.fields and "until" in d.fields
    d.deleteLater()
    d = FormDialog(ctx["win"], store, "tasks")
    assert "end" in d.fields
    d.deleteLater()
    store.delete("routine", r["id"])
    store.flush()
    _pump(app)
    # başka biri (ya da elle) dosyayı değiştirdi → bekleyen kayıt yoksa yeniden okunur
    assert not store.check_external()
    time.sleep(1.1)
    with open(store.path, encoding="utf-8") as f:
        raw = json.load(f)
    raw["tasks"].append({"id": "disaridan1", "title": "Dışarıdan eklendi", "category": "personal"})
    with open(store.path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False)
    assert store.check_external()
    assert store.get("tasks", "disaridan1")
    store.delete("tasks", "disaridan1")
    store.flush()
    assert not store.check_external()


@step("program sürükle-bırak: görev başka güne, ders yalnızca bu hafta / her hafta, geri al")
def _dnd(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from PyQt6.QtCore import QMimeData, QPointF, Qt
    from PyQt6.QtGui import QDropEvent, QDragEnterEvent
    from alphaapp.pages.schedule import MIME, Block
    page = win.pages["schedule"]
    win.show_page("schedule")
    page._shift(0, reset=True)
    _pump(app)
    ws = page.col_dates[0]
    mon, wed = ws, ws + timedelta(days=2)
    tk = store.add("tasks", {"title": "Taşınacak iş", "category": "work", "due": mon.isoformat(), "time": "11:00"})
    page.refresh()
    blk = [b for b in page.findChildren(Block) if b.drag_info and b.drag_info[1]["id"] == tk["id"]]
    assert blk and blk[0].drag_info[2] == mon
    # bırakma olayı: çarşamba sütunu hedef tarihi kaydeder ve vurgusu kalkar
    md = QMimeData()
    md.setData(MIME, f"tasks:{tk['id']}".encode())
    col = page.cols[2]
    ev = QDragEnterEvent(col.rect().center(), Qt.DropAction.MoveAction, md, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier)
    page.eventFilter(col, ev)
    assert col.objectName() == "CardDrop"
    ev = QDropEvent(QPointF(col.rect().center()), Qt.DropAction.MoveAction, md, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    page.eventFilter(col, ev)
    assert page._drop_date == wed and col.objectName() != "CardDrop"
    page.move_item("tasks", tk["id"], mon, wed)
    assert store.get("tasks", tk["id"])["due"] == wed.isoformat()
    win.toast_w._clicked()                      # geri al
    assert store.get("tasks", tk["id"])["due"] == mon.isoformat()
    store.delete("tasks", tk["id"])
    # haftalık ders: yalnızca bu hafta
    r = store.add("routine", {"title": "Sürüklenen ders", "category": "education", "days": [0], "start": "13:00",
                              "end": "14:00"})
    ids = lambda d: [x["id"] for x in store.routine_for(d)]  # noqa: E731
    titles = lambda d: [x["title"] for x in store.routine_for(d)]  # noqa: E731
    page.move_item("routine", r["id"], mon, wed, mode="once")
    assert r["id"] not in ids(mon) and "Sürüklenen ders" in titles(wed)
    assert r["id"] in ids(mon + timedelta(days=7)) and "Sürüklenen ders" not in titles(wed + timedelta(days=7))
    win.toast_w._clicked()
    assert r["id"] in ids(mon) and "Sürüklenen ders" not in titles(wed)
    # her hafta
    page.move_item("routine", r["id"], mon, wed, mode="week")
    assert store.get("routine", r["id"])["days"] == [2]
    win.toast_w._clicked()
    assert store.get("routine", r["id"])["days"] == [0]
    store.delete("routine", r["id"])
    _pump(app)


@step("programda güne sağ tık: menü açılır, seçenekler o güne ön değerle form açar")
def _day_menu(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QContextMenuEvent
    from alphaapp.forms import FormDialog
    page = win.pages["schedule"]
    win.show_page("schedule")
    _pump(app)
    col, d = page.cols[3], page.col_dates[3]
    called = []
    orig = page.day_menu
    page.day_menu = lambda dd, pos: called.append(dd)
    page.eventFilter(col, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5), col.mapToGlobal(QPoint(5, 5))))
    page.day_menu = orig
    assert called == [d]
    acts = page.day_actions(d)
    assert len(acts) >= 5
    for _text, coll, preset in acts:
        dlg = FormDialog(win, store, coll, preset=dict(preset))
        v = dlg.values()
        if coll == "tasks":
            assert v["due"] == d.isoformat()
        elif coll == "routine":
            assert v["days"] == [d.weekday()]
            if "from" in preset:
                assert v["from"] == v["until"] == d.isoformat()
        else:
            assert v["date"] == d.isoformat()
        dlg.deleteLater()
    # bu güne özel ders yalnızca o gün görünür
    once = dict(acts[2][2], title="Tek seferlik", category="education", start="09:00", end="10:00")
    r = store.add("routine", once)
    assert r["id"] in [x["id"] for x in store.routine_for(d)]
    assert r["id"] not in [x["id"] for x in store.routine_for(d + timedelta(days=7))]
    store.delete("routine", r["id"])
    _pump(app)


@step("hatırlatıcı: X dk önce bir kez çalar, ertele, kapalıyken kaçan gelir, başlamış gelmez, ses dosyası")
def _reminders(ctx):
    import wave
    from datetime import datetime
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.config import prefs
    from alphaapp import sounds
    from alphaapp.reminders import upcoming, ReminderPopup
    rm = win.reminders
    td = date.today()
    prefs.set("reminder_lead", 10)
    prefs.set("reminded", None)
    tk = store.add("tasks", {"title": "Hatırlat beni", "category": "work", "due": td.isoformat(), "time": "15:00",
                             "end": "16:00", "priority": "high"})
    at = lambda h, m: datetime(td.year, td.month, td.day, h, m)  # noqa: E731
    keys = lambda now: [r["key"] for r in rm.due(now)]  # noqa: E731
    key = f"tasks:{tk['id']}:{td.isoformat()}T15:00"
    assert key in [r["key"] for r in upcoming(store, td)]
    assert key not in keys(at(14, 49))                 # 11 dk önce: henüz değil
    assert key in keys(at(14, 50))                     # 10 dk önce
    assert key in keys(at(14, 58))                     # uygulama kapalıydı, sonra açıldı: hâlâ gelir
    assert key not in keys(at(15, 2))                  # başladı: gelmez
    got = rm.check(at(14, 51))
    assert any(r["key"] == key for r in got)
    _pump(app)
    pops = [p for p in rm.popups if p.r["key"] == key]
    assert pops and pops[0].isVisible()
    assert key not in keys(at(14, 52))                 # bir kez
    rm.snooze(pops[0].r)
    rm.snoozes[key] = at(14, 56)
    assert key not in keys(at(14, 55)) and key in keys(at(14, 56))
    for p in list(rm.popups):
        p.close()
    prefs.set("reminders_on", False)
    prefs.set("reminded", None)
    assert rm.due(at(14, 55)) == []
    prefs.set("reminders_on", True)
    # sesler: dosya üretilir, offscreen'de çalınmaz
    for name in ("chime", "soft", "alarm"):
        p = sounds.ensure(name, 0.5)
        with wave.open(p) as w:
            assert w.getframerate() == sounds.RATE and w.getnframes() > 10000
        assert p.startswith(os.environ["LOCALAPPDATA"])
    assert sounds.play("chime", 0.5) is False
    t_pop = rm.test()
    assert isinstance(t_pop, ReminderPopup)
    if ctx["shots"]:
        _pump(app, 6)
        t_pop.grab().save(os.path.join(ctx["shots"], "reminder.png"))
        p2 = rm.show(upcoming(store, td)[[r["key"] for r in upcoming(store, td)].index(key)], at(14, 50))
        _pump(app, 6)
        p2.grab().save(os.path.join(ctx["shots"], "reminder_important.png"))
        p2.close()
    t_pop.close()
    store.delete("tasks", tk["id"])
    prefs.set("reminded", None)
    _pump(app)


@step("gün bitişi: gece 02:00 hâlâ dünkü gün sayılır (done_at → mantıksal gün)")
def _day_end(ctx):
    from datetime import datetime
    from alphaapp.config import prefs, day_of, day_today
    prefs.set("day_end_hour", 4)
    assert str(day_of("2026-11-14T02:30:00")) == "2026-11-13"
    assert str(day_of("2026-11-14T04:00:00")) == "2026-11-14"
    assert str(day_of("2026-11-14")) == "2026-11-14"          # yalnızca tarih: kaydırma yok
    assert day_of("") is None and day_of("bozuk") is None
    now = datetime.now()
    assert day_today() == (now.date() if now.hour >= 4 else now.date() - timedelta(days=1))
    prefs.set("day_end_hour", 0)
    assert str(day_of("2026-11-14T02:30:00")) == "2026-11-14" and day_today() == date.today()


@step("ekonomi: nakit, sabit gelir/gider, borçsuz hedef kartı; tanınmayan bölümler kayıtta korunur")
def _finance_goal(ctx):
    import json
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.config import prefs, day_today
    from alphaapp.components import Row
    td = day_today()
    goal = date(td.year + 1, 1, 1)
    prefs.set("debt_free_goal", goal.isoformat())
    acc = store.add("accounts", {"name": "Nakit", "balance": 550})
    inc = store.add("recurring", {"name": "Maaş", "kind": "income", "amount": 15000, "day": 5, "active": True})
    exp = store.add("recurring", {"name": "Kira", "kind": "expense", "amount": 4000, "day": 1, "active": True})
    occ = store.recurring_between(td, goal - timedelta(days=1))
    assert all(td < d < goal for d, _ in occ)
    assert sum(1 for _, r in occ if r["id"] == inc["id"]) == len({(d.year, d.month) for d, r in occ
                                                                   if r["id"] == inc["id"]})
    page = win.pages["finance"]
    win.show_page("finance")
    _pump(app)
    page.refresh()
    assert page.c_goal.isVisible()
    titles = [r.title_lbl.text() for r in page.c_goal.findChildren(Row)]
    assert any("Elindeki nakit" in x for x in titles), titles
    for key in ("fixed", "cash"):
        page.tabs.btns[key].click()
        _pump(app)
        assert page.tab_cards[key].isVisible()
    if ctx["shots"]:
        page.tabs.btns["fixed"].click()
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "finance_goal.png"))
    page.tabs.btns["tx"].click()
    for x, c in ((acc, "accounts"), (inc, "recurring"), (exp, "recurring")):
        store.delete(c, x["id"])
    # daha yeni bir sürümün yazdığı bölüm silinmez
    store.flush()
    with open(store.path, encoding="utf-8") as f:
        raw = json.load(f)
    raw["gelecek_bolum"] = [{"id": "z"}]
    import time
    time.sleep(1.1)
    with open(store.path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False)
    assert store.check_external()
    store.add("notes", {"title": "tetik"})
    store.flush()
    with open(store.path, encoding="utf-8") as f:
        assert json.load(f).get("gelecek_bolum") == [{"id": "z"}]


@step("spora ara: hedef orantılı düşer, ara haftası seriyi bozmaz, arayı bitir")
def _sport_break(ctx):
    from alphaapp.config import prefs, day_today
    from alphaapp.store import week_start
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    td = day_today()
    ws = week_start(td)
    prefs.set("sport_weekly_goal", 4)
    prefs.set("sport_break", {})
    assert store.sport_goal(ws) == 4 and store.sport_break() is None
    # tüm hafta ara → 0
    prefs.set("sport_break", {"from": ws.isoformat(), "until": (ws + timedelta(days=6)).isoformat()})
    assert store.sport_goal(ws) == 0
    assert store.sport_goal(ws + timedelta(weeks=1)) == 4
    # 3 gün ara → round(4*4/7) = 2
    prefs.set("sport_break", {"from": ws.isoformat(), "until": (ws + timedelta(days=2)).isoformat()})
    assert store.sport_goal(ws) == 2
    # seri: geçen hafta ara, iki hafta önce hedef tutmuş → seri 1 (ara haftası atlanır)
    for k in range(1, 4):
        a = ws - timedelta(weeks=k)
        for w in store.workouts_between(a, a + timedelta(days=6)):
            store.delete("workouts", w["id"])
    a2 = ws - timedelta(weeks=2)
    for i in range(4):
        store.add("workouts", {"date": (a2 + timedelta(days=i)).isoformat(), "kind": "Koşu", "minutes": 30})
    a1 = ws - timedelta(weeks=1)
    prefs.set("sport_break", {"from": a1.isoformat(), "until": (a1 + timedelta(days=6)).isoformat(), "note": "sakatlık"})
    sp = win.pages["sport"]
    win.show_page("sport")
    _pump(app)
    sp.refresh()
    assert sp.t_streak.findChildren(type(sp.title_lbl))
    streak_txt = [lb.text() for lb in sp.t_streak.findChildren(type(sp.title_lbl)) if lb.objectName() == "StatValue"]
    assert streak_txt and int(streak_txt[0]) >= 1, streak_txt
    # bu hafta ara
    prefs.set("sport_break", {"from": td.isoformat(), "until": (td + timedelta(days=10)).isoformat()})
    sp.refresh()
    _pump(app)
    assert sp.break_btn.isChecked()
    win.pages["today"].refresh()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "sport_break.png"))
    prefs.set("sport_break", {})
    sp.refresh()
    assert not sp.break_btn.isChecked()


@step("hedefler: örnek ağaç, Pinterest panosu (masonry, filtre, Ctrl+V / bırak görsel), çark, silme + geri al, döngü")
def _goals(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from PyQt6.QtCore import QMimeData
    from PyQt6.QtGui import QImage, QPainter, QLinearGradient, QColor, QGuiApplication
    from alphaapp.config import IMAGES_DIR
    from alphaapp.forms import FormDialog
    from alphaapp.pages.goals import image_from_mime
    from alphaapp.store import LIFE_AREAS, life_area, life_scores
    page = win.pages["goals"]
    win.show_page("goals")
    _pump(app)
    assert page.c_empty.isVisible() and not page.board_host.isVisible()
    page._add_sample()
    _pump(app, 4)
    goals = store.all("goals")
    assert len(goals) >= 40, len(goals)
    assert page.sample_btn.isVisible()
    page.tabs.select("board")
    _pump(app, 4)
    assert page.board_host.isVisible()
    board = page.board
    pins = [g for _i, _f, g in board.tiles if g is not None]
    assert board.tiles[0][2] is None                                   # ilk kutu: + hedef ekle
    assert not any(g.get("horizon") == "action" for g in pins)        # eylemler panoda yok (görselsizse)
    # masonry: sütunlar dolu ve kartlar üst üste binmiyor
    rects = [f for _i, f, _g in board.tiles]
    assert len({round(r.x()) for r in rects}) >= 3
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not a.intersects(b), (a, b)

    # görseller: panodan yapıştır (karta) ve bırak (boşa → yeni hedef formu)
    def make(w, h, c1, c2):
        img = QImage(w, h, QImage.Format.Format_RGB32)
        p = QPainter(img)
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0, QColor(c1))
        g.setColorAt(1, QColor(c2))
        p.fillRect(img.rect(), g)
        p.end()
        return img
    imgs = [make(600, 900, "#3a4a55", "#c9b38a"), make(800, 520, "#2b3d2f", "#9fb48d"),
            make(600, 760, "#5a3a32", "#d8a48f"), make(700, 700, "#2c2c2c", "#8f8f8f")]
    targets = [g for g in pins if g.get("horizon") != "life"][:4]
    for g, img in zip(targets, imgs):
        md = QMimeData()
        md.setImageData(img)
        QGuiApplication.clipboard().setMimeData(md)
        board._hover = [k for k, (_i, _f, x) in enumerate(board.tiles) if x is g][0]
        name = board.paste()
        assert name and os.path.exists(os.path.join(IMAGES_DIR, name)), name
        _pump(app)
        assert store.get("goals", g["id"])["image"] == name
    board._hover = None
    _pump(app, 4)
    g0 = store.get("goals", targets[0]["id"])
    assert abs(board.ratio(g0) - 1.5) < 0.01, board.ratio(g0)
    win.toast_w._clicked()                                             # son görseli geri al
    assert not store.get("goals", targets[3]["id"]).get("image")
    store.update("goals", targets[3]["id"], image=image_from_mime(md))
    # boşa bırakılan görsel: yeni hedef formu görselle açılır
    opened = []
    import alphaapp.pages.goals as gm
    orig = gm.edit_item
    gm.edit_item = lambda w, coll, item=None, preset=None: opened.append(preset)
    page._image_in(None, "x.png")
    gm.edit_item = orig
    assert opened and opened[0]["image"] == "x.png"
    d = FormDialog(win, store, "goals", preset={"image": "x.png", "title": "Yeni"})
    assert d.fields["image"][1].value() == "x.png"
    d.deleteLater()
    # alan filtresi
    page._set_area("body")
    _pump(app, 4)
    assert all(life_area(g.get("area")) == "body" for _i, _f, g in board.tiles if g is not None)
    assert [g for _i, _f, g in board.tiles if g is not None]
    page._set_area("all")
    _pump(app, 4)
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "goals_board.png"))
        page.verticalScrollBar().setValue(page.verticalScrollBar().maximum())
        _pump(app, 4)
        win.grab().save(os.path.join(shots, "goals_board_bottom.png"))
        page.verticalScrollBar().setValue(0)
    root = store.goal_roots()[0]
    assert store.goal_activity(root)[0] > 0 and 0 <= store.goal_progress(root) <= 1
    edu = [g for g in goals if any(str(x).startswith("courses:") for x in g.get("links") or [])]
    c1 = [c for c in store.all("courses") if c.get("study_days")][0]
    linked = [g for g in edu if g["links"] == [f"courses:{c1['id']}"]][0]
    assert store.goal_activity(linked)[0] > 0
    # denge: puanlar verilerden (elle puan yok)
    from alphaapp.balance import area_report, history, month_ends
    page.tabs.select("wheel")
    _pump(app, 4)
    assert page.wheel_row.isVisible() and not page.board_host.isVisible()
    td = date.today()
    bal = page.balance
    assert set(bal.report) == set(LIFE_AREAS) and len(bal.rects) == len(LIFE_AREAS) + 1
    for ar in LIFE_AREAS:
        sc = bal.report[ar]["score"]
        assert sc is None or 0 <= sc <= 10, (ar, sc)
        assert len(bal.hist[ar]) == 6
    assert bal.report["body"]["score"] is not None and bal.report["education"]["parts"]
    ends = month_ends(td)
    assert ends[-1] == td and all(ends[i] < ends[i + 1] for i in range(5))
    # bilinen veri: 30 günde haftalık hedef kadar spor → spor parçası tam
    from alphaapp.config import prefs
    prefs.set("sport_weekly_goal", 2)
    extra = [store.add("workouts", {"date": (td - timedelta(days=k)).isoformat(), "kind": "Koşu"})
             for k in range(0, 30, 3)]
    rep = area_report(store, td)
    sport = [f for s_, f in rep["body"]["parts"] if "Spor" in s_]
    assert sport and sport[0] == 1.0, rep["body"]
    for w in extra:
        store.delete("workouts", w["id"])
    prefs.set("sport_weekly_goal", 4)
    h, _e = history(store, td)
    assert all(len(v) == 6 for v in h.values())
    page._show_area("body")
    _pump(app, 4)
    assert page.view == "board" and page.area == "body"
    page.area = "all"
    page.tabs.select("wheel")
    _pump(app, 4)
    # eski (kategori anahtarlı) kayıtlar yeni alanlara eşlenir
    assert life_area("work") == "career" and life_area("sport") == "body" and life_area("personal") == "growth"
    assert life_area("venture") == "venture" and life_area(None) == "growth" and life_area("??") == "growth"
    assert life_scores({"sport": 5, "work": 4, "social": 3, "personal": 6}) == {"body": 5, "career": 4, "growth": 6}
    assert life_scores({"body": 7, "sport": 2}) == {"body": 7}
    old = store.add("goals", {"title": "Eski kayıt", "area": "work", "horizon": "year", "sample": True})
    d = FormDialog(win, store, "goals", old)
    assert d.fields["area"][1].value() == "career" and len(d.fields["area"][1].btns) == len(LIFE_AREAS)
    d.fields["area"][1].btns["venture"].click()
    d._save()
    assert store.get("goals", old["id"])["area"] == "venture"
    d.deleteLater()
    store.delete("goals", old["id"])
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "goals_wheel.png"))
    # sütun silinince alt hedefleri de gider, geri al hepsini döndürür
    n0 = len(store.all("goals"))
    pillar = store.goal_children(root["id"])[1]
    kids = len(store.goal_descendants(pillar["id"]))
    assert kids >= 5
    removed = store.delete("goals", pillar["id"])
    assert len(store.all("goals")) == n0 - kids - 1
    store.restore(removed)
    assert len(store.all("goals")) == n0 and len(store.goal_descendants(pillar["id"])) == kids
    # üst hedef kendi alt hedefi seçilemez (döngü)
    sub = store.add("goals", {"title": "Ara hedef", "horizon": "term", "parent": pillar["id"], "sample": True})
    n0 += 1
    d = FormDialog(win, store, "goals", store.get("goals", pillar["id"]))
    cb = d.fields["parent"][1]
    assert cb.findData(sub["id"]) >= 0
    cb.setCurrentIndex(cb.findData(sub["id"]))
    assert d.fields["links"][1].value() == pillar.get("links", [])
    d._save()
    assert store.get("goals", pillar["id"])["parent"] == root["id"]
    d.deleteLater()
    child = store.goal_children(pillar["id"])[0]
    store.toggle_day("goals", child["id"], td)
    assert td.isoformat() in store.get("goals", child["id"])["days"]
    # örnekleri sil + geri al
    page._remove_sample()
    _pump(app)
    assert not store.all("goals")
    win.toast_w._clicked()
    _pump(app)
    assert len(store.all("goals")) == n0
    page.tabs.select("board")
    _pump(app)


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
    d = FormDialog(win, ctx["store"], "routine", ctx["store"].all("routine")[0])
    d.show()
    _pump(app, 6)
    d.grab().save(os.path.join(shots, "form_routine.png"))
    d.close()


if __name__ == "__main__":
    sys.exit(main())
