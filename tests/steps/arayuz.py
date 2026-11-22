"""Duman testi: tarih seçici, CV, harita + bucket list, spor girişi, sadeleştirme, cila."""
import os
from datetime import date, timedelta

from PyQt6.QtWidgets import QLabel

from smoke_base import step, _pump


@step("tarih / saat seçici: takvimden gün, Bugün / Yarın, saat + dakika ızgarası, yazarak, tekerlek adımı")
def _pickers(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from datetime import timedelta
    from PyQt6.QtWidgets import QPushButton, QLineEdit
    from erk.config import day_today
    from erk.components import MonthCalendar
    from erk.forms import FormDialog, OptDate, OptTime
    from erk.pickers import DateButton, TimeButton
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
    from erk.widgets import IconButton
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
    from erk import web
    from erk.pages import cv as cvmod
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
    from erk.components import Row
    from erk.i18n import t
    from erk import web
    from erk.pages import places as pl
    from erk.pages.bucket import toggle_done
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
    from erk.pages.sport_top import MaxDialog
    from erk.pages.sport_ui import LineChart
    from erk.config import prefs
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
    from erk import fitness
    from erk.pages.sport_top import FatDialog
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
    from erk import navmenu
    from erk.components import Row
    from erk.config import prefs
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


@step("cila: hesap ipuçları, ikinci yedek klasörü, dar pencerede tek hafta, CV'de kırılabilen iletişim")
def _polish(ctx):
    from erk.config import prefs
    from erk.pages.sport_ui import level_tip, e1rm_tip
    from erk.pages.cv import _breakable
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    tip = level_tip("Bench Press", 100, 80)
    assert "36" in tip and "108" in tip and "1,25" in tip, tip       # eşikler kg cinsinden (80 kg × 1.0 × .45 / 1.35)
    assert "110" in e1rm_tip({"w": 100, "r": 3, "e1rm": 110})
    # ikinci yedek klasörü: varsa yazılır, yoksa sessizce atlanır
    d = os.path.join(os.environ["ERK_DATA_DIR"], "usb")
    os.makedirs(d, exist_ok=True)
    prefs.set("backup_dir", d)
    p = store.backup_now()
    assert p and os.path.exists(p) and os.path.dirname(p) == d, p
    prefs.set("backup_dir", os.path.join(os.environ["ERK_DATA_DIR"], "yok_boyle_klasor"))
    assert store.backup_now() is None
    prefs.set("backup_dir", "")
    # dar pencerede yalnızca ilk hafta
    page = win.pages["schedule"]
    win.show_page("schedule")
    old = win.size()
    win.resize(1600, 900)
    _pump(app, 6)
    assert page.rows[1].isVisible(), "geniş pencerede ikinci hafta yok"
    win.resize(760, 900)
    _pump(app, 6)
    assert not page.rows[1].isVisible() and page.rows[0].isVisible(), "dar pencerede iki hafta"
    win.resize(old)
    _pump(app, 6)
    # not sistemi: okulun tablosu farklıysa harf karşılığı değişir
    from erk import grades
    from erk.dialogs import GradePointsDialog
    assert grades.point("CB") == 2.5
    gd = GradePointsDialog(win)
    gd.spins["CB"].setValue(2.25)
    gd._save()
    assert prefs.get("grade_points") == {"CB": 2.25} and grades.point("CB") == 2.25
    if ctx["shots"]:
        gd.grab().save(os.path.join(ctx["shots"], "grade_points.png"))
    gd.deleteLater()
    prefs.set("grade_points", {})
    assert grades.point("CB") == 2.5
    assert "​" in _breakable("adi.soyadi.cok.uzun@ornek-alan-adi.com") and _breakable("kısa a@b.c") == "kısa a@b.c"
