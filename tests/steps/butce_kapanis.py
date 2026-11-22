"""Duman testi: bütçe (grup tavanları, abonelikler), akşam kapanışı."""
import os
from datetime import date, datetime, timedelta

from smoke_base import step, _pump


@step("bütçe: kategori grupları, tavan / uyarı / hız çizgisi, abonelikler kartı")
def _budget(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from erk import budget
    from erk.forms.schemas import schema
    td = date.today()
    assert budget.group_of("Akaryakıt") == "transport" and budget.group_of("benzin") == "transport"
    assert budget.group_of("Yemek") == "food" and budget.group_of("bilinmeyen") == "other"
    cats = [f for f in schema("transactions", store) if f[0] == "category"]
    assert cats, "işlem formunda kategori yok"
    base = budget.spent(store, td.year, td.month).get("food", 0.0)
    tx = store.add("transactions", {"kind": "expense", "category": "Market", "amount": 900, "date": td.isoformat()})
    budget.set_cap("food", base + 1000)
    assert budget.caps()["food"] == round(base + 1000, 2)
    al = {g: r for g, _s, _c, r in budget.alerts(store, td)}
    assert "food" in al and 0.8 <= al["food"] <= 1, al
    st = {g: (s, c, r, p) for g, s, c, r, p in budget.status(store, td)}
    assert "subs" not in st and 0 < st["food"][3] <= 1
    sub = store.add("recurring", {"name": "Test Abonelik", "kind": "expense", "category": "Abonelik",
                                  "amount": 120, "day": td.day})
    names = [r["name"] for r, _a in budget.subscriptions(store)]
    assert "Test Abonelik" in names
    assert budget.next_renewal(sub, td) == td
    win.show_page("finance")
    _pump(app, 4)
    page = win.pages["finance"]
    assert page.c_budget.body.count() >= 1 and page.c_subs.body.count() >= 1
    assert page.c_subs.sub_lbl.text(), "abonelik toplamı yok"
    if shots:
        _pump(app, 6)
        page.grab().save(os.path.join(shots, "finance_budget.png"))
    budget.set_cap("food", 0)
    assert "food" not in budget.caps()
    store.delete("transactions", tx["id"])
    store.delete("recurring", sub["id"])
    _pump(app)


@step("akşam kapanışı: davet saati, kalanlar yarına / tarihsiz + geri al, yarının odağı, not → sabah planı")
def _shutdown(ctx):
    win, app, store, shots = ctx["win"], ctx["app"], ctx["store"], ctx["shots"]
    from erk.config import prefs
    from erk.config import day_today
    from erk.pages import shutdown
    td = day_today()
    D = lambda k: (td + timedelta(days=k)).isoformat()  # noqa: E731
    prefs.set("last_shutdown", None)
    late = datetime.combine(td, datetime.min.time()).replace(hour=21)
    early = late.replace(hour=9)
    assert shutdown.is_due(late) and not shutdown.is_due(early)
    prefs.set("evening_shutdown", False)
    assert not shutdown.is_due(late)
    prefs.set("evening_shutdown", True)

    a = store.add("tasks", {"title": "Akşam kalan 1", "category": "work", "due": D(0)})
    b = store.add("tasks", {"title": "Akşam kalan 2", "category": "personal", "due": D(-1)})
    store.set_day(td, intention="Raporu bitir")
    page = win.pages["shutdown"]
    win.open_shutdown()
    _pump(app)
    assert win.current == "shutdown" and page.step == 0
    assert page.c_intent.isVisible()
    page.out_btns["partly"].click()
    _pump(app)
    assert store.day(td)["intention_met"] == "partly"
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "shutdown_1_review.png"))
    page.next()
    _pump(app)
    assert {a["id"], b["id"]} <= set(page.left_rows), page.left_rows
    page.left_rows[b["id"]].btns["someday"].click()
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "shutdown_2_left.png"))
    page.next()
    _pump(app)
    assert store.get("tasks", a["id"])["due"] == D(1)
    assert store.get("tasks", b["id"])["due"] is None
    win.toast_w._cb()            # geri al
    _pump(app)
    assert store.get("tasks", a["id"])["due"] == D(0) and store.get("tasks", b["id"])["due"] == D(-1)
    page.go(1)
    _pump(app)
    page.next()                  # varsayılan: hepsi yarına
    _pump(app)
    assert store.get("tasks", b["id"])["due"] == D(1)
    page.toggle_focus(store.get("tasks", a["id"]))
    _pump(app)
    assert store.get("tasks", a["id"])["focus"] == D(1)
    if shots:
        _pump(app, 6)
        win.grab().save(os.path.join(shots, "shutdown_3_tomorrow.png"))
    page.next()
    _pump(app)
    page.note.setText("İlk iş grafikler")
    page.next()                  # bitir
    _pump(app)
    assert win.current == "today" and prefs.get("last_shutdown") == td.isoformat()
    assert store.day(td)["shutdown_note"] == "İlk iş grafikler" and store.day(td).get("closed_at")
    assert not shutdown.is_due(late)
    assert not win.pages["today"].c_shut.isVisible()
    for x in (a, b):
        store.delete("tasks", x["id"])
    _pump(app)
