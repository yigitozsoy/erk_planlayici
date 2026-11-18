"""Duman testi: antrenman hedefleri + progressive overload, hızlı ekle komutları."""
import os
from datetime import date, timedelta

from smoke_base import step, _pump


@step("antrenman hedefleri: e1RM ilerlemesi, eğilim / varış, çift ilerleme önerisi, haftalık hacim, kartlar")
def _overload(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from alphaapp import overload
    from alphaapp.config import prefs
    td = date.today()
    name = "Overload Test Press"
    tpl = store.add("templates", {"name": "OT", "exercises": [{"name": name, "sets": 3, "reps": "8-10"}]})
    ws = []
    for i, (w, reps) in enumerate(((60, (10, 10, 9)), (62.5, (9, 9, 8)), (62.5, (10, 10, 10)), (65, (8, 8, 8)),
                                   (65, (10, 10, 10)))):
        ws.append(store.add("workouts", {"date": (td - timedelta(days=28 - i * 7)).isoformat(), "kind": "Push",
                                         "exercises": [{"name": name, "sets": [{"r": r, "w": w} for r in reps]}]}))
    assert overload.rep_range(store, name) == (8, 10)
    s = overload.suggest(store, name)
    assert s["kind"] == "up" and s["w"] == 65 + overload.step_of(name) and s["reps"] == "8", s
    per_week, n = overload.trend(store, name, td)
    assert n == 5 and per_week > 0, (per_week, n)
    g = store.add("lift_goals", {"name": name, "w": 80, "r": 5})
    cur, tgt, ratio = overload.progress(store, g)
    assert abs(tgt - 80 * (1 + 5 / 30)) < 0.01 and 0 < ratio < 1
    e = overload.eta(store, g, td)
    assert e is None or e > td
    vol = overload.weekly_volume(store, name, td)
    assert len(vol) == 8 and vol[-1][1] == 65 * 30, vol[-1]
    # aynı ağırlıkta tekrar eksikse: tekrar artır
    store.update("workouts", ws[-1]["id"], exercises=[{"name": name, "sets": [{"r": 9, "w": 65}, {"r": 8, "w": 65}]}])
    s = overload.suggest(store, name)
    assert s["kind"] == "reps" and s["w"] == 65 and s["reps"] == "9", s

    sp = win.pages["sport"]
    win.show_page("sport")
    sp._tab("train")
    prefs.set("pr_ex", name)
    sp.refresh()
    _pump(app, 4)
    assert sp.c_lgoals.body.count() >= 1 and sp.c_lgoals.isVisible()
    assert sp.c_pr.body.count() >= 4
    if shots:
        _pump(app, 6)
        sp.ensureWidgetVisible(sp.c_pr)
        _pump(app, 2)
        win.grab().save(os.path.join(shots, "sport_overload.png"))
    store.delete("lift_goals", g["id"])
    for w in ws:
        store.delete("workouts", w["id"])
    store.delete("templates", tpl["id"])
    prefs.set("pr_ex", None)
    _pump(app)


@step("hızlı komut: İngilizce tarih / saat / #kategori / !öncelik / tekrar / harcama, tekrarlayan görev + geri al")
def _quick(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from alphaapp import quick
    from alphaapp.quick_ui import QuickDialog
    from alphaapp.pages import QuickTask
    td = date(2026, 11, 18)          # çarşamba
    P = lambda s: quick.parse(s, td, projects=[("px", "Thesis")])[1]  # noqa: E731
    x = P("call mom tomorrow 6pm #social !")
    assert (x["title"], x["due"], x["time"], x["category"], x["priority"]) == \
        ("call mom", "2026-11-19", "18:00", "social", "high"), x
    x = P("report fri 14:00-15:30 #work +thes")
    assert (x["due"], x["time"], x["end"], x["category"], x["project"]) == \
        ("2026-11-20", "14:00", "15:30", "work", "px"), x
    x = P("gym every mon,wed,fri 7am #sport")
    assert x["repeat"] == "w:0,2,4" and x["due"] == "2026-11-18" and x["title"] == "gym", x
    assert P("do 5-10 pushups")["title"] == "do 5-10 pushups"
    assert P("call tom")["title"] == "call tom" and P("call tom")["due"] is None
    assert P("exam nov 25 #school")["due"] == "2026-11-25" and P("x 21.11.2027")["due"] == "2027-11-21"
    assert P("read in 2 weeks !low")["due"] == "2026-12-02" and P("read in 2 weeks !low")["priority"] == "low"
    assert P("x next week")["due"] == "2026-11-23" and P("x tonight")["time"] == "20:00"
    coll, e = quick.parse("spent 85,5 lunch with ali", td)
    assert coll == "transactions" and e["amount"] == 85.5 and e["category"] == "Dışarıda yemek" and e["note"] == "with ali"
    assert quick.next_due("weekdays", date(2026, 11, 20), td) == date(2026, 11, 23)
    assert quick.next_due("monthly", date(2026, 10, 31), td) == date(2026, 11, 30)
    assert quick.next_due("daily", date(2026, 11, 1), td) == date(2026, 11, 19)

    # tekrarlayan görev: bitince sonraki açılır, geri alınca silinir
    real = date.today()
    tk = store.add("tasks", {"title": "Repeat test", "category": "personal", "due": real.isoformat(), "repeat": "daily"})
    store.update("tasks", tk["id"], done=True)
    nid = store.get("tasks", tk["id"])["next_id"]
    nx = store.get("tasks", nid)
    assert nx and nx["due"] == (real + timedelta(days=1)).isoformat() and nx["repeat"] == "daily" and not nx["done"]
    store.update("tasks", tk["id"], done=False)
    assert store.get("tasks", nid) is None and store.get("tasks", tk["id"])["repeat"] == "daily"
    store.delete("tasks", tk["id"])

    # Ctrl+N penceresi + kart altındaki satır
    d = QuickDialog(win)
    d.edit.setText("Quick cmd test fri 9am #work")
    assert "Quick cmd test" in d.prev.text() and d.btn.isEnabled()
    if shots:
        d.show()
        _pump(app, 4)
        d.grab().save(os.path.join(shots, "quick_command.png"))
    d._add()
    _pump(app)
    got = [x for x in store.all("tasks") if x["title"] == "Quick cmd test"]
    assert got and got[0]["category"] == "work" and got[0]["time"] == "09:00"
    win.toast_w._cb()            # geri al
    _pump(app)
    assert not [x for x in store.all("tasks") if x["title"] == "Quick cmd test"]
    q = QuickTask(win, category="education")
    q.setText("Line test every weekday")
    q._add()
    got = [x for x in store.all("tasks") if x["title"] == "Line test"]
    assert got and got[0]["repeat"] == "weekdays" and got[0]["category"] == "education", got
    store.delete("tasks", got[0]["id"])
    _pump(app)
