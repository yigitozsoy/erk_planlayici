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
    from alphaapp.navmenu import BUILTIN
    missing |= {v[1] for v in BUILTIN.values()} - set(S)
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
    for bad in ("GIZLI_HEDEF_XYZ", "gizli.png", '"transactions"', '"notes"', '"goals"', '"wishlist"'):
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
    assert guess_exam(store, f"{c['name']}: Midterm 2 (D220)") == (c["id"], "Vize 2")
    from alphaapp import grades as _gr
    assert _gr.exam_canon("midterm 1") == "Vize 1" and _gr.exam_canon("Lab") == "Laboratuvar"
    assert _gr.exam_label("Vize 2", False) == "Midterm 2" and _gr.exam_canon("Kendi sınavım") == "Kendi sınavım"
    assert _gr.exam_order("Final") > _gr.exam_order("Vize 2") > _gr.exam_order("Vize 1")
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

    # ders: kareler Eğitim'deki ders kartında (son 2 ay + önümüzdeki 1 ay), tıkla = o gün çalıştım
    win.show_page("education")
    _pump(app)
    course = [c for c in store.all("courses") if c["name"] == "Akışkanlar Mekaniği"][0]
    egrids = [g for g in win.pages["education"].findChildren(DayGrid) if g.isVisible()]
    assert len(egrids) == len(store.all("courses")), len(egrids)
    assert td.isoformat() not in course.get("study_days", [])
    store.toggle_day("courses", course["id"], td, "study_days")
    _pump(app)
    assert td.isoformat() in store.get("courses", course["id"])["study_days"]
    from alphaapp.components import Card
    cards = [c for c in win.pages["education"].findChildren(Card)
             if getattr(c, "grid", None) is not None and c.title_lbl.text() == "Akışkanlar Mekaniği" and c.isVisible()]
    g = cards[0].grid
    from datetime import timedelta as _td
    assert g.span == (2, 1) and 13 <= g.weeks() <= 15, g.weeks()
    f0 = g.first_day()
    last = f0 + _td(weeks=g.weeks()) - _td(days=1)
    assert f0.weekday() == 0 and last.weekday() == 6 and 55 <= (td - f0).days <= 68 and 28 <= (last - td).days <= 37,         (f0, last)
    assert 9 <= g.CELL <= 24, g.CELL            # kare, en fazla 24 px (kullanıcı büyüğünü istemedi)
    g.day_toggled.emit(td)   # geri al
    _pump(app)
    assert td.isoformat() not in store.get("courses", course["id"])["study_days"]
    win.show_page("habits")
    _pump(app)
    assert len([g for g in win.pages["habits"].findChildren(DayGrid) if g.isVisible()]) == len(store.all("habits"))

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
    assert len([g for g in page.findChildren(DayGrid) if g.isVisible()]) == len(store.all("habits"))
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
    h = store.add("habits", {"name": "Gitar çal", "category": "sport", "goal": 7, "days": [],
                             "weekdays": [td.weekday()]})
    hp = store.add("habits", {"name": "GIZLI_KISISEL_ALISKANLIK", "category": "personal", "goal": 7})
    prefs.set("habits_in_schedule", False)
    page.refresh()
    assert not [b for b in page.findChildren(Block) if "Gitar çal" in " ".join(
        lb.text() for lb in b.findChildren(QLabel))]
    prefs.set("habits_in_schedule", True)
    page.refresh()
    hb = [b for b in page.findChildren(Block) if "Gitar çal" in " ".join(
        lb.text() for lb in b.findChildren(QLabel))]
    assert len(hb) == page.weeks, len(hb)        # günde tek alışkanlık kutusu (her haftada bir)
    hb = hb[:1]                                  # ilk bulunan = bu haftanın kutusu
    txt = " ".join(lb.text() for lb in hb[0].findChildren(QLabel))
    assert "/" in txt, txt                       # spor alışkanlıkları tek kutuda
    assert not [b for b in page.findChildren(Block) if "GIZLI_KISISEL" in " ".join(
        lb.text() for lb in b.findChildren(QLabel))]   # programda yalnızca spor alışkanlıkları
    store.delete("habits", hp["id"])
    hb[0].clicked.emit()
    _pump(app)
    acts = [a for a in page.last_menu.actions() if a.text().endswith("Gitar çal")]
    assert acts and not acts[0].isChecked()
    acts[0].trigger()
    page.last_menu.close()
    _pump(app)
    assert td.isoformat() in store.get("habits", h["id"])["days"]
    # saatli alışkanlık ayrı kutu
    store.update("habits", h["id"], time="07:30")
    page.refresh()
    assert [b for b in page.findChildren(Block) if "07:30" in " ".join(
        lb.text() for lb in b.findChildren(QLabel))]
    store.update("habits", h["id"], time=None)
    d = FormDialog(win, store, "habits", store.get("habits", h["id"]))
    assert "weekdays" in d.fields and d.fields["weekdays"][1].value() == [td.weekday()]
    d.deleteLater()


@step("alışkanlık kuralları: bırakma, yarım, haftalık en az / ideal, üst üste boş gün, ders çalışmadan otomatik")
def _habit_rules(ctx):
    import json
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp import habits_core as hc
    from alphaapp.components import DayGrid
    td = date.today()
    D = lambda k: (td - timedelta(days=k))  # noqa: E731
    iso = lambda k: D(k).isoformat()  # noqa: E731
    # spor: haftada en az 3.5, ideal 4, 3 gün üst üste boş → bozulur
    mon = td - timedelta(days=td.weekday())
    w0 = mon - timedelta(days=14)                # iki hafta önceki pazartesi
    days = [w0 + timedelta(days=i) for i in (0, 2, 4)]
    half = [w0 + timedelta(days=6)]
    days += [w0 + timedelta(days=7 + i) for i in (0, 2, 4, 5)]
    gym = {"id": "x", "name": "Spor", "goal": 4, "week_min": 3.5, "gap": 3,
           "days": [d.isoformat() for d in days], "half": [d.isoformat() for d in half]}
    info = hc.streak_info(gym, mon + timedelta(days=1))
    # 3 + yarım = 3.5 geçer; geçen hafta 4 → seri sürüyor (pazartesi + salı boş, 2 gün < 3)
    assert info["start"] == w0, info
    gym2 = dict(gym, half=[])                    # ilk hafta 3 < 3.5 → pazartesi bozulur
    assert hc.streak_info(gym2, mon + timedelta(days=1))["start"] == w0 + timedelta(days=7)
    # 3 gün üst üste boş → bozulur
    g3 = {"id": "y", "gap": 3, "days": [iso(10), iso(9), iso(7), iso(6)]}
    i3 = hc.streak_info(g3, td)
    assert i3["start"] is None and i3["cur"] == 0 and i3["best"] == 5, i3   # 10..6 (1 boş gün geçer), sonra 5 gün boş
    assert len(i3["ranges"]) == 1
    # her gün, bugün işaretsiz → dünden say
    dly = {"id": "z", "days": [iso(k) for k in range(1, 6)]}
    assert hc.streak_info(dly, td)["cur"] == 5
    # bırakma: kayma seriyi sıfırlar, en uzun kalır
    nf = {"id": "q", "kind": "quit", "start": iso(10), "slips": [iso(4)]}
    i = hc.streak_info(nf, td)
    assert i["cur"] == 4 and i["best"] == 6, i
    assert hc.state(nf, D(4)) == 0 and hc.state(nf, td) == 1 and hc.state(nf, D(20)) is None
    # ders çalışmadan otomatik: oturumlar ≥ 3 sa tam, ≥ 1.5 sa yarım
    store.add("sessions", {"kind": "study", "date": iso(1), "minutes": 190})
    store.add("sessions", {"kind": "study", "date": iso(2), "minutes": 100})
    st = hc.from_template(store, [tp for tp in hc.TEMPLATES if tp["key"] == "study"][0], td)
    st = store.get("habits", st["id"])
    assert st["source"] == "study" and hc.state(st, D(1), store) == 1 and hc.state(st, D(2), store) == 0.5
    # tıklama döngüsü: yap boş → tam → yarım → boş · bırak temiz → kayma → yarım → temiz
    b = store.add("habits", {"name": "Dene", "days": []})
    seq = []
    for _ in range(3):
        seq.append(hc.cycle(store, store.get("habits", b["id"]), td))
    assert seq == [1, 0.5, 0], seq
    q = hc.from_template(store, [tp for tp in hc.TEMPLATES if tp["key"] == "nofap"][0], D(3))
    seq = [hc.cycle(store, store.get("habits", q["id"]), td) for _ in range(3)]
    assert seq == [0, 0.5, 1], seq
    hc.set_today(store, store.get("habits", q["id"]), td, False)
    assert hc.state(store.get("habits", q["id"]), td) == 0
    assert hc.streak_info(store.get("habits", q["id"]), td)["cur"] == 0     # bugün kaydı → seri sıfır
    # sayfa: hazır alışkanlık çipleri, bırakmada kayma düğmesi, kareler
    win.show_page("habits")
    _pump(app)
    page = win.pages["habits"]
    page.refresh()
    _pump(app)
    from PyQt6.QtWidgets import QPushButton
    names = [w.text() for w in page.sug_host.findChildren(QPushButton)]
    assert not any("NoFap" in n for n in names) and not any("ders çalışma" in n for n in names), names
    assert any("Spora git" in n for n in names), names
    nf_cards = [c for c in page.cards_host.findChildren(type(page.c_today)) if c.title_lbl.text() == "NoFap"]
    assert nf_cards and nf_cards[0].today_btn.isChecked()        # bugün kaydı
    assert nf_cards[0].grid.value(td) == 0
    assert len([g for g in page.findChildren(DayGrid) if g.isVisible()]) == len(store.all("habits"))
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "habits_rules.png"))
        page.cards_host.grab().save(os.path.join(ctx["shots"], "habits_cards.png"))
    # antrenman → "Spora git" kendiliğinden işaretlenir, Spor sayfası serisi alışkanlık kuralıyla
    gym = hc.from_template(store, [tp for tp in hc.TEMPLATES if tp["key"] == "gym"][0], td)
    w = store.add("workouts", {"date": td.isoformat(), "kind": "Gym", "minutes": 60})
    assert hc.state(store.get("habits", gym["id"]), td, store) == 1
    win.show_page("sport")
    _pump(app)
    sp = win.pages["sport"]
    sp.refresh()
    assert sp.t_streak.lbl.text() == "Spor serisi" and int(sp.t_streak.val.text()) >= 1, sp.t_streak.val.text()
    store.delete("workouts", w["id"])
    store.delete("habits", gym["id"])
    sp.refresh()
    assert sp.t_streak.lbl.text() != "Spor serisi"
    # Bugün sayfasında alışkanlık kartı: işaretle
    win.show_page("today")
    _pump(app)
    tp_ = win.pages["today"]
    from alphaapp.components import Row as _Row
    rows = [r for r in tp_.c_habits.findChildren(_Row) if r.title_lbl.text() == "Dene"]
    assert rows and tp_.c_habits.isVisible()
    rows[0]._toggle()
    _pump(app)
    assert (hc.state(store.get("habits", b["id"]), td) or 0) >= 1
    # web anlık görüntüsüne bırakma alışkanlığı gitmez
    from alphaapp import web
    snap = json.dumps(web.build_snapshot(store), ensure_ascii=False)
    assert "NoFap" not in snap


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


