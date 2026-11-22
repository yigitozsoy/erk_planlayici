"""Duman testi: sürüm 2 programı, alışkanlık kuralları, veri taşıma, plan 2, sürükle-bırak, hatırlatıcı, gün bitişi."""
import os
import sys
import tempfile
from datetime import date, timedelta

from PyQt6.QtWidgets import QLabel

from smoke_base import step, _pump, ROOT


@step("sürüm 2: önemliler kırmızı kutu, ikonlu kategori, konum kapatma, alışkanlıklar programda")
def _v2(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from erk.config import prefs
    from erk.forms import FormDialog, CategoryPicker
    from erk.pages.schedule import Block
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
    from erk import habits_core as hc
    from erk.components import DayGrid
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
    from erk.components import Row as _Row
    rows = [r for r in tp_.c_habits.findChildren(_Row) if r.title_lbl.text() == "Dene"]
    assert rows and tp_.c_habits.isVisible()
    rows[0]._toggle()
    _pump(app)
    assert (hc.state(store.get("habits", b["id"]), td) or 0) >= 1
    # web anlık görüntüsüne bırakma alışkanlığı gitmez
    from erk import web
    snap = json.dumps(web.build_snapshot(store), ensure_ascii=False)
    assert "NoFap" not in snap


# Sahte Windows Belgeler (OneDrive) klasörü: config._documents_dir SHGetFolderPathW'yi çağırır; alt süreçte taklit edilir
_FAKE_SHELL = """
import ctypes, os
class _Shell:
    def SHGetFolderPathW(self, a, b, c, d, buf):
        buf.value = os.environ["FAKE_ONEDRIVE_DOCS"]
        return 0
ctypes.windll.shell32 = _Shell()
"""


def _run_cfg(env, code):
    import subprocess
    out = subprocess.run([sys.executable, "-c", _FAKE_SHELL + code], cwd=ROOT, env=env, capture_output=True,
                         text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def _jw(path, title, **extra):
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tasks": [{"id": "x", "title": title}], **extra}, f)


def _jt(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)["tasks"][0]["title"]


def _mig_env(base):
    """Gerçek kullanıcı klasörleri yerine base altında sahte ev / LOCALAPPDATA / OneDrive (veri ortam değişkeni yok)."""
    env = {k: v for k, v in os.environ.items() if k not in ("ERK_DATA_DIR", "ALPHA_DATA_DIR")}
    env.update(USERPROFILE=os.path.join(base, "home"), LOCALAPPDATA=os.path.join(base, "local"),
               FAKE_ONEDRIVE_DOCS=os.path.join(base, "onedrive", "Belgeler"), PYTHONIOENCODING="utf-8")
    return env


_MIG = "import erk.config as c; c.migrate_old_data(); print(c.DATA_DIR + '|' + c.APP_DIR)"


@step("veri taşıma (alpha → erk): Documents\\alpha yeniden adlandırılır, OneDrive'daki eski kopya güncel veriyi EZMEZ")
def _migrate(ctx):
    import json
    import time
    # 1) gerçek durum: Documents\alpha (güncel) + OneDrive\Belgeler\alpha (16 Kasım kopyası) + %LOCALAPPDATA%\alpha
    base = tempfile.mkdtemp(prefix="erk-mig-")
    env = _mig_env(base)
    docs_a = os.path.join(base, "home", "Documents", "alpha")
    docs_e = os.path.join(base, "home", "Documents", "erk")
    one = os.path.join(base, "onedrive", "Belgeler", "alpha")
    loc_a, loc_e = os.path.join(base, "local", "alpha"), os.path.join(base, "local", "erk")
    _jw(os.path.join(one, "data.json"), "eski-onedrive")
    os.makedirs(os.path.join(one, "images"))
    open(os.path.join(one, "images", "eski.png"), "wb").close()
    one_mtime = os.path.getmtime(os.path.join(one, "data.json"))
    time.sleep(0.05)
    _jw(os.path.join(docs_a, "data.json"), "guncel")
    os.makedirs(os.path.join(docs_a, "images"))
    open(os.path.join(docs_a, "images", "hedef.png"), "wb").close()
    # 2.0 taşımasının işareti (yeni dosyaya o zamandan beri dokunuldu)
    with open(os.path.join(docs_a, ".tasindi.json"), "w", encoding="utf-8") as f:
        f.write('{"old_mtime": %f, "new_mtime": 1, "from": "x"}' % one_mtime)
    os.makedirs(loc_a)
    with open(os.path.join(loc_a, "preferences.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "Test", "backup_dir": os.path.join(docs_a, "usb"), "web_url": "https://x/api/alpha.php"}, f)
    _jw(os.path.join(loc_a, "data.json"), "eski-1x")
    os.makedirs(docs_e)                                   # boş Documents\erk (ör. elle açılmış) silinip yerine geçilir
    out = _run_cfg(env, _MIG)
    assert out == docs_e + "|" + loc_e, out
    assert not os.path.exists(docs_a) and not os.path.exists(loc_a)
    assert _jt(os.path.join(docs_e, "data.json")) == "guncel"          # 16 Kasım kopyası gelmedi
    assert os.path.exists(os.path.join(docs_e, "images", "hedef.png"))
    assert not os.path.exists(os.path.join(docs_e, "images", "eski.png"))
    assert _jt(os.path.join(one, "data.json")) == "eski-onedrive"       # eski kopyaya dokunulmadı
    assert not os.path.exists(os.path.join(one, "VERILER-TASINDI.txt"))
    with open(os.path.join(loc_e, "preferences.json"), encoding="utf-8") as f:
        p = json.load(f)
    assert p["backup_dir"] == os.path.join(docs_e, "usb") and p["name"] == "Test", p
    assert p["web_url"] == "https://x/api/alpha.php"
    # ikinci açılış: hiçbir şey değişmez; sonradan eski alpha Documents\alpha'yı yeniden yaratsa da erk onu kullanmaz
    _jw(os.path.join(docs_a, "data.json"), "eski-alpha-sonra")
    out = _run_cfg(env, _MIG)
    assert out.split("|")[0] == docs_e and _jt(os.path.join(docs_e, "data.json")) == "guncel"
    assert _jt(os.path.join(docs_a, "data.json")) == "eski-alpha-sonra"

    # 2) Documents\erk de Documents\alpha da yok → eski kopya (OneDrive\Belgeler\alpha) bir kez kopyalanır
    base = tempfile.mkdtemp(prefix="erk-mig-")
    env = _mig_env(base)
    one = os.path.join(base, "onedrive", "Belgeler", "alpha")
    _jw(os.path.join(one, "data.json"), "eski-onedrive")
    os.makedirs(os.path.join(one, "images"))
    open(os.path.join(one, "images", "eski.png"), "wb").close()
    out = _run_cfg(env, _MIG)
    docs_e = os.path.join(base, "home", "Documents", "erk")
    assert out.split("|")[0] == docs_e
    assert _jt(os.path.join(docs_e, "data.json")) == "eski-onedrive"
    assert os.path.exists(os.path.join(docs_e, "images", "eski.png")) and os.path.exists(os.path.join(one, "data.json"))
    # yeni dosya değiştikten sonra eski kopya bir daha asla üzerine yazmaz
    _jw(os.path.join(docs_e, "data.json"), "yeni")
    time.sleep(1.1)
    _jw(os.path.join(one, "data.json"), "eski-onedrive-sonra")
    _run_cfg(env, _MIG)
    assert _jt(os.path.join(docs_e, "data.json")) == "yeni"

    # 3) eski alpha açık (tek örnek borusu var) → yeniden adlandırma yok, bu oturum eski klasörlerle
    base = tempfile.mkdtemp(prefix="erk-mig-")
    env = _mig_env(base)
    docs_a = os.path.join(base, "home", "Documents", "alpha")
    _jw(os.path.join(docs_a, "data.json"), "guncel")
    _jw(os.path.join(base, "onedrive", "Belgeler", "alpha", "data.json"), "eski-onedrive")
    code = ("import os, zlib\nfrom multiprocessing.connection import Listener\n"
            "n = 'alpha-dashboard-%08x' % zlib.crc32(os.path.normcase(os.path.join(os.environ['USERPROFILE'], "
            "'Documents', 'alpha')).encode('utf-8'))\nL = Listener('\\\\\\\\.\\\\pipe\\\\' + n)\n" + _MIG.replace("; print", "\nL.close(); print"))
    out = _run_cfg(env, code)
    assert out.split("|")[0] == docs_a and out.split("|")[1] == os.path.join(base, "local", "erk"), out
    assert _jt(os.path.join(docs_a, "data.json")) == "guncel"
    assert not os.path.exists(os.path.join(base, "home", "Documents", "erk", "data.json"))

    # 4) Documents\alpha'da açık (kilitli) dosya → yeniden adlandırılamaz, o oturum Documents\alpha ile; eski kopya gelmez
    base = tempfile.mkdtemp(prefix="erk-mig-")
    env = _mig_env(base)
    docs_a = os.path.join(base, "home", "Documents", "alpha")
    _jw(os.path.join(docs_a, "data.json"), "guncel")
    _jw(os.path.join(base, "onedrive", "Belgeler", "alpha", "data.json"), "eski-onedrive")
    with open(os.path.join(docs_a, "kilit.txt"), "w") as lock:
        lock.write("x")
        lock.flush()
        out = _run_cfg(env, _MIG)
    if out.split("|")[0] == docs_a:                     # Windows: açık dosyalı klasör taşınamaz
        assert _jt(os.path.join(docs_a, "data.json")) == "guncel"
    else:
        assert _jt(os.path.join(out.split("|")[0], "data.json")) == "guncel", out

    # 5) eski ad ALPHA_DATA_DIR hâlâ okunur; ERK_DATA_DIR önceliklidir; 1.x %LOCALAPPDATA%\alpha yalnızca boşken
    base = tempfile.mkdtemp(prefix="erk-mig-")
    env = _mig_env(base)
    _jw(os.path.join(base, "local", "alpha", "data.json"), "eski-1x")
    env["ALPHA_DATA_DIR"] = os.path.join(base, "eski-ad")
    out = _run_cfg(env, "import erk.config as c; print(c.DATA_DIR)")
    assert out == os.path.join(base, "eski-ad") and not os.path.exists(os.path.join(out, "data.json"))  # import kopyalamaz
    env["ERK_DATA_DIR"] = os.path.join(base, "yeni-ad")
    out = _run_cfg(env, _MIG)
    assert out.split("|")[0] == os.path.join(base, "yeni-ad")
    assert _jt(os.path.join(base, "yeni-ad", "data.json")) == "eski-1x"
    assert os.path.exists(os.path.join(base, "local", "erk", "data.json"))   # 1.x dosyası silinmedi (yeni adla)


@step("sabah planı 2: 1-5 tuşları, dünün özeti, ilerleme, zaman şeridi + boşluğa iş koyma")
def _plan2(ctx):
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    from erk.timeline import find_gaps
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
        from erk.timeline import hhmm
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
    from erk.config import prefs
    prefs.set("last_plan", prefs_today)
    win.show_page("today")
    _pump(app)


@step("program tarih aralığı (ilk hafta / son gün), görev bitiş saati, dosya dışarıdan değişince yeniden okuma")
def _range_reload(ctx):
    import json
    import time
    store, app = ctx["store"], ctx["app"]
    from erk.forms import FormDialog
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
    from erk.pages.schedule import MIME, Block
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
    from erk.forms import FormDialog
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
    from erk.config import prefs
    from erk import sounds
    from erk.reminders import upcoming, ReminderPopup
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
    from erk.config import prefs, day_of, day_today
    prefs.set("day_end_hour", 4)
    assert str(day_of("2026-11-14T02:30:00")) == "2026-11-13"
    assert str(day_of("2026-11-14T04:00:00")) == "2026-11-14"
    assert str(day_of("2026-11-14")) == "2026-11-14"          # yalnızca tarih: kaydırma yok
    assert day_of("") is None and day_of("bozuk") is None
    now = datetime.now()
    assert day_today() == (now.date() if now.hour >= 4 else now.date() - timedelta(days=1))
    prefs.set("day_end_hour", 0)
    assert str(day_of("2026-11-14T02:30:00")) == "2026-11-14" and day_today() == date.today()
