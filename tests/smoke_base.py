"""Duman testinin ortak parçası: geçici veri klasörü (gerçek veriye dokunmaz), adım kaydı, örnek veri, _pump.
Adımlar tests/steps/*.py içinde; sıra = steps/__init__.py'deki içe aktarma sırası."""
import os
import sys
import tempfile
from datetime import date, timedelta

# gerçek tercihlere / verilere ASLA dokunma
_tmp = tempfile.mkdtemp(prefix="erk-test-")
os.environ["LOCALAPPDATA"] = _tmp
os.environ["ERK_DATA_DIR"] = os.path.join(_tmp, "docs-erk")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


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


def _pump(app, n=3):
    for _ in range(n):
        app.processEvents()