def _mini_xlsx(path, rows):
    """Testlik küçük xlsx: rows = {(satır, sütun): değer} (satır içi metin; openpyxl gerekmez)."""
    import zipfile
    from xml.sax.saxutils import escape
    by_row = {}
    for (r, c), v in rows.items():
        by_row.setdefault(r, []).append((c, v))
    sheet = ['<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>']
    for r in sorted(by_row):
        sheet.append(f'<row r="{r}">')
        for c, v in sorted(by_row[r]):
            if isinstance(v, (int, float)):
                sheet.append(f'<c r="{c}{r}"><v>{v}</v></c>')
            else:
                sheet.append(f'<c r="{c}{r}" t="inlineStr"><is><t>{escape(v)}</t></is></c>')
        sheet.append("</row>")
    sheet.append("</sheetData></worksheet>")
    m = "http://schemas.openxmlformats.org/"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", f'<?xml version="1.0"?><Types xmlns="{m}package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook xmlns="{m}spreadsheetml/2006/main" '
                   f'xmlns:r="{m}officeDocument/2006/relationships"><sheets><sheet name="lectures" sheetId="1" '
                   'r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", f'<?xml version="1.0"?><Relationships xmlns="{m}package/2006/'
                   'relationships"><Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", "".join(sheet))


@step("not ortalaması: harf → not, ANO / AGNO (Excel ile aynı), tekrar alınan ders, Excel'den al, dönemi bitir")
def _grades(ctx):
    from alphaapp import grades
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    assert grades.point("bb") == 3.0 and grades.point("XX") is None and grades.point("NA") == 0.0
    assert grades.point("") is None and grades.point(2.5) == 2.5
    # transkript: Excel düzeni (KOD / ÖNŞART / DERS / DİL / AKTS / HARF, sağda hedef bloğu), AGNO satırında biter
    path = os.path.join(_tmp, "tr.xlsx")
    cells = {(2, "A"): "KOD", (2, "C"): "DERS", (2, "D"): "DİL", (2, "E"): "AKTS", (2, "F"): "HARF ",
             (2, "I"): "KOD", (2, "K"): "DERS", (2, "L"): "DİL", (2, "M"): "AKTS", (2, "N"): "HARF ",
             (3, "A"): "1. SINIF 1. DÖNEM", (4, "A"): "FIZ103", (4, "C"): "Fizik I", (4, "E"): 6, (4, "F"): "DC",
             (4, "N"): "AA", (5, "A"): "FIZ104", (5, "C"): "Fizik II", (5, "E"): 6, (5, "F"): "BB",
             (6, "A"): "TOPLAM AKTS", (7, "A"): "1. SINIF 2. DÖNEM", (8, "A"): "MM423",
             (8, "C"): "Bitirme Tasarım Projesi I", (8, "E"): 5, (8, "F"): "XX", (8, "N"): "BA",
             (10, "A"): "AGNO", (12, "A"): "PLAN", (12, "C"): "alınmamalı", (12, "E"): 9, (12, "F"): "AA"}
    _mini_xlsx(path, cells)
    rows = grades.read_transcript_xlsx(path)
    assert [r["code"] for r in rows] == ["FIZ103", "FIZ104", "MM423"], rows
    assert rows[0]["term"] == "1.1" and rows[2]["term"] == "1.2" and rows[0]["target"] == "AA"
    for r in list(store.all("transcript")):
        store.delete("transcript", r["id"])
    for r in rows:
        store.add("transcript", r)
    tr = store.all("transcript")
    pts, akts = grades.totals(tr)
    assert (pts, akts) == (6 * 1.5 + 6 * 3, 12)           # XX AKTS'ye girmez
    assert grades.totals(tr, "target") == (6 * 4 + 6 * 3 + 5 * 3.5, 17)
    # bu dönem: Fizik I tekrar (eski DC düşülür), "Fizik I" ↔ "Fizik II" karışmaz
    cs = [{"id": "a", "name": "Fizik I", "credits": 6, "letter": "BA"},
          {"id": "b", "name": "Kalite Kontrol", "credits": 5, "guess": "CC", "target": "AA"}]
    assert grades.match_retake(cs[0], tr)["code"] == "FIZ103"
    r = grades.semester(cs, tr)
    assert abs(r["agno"] - (6 * 3.5 + 6 * 3) / 12) < 1e-9 and r["ano"] == 3.5
    g = grades.semester(cs, tr, "guess")                  # gerçek harf ihtimalde de kullanılır
    assert abs(g["ano"] - (6 * 3.5 + 5 * 2) / 11) < 1e-9
    need = grades.needed_point(cs, tr, 3.0)
    assert abs(((6 * 3.5 + 6 * 3) + need * 5) / 17 - 3.0) < 1e-9
    assert grades.match_retake(dict(cs[0], retake="none"), tr) is None
    # sayfa: kart satırları ve yerinde harf seçimi
    c = store.all("courses")[0]
    win.show_page("education")
    _pump(app)
    page = win.pages["education"]
    from alphaapp.pages.grades_view import _Combo
    combos = page.c_grades.findChildren(_Combo)
    assert len(combos) == 2 * len(store.all("courses")), len(combos)
    # sınav çubuğu: sınavı olan her derste bir ExamBar; kalem = sınav çipleri (düzenleme kipi)
    from PyQt6.QtWidgets import QPushButton
    from alphaapp.pages.grades_view import ExamBar
    ids = {x["id"] for x in store.all("courses")}
    n_ex = len([e for e in store.all("exams") if e.get("course") in ids])
    with_ex = {e.get("course") for e in store.all("exams") if e.get("course") in ids}
    bars = page.c_grades.findChildren(ExamBar)
    assert len(bars) == len(with_ex), (len(bars), len(with_ex))
    for b in bars:
        b.resize(400, b.H)
        r = b._rects()
        assert len(r) == len(b.exams) and r[-1].right() <= 401, r
        b._tip(b.exams[0])
        b.repaint()
    chips = [b for b in page.c_grades.findChildren(QPushButton) if b.objectName() == "Chip" and b.isVisibleTo(page)]
    assert not chips, len(chips)
    page.c_grades.pen.setChecked(True)
    _pump(app, 4)
    chips = [b for b in page.c_grades.findChildren(QPushButton) if b.objectName() == "Chip" and b.isVisibleTo(page)]
    assert len(chips) == n_ex, (len(chips), n_ex)
    page.c_grades.pen.setChecked(False)
    _pump(app, 4)
    combos = page.c_grades.findChildren(_Combo)
    # kısa ad, sabit hedef kutusu, aynı ders + türde sınav birleşir
    from alphaapp.pages.grades_view import _short
    assert _short("Vize 1") == "V1" and _short("Laboratuvar") == "L" and _short("Ödev") == "Ö"
    from alphaapp.config import prefs as _pf
    _pf.set("agno_goal", 3.0)
    page.c_grades.refresh()
    _pump(app, 2)
    from PyQt6.QtWidgets import QLabel as _QL
    assert any(x.text() == "3.00" for x in page.c_grades.findChildren(_QL)), "hedef kutusu"
    c0 = store.all("courses")[0]["id"]
    ph, _b = store.add_exam({"course": c0, "name": "Final", "date": None, "weight": 60, "target": 90})
    n0 = len(store.all("exams"))
    got, before = store.add_exam({"course": c0, "name": "final", "date": "2030-01-10", "weight": None,
                                  "note": "D220"})
    assert got["id"] == ph["id"] and before is not None and len(store.all("exams")) == n0
    assert got["date"] == "2030-01-10" and got["weight"] == 60 and got["target"] == 90, got
    store.undo_exam(got, before)
    assert store.get("exams", ph["id"]).get("date") is None
    store.delete("exams", ph["id"])
    cb = [x for x in combos if x.isEnabled()][0]
    cb.setCurrentIndex(cb.findData("BB"))
    cb.activated.emit(cb.currentIndex())
    _pump(app, 6)
    assert any(x.get("letter") == "BB" or x.get("guess") == "BB" or x.get("target") == "BB"
               for x in store.all("courses"))
    page.c_transcript._toggle("1.1")
    _pump(app, 4)
    # dönemi bitir: gerçek harf transkripte yazılır, tekrar alınan ders güncellenir, geri al
    store.update("courses", c["id"], letter="AA", name="Fizik I", credits=6)
    n0 = len(store.all("transcript"))
    added, changed = grades.finish_semester(store, "1.2")
    assert not added and changed and store.get("transcript", changed[0]["id"])["letter"] == "AA"
    assert store.get("transcript", changed[0]["id"])["old_letter"] == "DC" and len(store.all("transcript")) == n0
    store.update("transcript", changed[0]["id"], letter="DC", old_letter=None)
    store.update("courses", c["id"], letter=None)
    _pump(app)


