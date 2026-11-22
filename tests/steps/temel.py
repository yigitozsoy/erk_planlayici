"""Duman testi: i18n, sayfalar, Bugün, web, formlar, biçimler, notlar, kalıcılık, tema, dar pencere."""
import os
import re
import glob
from datetime import date, timedelta


from smoke_base import step, _pump, ROOT


@step("i18n: koddaki tüm anahtarlar tanımlı")
def _i18n(ctx):
    from erk.i18n import S
    missing = set()
    for f in glob.glob(os.path.join(ROOT, "erk", "**", "*.py"), recursive=True):
        s = open(f, encoding="utf-8").read()
        for k in re.findall(r'\bt\(\s*"([a-z0-9_]+)"\s*[,)]', s):
            if k not in S and k != "anahtar":   # i18n.py belge metnindeki örnek
                missing.add(k)
        for k in re.findall(r'"((?:f|qa)_[a-z_]+)"', s):
            if k not in S:
                missing.add(k)
    from erk.store import CATEGORIES, COLLECTIONS
    from erk.forms import TASK_PRIORITIES, PROJECT_STATUS
    from erk.navmenu import BUILTIN
    missing |= {v[1] for v in BUILTIN.values()} - set(S)
    for c in CATEGORIES:
        missing |= {"cat_" + c} - set(S)
    for p in TASK_PRIORITIES:
        missing |= {"prio_" + p} - set(S)
    for p in PROJECT_STATUS:
        missing |= {"status_" + p} - set(S)
    from erk.pages.plan import STEPS as PSTEPS, CHOICES
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
    from erk.components import Row
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
    from erk import web
    from erk.config import day_today
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
    from erk.forms import FormDialog, guess_exam
    store, win = ctx["store"], ctx["win"]
    c = store.all("courses")[0]
    assert guess_exam(store, f"{c['name']}: Midterm 2 (D220)") == (c["id"], "Vize 2")
    from erk import grades as _gr
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
    from erk.pages import toggle_task
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
    from erk.forms import FormDialog
    from erk.store import COLLECTIONS
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
    from erk.forms import _parse_num
    assert _parse_num("1.250,50") == 1250.5
    assert _parse_num("12,5") == 12.5
    assert _parse_num("12.5") == 12.5
    assert _parse_num("") is None
    assert _parse_num("abc") is None


@step("biçimler: para, tarih")
def _fmt(ctx):
    from erk.i18n import fmt_money, fmt_day, due_badge
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
    from erk.store import Store
    store.flush()
    s2 = Store()
    for c in ("tasks", "courses", "transactions", "notes"):
        assert len(s2.all(c)) == len(store.all(c)), c


@step("tema değişimi (aydınlık ↔ karanlık)")
def _theme(ctx):
    from erk.theme import theme
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
