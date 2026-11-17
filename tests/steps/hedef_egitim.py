"""Duman testi: ekonomi hedefi, spor arası, hedefler, not ortalaması, menü, projeler, sınava sürükleme."""
import os
from datetime import date, timedelta


from smoke_base import step, _pump, _tmp


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
    page.tabs.btns["grades"].click()        # not çubukları Notlar sekmesinde
    _pump(app)
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
    from alphaapp.pages.grades_view import _TermTile
    tiles = page.c_transcript.findChildren(_TermTile)
    assert tiles and sum(1 for x in tiles if x.property("open")) == 1          # sınıf × dönem ızgarası
    # dönemi bitir: gerçek harf transkripte yazılır, tekrar alınan ders güncellenir, geri al
    store.update("courses", c["id"], letter="AA", name="Fizik I", credits=6)
    n0 = len(store.all("transcript"))
    added, changed = grades.finish_semester(store, "1.2")
    assert not added and changed and store.get("transcript", changed[0]["id"])["letter"] == "AA"
    assert store.get("transcript", changed[0]["id"])["old_letter"] == "DC" and len(store.all("transcript")) == n0
    store.update("transcript", changed[0]["id"], letter="DC", old_letter=None)
    store.update("courses", c["id"], letter=None)
    _pump(app)