@step("menüyü düzenle: kategori ekle / adlandır / gizle, sayfası açılır, formda seçilir, silince Kişisel'e geçer")
def _navmenu(ctx):
    from alphaapp import navmenu
    from alphaapp.config import prefs
    from alphaapp.i18n import t
    from alphaapp.forms import CategoryPicker
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    assert navmenu.visible()[:2] == ["today", "schedule"] and "personal" not in navmenu.visible()
    ed = navmenu.NavEditor(win)
    ed._add_cat()
    cid = ed.cats[-1]["id"]
    ed._rename(cid, "Hobi && Müzik")
    i_sport = [i for i, (k, _) in enumerate(ed.items) if k == "sport"][0]
    ed._set_hidden(i_sport, True)
    ed._rename("work", "Kinesis İşleri")
    ed._move(0, 1)
    ed._save()
    win._ensure_pages()
    win.nav.rebuild()
    assert cid in win.pages and cid in win.nav.btns and "sport" not in win.nav.btns
    assert navmenu.visible()[0] == "schedule"
    assert t("cat_" + cid) == "Hobi && Müzik" and t("nav_work") == "Kinesis İşleri" and t("cat_work") == "Kinesis İşleri"
    assert cid in CategoryPicker("personal").btns
    tk = store.add("tasks", {"title": "Gitar çal", "category": cid, "done": False})
    win.show_page(cid)
    _pump(app)
    assert win.pages[cid].c_tasks.body.count() >= 1
    # sil: kayıtları Kişisel'e geçer, sayfa kalkar
    ed = navmenu.NavEditor(win)
    from PyQt6.QtWidgets import QMessageBox
    orig = QMessageBox.question
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    try:
        ed._remove([i for i, (k, _) in enumerate(ed.items) if k == cid][0])
    finally:
        QMessageBox.question = orig
    ed._reset()
    ed._save()
    win._ensure_pages()
    win.nav.rebuild()
    assert store.get("tasks", tk["id"])["category"] == "personal" and cid not in win.pages
    assert "sport" in win.nav.btns and t("nav_work") == "İş" and navmenu.visible()[0] == "today"
    store.delete("tasks", tk["id"])
    prefs.set("nav_layout", None)
    win.show_page("today")
    _pump(app)


@step("projeler: logo karo, görev atama, ilerleme görevlerden, zaman çizelgesi, karta sürükle, İş / Eğitim ayrımı")
def _projects(ctx):
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    from alphaapp.pages.projects import logo_pixmap, sorted_projects
    from alphaapp.pages import task_row
    p = store.add("projects", {"name": "BEDROCK", "category": "education", "status": "doing", "start":
                               date.today().isoformat(), "due": (date.today() + timedelta(days=40)).isoformat()})
    assert not logo_pixmap(p, 40).isNull()
    a = store.add("tasks", {"title": "Rapor taslağı", "category": "education", "project": p["id"], "done": False,
                            "due": (date.today() + timedelta(days=5)).isoformat()})
    store.add("tasks", {"title": "Sunum", "category": "education", "project": p["id"], "done": True})
    assert store.project_task_counts(p["id"]) == (1, 2) and store.project_progress(p) == 50.0
    assert p in sorted_projects(store, "education") and p not in sorted_projects(store, "work")
    from alphaapp.forms import FormDialog
    d = FormDialog(win, store, "tasks", preset={"project": p["id"]})
    assert d.fields["project"][1].currentData() == p["id"]
    d.deleteLater()
    r = task_row(win, a)
    assert r.drag_data == "tasks:" + a["id"]
    win.show_page("projects")
    _pump(app)
    page = win.pages["projects"]
    assert p in page.timeline.projects and page.timeline.height() > 60
    # başka bir görevi proje kartının bırakma işleviyle projeye ata
    b = store.add("tasks", {"title": "Literatür", "category": "education", "done": False})
    card = [c for c in page.findChildren(type(page.c_time)) if c.title_lbl.text() == "BEDROCK"][0]
    card._drop[1]("tasks", b["id"])
    assert store.get("tasks", b["id"])["project"] == p["id"]
    win.show_page("education")
    _pump(app)
    assert win.pages["education"].c_proj.body.count() >= 1
    for x in [x for x in store.all("tasks") if x.get("project") == p["id"]]:
        store.delete("tasks", x["id"])
    store.delete("projects", p["id"])


@step("sürükle-bırak: ders görevi sınavlara / ders kartına bırakılınca sınav olur, geri al")
def _drag_exam(ctx):
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    from alphaapp.pages import drop_task_to_exam
    c = store.all("courses")[0]
    tk = store.add("tasks", {"title": f"{c['name']}: Final", "category": "education", "done": False,
                             "due": date.today().isoformat()})
    n = len(store.all("exams"))
    drop_task_to_exam(win)("tasks", tk["id"])
    assert store.get("tasks", tk["id"]) is None and len(store.all("exams")) == n + 1
    assert store.all("exams")[-1]["name"] == "Final" and store.all("exams")[-1]["course"] == c["id"]
    win.toast_w._clicked()
    _pump(app)
    assert store.get("tasks", tk["id"]) is not None and len(store.all("exams")) == n
    store.delete("tasks", tk["id"])


