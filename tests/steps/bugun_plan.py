"""Duman testi: sabah planı, Bugün takvimi, kareler, masaüstü widget'ı."""
import os
from datetime import date, timedelta


from smoke_base import step, _pump


@step("sabah planı: kalanlar taşınıyor/siliniyor + geri al, hızlı ekle, odak (en fazla 3), hedef, bitir")
def _plan(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from datetime import datetime
    from erk.config import prefs
    from erk.components import Row
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
    from erk import icons
    from erk.components import Row
    from erk.pages import CAT_ICON
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
    from erk.store import streaks
    from erk.components import DayGrid, Row
    from erk.forms import FormDialog
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
    win.pages["education"].show_course(course["id"])      # Dersler sekmesi: seçili dersin kartı
    _pump(app)
    egrids = [g for g in win.pages["education"].findChildren(DayGrid) if g.isVisible()]
    assert len(egrids) == 1, len(egrids)
    assert td.isoformat() not in course.get("study_days", [])
    store.toggle_day("courses", course["id"], td, "study_days")
    _pump(app)
    assert td.isoformat() in store.get("courses", course["id"])["study_days"]
    from erk.components import Card
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
    assert abs(sp.food_rings["kcal"].value - 1250 / float(__import__("erk.config").config.prefs.get("goal_kcal") or 1)) < 1e-6
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
    from erk.config import prefs
    from erk.components import Row
    from erk.desk_widget import SECTIONS
    from erk.i18n import S
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
