"""Form şemaları: her koleksiyonun alanları (schema), varsayılanlar, seçenek listeleri."""
from ..config import day_today
from ..config import prefs
from ..i18n import t


LETTERS = ("AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF")
GRADE_LETTERS = LETTERS + ("D", "NA")     # D devamsız, NA girmedi: ortalamada 0


def retake_choices(store):
    """Ders formunda "tekrar alınan ders": otomatik / yok / transkriptteki satırlar."""
    from ..grades import by_term
    out = [("", t("retake_auto")), ("none", t("retake_none"))]
    for term, rows in by_term(store.all("transcript")):
        for e in rows:
            out.append((e["id"], f"{term} · {e.get('code') or ''} {e.get('name') or ''} ({e.get('letter') or 'XX'})"))
    return out

TASK_PRIORITIES = ("normal", "high", "low")
PROJECT_STATUS = ("doing", "todo", "waiting", "done")

WORKOUT_KINDS = ("Gym", "Koşu", "Yüzme", "Bisiklet", "Yürüyüş", "Futbol", "Basketbol", "Tenis", "Yoga", "Pilates",
                 "Dövüş sporu", "Diğer")
WORKOUT_FOCUS = ("Göğüs", "Sırt", "Bacak", "Omuz", "Kol", "Karın / core", "Tüm vücut", "Push", "Pull", "Legs",
                 "Kardiyo", "Esneme")
def exam_names(store):
    """Sınav adı listesi: tanımlı türler (dile göre) + kayıtlarda geçen tanınmayan adlar."""
    from .. import grades
    from ..i18n import is_tr
    out = list(grades.exam_names(is_tr()))
    for x in store.all("exams"):
        n = (x.get("name") or "").strip()
        if n and grades.exam_kind(n) is None and n not in out:
            out.append(n)
    return out


def guess_exam(store, title):
    """Görev başlığından ders ve sınav türü tahmini: "Fizik I: Vize (D118)" → (Fizik I'in id'si, "Vize")."""
    low = (title or "").casefold()
    course = None
    best = 0
    for c in store.all("courses"):
        for key in (c.get("name"), c.get("code")):
            k = (key or "").strip().casefold()
            if k and k in low and len(k) > best:
                course, best = c["id"], len(k)
    from .. import grades
    kind = grades.find_exam_kind(low)
    if kind is None:
        for word, n in (("rapor", "Rapor teslimi"), ("teslim", "Ödev"), ("ödev", "Ödev"), ("sınav", "Vize")):
            if word in low:
                kind = n
                break
    return course, kind
EXPENSE_CATS = ("Yemek", "Dışarıda yemek", "Market", "Akaryakıt", "Otopark", "Ulaşım", "Kira", "Faturalar", "Abonelik",
                "Hobi", "Kahve", "Seyahat", "Eğlence", "Giyim", "Eğitim", "Sağlık", "Spor", "Hediye", "Diğer")
INCOME_CATS = ("Maaş", "Burs", "Harçlık", "Serbest iş", "Satış", "Faiz / getiri", "Diğer")
INVEST_KINDS = ("Hisse", "Fon", "Altın", "Döviz", "Kripto", "Mevduat", "Tahvil / bono", "Diğer")


# alan: (anahtar, etiket anahtarı, tür, seçenekler)
#   tür: text · multiline · date · date? (isteğe bağlı) · time? · number · number? · money · money? · choice ·
#        combo (yazılabilir öneri listesi) · days · bool
def project_choices(store):
    """Görev formundaki proje seçimi: (yok) + bitmemiş projeler."""
    out = [(None, t("no_project"))]
    for p in sorted(store.all("projects"), key=lambda p: (p.get("name") or "").lower()):
        if p.get("status") != "done":
            out.append((p["id"], p.get("name") or "—"))
    return out


def schema(coll, store):
    out = _schema(coll, store)
    if not prefs.get("show_place", True):
        out = [f for f in out if f[0] != "place"]
    # proje yoksa görev formunda proje satırı çıkmasın
    out = [f for f in out if not (f[0] == "project" and coll == "tasks" and len(f[3]) < 2)]
    return out