@step("kütüphane: kapak duvarı, filtreler, aramadan gelen kayıt formdan kaydedilir, ilerlet, Şu an kartı, web'e gitmez")
def _library(ctx):
    import json
    from alphaapp import library, web
    from alphaapp.forms import FormDialog
    from alphaapp.pages.library import SearchDialog, cover_pixmap
    store, win, app = ctx["store"], ctx["win"], ctx["app"]
    # arama sonucu seçilmiş gibi (ağa çıkmadan): preset → form → kayıt; bağlantılar korunur
    sd = SearchDialog(win, "series")
    sd._picked("series", {"title": "GIZLI_DIZI_Q", "year": "2022", "genres": ["Dram", "Gerilim"],
                          "links": {"letterboxd": "https://letterboxd.com/x"}, "source": "tmdb:tv:1"},
               {"total": 9, "seasons": 1, "creator": "Dan Erickson"}, None)
    assert sd.preset["total"] == 9 and sd.preset["genres"] == "Dram, Gerilim" and sd.preset["year"] == 2022
    d = FormDialog(win, store, "media", preset=dict(sd.preset, status="doing"))
    d._save()
    m = d.item
    assert m["links"]["letterboxd"] and m["source"] == "tmdb:tv:1" and m["started"] and m["creator"] == "Dan Erickson"
    assert not cover_pixmap(m, 120, 180).isNull()
    store.add("media", {"type": "book", "title": "Dune", "status": "done", "finished": date.today().isoformat(),
                               "rating": 4.5})
    assert library.year_count(store, "book") == 1 and library.current(store)[0]["id"] == m["id"]
    win.show_page("library")
    _pump(app)
    page = win.pages["library"]
    assert len(page.wall.items) == 2
    page.f_type.select("book")
    _pump(app)
    assert [x["title"] for x in page.wall.items] == ["Dune"]
    page.f_type.select("all")
    page.f_status.select("doing")
    _pump(app)
    assert [x["id"] for x in page.wall.items] == [m["id"]]
    page.f_status.select("all")
    _pump(app)
    # raf: fare yaklaşınca dışarı çıkar, tıkla = kitap açılır / disk çıkar, Esc = kapanır
    from alphaapp.pages.shelf import Shelf, MediaViewer, open_viewer
    sh = page.wall
    assert isinstance(sh, Shelf) and sh.rows and sh.height() > 100
    i0, r0, _fw, _k = sh._geom()[0]
    sh._set_hover(i0)
    for _ in range(40):
        sh._tick()
    assert sh.anim.get(i0) == 1.0 and sh._geom()[0][2] > 10, sh.anim
    assert sh._at(sh._geom()[0][1].center()) == i0
    sh.repaint()
    sh._set_hover(-1)
    for _ in range(40):
        sh._tick()
    assert not sh.anim
    for it in sh.items:
        v = open_viewer(win, it)
        v.timer.stop()
        for tt in (0.0, 0.3, 0.6, 1.0):
            v.t = tt
            v.repaint()
        v._tick()
        v.close_anim()
        for _ in range(40):
            v.last = v.clock.elapsed() - 20
            v._tick()
            if v.t <= 0:
                break
        assert v.t == 0, v.t
    _pump(app, 4)
    assert not [w for w in win.findChildren(MediaViewer) if w.isVisible()]
    # Şu an kartı ve ilerlet: dizi 1 bölüm; son bölümde bitti
    win.show_page("today")
    _pump(app)
    assert win.pages["today"].c_now.isVisible()
    assert library.progress_text(m, __import__("alphaapp.i18n", fromlist=["t"]).t)
    for _ in range(9):
        library.bump(store, store.get("media", m["id"]))
    m2 = store.get("media", m["id"])
    assert m2["status"] == "done" and m2["progress"] == 9 and m2["finished"]
    _pump(app)
    assert not win.pages["today"].c_now.isVisible()
    txt = json.dumps(web.build_snapshot(store), ensure_ascii=False)
    assert "GIZLI_DIZI_Q" not in txt and '"media"' not in txt
    # ekran görüntüsü için birkaç kayıt kalsın (kapaksız: tür ikonu + başlık)
    store.add("media", {"type": "series", "title": "Severance", "status": "doing", "progress": 4, "total": 19,
                        "creator": "Dan Erickson"})
    store.add("media", {"type": "podcast", "title": "Lex Fridman Podcast", "status": "want"})
    store.add("media", {"type": "film", "title": "Interstellar", "status": "done", "rating": 5,
                        "finished": date.today().isoformat(), "year": 2014})
    store.delete("media", m["id"])
    _pump(app)


@step("spor: antrenman setleri, programdan başlat, 3B vücut (gelişim / programlar), rekorlar, vücut")
def _fitness(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from datetime import timedelta
    from alphaapp import fitness
    from alphaapp.config import prefs, day_today
    from alphaapp.pages.sport_ui import WorkoutDialog, TemplateDialog, focus_text
    from PyQt6.QtCore import QPointF
    td = day_today()
    assert fitness.muscles_of("bench press")[0] == ("chest",)
    assert fitness.muscles_of("Incline Dumbbell Curl")[0] == ("biceps",)
    assert fitness.first_int("6-8") == 6 and fitness.intensity(18) == 3 and fitness.intensity(26) == 5
    assert abs(fitness.e1rm(100, 5) - 116.6667) < 0.01 and fitness.e1rm(80, 1) == 80
    # eski antrenman (3 gün önce): Bench 60×8 ×3
    d3 = (td - timedelta(days=3)).isoformat()
    store.add("workouts", {"date": d3, "kind": "Gym", "exercises": [
        {"name": "Bench Press", "sets": [{"r": 8, "w": 60}, {"r": 8, "w": 60}, {"r": 6, "w": 62.5}]}]})
    tp = store.add("templates", {"name": "PUSH", "exercises": [
        {"name": "Bench Press", "sets": 3, "reps": "6-8", "rir": "1"},
        {"name": "Cable Fly", "sets": 3, "reps": "10", "rir": "1"}]})
    assert fitness.template_sets(tp) == 6
    load = fitness.muscle_load(tp["exercises"])
    assert load["chest"] == 6 and load["front_delts"] == 3 and load["triceps"] == 1.5, load
    # programdan başlat: set sayısı, tekrar, geçen seferki kilo dolu
    d = WorkoutDialog(win, template=tp)
    assert len(d.blocks) == 2 and len(d.blocks[0].rows) == 3
    assert d.blocks[0].rows[0][1].value() == 6 and d.blocks[0].rows[0][2].value() == 60
    assert d.blocks[0].rows[2][2].value() == 62.5
    assert "60" in d.blocks[0].hint.text()
    d.blocks[0].add_set()
    assert len(d.blocks[0].rows) == 4 and d.blocks[0].rows[3][2].value() == 62.5
    d.blocks[0]._remove_set(d.blocks[0].rows[3])
    d.blocks[0].rows[0][2].setValue(70)
    d.blocks[1].rows[0][2].setValue(15)
    d._save()
    w = d.item
    assert w["template"] == tp["id"] and len(w["exercises"]) == 2 and w["exercises"][0]["sets"][0]["w"] == 70
    assert "Göğüs" in w["focus"] or "Chest" in w["focus"], w["focus"]
    assert fitness.best(store, "Bench Press")["w"] == 70
    assert len(fitness.progress_series(store, "Bench Press")) == 2
    assert fitness.last_sets(store, "Bench Press", before=td)[0]["w"] == 60
    # düzenle: bloklar kayıttan gelir
    d = WorkoutDialog(win, w)
    assert len(d.blocks) == 2 and d.blocks[0].rows[0][2].value() == 70
    d.remove_block(d.blocks[1])
    d._save()
    assert len(store.get("workouts", w["id"])["exercises"]) == 1
    load, last = fitness.recent_load(store, 7, td)
    assert load["chest"] == 6 and last["chest"] == td, (load, last)
    assert focus_text(tp["exercises"])
    # program penceresi
    d = TemplateDialog(win)
    d.name.setText("LEGS")
    d.rows[0][1].setCurrentText("Leg Press")
    d.add_row({"name": "Seated Calf Raise", "sets": 4})
    d._save()
    legs = d.item
    assert [e["name"] for e in legs["exercises"]] == ["Leg Press", "Seated Calf Raise"]
    assert legs["exercises"][1]["sets"] == 4
    # sayfa kartları
    store.add("body", {"date": (td - timedelta(days=20)).isoformat(), "weight": 85.4, "fat": 18})
    store.add("body", {"date": td.isoformat(), "weight": 83})
    prefs.set("goal_weight", 78)
    win.show_page("sport")
    _pump(app)
    sp = win.pages["sport"]
    sp.refresh()
    _pump(app)
    from alphaapp.components import Row
    assert len([r for r in sp.c_tpl.findChildren(Row)]) == 2
    # giriş kartı: gelişim (rekorlardan), son 7 gün, programlarım, popüler programlar
    from alphaapp.body3d import Body3D, ModelView, load_frames
    hero = sp.c_hero
    hero._set_mode("dev")
    _pump(app)
    dev = fitness.development(store)
    assert dev["chest"]["level"] == 2 and dev["chest"]["ex"] == "Bench Press", dev["chest"]
    assert hero.model.heat["chest"] > 0 and "quads" not in hero.model.heat
    store.add("lifts", {"date": td.isoformat(), "name": "Squat", "w": 120, "r": 1})
    _pump(app)
    hero.refresh()
    assert fitness.best(store, "Squat")["w"] == 120 and "Squat" in fitness.logged_exercises(store)
    assert hero.model.heat.get("quads", 0) > 0, hero.model.heat
    for mode, key in (("week", "chest"), ("mine", "chest"), ("pop", "quads")):
        hero._set_mode(mode)
        _pump(app)
        assert hero.model.heat.get(key, 0) > 0, (mode, hero.model.heat)
    hero._pick("pop", "sl5")
    _pump(app)
    assert hero.model.heat["quads"] > 0.7, hero.model.heat
    assert len(fitness.POPULAR) == 8 and fitness.POPULAR[0]["key"] == "mine"
    mine = {e["name"]: e["sets"] for e in fitness.POPULAR[0]["exercises"]}
    assert sum(mine.values()) == 18 + 18 + 13 + 24 and mine["Dumbbell Lateral Raise"] == 6, mine
    assert sum(e["sets"] for e in next(p for p in fitness.POPULAR if p["key"] == "guray")["exercises"]) == 115
    # ekran görüntülerindeki kas haritası: ağırlıklı yük
    assert fitness.muscles_of("Leg Press")[0] == ("quads", "adductors")
    assert fitness.weights_of("Seated Calf Raise") == {"calves": 0.75}
    assert fitness.muscles_of("Cable Face Pull")[0][0] == "rear_delts"
    hero._set_mode("dev")
    _pump(app)
    # model: kas seçimi ve dönüş
    mv = hero.model
    mv.resize(360, mv.height())
    mv.yaw = 0
    mv._cache = None
    mv.repaint()
    if isinstance(mv, ModelView):
        assert load_frames() is not None
        r = mv._rect()
        assert mv.muscle_at(QPointF(r.center().x() - r.width() * 0.07, r.top() + r.height() * 0.235)) == "chest"
        assert mv.muscle_at(QPointF(2, 2)) is None
    mv.turn_to(180)
    for _ in range(80):
        mv._tick()
    assert mv.facing_back()
    b3 = Body3D(300)
    b3.resize(220, 300)
    b3.set_heat({"chest": 1})
    b3.yaw = 0
    b3.repaint()
    b3._render()
    assert any(k == "chest" for _p, k in b3._polys)
    assert len(sp.c_pr.findChildren(Row)) >= 1
    assert len(sp.c_body.findChildren(Row)) == 2
    from alphaapp.components import ElideLabel
    subs = [lb.text() for r in sp.c_log.findChildren(Row) for lb in r.findChildren(ElideLabel)]
    assert any("Bench Press" in x for x in subs), subs
    for c in (sp.c_hero, sp.c_pr, sp.c_body):
        c.repaint()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "sport_fitness.png"))
        sp.c_hero.grab().save(os.path.join(ctx["shots"], "sport_hero.png"))
        hero._set_mode("pop")
        _pump(app, 4)
        sp.c_hero.grab().save(os.path.join(ctx["shots"], "sport_hero_pop.png"))
        hero._set_mode("dev")
        sp.c_body.grab().save(os.path.join(ctx["shots"], "sport_body.png"))
        sp.c_pr.grab().save(os.path.join(ctx["shots"], "sport_pr.png"))
        sp.c_tpl.grab().save(os.path.join(ctx["shots"], "sport_tpl.png"))
        dd = WorkoutDialog(win, template=tp)
        dd.show()
        _pump(app, 4)
        dd.grab().save(os.path.join(ctx["shots"], "sport_workout_dialog.png"))
        dd.close()