@step("sınav sırası: ders kartı = not çubuğu (Quiz 1/2 finalden önce); not alanına NA → 0")
def _exam_order(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp import grades
    from alphaapp.forms import _parse_num
    from alphaapp.pages.grades_view import course_exams
    from alphaapp.components import Row
    assert grades.exam_order("Quiz 2") == grades.exam_order("Quiz") < grades.exam_order("Final")
    assert grades.exam_order("Bilinmeyen") < grades.exam_order("Final")
    assert grades.exam_canon("Quiz 2") == "Quiz 2"            # kayıttaki ad değişmez
    assert _parse_num("NA") == 0.0 and _parse_num("na") == 0.0 and _parse_num("") is None
    c = store.add("courses", {"name": "Sıra Dersi", "credits": 5})
    for nm, w, d in (("Final", 40, "2027-01-10"), ("Quiz 2", 2.5, None), ("Vize 2", 30, "2026-12-01"),
                     ("Vize 1", 25, "2026-12-20"), ("Quiz 1", 2.5, None)):
        store.add("exams", {"course": c["id"], "name": nm, "weight": w, "date": d})
    order = [e["name"] for e in course_exams(store, c["id"])]
    assert order == ["Vize 1", "Vize 2", "Quiz 1", "Quiz 2", "Final"], order
    win.show_page("education")
    _pump(app)
    page = win.pages["education"]
    page.refresh()
    page.show_course(c["id"])
    _pump(app)
    names = [r.title_lbl.text() for r in page.detail_host.findChildren(Row) if r.isVisible()]
    shown = [n for n in names if n in order]
    assert shown == order, shown
    for e in list(store.all("exams")):
        if e.get("course") == c["id"]:
            store.delete("exams", e["id"])
    store.delete("courses", c["id"])


@step("Eğitim sekmeleri: ev / Dersler / Notlar; sınav çalışma kareleri (konu satırları, tıkla = doldur / uzat)")
def _edu_tabs(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from alphaapp.components import Row
    from alphaapp.config import day_today
    from alphaapp.pages.edu_study import ExamStudy, cols_for, wants_blocks, rows_of, goal_of, done_of
    td = day_today()
    assert cols_for(12) == 4 and cols_for(20) == 5 and cols_for(3) == 3
    c = store.add("courses", {"name": "Kare Dersi", "credits": 5, "target": "BA"})
    v1 = store.add("exams", {"course": c["id"], "name": "Vize 1", "weight": 40,
                             "date": (td + timedelta(days=5)).isoformat()})
    q = store.add("exams", {"course": c["id"], "name": "Quiz 1", "weight": 10})
    old = store.add("exams", {"course": c["id"], "name": "Vize 2", "weight": 10,
                              "date": (td - timedelta(days=3)).isoformat()})
    store.add("exams", {"course": c["id"], "name": "Final", "weight": 40})
    assert not wants_blocks(v1, td) and not wants_blocks(q, td)          # kare atanmadan özete girmez
    # eski kayıt (study_goal / study_done) satırlara bölünür
    assert [r["n"] for r in rows_of({"study_goal": 20, "study_done": 7})] == [5, 5, 5, 5]
    assert done_of({"study_goal": 20, "study_done": 7}) == 7 and goal_of({}) == 0
    page = win.pages["education"]
    win.show_page("education")
    _pump(app)
    page._tab("home")
    _pump(app)
    assert page.c_over.isVisible() and page.c_exams.isVisible() and not page.c_list.isVisible()
    assert not page.c_grades.isVisible()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "edu_home.png"))
    # Derslerim satırına tıkla → Dersler sekmesi, o ders seçili
    r = [x for x in page.c_over.findChildren(Row) if x.title_lbl.text() == "Kare Dersi"][0]
    r.clicked.emit()
    _pump(app)
    assert page.tabs.current == "courses" and page.sel == c["id"] and page.c_list.isVisible()
    sel_rows = [x for x in page.c_list.findChildren(Row) if x.property("sel")]
    assert len(sel_rows) == 1 and sel_rows[0].title_lbl.text() == "Kare Dersi"
    studies = [w for w in page.detail_host.findChildren(ExamStudy) if w.isVisible()]
    assert len(studies) == 4, len(studies)          # her sınavda (geçmiş Vize 2 dahil) kare atanabilir
    def study(eid):
        return [w for w in page.detail_host.findChildren(ExamStudy) if w.eid == eid and w.isVisible()][0]
    b = study(v1["id"]).blocks
    assert b.rows == [] and not study(v1["id"]).lbl.isVisible()
    b.click(0, 2)                                  # yeni konu satırı, 3. soluk kare → 3 karelik konu
    assert rows_of(store.get("exams", v1["id"])) == [{"t": "", "n": 3, "d": 0}]
    b.click(1, 4)                                  # ikinci konu: 5 kare
    b.click(0, 1)                                  # ilk konu: 2 kare dolu
    b.click(0, 5)                                  # ilk konuyu 6 kareye uzat
    b.click(1, 0)
    b.click(1, 0)                                  # son dolu kare → geri al
    e = store.get("exams", v1["id"])
    assert [(r["n"], r["d"]) for r in rows_of(e)] == [(6, 2), (5, 0)], rows_of(e)
    assert goal_of(e) == 11 and done_of(e) == 2 and wants_blocks(e, td)
    b.cut(0, 1)                                    # buradan sonrasını sil
    assert [(r["n"], r["d"]) for r in rows_of(store.get("exams", v1["id"]))] == [(1, 1), (5, 0)]
    b.rows[0]["t"] = "Türev"
    b.cut(1, 0)                                    # konuyu sil
    assert rows_of(store.get("exams", v1["id"])) == [{"t": "Türev", "n": 1, "d": 1}]
    # geçmiş sınava kare: kendisine yazılır, sonrakine değil
    ob = study(old["id"]).blocks
    ob.click(0, 3)
    ob.click(0, 3)
    assert done_of(store.get("exams", old["id"])) == 4 and not store.get("exams", v1["id"]).get("study_goal")
    fin = [x for x in store.all("exams") if x.get("course") == c["id"] and x["name"] == "Final"][0]
    assert goal_of(fin) == 0
    store.update("exams", v1["id"], study=[{"t": "Türev", "n": 4, "d": 3}, {"t": "İntegral", "n": 3, "d": 1},
                                           {"t": "Seriler", "n": 5, "d": 2}])
    page.refresh()
    _pump(app)
    assert study(v1["id"]).blocks.rows[1]["t"] == "İntegral" and study(v1["id"]).lbl.isVisible()
    if ctx["shots"]:
        page.refresh()
        page.verticalScrollBar().setValue(0)
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "edu_courses.png"))
    # yaklaşan sınavlar (ev): haftalara bölünmüş, geçmiş yok, tarihsizler sonda; ders ikonları
    from alphaapp.pages.education import course_icon
    assert course_icon("Akışkanlar Mekaniği I") == "course_fire" and course_icon("Fizik I") == "course_science"
    assert course_icon("Kalite Kontrol") == "course_gear" and course_icon("Edebiyat") == "cat_education"
    assert "calendar" not in page.tabs.btns
    page._tab("home")
    _pump(app)
    titles = [x.title_lbl.text() for x in page.c_exams.findChildren(Row)]
    assert "Kare Dersi · Vize 1" in titles and "Kare Dersi · Final" in titles and "Kare Dersi · Vize 2" not in titles
    assert titles.index("Kare Dersi · Vize 1") < titles.index("Kare Dersi · Final")
    assert page.t_study.val.text() == "6 / 12", page.t_study.val.text()
    if ctx["shots"]:
        _pump(app, 6)
        win.grab().save(os.path.join(ctx["shots"], "edu_home2.png"))
    page.tabs.btns["grades"].click()
    _pump(app)
    assert page.c_grades.isVisible() and page.c_transcript.isVisible() and not page.c_exams.isVisible()
    page._tab("home")
    for x in list(store.all("exams")):
        if x.get("course") == c["id"]:
            store.delete("exams", x["id"])
    store.delete("courses", c["id"])
    page.sel = None


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
