"""Duman testi: komut satırı kapısı (cli.run) ve besin kütüphanesi (nutrition)."""
import json
import os

from smoke_base import step, _pump


@step("komut satırı: besin kütüphanesi, gramla öğün (yarım öğün yazmaz), day özeti, list / add / set / del, alışkanlık")
def _cli(ctx):
    from erk import cli, nutrition as nu
    from erk.config import day_today
    from erk.components import Row
    win, app, store = ctx["win"], ctx["app"], ctx["store"]
    td = day_today()

    def ok(*argv):
        code, out = cli.run(store, list(argv))
        assert code == 0, (argv, out)
        return out

    def bad(*argv):
        code, out = cli.run(store, list(argv))
        assert code != 0 and out.startswith("hata"), (argv, out)
        return out

    assert "meal" in ok("help")
    ok("food", "add", "GIZLI Pirinç (çiğ)", "kcal=360", "protein=7", "carbs=79", "fat=0,6", "aliases=gizlipirinç,baldo")
    ok("food", "add", "GIZLI Protein tozu", "kcal=380", "protein=78", "carbs=8", "fat=5", "unit=ölçek", "unit_g=30")
    bad("food", "add", "GIZLI Pirinç (çiğ)", "kcal=1", "protein=1", "carbs=1", "fat=1")       # aynısı var
    bad("food", "add", "GIZLI eksik", "kcal=1")                                                 # makro eksik
    rice = nu.find_food(store, "baldo")[0]
    powder = nu.find_food(store, "gizli protein")[0]
    assert rice and powder and rice["fat"] == 0.6
    # miktar: gram, birimli, birimsiz küçük sayı = birim
    assert nu.parse_amount("200", rice) == (200.0, "200 g")
    assert nu.parse_amount("2 ölçek", powder)[0] == 60 and nu.parse_amount("2", powder)[0] == 60
    assert nu.parse_amount("45g", powder)[0] == 45
    try:
        nu.parse_amount("2 kase", rice)
        raise AssertionError("tanınmayan birim kabul edildi")
    except ValueError:
        pass
    n0 = len(store.meals_on(td))
    out = bad("meal", "baldo:200", "yok_boyle_besin:100")          # biri bilinmiyorsa hiçbiri yazılmaz
    assert "kütüphanede yok" in out and len(store.meals_on(td)) == n0
    out = ok("meal", "baldo:200", "GIZLI protein tozu:2 ölçek")
    assert "720 kcal" in out and "228 kcal" in out and "gün:" in out, out
    added = store.meals_on(td)[n0:]
    assert [m["grams"] for m in added] == [200.0, 60.0] and added[0]["food"] == rice["id"]
    assert ok("meal", "baldo 100", "--date", "dün").startswith("+ ")
    assert any(m.get("grams") == 100.0 for m in store.meals_on(td.fromordinal(td.toordinal() - 1)))
    day = ok("day")
    assert day.startswith("# " + td.isoformat()) and "GIZLI Pirinç" in day
    # genel komutlar
    out = ok("add", "tasks", "title=GIZLI cli görevi", "due=yarın", "category=education")
    tid = json.loads(out[2:])["id"]
    assert store.get("tasks", tid)["due"] == td.fromordinal(td.toordinal() + 1).isoformat()
    ok("set", "tasks", "GIZLI cli görevi", "priority=high")
    assert store.get("tasks", tid)["priority"] == "high"
    lst = ok("list", "tasks", "--q", "GIZLI cli", "--fields", "title,priority")
    assert json.loads(lst) == {"id": tid, "title": "GIZLI cli görevi", "priority": "high"}
    ok("del", "tasks", tid)
    assert store.get("tasks", tid) is None
    bad("list", "yok_boyle")
    bad("add", "sleep", "date=31.02.2026")
    # alışkanlık
    h = store.add("habits", {"name": "GIZLI cli alışkanlık", "goal": 7})
    assert "tam" in ok("habit", "gizli cli alış")
    assert "yarım" in ok("habit", "GIZLI cli alışkanlık", "--half")
    assert "boş" in ok("habit", "GIZLI cli alışkanlık", "--off")
    # çalışan uygulamanın sunucu yanıtı (tek satır JSON)
    r = json.loads(cli.handle_request(store, json.dumps({"cli": ["food", "list", "gizli"]}).encode()).decode())
    assert r["code"] == 0 and "GIZLI Protein tozu" in r["out"]
    r = json.loads(cli.handle_request(store, b"{bozuk").decode())
    assert r["code"] == 1
    # Spor sayfasında besin kütüphanesi kartı
    page = win.pages["sport"]
    win.show_page("sport")
    _pump(app, 4)
    rows = [w.title.text() if hasattr(w, "title") else "" for w in page.c_foods.findChildren(Row)]
    assert len(page.c_foods.findChildren(Row)) >= 2, rows
    if ctx["shots"]:
        page.ensureWidgetVisible(page.c_foods)
        _pump(app, 4)
        win.grab().save(os.path.join(ctx["shots"], "sport_foods.png"))
    # temizlik
    for m in list(store.all("meals")):
        if m.get("food") in (rice["id"], powder["id"]):
            store.delete("meals", m["id"])
    for f in (rice, powder):
        store.delete("foods", f["id"])
    store.delete("habits", h["id"])