@step("zihin: puanlama yok, uyku, meditasyon sayacı, nefes, ders kronometresi / zamanlayıcısı, menü, denge")
def _mind(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from datetime import timedelta
    from alphaapp import navmenu, balance
    from alphaapp.config import prefs, day_today
    from alphaapp.clock_ui import CourseClock
    from alphaapp.pages.mind import sleep_hours, ClockPanel
    td = day_today()
    # menü: kayıtlı eski düzende "mind" yoktu → Spor'un ardına görünür eklenir
    saved = prefs.get("nav_layout")
    prefs.set("nav_layout", [{"k": k, "h": False} for k in ("today", "sport", "notes")])
    lay = [k for k, _h in navmenu.layout()]
    assert lay.index("mind") == lay.index("sport") + 1 and "mind" in navmenu.visible(), lay
    prefs.set("nav_layout", saved)
    assert sleep_hours({"bed": "23:30", "wake": "07:15"}) == 7.75 and sleep_hours({"bed": "x"}) is None
    for i in range(1, 15):
        d = td - timedelta(days=i)
        store.add("sleep", {"date": d.isoformat(), "bed": "23:00", "wake": "07:30" if i % 2 else "05:00", "quality": 3})
    # sayaç (sahte saat)
    clk = win.clock
    clk.cancel()
    now = [1000.0]
    clk.now = lambda: now[0]
    n0 = len(store.all("sessions"))
    clk.start("meditation", mode="timer", minutes=10, label="Meditasyon")
    assert clk.running() and clk.display() == "10:00"
    now[0] += 125
    assert clk.display() == "07:55"
    clk.pause()
    now[0] += 500
    assert clk.display() == "07:55" and not clk.running()
    clk.resume()
    assert prefs.get("clock")["kind"] == "meditation"
    now[0] += 600
    clk._tick()                                    # süre doldu → kaydedilir
    assert not clk.active() and prefs.get("clock") is None
    ses = store.all("sessions")[-1]
    assert len(store.all("sessions")) == n0 + 1 and ses["kind"] == "meditation" and ses["minutes"] == 10.0, ses
    clk.start("meditation")
    now[0] += 20
    assert clk.stop() is None and len(store.all("sessions")) == n0 + 1    # 1 dk'dan kısa: kaydedilmez
    # ders: kronometre ders kartında, çalışma karesi işaretlenir
    course = store.all("courses")[0]
    store.update("courses", course["id"], study_days=[])
    win.show_page("education")
    _pump(app)
    cc = [w for w in win.pages["education"].findChildren(CourseClock) if w.c["id"] == course["id"]][0]
    cc.b_sw.click()
    assert clk.is_for("study", course["id"]) and win.clock_pill.isVisibleTo(win)
    assert cc.b_stop.isVisibleTo(cc) and not cc.b_sw.isVisibleTo(cc)
    assert course.get("name", "") in win.clock_pill.text()
    now[0] += 45 * 60
    clk._tick()
    assert "45:00" in cc.lbl.text(), cc.lbl.text()
    cc.b_stop.click()
    _pump(app)
    assert td.isoformat() in store.get("courses", course["id"])["study_days"]
    assert store.all("sessions")[-1]["course"] == course["id"] and store.all("sessions")[-1]["minutes"] == 45.0
    cc2 = [w for w in win.pages["education"].findChildren(CourseClock) if w.c["id"] == course["id"]][-1]
    assert "45 dk" in cc2.lbl.text() or "45 min" in cc2.lbl.text(), cc2.lbl.text()
    # zihin sayfası
    win.show_page("mind")
    _pump(app)
    mp = win.pages["mind"]
    mp.refresh()
    _pump(app)
    assert not hasattr(mp, "t_mood") and not hasattr(mp, "c_check")
    assert mp.t_sleep.val.text() not in ("", "—") and mp.t_study.val.text() not in ("", "—")
    panel = mp.med_clock
    assert isinstance(panel, ClockPanel)
    mp._med_tab("timer")
    panel._set_minutes(15)
    assert panel.digits.text() == "15:00" and panel.pre_host.isVisibleTo(panel)
    panel.go.click()
    assert clk.is_for("meditation") and panel.done.isVisibleTo(panel)
    now[0] += 61
    clk._tick()
    assert panel.digits.text() == "13:59", panel.digits.text()
    panel.go.click()          # duraklat
    assert not clk.running()
    panel.reset.click()       # sıfırla: kaydetmez
    assert not clk.active()
    br = mp.breath
    assert br.phase(0)[0] == 0 and br.phase(5)[0] == 1 and br.phase(9)[0] == 2
    br.pat = "478"
    assert br.phase(4.5)[0] == 1 and br.phase(12)[0] == 2
    br.pat = "box"
    rep = balance.area_report(store)
    assert rep["mind"]["score"] is not None and rep["mind"]["parts"], rep["mind"]
    import time as _time
    clk.now = _time.time
    if ctx["shots"]:
        win.resize(1280, 900)
        mp.verticalScrollBar().setValue(0) if hasattr(mp, "verticalScrollBar") else None
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "mind.png"))
        for c, n in ((mp.c_med, "mind_med"), (mp.c_sleep, "mind_sleep"), (mp.c_study, "mind_study")):
            c.grab().save(os.path.join(ctx["shots"], n + ".png"))
        clk.start("study", course["id"], "timer", 25, label=course.get("name", ""))
        win.show_page("education")
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "education_clock.png"))
        clk.cancel()