def _schema(coll, store):
    if coll == "tasks":
        return [("title", "f_title", "text", None),
                ("category", "f_category", "cats", None),
                ("due", "f_due", "date?", None),
                ("time", "f_time", "time?", None),
                ("end", "f_end", "time?", None),
                ("priority", "f_priority", "choice", [(p, t("prio_" + p)) for p in TASK_PRIORITIES]),
                ("project", "f_project", "choice", project_choices(store)),
                ("note", "f_note", "multiline", None)]
    if coll == "routine":
        return [("title", "f_title", "text", None),
                ("category", "f_category", "cats", None),
                ("days", "f_days", "days", None),
                ("start", "f_start", "time?", None),
                ("end", "f_end", "time?", None),
                ("place", "f_place", "text", None),
                ("from", "f_from", "date?", None),
                ("until", "f_until", "date?", None),
                ("important", "f_important", "bool", None)]
    if coll == "courses":
        return [("name", "f_course_name", "text", None),
                ("code", "f_code", "text", None),
                ("credits", "f_credits", "number?", None),
                ("letter", "f_letter", "choice", [("", "—")] + [(x, x) for x in GRADE_LETTERS]),
                ("target", "f_target_letter", "choice", [("", "—")] + [(x, x) for x in LETTERS]),
                ("retake", "f_retake", "choice", retake_choices(store)),
                ("note", "f_note", "multiline", None)]
    if coll == "media":
        from ..library import TYPES, STATUSES
        return [("type", "f_mtype", "choice", [(k, t("mt_" + k)) for k in TYPES]),
                ("title", "f_title", "text", None),
                ("creator", "f_creator", "text", None),
                ("status", "f_status", "choice", [(k, t("ms_" + k)) for k in STATUSES]),
                ("rating", "f_rating", "choice", [(None, "—")] + [(x / 2, "★" * (x // 2) + ("½" if x % 2 else ""))
                                                                  for x in range(1, 11)]),
                ("progress", "f_mprogress", "number?", None),
                ("total", "f_mtotal", "number?", None),
                ("started", "f_started", "date?", None),
                ("finished", "f_finished", "date?", None),
                ("year", "f_year", "number?", None),
                ("genres", "f_genres", "text", None),
                ("cover", "f_cover", "image", None),
                ("link", "f_link", "text", None),
                ("note", "f_note", "multiline", None)]
    if coll == "transcript":
        return [("name", "f_course_name", "text", None),
                ("code", "f_code", "text", None),
                ("term", "f_term", "combo", _with_used(("1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2"),
                                                       store, "transcript", "term")),
                ("credits", "f_credits", "number?", None),
                ("letter", "f_letter", "choice", [("XX", t("not_taken"))] + [(x, x) for x in GRADE_LETTERS]),
                ("target", "f_target_letter", "choice", [("", "—")] + [(x, x) for x in LETTERS]),
                ("lang", "f_lang", "text", None)]
    if coll == "exams":
        courses = [(c["id"], c.get("name", "")) for c in store.all("courses")]
        return [("course", "f_course", "choice", courses),
                ("name", "f_exam_name", "combo", exam_names(store)),
                ("date", "f_date", "date?", None),
                ("time", "f_time", "time?", None),
                ("weight", "f_weight", "number?", None),
                ("target", "f_target_score", "number?", None),
                ("score", "f_score", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "templates":            # hareketler pages/sport_ui.TemplateDialog'da düzenlenir
        return [("name", "tpl_name", "text", None),
                ("note", "f_note", "multiline", None)]
    if coll == "mood":
        return [("date", "f_date", "date", None),
                ("mood", "mood_mood", "number", None),
                ("energy", "mood_energy_l", "number?", None),
                ("stress", "mood_stress", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "sleep":
        return [("date", "f_sleep_date", "date", None),
                ("bed", "sleep_bed", "time?", None),
                ("wake", "sleep_wake", "time?", None),
                ("quality", "sleep_quality", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "sessions":
        courses = [("", "—")] + [(c["id"], c.get("name", "")) for c in store.all("courses")]
        return [("date", "f_date", "date", None),
                ("kind", "f_session_kind", "choice", [("study", t("clock_study")), ("meditation", t("clock_meditation"))]),
                ("minutes", "f_minutes", "number", None),
                ("course", "f_course", "choice", courses),
                ("note", "f_note", "multiline", None)]
    if coll == "lifts":
        from ..fitness import exercise_names
        return [("name", "f_exercise", "combo", exercise_names(store)),
                ("w", "f_lift_w", "number", None),
                ("r", "f_lift_r", "number", None),
                ("date", "f_date", "date", None),
                ("note", "f_note", "multiline", None)]
    if coll == "body":
        return [("date", "f_date", "date", None),
                ("weight", "f_weight_kg", "number?", None),
                ("fat", "f_bodyfat", "number?", None),
                ("neck", "f_neck", "number?", None),
                ("waist", "f_waist", "number?", None),
                ("hip", "f_hip", "number?", None),
                ("chest", "f_chest_cm", "number?", None),
                ("arm", "f_arm", "number?", None),
                ("thigh", "f_thigh", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "workouts":
        return [("date", "f_date", "date", None),
                ("kind", "f_kind", "combo", _with_used(WORKOUT_KINDS, store, "workouts", "kind")),
                ("focus", "f_focus", "combo", _with_used(WORKOUT_FOCUS, store, "workouts", "focus")),
                ("minutes", "f_minutes", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "projects":
        return [("name", "f_project_name", "text", None),
                ("category", "f_category", "cats", None),
                ("logo", "f_logo", "image", None),
                ("status", "f_status", "choice", [(s, t("status_" + s)) for s in PROJECT_STATUS]),
                ("start", "f_start_date", "date?", None),
                ("due", "f_due", "date?", None),
                ("progress", "f_progress_manual", "number?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "events":
        return [("title", "f_title", "text", None),
                ("date", "f_date", "date", None),
                ("time", "f_time", "time?", None),
                ("people", "f_people", "text", None),
                ("place", "f_place", "text", None),
                ("important", "f_important", "bool", None),
                ("note", "f_note", "multiline", None)]
    if coll == "birthdays":
        return [("name", "f_person", "text", None),
                ("date", "f_birthday", "date", None)]
    if coll == "transactions":
        return [("kind", "f_tx_kind", "choice", [("expense", t("expense")), ("income", t("income"))]),
                ("amount", "f_amount", "money", None),
                ("category", "f_category", "combo",
                 _with_used(EXPENSE_CATS + INCOME_CATS, store, "transactions", "category")),
                ("date", "f_date", "date", None),
                ("note", "f_note", "text", None)]
    if coll == "debts":
        return [("direction", "f_direction", "choice", [("owe", t("dir_owe")), ("owed", t("dir_owed"))]),
                ("person", "f_person", "text", None),
                ("amount", "f_amount", "money", None),
                ("due", "f_due", "date?", None),
                ("settled", "f_settled", "bool", None),
                ("note", "f_note", "text", None)]
    if coll == "investments":
        from ..markets import options
        from ..i18n import is_tr
        return [("name", "f_inv_name", "text", None),
                ("kind", "f_kind", "combo", _with_used(INVEST_KINDS, store, "investments", "kind")),
                ("asset", "f_asset", "combo", [""] + options(is_tr())),
                ("qty", "f_qty", "number?", None),
                ("invested", "f_invested", "money", None),
                ("value", "f_value", "money?", None),
                ("date", "f_date", "date", None),
                ("note", "f_note", "text", None)]
    if coll == "habits":
        out = [("name", "f_habit_name", "text", None),
               ("category", "f_category", "cats", None),
               ("kind", "f_habit_kind", "choice", [("build", t("habit_kind_build")), ("quit", t("habit_kind_quit"))]),
               ("goal", "f_goal_days", "number?", None),
               ("week_min", "f_week_min", "number?", None),
               ("gap", "f_gap", "number?", None)]
        if prefs.get("habits_in_schedule", False):
            out += [("weekdays", "f_habit_weekdays", "days", None),
                    ("time", "f_time", "time?", None)]
        return out + [("note", "f_note", "text", None)]
    if coll == "accounts":
        return [("name", "f_account_name", "combo", _with_used(["Nakit", "Banka hesabı"], store, "accounts", "name")),
                ("balance", "f_balance", "money", None),
                ("note", "f_note", "text", None)]
    if coll == "recurring":
        return [("kind", "f_tx_kind", "choice", [("expense", t("expense")), ("income", t("income"))]),
                ("name", "f_rec_name", "text", None),
                ("amount", "f_amount", "money", None),
                ("day", "f_day_of_month", "number?", None),
                ("category", "f_category", "combo",
                 _with_used(EXPENSE_CATS + INCOME_CATS, store, "recurring", "category")),
                ("active", "f_active", "bool", None),
                ("note", "f_note", "text", None)]
    if coll == "goals":
        parents = [("", "—")] + [(g["id"], g.get("title") or "—") for g in store.all("goals")
                                 if g.get("horizon") != "action"]
        return [("title", "f_goal_title", "text", None),
                ("area", "f_area", "areas", None),
                ("horizon", "f_horizon", "choice", [(h, t("hz_" + h)) for h in GOAL_HORIZONS]),
                ("parent", "f_parent", "choice", parents),
                ("due", "f_target_date", "date?", None),
                ("progress", "f_progress", "number?", None),
                ("links", "f_links", "links", None),
                ("image", "f_image", "image", None),
                ("done", "f_goal_done", "bool", None),
                ("note", "f_note", "multiline", None)]
    if coll == "cv":
        from ..pages.cv import ALL_SECTIONS, section_name
        return [("side", "f_cv_side", "choice", [("now", t("cv_now")), ("dream", t("cv_dream"))]),
                ("section", "f_cv_section", "choice", [(k, section_name(k)) for k in ALL_SECTIONS]),
                ("title", "f_cv_title", "text", None),
                ("org", "f_cv_org", "text", None),
                ("when", "f_cv_when", "text", None),
                ("detail", "f_cv_detail", "multiline", None),
                ("note", "f_note", "multiline", None)]
    if coll == "bucket":
        from ..pages.bucket import CATS, cat_name
        return [("title", "f_bk_title", "text", None),
                ("category", "f_category", "choice", [(k, cat_name(k)) for k in CATS]),
                ("place", "f_bk_place", "text", None),
                ("year", "f_bk_year", "number?", None),
                ("image", "f_image", "image", None),
                ("link", "f_link", "text", None),
                ("done", "f_bk_done", "bool", None),
                ("note", "f_note", "multiline", None)]
    if coll == "places":
        return [("name", "f_pl_name", "text", None),
                ("status", "f_pl_status", "choice", [("been", t("pl_been")), ("want", t("pl_want"))]),
                ("date", "f_pl_date", "date?", None),
                ("note", "f_note", "multiline", None)]
    if coll == "wishlist":
        return [("name", "f_wish_name", "text", None),
                ("price", "f_price", "money?", None),
                ("category", "f_category", "combo", _with_used(["Gadget", "Giyim", "Ev", "Kitap", "Elektronik"],
                                                              store, "wishlist", "category")),
                ("link", "f_link", "text", None),
                ("image", "f_wish_image", "image", None),
                ("bought", "f_bought", "bool", None),
                ("note", "f_note", "text", None)]
    if coll == "meals":
        return [("name", "f_meal_name", "combo", _with_used([], store, "meals", "name")),
                ("date", "f_date", "date", None),
                ("kcal", "f_kcal", "number?", None),
                ("protein", "f_protein", "number?", None),
                ("carbs", "f_carbs", "number?", None),
                ("fat", "f_fat", "number?", None)]
    raise KeyError(coll)


REQUIRED = {"tasks": "title", "routine": "title", "courses": "name", "exams": "course", "projects": "name",
            "events": "title", "birthdays": "name", "debts": "person", "investments": "name",
            "transactions": "amount", "workouts": "date", "habits": "name", "meals": "name",
            "accounts": "name", "recurring": "name", "goals": "title", "transcript": "name", "media": "title",
            "lifts": "name", "wishlist": "name", "cv": "title", "bucket": "title", "places": "name"}

GOAL_HORIZONS = ("life", "y10", "y3", "year", "term", "action")


def _with_used(base, store, coll, key):
    seen = list(base)
    for x in store.all(coll):
        v = (x.get(key) or "").strip()
        if v and v not in seen:
            seen.append(v)
    return seen


def defaults(coll):
    d = day_today().isoformat()
    return {
        "tasks": {"category": "personal", "priority": "normal"},
        "routine": {"category": "education", "days": [day_today().weekday()], "start": "09:00", "end": "10:00"},
        "exams": {"name": "Vize", "weight": 40},
        "workouts": {"date": d, "kind": "Gym"},
        "projects": {"status": "doing", "category": "work", "start": d},
        "media": {"type": "book", "status": "want"},
        "events": {"date": d},
        "transactions": {"kind": "expense", "date": d, "category": "Yemek"},
        "debts": {"direction": "owe"},
        "investments": {"date": d, "kind": "Hisse"},
        "habits": {"category": "personal", "goal": 7, "kind": "build"},
        "meals": {"date": d},
        "body": {"date": d},
        "lifts": {"date": d, "r": 1},
        "mood": {"date": d, "mood": 3},
        "sleep": {"date": d, "bed": prefs.get("sleep_bed", "23:30"), "wake": prefs.get("sleep_wake", "07:30")},
        "sessions": {"date": d, "kind": "study", "minutes": 25},
        "accounts": {"name": "Nakit"},
        "recurring": {"kind": "expense", "active": True, "category": "Faturalar"},
        "goals": {"area": "growth", "horizon": "year"},
        "bucket": {"category": "experience"},
        "places": {"status": "want"},
    }.get(coll, {})
