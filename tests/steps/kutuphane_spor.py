"""Duman testi: kütüphane, spor, zihin, piyasalar, oyunlar."""
import os
from datetime import date

from PyQt6.QtWidgets import QLabel

from smoke_base import step, _pump


@step("kütüphane: kapak duvarı, filtreler, aramadan gelen kayıt formdan kaydedilir, ilerlet, Şu an kartı, web'e gitmez")
def _library(ctx):
    import json
    from erk import library, web
    from erk.forms import FormDialog
    from erk.pages.library import SearchDialog, cover_pixmap
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
    from erk.pages.shelf import Shelf, MediaViewer, open_viewer
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
    assert library.progress_text(m, __import__("erk.i18n", fromlist=["t"]).t)
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
    from erk import fitness
    from erk.config import prefs, day_today
    from erk.pages.sport_ui import WorkoutDialog, TemplateDialog, focus_text
    from PyQt6.QtCore import QPointF
    td = day_today()
    assert fitness.muscles_of("bench press")[0][0] == "chest"
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
    assert load["chest"] == 6 and load["front_delts"] == 3.75 and load["triceps"] == 2.25, load   # haritalı ağırlıklar
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
    from erk.components import Row
    assert len([r for r in sp.c_tpl.findChildren(Row)]) == 2
    # giriş kartı: gelişim (rekorlardan), son 7 gün, programlarım, popüler programlar
    from erk.body3d import Body3D, ModelView, load_frames
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
    assert fitness.muscles_of("Face Pull") == fitness.muscles_of("Cable Face Pull")          # takma ad
    assert fitness.weights_of("Barbell Squat")["quads"] == 1.0 and "Face Pull" not in fitness.EXERCISES
    assert fitness.weights_of("Arnold Press")["front_delts"] == 1.0 and fitness.standard("Barbell Squat")
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
    from erk.components import ElideLabel
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
    from erk import navmenu, balance
    from erk.config import prefs, day_today
    from erk.clock_ui import CourseClock
    from erk.pages.mind import sleep_hours, ClockPanel
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
    win.pages["education"].show_course(course["id"])
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
    from erk import markets
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
    from erk import web
    import json
    from erk.pages.wishlist import WishCard
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
    from erk import library
    from erk.i18n import t
    from erk.pages.shelf import DISC_TYPES
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


@step("Beden: ev sekmesinde başlar (kilo / yağ / gelişim), Antrenmanlar / Beslenme, ayrıntıya kaydırma sekme değiştirir")
def _body_tabs(ctx):
    win, app = ctx["win"], ctx["app"]
    from erk.i18n import t
    sp = win.pages["sport"]
    win.show_page("sport")
    _pump(app)
    assert t("nav_sport") in ("Beden", "Body") and t("cat_sport") in ("Spor", "Sport")
    assert list(sp.tabs.btns)[0] == "home"
    sp.tabs.btns["home"].click()
    _pump(app)
    assert sp.c_stats.isVisible() and sp.c_dev.isVisible() and sp.c_hero.isVisible() and sp.c_body.isVisible()
    assert not sp.c_log.isVisible() and not sp.c_food.isVisible() and not sp.c_week.isVisible()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "body_tab_home.png"))
    sp.tabs.btns["food"].click()
    _pump(app)
    assert sp.c_food.isVisible() and sp.c_meals.isVisible() and sp.c_foods.isVisible()
    assert not sp.c_log.isVisible() and not sp.c_hero.isVisible() and not sp.c_stats.isVisible()
    assert all(b.isVisible() for b in sp.tab_actions["food"]) and not any(b.isVisible() for b in sp.tab_actions["train"])
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "body_tab_food.png"))
    sp.scroll_to(sp.c_body)              # kilo ayrıntısı → ev sekmesi
    _pump(app)
    assert sp.tabs.current == "home" and sp.c_body.isVisible() and not sp.c_food.isVisible()
    sp.scroll_to(sp.c_log)               # günlük → Antrenmanlar
    _pump(app)
    assert sp.tabs.current == "train" and sp.c_log.isVisible() and sp.c_week.isVisible()
    if ctx["shots"]:
        sp.verticalScrollBar().setValue(0)
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "body_tab_train.png"))
    sp.tabs.btns["home"].click()
    _pump(app)