@step("ekonomi: anlık fiyat (sahte kaynak), yatırım değeri, net varlık, Varlıklarım kartı")
def _markets(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp import markets
    asked = []

    def fake(sym):
        asked.append(sym)
        table = {"USDTRY=X": (40.0, 39.0, "TRY"), "EURTRY=X": (45.0, 45.0, "TRY"), "GC=F": (3110.34768, 3000.0, "USD"),
                 "BTC-USD": (100000.0, 100000.0, "USD"), "AAPL": (200.0, 190.0, "USD"), "THYAO.IS": (300.0, 310.0, "TRY")}
        if sym not in table:
            raise ValueError("unknown")
        p, prev, c = table[sym]
        return p, prev, c, 0

    out, errs = markets.fetch(["USD", "GA", "AAPL", "THYAO", "NOPE.XX"], get=fake)
    assert abs(out["USD"]["p"] - 40) < 1e-9 and abs(out["GA"]["p"] - 4000) < 1e-6, out
    assert abs(out["AAPL"]["p"] - 8000) < 1e-6 and abs(out["AAPL"]["prev"] - 190 * 39) < 1e-6
    assert out["THYAO"]["p"] == 300 and "THYAO.IS" in asked and "NOPE.XX" in errs, (out, errs)
    assert markets.parse_code("Gram altın (GA)") == "GA" and markets.parse_code(" thyao.is ") == "THYAO.IS"
    markets.remember(out)
    gold = store.add("investments", {"name": "Altın", "kind": "Altın", "asset": "Gram altın (GA)", "qty": 10,
                                     "invested": 30000, "value": 1})
    manual = store.add("investments", {"name": "Fon", "kind": "Fon", "invested": 5000, "value": 6000})
    assert abs(markets.value_of(gold) - 40000) < 1e-6 and markets.value_of(manual) == 6000
    assert abs(markets.day_change(gold) - 10 * (4000 - 3000 * 39 / markets.OZ)) < 1e-6
    nw = markets.net_worth(store)
    assert nw["invest"] >= 46000 and nw["total"] == nw["cash"] + nw["invest"] + nw["owed"] - nw["owe"], nw
    assert "GA" in markets.wanted(store)
    win.show_page("finance")
    _pump(app)
    fp = win.pages["finance"]
    fp.refresh()
    _pump(app)
    texts = [w.text() for w in fp.c_assets.findChildren(QLabel)]
    assert any(x.startswith("4.000") or x.startswith("4,000") for x in texts) and "Gram altın" in texts, texts
    if ctx["shots"]:
        win.resize(1280, 900)
        _pump(app, 6)
        fp.c_assets.grab().save(os.path.join(ctx["shots"], "finance_assets.png"))
    store.delete("investments", gold["id"])
    store.delete("investments", manual["id"])
    # alınacaklar: işaretle = alındı (sona iner, toplamdan düşer), telefona gitmez
    from alphaapp import web
    import json
    from alphaapp.pages.wishlist import WishCard
    a = store.add("wishlist", {"name": "GIZLI_ALINACAK", "price": 1350, "category": "Gadget"})
    b = store.add("wishlist", {"name": "Lamy Safari dolma kalem", "price": 500, "category": "Kırtasiye"})
    more = [store.add("wishlist", {"name": n, "category": c}) for n, c in
            (("Bose QuietComfort 35", "Elektronik"), ("New Balance 1000", "Giyim"), ("Döküm demlik", "Ev"))]
    fp.tabs.select("wish")
    fp.refresh()
    _pump(app)
    assert fp.c_wish.isVisible() and not fp.c_inv.isVisible()
    assert "1.850" in fp.c_wish.sub_lbl.text() or "1,850" in fp.c_wish.sub_lbl.text(), fp.c_wish.sub_lbl.text()
    cards = {c.w["id"]: c for c in fp.c_wish.grid.cards}
    assert len(cards) == 5
    if ctx["shots"]:
        win.resize(1280, 900)
        _pump(app, 6)
        fp.c_wish.grab().save(os.path.join(ctx["shots"], "finance_wish.png"))
    cards[a["id"]].btn.click()
    _pump(app)
    assert store.get("wishlist", a["id"])["bought"] and store.get("wishlist", a["id"])["bought_at"]
    assert "500" in fp.c_wish.sub_lbl.text() and "1.850" not in fp.c_wish.sub_lbl.text()
    assert a["id"] not in {c.w["id"] for c in fp.c_wish.grid.cards}
    fp.c_wish._set_filter("bought")
    assert [c.w["id"] for c in fp.c_wish.grid.cards] == [a["id"]]
    assert isinstance(fp.c_wish.grid.cards[0], WishCard)
    fp.c_wish._set_filter("c:Ev")
    assert [c.w["name"] for c in fp.c_wish.grid.cards] == ["Döküm demlik"]
    fp.c_wish._set_filter("all")
    assert "GIZLI_ALINACAK" not in json.dumps(web.build_snapshot(store), ensure_ascii=False)
    for x in [a, b] + more:
        store.delete("wishlist", x["id"])
    fp.tabs.select("tx")


@step("kütüphane: oyun türü (Steam araması sahte, ayrıntı, saat ilerlemesi, rafta kutu)")
def _games(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp import library
    from alphaapp.i18n import t
    from alphaapp.pages.shelf import DISC_TYPES
    assert "game" in library.TYPES and "game" in DISC_TYPES
    real = library._get

    def fake(url, headers=None, raw=False):
        if "storesearch" in url:
            return {"items": [{"id": 1, "name": "Outer Wilds", "type": "app"},
                              {"id": 2, "name": "Outer Wilds Soundtrack", "type": "app"}]}
        if "appdetails" in url:
            return {"1": {"data": {"name": "Outer Wilds", "developers": ["Mobius Digital"],
                                   "release_date": {"date": "18 Haz 2020"}, "genres": [{"description": "RYO"}]}}}
        raise OSError(url)
    library._get = fake
    try:
        r = library.search("game", "outer wilds")
        assert [x["title"] for x in r] == ["Outer Wilds"] and r[0]["source"] == "steam:1", r
        d = library.steam_details("steam:1")
        assert d["creator"] == "Mobius Digital" and d["year"] == "2020" and d["genres"] == ["Rol yapma"], d
    finally:
        library._get = real
    g = store.add("media", {"type": "game", "title": "Outer Wilds", "status": "doing", "progress": 3, "total": 22})
    assert library.progress_text(store.get("media", g["id"]), t) in ("3/22 saat", "3/22 h")
    library.bump(store, store.get("media", g["id"]))
    assert store.get("media", g["id"])["progress"] == 4
    win.show_page("library")
    _pump(app, 4)
    win.pages["library"].refresh()
    _pump(app, 4)
    store.delete("media", g["id"])


@step("tarih / saat seçici: takvimden gün, Bugün / Yarın, saat + dakika ızgarası, yazarak, tekerlek adımı")
def _pickers(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from datetime import timedelta
    from PyQt6.QtWidgets import QPushButton, QLineEdit
    from alphaapp.config import day_today
    from alphaapp.components import MonthCalendar
    from alphaapp.forms import FormDialog, OptDate, OptTime
    from alphaapp.pickers import DateButton, TimeButton
    from PyQt6 import sip

    def gone(w):
        return sip.isdeleted(w) or not w.isVisible()
    td = day_today()
    d = FormDialog(win, store, "tasks", None)
    d.show()
    _pump(app)
    od = next(w for k, (kind, w) in d.fields.items() if k == "due")
    ot = next(w for k, (kind, w) in d.fields.items() if k == "time")
    assert isinstance(od, OptDate) and isinstance(od.ed, DateButton) and isinstance(ot, OptTime)
    od.sw.setChecked(False)
    assert od.value() is None and od.ed.isEnabled() and od.ed.property("off")
    od.ed.click()
    _pump(app)
    pop = od.ed.popup
    assert pop.isVisible()
    pop.findChildren(MonthCalendar)[0].day_clicked.emit(td + timedelta(days=3))
    _pump(app)
    assert od.value() == (td + timedelta(days=3)).isoformat() and gone(pop)
    od.ed.click()
    _pump(app)
    tomorrow = [b for b in od.ed.popup.findChildren(QPushButton) if b.text() in ("Yarın", "Tomorrow")][0]
    tomorrow.click()
    _pump(app)
    assert od.value() == (td + timedelta(days=1)).isoformat()
    od.ed.step(-1)
    assert od.value() == td.isoformat()
    # yıl: başlık → aylar → yıllar, 12'şer geri, 1998 → Mart → 14
    from datetime import date as _date
    od.ed.click()
    _pump(app)
    pop = od.ed.popup
    title = [b for b in pop.findChildren(QPushButton) if b.objectName() == "PickTitle"][0]
    title.click()
    assert pop.st["mode"] == "months"
    title.click()
    assert pop.st["mode"] == "years"
    from alphaapp.widgets import IconButton
    prev = [b for b in pop.findChildren(IconButton) if b.toolTip() in ("Geri", "Back")][0]
    while pop.st["y0"] > 1998:
        prev.click()
    if ctx["shots"]:
        _pump(app, 4)
        pop.grab().save(os.path.join(ctx["shots"], "picker_years.png"))
    [b for b in pop.findChildren(QPushButton) if b.text() == "1998"][0].click()
    assert pop.st["mode"] == "months" and pop.st["y"] == 1998
    [b for b in pop.findChildren(QPushButton) if b.text() in ("Mart", "March")][0].click()
    assert pop.st["mode"] == "days" and (pop.st["y"], pop.st["m"]) == (1998, 3)
    pop.findChildren(MonthCalendar)[0].day_clicked.emit(_date(1998, 3, 14))
    _pump(app)
    assert od.value() == "1998-03-14" and gone(pop)
    # yazarak
    od.ed.click()
    _pump(app)
    pop = od.ed.popup
    e = pop.findChildren(QLineEdit)[0]
    e.setText("5.1.2027")
    e.returnPressed.emit()
    _pump(app)
    assert od.value() == "2027-01-05" and gone(pop)
    assert DateButton.parse("31.02.2026") is None and DateButton.parse("17/11/26") == _date(2026, 11, 17)
    assert DateButton.parse("2026-11-17") == _date(2026, 11, 17) and DateButton.parse("abc") is None
    # saat: önce kapalı; saat seçince anahtar açılır
    assert ot.value() is None
    ot.ed.setEnabled(True)
    ot.ed.click()
    _pump(app)
    pop = ot.ed.popup
    if ctx["shots"]:
        _pump(app, 4)
        pop.grab().save(os.path.join(ctx["shots"], "picker_time.png"))
    [b for b in pop.findChildren(QPushButton) if b.text() == "14"][0].click()
    [b for b in pop.findChildren(QPushButton) if b.text() == ":35"][0].click()
    _pump(app)
    assert ot.value() == "14:35" and gone(pop), ot.value()
    ot.ed.click()
    _pump(app)
    ed = ot.ed.popup.findChildren(QLineEdit)[0]
    ed.setText("0830")
    ed.returnPressed.emit()
    _pump(app)
    assert ot.value() == "08:30", ot.value()
    ot.ed.step(1)
    assert ot.value() == "08:45"
    ot.ed.set_value("08:50")
    ot.ed.step(-1)
    assert ot.value() == "08:45"
    ot.ed.set_value("23:50")
    ot.ed.step(1)
    assert ot.value() == "00:00"
    assert TimeButton._parse("9.30") == (9, 30) and TimeButton._parse("abc") is None and TimeButton._parse("9") == (9, 0) and TimeButton._parse("25:00") is None
    if ctx["shots"]:
        od.ed.click()
        _pump(app, 4)
        od.ed.popup.grab().save(os.path.join(ctx["shots"], "picker_date.png"))
        od.ed.popup.close()
    d.reject()
    _pump(app)


@step("hedefler > CV: şu anki + hayalimdeki yan yana, gerçekleşti, hedefe çevir, PDF, telefona gitmez")
def _cv(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    import json
    import tempfile
    from alphaapp import web
    from alphaapp.pages import cv as cvmod
    a = store.add("cv", {"side": "now", "section": "education", "title": "Makine Mühendisliği", "when": "2023 – "})
    b = store.add("cv", {"side": "dream", "section": "experience", "title": "GIZLI_CV_STAJ", "org": "Baykar"})
    c = store.add("cv", {"side": "dream", "section": "languages", "title": "Almanca", "detail": "B2"})
    gp = win.pages["goals"]
    gp.tabs.select("cv")
    win.show_page("goals")
    _pump(app)
    gp.refresh()
    _pump(app)
    assert gp.cv.isVisible() and not gp.board_host.isVisible() and gp.tabs.isVisible()
    titles = [lb.text() for lb in gp.cv.c_dream.findChildren(QLabel) if lb.isVisibleTo(gp.cv.c_dream)]
    assert any("GIZLI_CV_STAJ" in x for x in titles), titles
    # hayaldeki sayfada şu anki madde soluk görünür; aynı kurumla hayalde madde varsa gizlenir
    assert "Makine Mühendisliği" in titles, titles
    store.update("cv", a["id"], org="Gazi Üniversitesi")
    d = store.add("cv", {"side": "dream", "section": "education", "title": "Makine Müh. (mezun)",
                         "org": "Gazi Üniversitesi", "detail": "AGNO 3.00"})
    gp.refresh()
    _pump(app)
    dt = [lb.text() for lb in gp.cv.c_dream.findChildren(QLabel) if lb.isVisibleTo(gp.cv.c_dream)]
    nt = [lb.text() for lb in gp.cv.c_now.findChildren(QLabel) if lb.isVisibleTo(gp.cv.c_now)]
    assert "Makine Mühendisliği" not in dt and "Makine Müh. (mezun)" in dt and "Makine Mühendisliği" in nt, dt
    store.delete("cv", d["id"])
    pr = store.add("cv", {"side": "now", "section": "profile", "title": "GIZLI_AD", "org": "Yaş 20"})
    gp.refresh()
    _pump(app)
    dt = [lb.text() for lb in gp.cv.c_dream.findChildren(QLabel) if lb.isVisibleTo(gp.cv.c_dream)]
    assert "GIZLI_AD" in dt     # hayalde üst bilgi yoksa şu ankinden
    assert cvmod._year("2021 - Günümüz") == 9999 and cvmod._year("Haziran 2024 – Eylül 2024") == 2024
    assert "0" in gp.cv.summary.text() and "2" in gp.cv.summary.text(), gp.cv.summary.text()
    new = cvmod.realize(store, store.get("cv", b["id"]))
    assert new["side"] == "now" and new["title"] == "GIZLI_CV_STAJ" and store.get("cv", b["id"])["done"]
    assert cvmod.progress(store) == (1, 2)
    g = cvmod.to_goal(store, store.get("cv", c["id"]))
    assert store.get("goals", g["id"])["area"] == "education" and store.get("cv", c["id"])["goal"] == g["id"]
    f = os.path.join(tempfile.mkdtemp(), "ozgecmis.pdf")
    open(f, "wb").write(b"%PDF-1.4 test")
    cvmod.attach_pdf(f)
    assert cvmod.pdf_path() and cvmod.pdf_path().startswith(cvmod.CV_DIR)
    gp.refresh()
    _pump(app)
    assert gp.cv.b_pdf.isVisibleTo(gp.cv.c_now)
    assert "GIZLI_CV_STAJ" not in json.dumps(web.build_snapshot(store), ensure_ascii=False)
    if ctx["shots"]:
        win.resize(1280, 900)
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "goals_cv.png"))
    for x in (a, b, c, new, pr):
        store.delete("cv", x["id"])
    store.delete("goals", g["id"])
    gp.tabs.select("board")


@step("hayat > harita (il / ülke / şehir işaretle, türetilmiş renk) + bucket list panosu; telefona gitmez")
def _places_bucket(ctx):
    import json
    from PyQt6.QtCore import QPoint, QPointF
    from alphaapp.components import Row
    from alphaapp.i18n import t
    from alphaapp import web
    from alphaapp.pages import places as pl
    from alphaapp.pages.bucket import toggle_done
    from PyQt6.QtWidgets import QPushButton
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    g = pl.geo()
    assert len(g["tr"]) == 81 and len(g["world"]) > 150 and g["cities"], "geo verisi"
    assert pl.province_at(32.85, 39.93)[1] == "Ankara" and pl.province_at(29.0, 41.05)[1] == "İstanbul"
    page = win.pages["goals"]
    win.show_page("goals")
    page.tabs.select("map")
    _pump(app)
    pv = page.places
    assert pv.isVisible() and not page.cv.isVisible() and not page.bucket.isVisible()
    assert not hasattr(win.pages["library"], "places"), "harita Kütüphane'de kalmış"
    assert all(c.text() != "gv_" + v for v in ("bucket", "map") for c in page.tabs.findChildren(QPushButton)), "sekme adı çevrilmemiş"
    # haritada tıkla → menü → Gittim
    mp = pv.map
    xf = mp._xf()
    pt = xf.map(QPointF(32.85 * pl._K["tr"], -39.93))
    mp.click_at(pt, QPoint(0, 0))
    acts = [a for a in pv.last_menu.actions() if a.text() == t("pl_mark_been")]
    acts[0].trigger()
    _pump(app)
    assert pl.find_place(store, "province", "6")["status"] == "been"
    # arama: şehir (İzmir il olarak), ülke
    pv.search.setText("GIZLI_YOK_BOYLE")
    pv._add_search("want")
    pv.search.setText("İzmir (" + t("pl_province") + ")")
    pv._add_search("want")
    jp = next((k for k in pv._names if k.startswith("Tokyo, ")), None)
    assert jp, "Tokyo yok"
    pv.search.setText(jp)
    pv._add_search("want")
    pv.search.setText("İtalya (" + t("pl_country") + ")")
    pv._add_search("been")
    _pump(app)
    rec, prov, country = pl.status_maps(store)
    assert prov["6"] == "been" and prov["35"] == "want" and country["TUR"] == "been"
    assert country["JPN"] == "want" and country["ITA"] == "been", country
    assert pv.modes.current == "world"
    assert "1/81" in pv.card.sub_lbl.text() and "2" in pv.card.sub_lbl.text(), pv.card.sub_lbl.text()
    assert len(pv.c_been.findChildren(Row)) == 2 and len(pv.c_want.findChildren(Row)) == 2
    # aynı yere ikinci kez: tekrar eklenmez, durum değişir; menüden kaldır
    pl.set_status(store, "province", "35", "İzmir", "been")
    assert len([x for x in store.all("places") if x["key"] == "35"]) == 1 and pl.status_maps(store)[1]["35"] == "been"
    pl.set_status(store, "province", "35", "İzmir", None)
    assert pl.find_place(store, "province", "35") is None
    mp.grab()
    pv.modes.select("tr")
    _pump(app)
    if ctx["shots"]:
        win.resize(1280, 900)
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "library_map_tr.png"))
        pv.modes.select("world")
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "library_map_world.png"))
    # bucket list
    page.tabs.select("bucket")
    _pump(app)
    bv = page.bucket
    assert bv.isVisible() and not pv.isVisible()
    a = store.add("bucket", {"title": "GIZLI_F1_YARISI", "category": "event", "place": "Monza", "year": 2028})
    b = store.add("bucket", {"title": "Kuzey ışıkları", "category": "travel"})
    _pump(app)
    assert len(bv.board.goals) == 2 and "Monza" in bv.board.meta_of(store.get("bucket", a["id"]), 0, 0)
    toggle_done(store, store.get("bucket", a["id"]))
    assert store.get("bucket", a["id"])["done"] and store.get("bucket", a["id"])["done_date"]
    bv.filter.select("open")
    _pump(app)
    assert [x["id"] for x in bv.board.goals] == [b["id"]]
    bv.filter.select("all")
    snap = json.dumps(web.build_snapshot(store), ensure_ascii=False)
    assert "GIZLI_F1" not in snap and "Monza" not in snap and "Tokyo" not in snap
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "library_bucket.png"))
    for c in ("bucket", "places"):
        for x in list(store.all(c)):
            store.delete(c, x["id"])
    page.tabs.select("board")


@step("spor girişi: Vücudum (kilo / yağ grafiği), Gelişimim yakın plan + max değer girişi, ayrıntıya kaydırma")
def _sport_top(ctx):
    from alphaapp.pages.sport_top import MaxDialog
    from alphaapp.pages.sport_ui import LineChart
    from alphaapp.config import prefs
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    page = win.pages["sport"]
    win.show_page("sport")
    _pump(app)
    added = []
    for k, (w, f) in enumerate(((84.0, 18.0), (82.5, 17.0), (81.0, 16.0))):
        added.append(store.add("body", {"date": (date.today() - timedelta(days=20 - 10 * k)).isoformat(),
                                        "weight": w, "fat": f}))
    _pump(app)
    page.refresh()
    _pump(app)
    assert len(page.c_stats.findChildren(LineChart)) == 1
    txt = " ".join(lb.text() for lb in page.c_stats.findChildren(QLabel))
    assert "81" in txt and "16" in txt and "68" in txt, txt     # yağsız kütle 81 × 0.84 ≈ 68
    n0 = len(store.all("lifts"))
    d = MaxDialog(win)
    d.rows["Bench Press"][0].setValue(100)
    d.rows["Deadlift"][0].setValue(180)
    d.rows["Deadlift"][1].setValue(3)
    d.save()
    _pump(app)
    new = store.all("lifts")[n0:]
    assert {x["name"] for x in new} >= {"Bench Press", "Deadlift"}, new
    page.refresh()
    _pump(app)
    assert page.c_dev.model.heat and any(v > 0 for v in page.c_dev.model.heat.values())
    assert "Bench Press" in " ".join(lb.text() for lb in page.c_dev.findChildren(QLabel))
    page._open_dev()
    _pump(app)
    assert page.c_hero.mode == "dev"
    # ölçülerle yağ oranı (ABD Donanması): boyun / bel (/ kalça)
    from alphaapp import fitness
    from alphaapp.pages.sport_top import FatDialog
    assert fitness.navy_bodyfat("m", 180, 38, 85) == 16.1 and fitness.navy_bodyfat("f", 165, 32, 70) is None
    assert 20 < fitness.navy_bodyfat("f", 165, 32, 70, 95) < 30 and fitness.navy_bodyfat("m", 180, 50, 40) is None
    fd = FatDialog(win)
    fd.sex.select("m")
    for k, v in (("height", 180), ("weight", 80), ("neck", 38), ("waist", 85), ("hip", 0), ("chest", 102)):
        fd.spins[k].setValue(v)
    assert fd.ok.isEnabled() and "16" in fd.result.text(), fd.result.text()
    if ctx["shots"]:
        fd.show()
        _pump(app, 4)
        fd.grab().save(os.path.join(ctx["shots"], "fat_dialog.png"))
    fd.save()
    _pump(app)
    rec = next(b for b in store.all("body") if b["date"] == date.today().isoformat())
    assert rec["fat"] == 16.1 and rec["neck"] == 38 and rec["chest"] == 102 and prefs.get("body_height") == 180
    added.append(rec)
    hb = store.add("body", {"date": (date.today() - timedelta(days=1)).isoformat(), "neck": 38, "waist": 90})
    assert fitness.fat_of(hb) and fitness.fat_of(hb) > 16      # yağ girilmemiş: ölçülerden hesaplanır
    added.append(hb)
    page.refresh()
    _pump(app)
    page.verticalScrollBar().setValue(0)
    if ctx["shots"]:
        win.resize(1400, 900)
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "sport_top.png"))
    for x in new:
        store.delete("lifts", x["id"])
    for x in added:
        store.delete("body", x["id"])


@step("sadeleştirme: bölüm seçimi (hazır seçim, menüden gizle, veri kalır), ilk açılış koşulu, satırda ⋮ menü düğmesi")
def _sections(ctx):
    from alphaapp import navmenu
    from alphaapp.components import Row
    from alphaapp.config import prefs
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    old = prefs.get("nav_layout")
    assert not navmenu.should_onboard(store)          # kayıt varken ilk açılış penceresi çıkmaz
    d = navmenu.SectionsDialog(win)
    d._preset("fitness")
    assert d.selected() == {"habits", "sport", "mind"}
    if ctx["shots"]:
        d.show()
        _pump(app, 4)
        d.grab().save(os.path.join(ctx["shots"], "sections_dialog.png"))
    d._save()
    win.nav.rebuild()
    vis = navmenu.visible()
    assert "sport" in vis and "today" in vis and "schedule" in vis and "finance" not in vis and "education" not in vis
    assert store.all("courses"), "gizlenen bölümün verisi silinmez"
    assert prefs.get("sections_done")
    navmenu.apply_sections(navmenu.SECTIONS)
    assert set(navmenu.SECTIONS) <= set(navmenu.visible())
    prefs.set("nav_layout", old)
    win.nav.rebuild()
    # sağ tık menüsü olan satırda ⋮
    win.show_page("today")
    _pump(app, 4)
    rows = [r for r in win.pages["today"].findChildren(Row) if r.isVisible() and r.receivers(r.menu_requested)]
    assert rows and all(r._more is not None for r in rows)
    r = Row("GIZLI_SATIR", "alt")                       # ⋮ tıklanınca menü sinyali (gerçek menü açılmadan)
    got = []
    r.menu_requested.connect(lambda pos: got.append(pos))
    win.pages["today"].add(r)
    _pump(app, 2)
    r._more.click()
    assert got
    r.hide()
    r.setParent(None)


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
