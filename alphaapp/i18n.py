"""Türkçe / İngilizce metinler ve tarih / para biçimleri. t("anahtar", **biçim) ile kullanılır."""
from datetime import date, datetime

from .config import day_today
from .config import prefs

S = {
    # genel
    "ok": ("Tamam", "OK"), "cancel": ("İptal", "Cancel"), "save": ("Kaydet", "Save"), "done": ("Bitti", "Done"),
    "delete": ("Sil", "Delete"), "edit": ("Düzenle", "Edit"), "undo": ("Geri al", "Undo"),
    "deleted": ("Silindi", "Deleted"), "all": ("Tümü", "All"), "other": ("Diğer", "Other"),
    "untitled": ("Başlıksız", "Untitled"), "today": ("Bugün", "Today"), "tomorrow": ("Yarın", "Tomorrow"),
    "yesterday": ("Dün", "Yesterday"), "now": ("Şimdi", "Now"), "all_day": ("Gün boyu", "All day"),
    "and_more": ("+{n} tane daha", "+{n} more"), "n_total": ("Toplam {n}", "{n} total"),
    "n_items": ("{n} kalem", "{n} items"), "days": ("gün", "days"), "weeks": ("hafta", "weeks"),
    "minutes": ("dakika", "minutes"), "n_min": ("{n} dk", "{n} min"), "n_times": ("{n} kez", "{n}×"),
    "n_people": ("{n} kişi", "{n} people"), "net": ("Net", "Net"),
    "err_required": ("\"{f}\" boş olamaz", "\"{f}\" is required"),
    "err_number": ("Sayı alanlarına yalnızca sayı yaz (ör. 1250,50)", "Number fields accept numbers only (e.g. 1250.50)"),
    # başlık çubuğu
    "preferences": ("Seçenekler", "Preferences"), "toggle_nav": ("Menü (Ctrl+B)", "Menu (Ctrl+B)"),
    "quick_add": ("Hızlı ekle", "Quick add"), "theme": ("Tema", "Theme"),
    "dark_mode": ("Karanlık tema", "Dark theme"), "light_mode": ("Aydınlık tema", "Light theme"),
    "qa_task": ("Görev", "Task"), "qa_routine": ("Haftalık programa ekle", "Add to weekly schedule"),
    "qa_exam": ("Sınav / ödev notu", "Exam / assignment"), "qa_workout": ("Antrenman", "Workout"),
    "qa_event": ("Sosyal plan", "Social plan"), "qa_tx": ("Gelir / gider", "Income / expense"),
    "qa_debt": ("Borç / alacak", "Debt / receivable"), "qa_note": ("Not", "Note"),
    # menü
    "nav_today": ("Bugün", "Today"), "nav_schedule": ("Haftalık program", "Weekly schedule"),
    "nav_education": ("Eğitim", "Education"), "nav_work": ("İş", "Work"), "nav_sport": ("Spor", "Sport"),
    "nav_social": ("Sosyal hayat", "Social life"), "nav_finance": ("Ekonomi", "Finance"),
    "nav_notes": ("Notlar", "Notes"),
    # kategoriler
    "cat_education": ("Eğitim", "Education"), "cat_work": ("İş", "Work"), "cat_sport": ("Spor", "Sport"),
    "cat_social": ("Sosyal", "Social"), "cat_finance": ("Ekonomi", "Finance"), "cat_personal": ("Kişisel", "Personal"),
    "prio_normal": ("Normal", "Normal"), "prio_high": ("Önemli", "Important"), "prio_low": ("Düşük", "Low"),
    "status_todo": ("Planlandı", "Planned"), "status_doing": ("Devam ediyor", "In progress"),
    "status_waiting": ("Beklemede", "On hold"), "status_done": ("Bitti", "Done"),
    "dir_owe": ("Borcum var", "I owe"), "dir_owed": ("Alacağım var", "Owed to me"),
    # ortak satır eylemleri
    "add_task": ("Görev ekle", "Add task"), "add_routine": ("Programa ekle", "Add to schedule"),
    "task_done": ("Tamamlandı", "Completed"), "mark_done": ("Tamamlandı işaretle", "Mark as done"),
    "move_today": ("Bugüne taşı", "Move to today"), "move_tomorrow": ("Yarına ertele", "Postpone to tomorrow"),
    "quick_task_ph": ("Bugün için görev yaz, Enter'a bas", "Type a task for today, press Enter"),
    "quick_task_ph2": ("Görev yaz, Enter'a bas", "Type a task, press Enter"),
    "undated": ("TARİHSİZ", "NO DATE"), "deadline": ("Deadline", "Deadline"),
    "overdue_n": ("{n} gün gecikti", "{n} days late"), "in_n_days": ("{n} gün", "{n} days"),
    # bugün
    "greet_morning": ("Günaydın", "Good morning"), "greet_day": ("İyi günler", "Good afternoon"),
    "greet_evening": ("İyi akşamlar", "Good evening"),
    "today_program": ("Bugünün programı", "Today's schedule"), "todo": ("Yapılacaklar", "To do"),
    "upcoming": ("Yaklaşanlar", "Coming up"), "week_summary": ("Özet", "Summary"),
    "pinned_notes": ("Sabitlenmiş notlar", "Pinned notes"),
    "no_program": ("Bugün için program yok. Haftalık programa ders, iş ya da spor saatlerini ekleyince her sabah "
                   "burada hazır olur.", "Nothing scheduled today. Add your classes, work or gym hours to the weekly "
                   "schedule and they'll be here every morning."),
    "no_todo": ("Bugün için yapılacak yok 🎉", "Nothing to do today 🎉"),
    "no_deadlines": ("Önümüzdeki {n} günde deadline yok", "No deadlines in the next {n} days"),
    "next_n_days": ("Önümüzdeki {n} gün", "Next {n} days"),
    "n_open": ("{n} açık", "{n} open"), "n_overdue": ("{n} gecikmiş", "{n} overdue"),
    "n_done_today": ("bugün {n} bitti", "{n} done today"),
    "sport_week": ("Bu hafta {n} gün spor · hedef {g}", "{n} workout days this week · goal {g}"),
    "month_income": ("Bu ay gelir", "Income this month"), "month_expense": ("Bu ay gider", "Spent this month"),
    "month_net": ("Bu ay net", "Net this month"),
    "total_owe": ("Borcum", "I owe"), "total_owed": ("Alacağım", "Owed to me"),
    "courses_status": ("Dersler", "Courses"), "courses_ok": ("Hepsi hedefte", "All on target"),
    "courses_below": ("{n} ders hedefin altında", "{n} courses below target"),
    "exam": ("Sınav", "Exam"), "exam_short": ("Sınav", "Exam"), "birthday": ("Doğum günü", "Birthday"),
    # program
    "prev_week": ("Önceki hafta", "Previous week"), "next_week": ("Sonraki hafta", "Next week"),
    "this_week": ("Bu hafta", "This week"),
    # eğitim
    "education_sub": ("Dersler, sınavlar ve not hedeflerin", "Courses, exams and grade goals"),
    "add_course": ("Ders ekle", "Add course"), "add_exam": ("Sınav / not ekle", "Add exam / grade"),
    "add_exam_for": ("Bu derse sınav / ödev ekle", "Add exam / assignment to this course"),
    "course_menu": ("Ders seçenekleri", "Course options"),
    "courses": ("Dersler", "Courses"), "overall_avg": ("Genel ortalama", "Overall average"),
    "below_target": ("Hedefin altında", "Below target"), "next_exam": ("Sıradaki sınav", "Next exam"),
    "upcoming_exams": ("Yaklaşan sınavlar", "Upcoming exams"), "edu_tasks": ("Ödevler & görevler", "Homework & tasks"),
    "no_courses": ("Henüz ders yok. \"Ders ekle\" ile başla, sonra her derse vize / final / ödev ekleyip hedef ve "
                   "aldığın notu gir.", "No courses yet. Start with \"Add course\", then add midterms / finals / "
                   "assignments with your target and actual grade."),
    "n_credits": ("{n} kredi", "{n} credits"), "target_letter": ("hedef {l}", "target {l}"),
    "avg_note": ("kredi ağırlıklı, girilen notlarla", "credit-weighted, from entered grades"),
    "no_scores": ("henüz not girilmedi", "no grades yet"),
    "courses_below_note": ("ders hedefin altında", "courses below target"),
    "all_on_track": ("hepsi yolunda", "all on track"), "no_upcoming_exam": ("Yaklaşan sınav yok", "No upcoming exams"),
    "no_tasks": ("Açık görev yok", "No open tasks"),
    "now_avg": ("Şu an {v}", "Now {v}"), "target_avg": ("hedef {v}", "target {v}"),
    "weight_done": ("%{d} / %{a} not girildi", "{d}% of {a}% graded"),
    "need_avg": ("hedef için kalanlardan ort. {v} almalısın", "you need {v} avg on the rest"),
    "need_impossible": ("hedef için kalanlardan {v} gerekiyor — hedefi gözden geçir",
                        "you'd need {v} on the rest — revisit the target"),
    "need_done": ("hedef garantide", "target secured"),
    "course_empty_hint": ("Sağ üstteki + ile vize, final, ödev ekle", "Use + to add midterm, final, homework"),
    "weight_pct": ("%{w}", "{w}%"), "target_score": ("hedef {v}", "target {v}"),
    "enter_score": ("Notu gir", "Enter grade"),
    "need_course": ("Önce bir ders ekle", "Add a course first"),
    # iş
    "work_sub": ("Projeler, işler ve deadline'lar", "Projects, tasks and deadlines"),
    "add_project": ("Proje ekle", "Add project"), "active_projects": ("Aktif proje", "Active projects"),
    "open_tasks": ("Açık iş", "Open tasks"), "due_this_week": ("Bu hafta teslim", "Due this week"),
    "done_this_week": ("Bu hafta biten", "Done this week"), "projects": ("Projeler", "Projects"),
    "work_tasks": ("İş görevleri", "Work tasks"), "today_work": ("Bugün iş", "Work today"),
    "no_projects": ("Proje yok", "No projects"), "no_work_today": ("Bugün iş programı yok", "No work hours today"),
    "mark_project_done": ("Bitti olarak işaretle", "Mark as done"),
    # spor
    "sport_sub": ("Haftalık hedefin ve antrenman günlüğün", "Your weekly goal and workout log"),
    "add_workout": ("Antrenman ekle", "Log workout"), "this_month": ("Bu ay", "This month"),
    "minutes_month": ("Bu ay süre", "Time this month"), "streak": ("Hedef serisi", "Goal streak"),
    "weekly_goal": ("Haftalık hedef", "Weekly goal"), "days_per_week": ("gün / hafta", "days / week"),
    "last_weeks": ("Son 8 hafta", "Last 8 weeks"), "workout_log": ("Antrenman günlüğü", "Workout log"),
    "what_trained": ("Ne çalıştım", "What I trained"), "last_30": ("Son 30 gün", "Last 30 days"),
    "sport_plan": ("Spor programı", "Training plan"), "workout": ("Antrenman", "Workout"),
    "goal_reached": ("Bu haftaki hedef tamam 💪", "Weekly goal reached 💪"),
    "goal_left": ("Hedefe {n} gün kaldı · haftanın bitmesine {d} gün var", "{n} more days to goal · {d} days left"),
    "no_workouts": ("Son 30 günde kayıt yok", "Nothing logged in the last 30 days"),
    "no_workouts_hint": ("Henüz antrenman yok. Spora gittiğin gün \"Antrenman ekle\" — ne çalıştığını da yaz.",
                         "No workouts yet. Log each session with \"Log workout\" and note what you trained."),
    "no_sport_plan": ("Antrenman günlerini programa ekle (ör. Pzt-Çar-Cum 18:00 Gym)",
                      "Add training days to your schedule (e.g. Mon-Wed-Fri 18:00 Gym)"),
    "repeat_today": ("Bugün tekrar et", "Repeat today"),
    # sosyal
    "social_sub": ("Planlar, buluşmalar ve doğum günleri", "Plans, meetups and birthdays"),
    "add_event": ("Plan ekle", "Add plan"), "add_birthday": ("Doğum günü ekle", "Add birthday"),
    "upcoming_plans": ("Yaklaşan planlar", "Upcoming plans"), "met_this_month": ("Bu ay buluşma", "Meetups this month"),
    "next_birthday": ("Sıradaki doğum günü", "Next birthday"), "birthdays": ("Doğum günleri", "Birthdays"),
    "social_tasks": ("Aranacaklar & yapılacaklar", "Calls & to-dos"), "past_events": ("Geçmiş", "Past"),
    "plans": ("plan", "plans"), "no_plans": ("Yaklaşan plan yok", "No upcoming plans"),
    "no_birthdays": ("Doğum günü eklenmedi", "No birthdays added"), "no_past": ("Henüz yok", "Nothing yet"),
    "turns": ("{n} yaşına giriyor", "turns {n}"),
    "quick_social_ph": ("Ör. Annemi ara — Enter", "e.g. Call mom — Enter"),
    # ekonomi
    "finance_sub": ("Gelir, gider, borç, alacak ve yatırımlar", "Income, expenses, debts and investments"),
    "add_expense": ("Gider ekle", "Add expense"), "add_income": ("Gelir ekle", "Add income"),
    "add_debt": ("Borç / alacak ekle", "Add debt / receivable"), "add_investment": ("Yatırım ekle", "Add investment"),
    "add_tx": ("Bu aya hareket ekle", "Add transaction to this month"),
    "income": ("Gelir", "Income"), "expense": ("Gider", "Expense"), "portfolio": ("Yatırımlar", "Investments"),
    "last_6_months": ("Son 6 ay", "Last 6 months"), "expense_by_cat": ("Nereye harcadım", "Where it went"),
    "tab_tx": ("Hareketler", "Transactions"), "tab_debts": ("Borç & alacak", "Debts & receivables"),
    "tab_inv": ("Yatırımlar", "Investments"), "prev_month": ("Önceki ay", "Previous month"),
    "next_month": ("Sonraki ay", "Next month"), "saved": ("biriktirdin", "saved"),
    "overspent": ("gelirden fazla harcadın", "spent more than earned"),
    "no_expense_month": ("Bu ay gider yok", "No expenses this month"),
    "no_tx": ("Bu ayda hareket yok", "No transactions this month"),
    "no_debts": ("Borç ya da alacak yok", "No debts or receivables"),
    "no_inv": ("Yatırım yok", "No investments"), "settled": ("Kapandı", "Settled"),
    "mark_settled": ("Ödendi / kapandı", "Mark as settled"), "mark_unsettled": ("Tekrar aç", "Reopen"),
    "duplicate_today": ("Bugün tekrar ekle", "Add again today"),
    "invested_amt": ("yatırılan {v}", "invested {v}"),
    "inv_sub": ("Yatırılan {i} · şu anki değer {v}", "Invested {i} · current value {v}"),
    "inv_hint": ("Güncel değeri arada bir elle güncelle", "Update the current value now and then"),
    "vs_last_month": ("geçen aya göre {p}", "{p} vs last month"),
    # notlar
    "new_note": ("Yeni not", "New note"), "search_notes": ("Notlarda ara", "Search notes"),
    "note_title_ph": ("Başlık", "Title"), "note_body_ph": ("Yazmaya başla…", "Start writing…"),
    "pin_note": ("Sabitle (Bugün sayfasında görünür)", "Pin (shows on Today)"),
    "no_note_selected": ("Soldan bir not seç ya da + ile yeni not aç", "Pick a note or create one with +"),
    "no_notes": ("Henüz not yok", "No notes yet"), "no_match": ("Eşleşen not yok", "No matching notes"),
    "edited_at": ("Son düzenleme: {d}", "Edited {d}"),
    # form başlıkları
    "new_tasks": ("Yeni görev", "New task"), "edit_tasks": ("Görevi düzenle", "Edit task"),
    "new_routine": ("Haftalık programa ekle", "Add to weekly schedule"),
    "edit_routine": ("Program saatini düzenle", "Edit schedule slot"),
    "new_courses": ("Yeni ders", "New course"), "edit_courses": ("Dersi düzenle", "Edit course"),
    "new_exams": ("Sınav / ödev notu", "Exam / assignment"), "edit_exams": ("Sınavı düzenle", "Edit exam"),
    "new_workouts": ("Antrenman ekle", "Log workout"), "edit_workouts": ("Antrenmanı düzenle", "Edit workout"),
    "new_projects": ("Yeni proje", "New project"), "edit_projects": ("Projeyi düzenle", "Edit project"),
    "new_events": ("Yeni plan", "New plan"), "edit_events": ("Planı düzenle", "Edit plan"),
    "new_birthdays": ("Doğum günü ekle", "Add birthday"), "edit_birthdays": ("Doğum gününü düzenle", "Edit birthday"),
    "new_transactions": ("Gelir / gider ekle", "Add income / expense"),
    "edit_transactions": ("Hareketi düzenle", "Edit transaction"),
    "new_debts": ("Borç / alacak ekle", "Add debt / receivable"), "edit_debts": ("Borç / alacağı düzenle", "Edit debt"),
    "new_investments": ("Yatırım ekle", "Add investment"), "edit_investments": ("Yatırımı düzenle", "Edit investment"),
    # form alanları
    "f_title": ("Başlık", "Title"), "f_category": ("Kategori", "Category"), "f_due": ("Son tarih", "Due date"),
    "f_time": ("Saat", "Time"), "f_priority": ("Önem", "Priority"), "f_note": ("Not", "Note"),
    "f_days": ("Günler", "Days"), "f_start": ("Başlangıç", "Start"), "f_end": ("Bitiş", "End"),
    "f_place": ("Yer", "Place"), "f_course_name": ("Ders adı", "Course name"), "f_code": ("Ders kodu", "Code"),
    "f_credits": ("Kredi / AKTS", "Credits"), "f_target_letter": ("Hedef harf notu", "Target letter grade"),
    "f_course": ("Ders", "Course"), "f_exam_name": ("Ne", "What"), "f_date": ("Tarih", "Date"),
    "f_weight": ("Etkisi (%)", "Weight (%)"), "f_target_score": ("Hedeflediğim not", "Target score"),
    "f_score": ("Aldığım not", "Actual score"), "f_kind": ("Tür", "Type"), "f_focus": ("Ne çalıştım", "Focus"),
    "f_minutes": ("Süre (dk)", "Duration (min)"), "f_project_name": ("Proje", "Project"),
    "f_status": ("Durum", "Status"), "f_progress": ("İlerleme (%)", "Progress (%)"),
    "f_people": ("Kimlerle", "With"), "f_person": ("Kişi", "Person"), "f_birthday": ("Doğum tarihi", "Birth date"),
    "f_tx_kind": ("Tür", "Type"), "f_amount": ("Tutar", "Amount"), "f_direction": ("Yön", "Direction"),
    "f_settled": ("Kapandı / ödendi", "Settled"), "f_inv_name": ("Yatırım", "Investment"),
    "f_invested": ("Yatırdığım", "Invested"), "f_value": ("Şu anki değeri", "Current value"),
    # masaüstü widget'ı
    "desk_tip": ("Masaüstüne sabitle (widget)", "Pin to desktop (widget)"),
    "desk_tip_on": ("Masaüstü widget'ını kaldır", "Remove desktop widget"),
    "desk_open": ("alpha'yı aç", "Open alpha"), "desk_menu": ("Widget seçenekleri", "Widget options"),
    "desk_mode_bottom": ("Masaüstünde (pencerelerin arkasında)", "On desktop (behind windows)"),
    "desk_mode_top": ("Her zaman üstte", "Always on top"),
    "desk_opacity": ("Saydamlık", "Opacity"), "desk_sections": ("Bölümler", "Sections"),
    "desk_close": ("Widget'ı kaldır", "Remove widget"),
    "desk_sec_now": ("Şimdi / sıradaki", "Now / next"), "desk_sec_program": ("Bugünün programı", "Today's schedule"),
    "desk_sec_todo": ("Yapılacaklar", "To do"), "desk_sec_upcoming": ("Yaklaşanlar (7 gün)", "Coming up (7 days)"),
    "desk_sec_sport": ("Spor hedefi", "Sport goal"),
    "desk_now": ("Şimdi: {x} · {e}'e kadar", "Now: {x} · until {e}"),
    "desk_next": ("Sıradaki: {x} · {s}", "Next: {x} · {s}"),
    "desk_free": ("Bugün başka program yok", "Nothing else scheduled today"),
    "desk_no_program": ("Bugün için program yok", "Nothing scheduled today"),
    "desk_sport": ("Spor bu hafta {n}/{g} gün", "Sport this week {n}/{g} days"),
    "desk_section": ("Masaüstü widget'ı", "Desktop widget"),
    "desk_show": ("Widget'ı göster", "Show widget"),
    "desk_show_sub": ("Bugünün programı, yapılacaklar ve yaklaşanlar masaüstünde küçük bir kartta. Sürükleyerek taşı, "
                      "sağ tıkla ayarla.", "Today's schedule, to-dos and deadlines in a small card on your desktop. "
                      "Drag to move, right-click for options."),
    "desk_mode": ("Konum", "Placement"),
    "desk_autostart_note": ("Widget açıksa Windows ile başlarken yalnızca widget gelir, ana pencere açılmaz.",
                            "When starting with Windows and the widget is on, only the widget opens."),
    # seçenekler
    "appearance": ("Görünüm", "Appearance"), "language": ("Dil", "Language"),
    "language_sub": ("Yeniden başlatınca uygulanır", "Applied after restart"),
    "personal": ("Kişisel", "Personal"), "your_name": ("Adın", "Your name"),
    "your_name_sub": ("Selamlamada görünür: \"Günaydın, …\"", "Shown in the greeting"),
    "currency": ("Para birimi", "Currency"),
    "today_page": ("Bugün sayfası", "Today page"),
    "schedule_section": ("Program ve ekleme", "Schedule and adding"),
    "pref_show_place": ("Konum ekle", "Add a place"),
    "pref_show_place_sub": ("Kapalıyken ekleme pencerelerinde \"Yer\" alanı çıkmaz, programda konum gösterilmez",
                            "When off, forms hide the \"Place\" field and the schedule hides places"),
    "pref_habits_sched": ("Alışkanlıklar programda", "Habits in the schedule"),
    "pref_habits_sched_sub": ("Alışkanlıklar haftalık programda kutu olarak görünür; tıklayınca o gün işaretlenir",
                              "Habits show up as boxes in the weekly schedule; click to tick that day"),
    "f_important": ("Önemli", "Important"),
    "dm_task": ("Görev ekle", "Add task"), "dm_important": ("Önemli görev ekle", "Add important task"),
    "dm_once": ("Bu güne özel ders / saat ekle", "Add a one-off class / slot"),
    "dm_weekly": ("Her {d} tekrar eden ders / saat ekle", "Add a weekly class / slot on {d}"),
    "dm_event": ("Sosyal plan ekle", "Add social plan"), "dm_exam": ("Sınav / ödev ekle", "Add exam / assignment"),
    "rem_title": ("Hatırlatma", "Reminder"), "rem_now": ("şimdi", "now"),
    "rem_in": ("{n} dk sonra", "in {n} min"), "rem_ok": ("Tamam", "OK"),
    "rem_snooze": ("{n} dk ertele", "Snooze {n} min"),
    "rem_test_title": ("Örnek hatırlatma", "Sample reminder"),
    "rem_test_sub": ("Sesler ve kutu böyle görünecek", "This is how it will look and sound"),
    "rem_section": ("Hatırlatıcılar", "Reminders"),
    "rem_on": ("Hatırlat", "Remind me"),
    "rem_on_sub": ("Saatli görev, ders ve planlardan önce ses çalar, sağ altta bir kutu açılır. alpha (ya da masaüstü "
                   "widget'ı) açıkken çalışır.",
                   "Plays a sound and shows a box before timed tasks, classes and plans while alpha (or the widget) runs."),
    "rem_lead": ("Kaç dakika önce", "How many minutes before"),
    "rem_sound": ("Ses", "Sound"), "rem_volume": ("Ses düzeyi", "Volume"),
    "snd_chime": ("Zil", "Chime"), "snd_soft": ("Yumuşak", "Soft"), "snd_alarm": ("Alarm", "Alarm"),
    "snd_system": ("Windows bildirim sesi", "Windows notification"), "snd_none": ("Sessiz", "Silent"),
    "rem_try": ("Dene", "Try"),
    "rem_important": ("Önemlilerde alarm sesi", "Alarm sound for important items"),
    "rem_routine": ("Dersler ve program saatleri de", "Classes and schedule slots too"),
    "day_end": ("Gün bitişi", "Day ends at"),
    "day_end_sub": ("Bu saate kadar hâlâ \"bugün\" sayılır: gece 02:00'de bitirdiğin iş bugünün işi olur, yarına kaymaz",
                    "Until this time it still counts as \"today\": a task finished at 2 AM stays today's"),
    "day_end_midnight": ("Gece yarısı (00:00)", "Midnight (00:00)"),
    "new_accounts": ("Nakit / hesap ekle", "Add cash / account"), "edit_accounts": ("Hesabı düzenle", "Edit account"),
    "new_recurring": ("Sabit gelir / gider ekle", "Add fixed income / expense"),
    "edit_recurring": ("Sabit gelir / gideri düzenle", "Edit fixed income / expense"),
    "f_account_name": ("Ad", "Name"), "f_balance": ("Bakiye", "Balance"), "f_rec_name": ("Ad", "Name"),
    "f_day_of_month": ("Ayın kaçında", "Day of month"), "f_active": ("Etkin", "Active"),
    "tab_fixed": ("Sabit gelir / gider", "Fixed income / expenses"), "tab_cash": ("Nakit", "Cash"),
    "no_fixed": ("Henüz sabit gelir / gider yok", "No fixed income / expenses yet"),
    "no_cash": ("Nakit ya da hesap bakiyesi girilmedi", "No cash or account balance yet"),
    "fixed_sub": ("Aylık gelir {i} · gider {e} · kalan {n}", "Monthly income {i} · expenses {e} · left {n}"),
    "every_month": ("her ayın {d}'i", "every month on day {d}"),
    "every_month_nd": ("her ay (gün belirtilmedi)", "every month (no day set)"),
    "goal_title": ("Hedef: borçsuz gir · {d}", "Goal: debt-free by {d}"),
    "goal_cash": ("Elindeki nakit", "Cash in hand"),
    "goal_income": ("Gelecek gelir ({n})", "Income coming ({n})"),
    "goal_fixed": ("Sabit giderler ({n})", "Fixed expenses ({n})"),
    "goal_fixed_none": ("Sabit giderler (henüz girilmedi)", "Fixed expenses (none entered)"),
    "goal_owed": ("Geri gelecek para (alacaklar)", "Money coming back (receivables)"),
    "goal_debt": ("Ödenecek borçlar", "Debts to pay"),
    "goal_result": ("Tahmini durum · {d}", "Estimated on {d}"),
    "goal_ok": ("Bu gidişle hedefe ulaşılıyor", "On track"),
    "goal_short": ("Hedefe {v} eksik", "{v} short of the goal"),
    "goal_note": ("Yalnızca girdiğin rakamlarla hesaplanır; değişken harcamalar dahil değil.",
                  "Calculated only from what you entered; day-to-day spending is not included."),
    "sport_break": ("Ara ver", "Take a break"), "sport_break_edit": ("Arayı düzenle", "Edit break"),
    "sport_break_short": ("Ara", "Break"),
    "sport_break_info": ("Bu tarihler arasında haftalık hedef ara günleri kadar düşer; tamamen ara verilen hafta "
                         "seriyi bozmaz.",
                         "Between these dates the weekly goal shrinks by the break days; a full break week doesn't "
                         "break your streak."),
    "sport_break_note": ("Neden? (sakatlık, sınav haftası, tatil…)", "Why? (injury, exams, holiday…)"),
    "sport_break_end": ("Arayı bitir", "End break"),
    "sport_break_until": ("Ara veriyorsun · bitiş {d}", "On a break until {d}"),
    "sport_break_from": ("Planlı ara: {a} – {z}", "Planned break: {a} – {z}"),
    "sport_goal_scaled": ("ara nedeniyle bu hafta hedef {g} gün", "goal is {g} days this week due to the break"),
    "n_days_short": ("{n} gün", "{n} days"),
    "study_section": ("Ders çalışma", "Study"),
    "moved_to": ("{d} gününe taşındı", "Moved to {d}"),
    "move_every_week": ("Her hafta {d} gününe taşı", "Move to {d} every week"),
    "move_once": ("Yalnızca bu hafta ({a} → {b})", "Only this week ({a} → {b})"),
    "f_from": ("İlk hafta", "Starts"), "f_until": ("Son gün", "Ends"),
    "f_habit_weekdays": ("Programdaki günler", "Days in schedule"),
    "habit": ("Alışkanlık", "Habit"), "qa_habit": ("Alışkanlık", "Habit"),
    "deadline_days": ("Yaklaşanlar kaç gün ileriyi göstersin", "How far ahead \"Coming up\" looks"),
    "show_sport": ("Spor özetini göster", "Show sport summary"),
    "show_finance": ("Para özetini göster", "Show money summary"),
    "behavior": ("Davranış", "Behavior"), "start_page": ("Açılış sayfası", "Start page"),
    "start_last": ("En son açık olan", "Last opened"),
    "autostart": ("Windows ile başlat", "Start with Windows"),
    "autostart_sub": ("Bilgisayarı açınca alpha Bugün sayfasıyla açılsın — sabah planın hazır olsun",
                      "Open alpha on Today when you sign in — your plan is ready in the morning"),
    "data": ("Veriler", "Data"),
    "data_sub": ("Her şey bu bilgisayarda (Belgeler\\alpha): kayıtlar tek dosyada, hedef görselleri images klasöründe. "
                 "Her gün otomatik yedek alınır (son 14 gün).",
                 "Everything stays on this PC (Documents\\alpha): records in one file, goal images in the images "
                 "folder. A daily backup is kept (last 14 days)."),
    # görev → sınav / teslim
    "f_as_exam": ("Sınav / teslim", "Exam / due"),
    "f_as_exam_hint": ("Vize, quiz, ödev, rapor teslimi… → Sınavlar'a gider", "Midterm, quiz, homework, report… → goes to Exams"),
    "saved_as_exam": ("Sınavlara eklendi", "Added to exams"),
    "move_to_exams": ("Sınavlara taşı", "Move to exams"),
    "moved_to_exams": ("Sınavlara taşındı", "Moved to exams"),
    # seçenek kategorileri
    "pcat_general": ("Genel", "General"),
    "pcat_today": ("Bugün ve program", "Today and schedule"),
    "pcat_sport_food": ("Spor ve beslenme", "Sport and nutrition"),
    "pcat_phone": ("Telefonda aç", "Open on phone"),
    # telefonda aç (web.py)
    "web_sub": ("Bilgisayarın yanında değilken bugünün programını, yapılacakları ve takvimi telefonundan gör. "
                "Sitene yalnızca bunlar gider (önümüzdeki 30 gün); hedefler, vision board, notlar ve ekonomi "
                "kayıtları gitmez. Sayfa yalnızca senin bağlantınla açılır.",
                "See today's schedule, to-dos and calendar on your phone when your PC isn't with you. Only these "
                "are sent to your site (next 30 days); goals, vision board, notes and finance records are not. "
                "Only your link can open the page."),
    "web_on": ("Telefondan erişim", "Phone access"),
    "web_on_sub": ("Açıkken alpha, gündemindeki her değişikliği birkaç saniye içinde sitene gönderir.",
                   "When on, alpha sends every change in your agenda to your site within seconds."),
    "web_link": ("Telefonuna kur", "Set up your phone"),
    "web_link_sub": ("Bağlantıyı kopyala, kendine gönder ve telefonunda bir kez aç. Sonra yalnızca {u} yazman "
                     "yeterli; istersen tarayıcıdan \u201cAna ekrana ekle\u201d de.",
                     "Copy the link, send it to yourself and open it once on your phone. After that just type {u}; "
                     "you can also \u201cAdd to home screen\u201d."),
    "web_copy": ("Bağlantıyı kopyala", "Copy link"),
    "web_status": ("Durum", "Status"),
    "web_send": ("Şimdi güncelle", "Update now"),
    "web_setup": ("Site kurulumu", "Site setup"),
    "web_url": ("Site adresi", "Site address"),
    "web_url_sub": ("alpha'nın gönderdiği sunucu dosyası (api/alpha.php).", "The server file alpha sends to (api/alpha.php)."),
    "web_key": ("Erişim anahtarı", "Access key"),
    "web_key_sub": ("Sitende yalnızca anahtarın şifreli özeti durur (api/_alpha_key.php). Bağlantın başkasının eline "
                    "geçtiyse anahtarı değiştir, dosyayı yeniden yükle ve telefonunu yeniden kur.",
                    "Your site only keeps a hash of the key (api/_alpha_key.php). If your link leaked, change the key, "
                    "upload the file again and set up your phone again."),
    "web_keyfile": ("Anahtar dosyasını kaydet…", "Save key file…"),
    "web_keyfile_pick": ("Sitenin klasörünü seç", "Choose the site folder"),
    "web_keyfile_saved": ("Kaydedildi: {p} — siteye yükle", "Saved: {p} — upload it to the site"),
    "web_new_key": ("Anahtarı değiştir", "Change key"),
    "web_new_key_done": ("Anahtar değişti: api/_alpha_key.php'yi siteye yükle ve telefonunu yeniden kur",
                         "Key changed: upload api/_alpha_key.php and set up your phone again"),
    "web_copied": ("Bağlantı kopyalandı — telefonunda bir kez aç", "Link copied — open it once on your phone"),
    "web_off": ("Kapalı — telefondan erişim açık değil", "Off — phone access is not on"),
    "web_need_url": ("Site adresini yaz (https://…/api/alpha.php)", "Enter the site address (https://…/api/alpha.php)"),
    "web_err": ("Gönderilemedi: {e}", "Couldn't send: {e}"),
    "web_last": ("Güncel · son gönderim {d}", "Up to date · last sent {d}"),
    "web_never": ("Henüz gönderilmedi", "Not sent yet"),
    "open_folder": ("Klasörü aç", "Open folder"), "export_json": ("Dışa aktar (JSON)", "Export (JSON)"),
    "exported": ("Dışa aktarıldı: {p}", "Exported: {p}"),
    # çalışma kareleri / alışkanlıklar / beslenme
    "study_title": ("Çalışma günleri", "Study days"),
    "study_info": ("bu hafta {w} gün · seri {s} · toplam {n}", "{w} days this week · streak {s} · {n} total"),
    "study_today": ("Bugün çalıştım", "Studied today"), "study_done_today": ("Bugün çalıştım ✓", "Studied today ✓"),
    "nav_habits": ("Alışkanlıklar", "Habits"),
    "habits_sub": ("Her gün küçük adımlar — kareleri doldur, seriyi bozma", "Small steps every day — fill the squares, keep the streak"),
    "add_habit": ("Alışkanlık ekle", "Add habit"),
    "new_habits": ("Alışkanlık ekle", "Add habit"), "edit_habits": ("Alışkanlığı düzenle", "Edit habit"),
    "f_habit_name": ("Alışkanlık", "Habit"), "f_goal_days": ("Haftalık hedef (gün)", "Weekly goal (days)"),
    "habits_today": ("Bugün", "Today"),
    "habit_done_today": ("Bugün ✓", "Today ✓"), "habit_menu": ("Alışkanlık menüsü", "Habit menu"),
    "habits_today_sub": ("{d}/{n} tamam", "{d}/{n} done"),
    "habit_stats": ("Seri {s} gün · en uzun {b} · bu hafta {w}/{g} · toplam {n}",
                    "Streak {s} days · best {b} · this week {w}/{g} · {n} total"),
    "habit_streak": ("{n} günlük seri", "{n}-day streak"),
    "habit_week": ("bu hafta {w}/{g}", "this week {w}/{g}"),
    "no_habits": ("Henüz alışkanlık yok. Aşağıdan birini seç ya da kendin ekle.",
                  "No habits yet. Pick one below or add your own."),
    "habit_suggest": ("Öneriler", "Suggestions"),
    "habit_suggestions": ("Su iç (2 L)|Kitap oku|Erken kalk|Ders tekrarı|Yürüyüş|Ekransız akşam",
                          "Drink water (2 L)|Read|Wake up early|Review lessons|Walk|No screens at night"),
    "habit_tiles_active": ("Aktif alışkanlık", "Active habits"),
    "habit_tiles_today": ("Bugün", "Today"),
    "habit_tiles_best": ("En uzun seri", "Longest streak"),
    "habit_tiles_rate": ("Son 30 gün", "Last 30 days"),
    "habit_rate_note": ("işaretlenen karelerin oranı", "share of squares filled"),
    "nutrition": ("Beslenme · bugün", "Nutrition · today"),
    "nutrition_sub": ("7 gün ort. {k} kcal · {p} g protein", "7-day avg {k} kcal · {p} g protein"),
    "add_meal": ("Öğün ekle", "Add meal"), "todays_meals": ("Bugünkü öğünler", "Today's meals"),
    "new_meals": ("Öğün ekle", "Add meal"), "edit_meals": ("Öğünü düzenle", "Edit meal"),
    "f_meal_name": ("Ne yedin?", "What did you eat?"), "f_kcal": ("Kalori (kcal)", "Calories (kcal)"),
    "f_protein": ("Protein (g)", "Protein (g)"), "f_carbs": ("Karbonhidrat (g)", "Carbs (g)"), "f_fat": ("Yağ (g)", "Fat (g)"),
    "macro_kcal": ("Kalori", "Calories"), "macro_protein": ("Protein", "Protein"),
    "macro_carbs": ("Karbonhidrat", "Carbs"), "macro_fat": ("Yağ", "Fat"),
    "macro_val": ("{v} / {g} {u}", "{v} / {g} {u}"),
    "macro_left": ("{v} {u} kaldı", "{v} {u} left"), "macro_over": ("{v} {u} fazla", "{v} {u} over"),
    "meal_macros": ("P {p} · K {c} · Y {f} g", "P {p} · C {c} · F {f} g"),
    "no_meals": ("Bugün henüz öğün yok. + ile ya da aşağıdaki sık yediklerinden ekle.",
                 "No meals yet today. Add with + or from your usual meals below."),
    "frequent_meals": ("Sık yediklerin (tıkla, bugüne ekle)", "Your usual meals (click to add today)"),
    "meal_added": ("{x} eklendi", "{x} added"),
    "nutrition_goals": ("Beslenme hedefleri", "Nutrition goals"),
    "goal_kcal": ("Günlük kalori", "Daily calories"), "goal_protein": ("Günlük protein (g)", "Daily protein (g)"),
    "goal_carbs": ("Günlük karbonhidrat (g)", "Daily carbs (g)"), "goal_fat": ("Günlük yağ (g)", "Daily fat (g)"),
    # takvim
    "cal_prev": ("Önceki ay", "Previous month"), "cal_next": ("Sonraki ay", "Next month"),
    "cal_hint": ("{n} kayıt · ayrıntı için bir güne tıkla", "{n} items · click a day for details"),
    "cal_hint_empty": ("Bu ay boş", "Nothing this month"),
    "cal_tip": ("Tıkla: o günün ayrıntısı · Çift tıkla: o güne görev ekle",
                "Click: that day's details · Double-click: add a task on that day"),
    "cal_empty": ("Bu gün boş", "Nothing on this day"),
    # sabah planı
    "plan_day": ("Günü planla", "Plan the day"),
    "plan_skip": ("Şimdi değil", "Not now"),
    "plan_sub": ("Sabah planı  ·  {d}", "Morning plan  ·  {d}"),
    "plan_step_carry": ("Dünden kalanlar", "Left over"), "plan_step_today": ("Bugün", "Today"),
    "plan_step_focus": ("Odak", "Focus"), "plan_step_ready": ("Hazır", "Ready"),
    "plan_lead_carry": ("Geciken her iş için karar ver: bugüne mi, yarına mı, yoksa bırakıyor musun? "
                        "Seçimler İleri'ye basınca uygulanır.",
                        "Decide on each overdue task: today, tomorrow, or let it go? Choices apply when you press Next."),
    "plan_lead_today": ("Bugün seni neler bekliyor? Eksik olan bir şey varsa şimdi ekle.",
                        "What's waiting for you today? Add anything that's missing now."),
    "plan_lead_focus": ("Gün nasıl geçerse geçsin bitmesini istediğin en fazla 3 işi seç, günün hedefini tek cümleyle yaz.",
                        "Pick up to 3 tasks that must get done no matter what, and sum up the day in one sentence."),
    "plan_lead_ready": ("Planın hazır. İyi bir gün olsun.", "Your plan is ready. Have a good day."),
    "plan_carry_title": ("Dünden kalanlar", "Left over from before"),
    "plan_carry_none": ("Geciken iş yok — temiz bir başlangıç.", "Nothing overdue — a clean start."),
    "plan_done_yesterday": ("dün {n} iş bitti", "{n} done yesterday"),
    "plan_key_tip": ("Kısayol: {k}", "Shortcut: {k}"),
    "plan_keys_hint": ("Klavye: ↑ ↓ iş seç · 1 bugün · 2 yarın · 3 tarihsiz · 4 bitti · 5 / Del sil · Enter ileri",
                       "Keyboard: ↑ ↓ pick · 1 today · 2 tomorrow · 3 someday · 4 done · 5 / Del delete · Enter next"),
    "plan_yesterday": ("Dün nasıl geçti", "How yesterday went"),
    "plan_y_tasks": ("Biten işler", "Tasks done"), "plan_y_habits": ("Alışkanlıklar", "Habits"),
    "plan_y_streak": ("Süren en uzun seri", "Longest running streak"), "plan_y_sport": ("Spor", "Sport"),
    "plan_y_tasks_note": ("{n} iş kaldı", "{n} left"), "plan_y_all_done": ("hepsi bitti", "all done"),
    "plan_y_rest": ("dinlenme günü", "rest day"),
    "plan_flow": ("Günün akışı", "Your day"),
    "plan_flow_sub": ("Boş bir aralığa tıkla: bir işi o saate yerleştir", "Click a free slot to put a task there"),
    "plan_flow_sub_n": ("Bugün {d} boş zamanın var · boş bir aralığa tıkla, bir işi oraya yerleştir",
                        "{d} free today · click a free slot to put a task there"),
    "plan_flow_full": ("Bugün dolu dolu — boş aralık yok", "Packed day — no free slots"),
    "plan_gap_new": ("Yeni görev…", "New task…"),
    "tl_free": ("boş {d}", "free {d}"), "tl_free_tip": ("tıkla: buraya bir iş koy", "click to put a task here"),
    "dur_hm": ("{h} sa {m} dk", "{h} h {m} min"), "dur_h": ("{h} sa", "{h} h"), "dur_m": ("{m} dk", "{m} min"),
    "n_days": ("{n} gün", "{n} days"),
    "plan_ch_today": ("Bugün", "Today"), "plan_ch_tomorrow": ("Yarın", "Tomorrow"),
    "plan_ch_someday": ("Tarihsiz", "Someday"), "plan_ch_done": ("Bitti", "Done"), "plan_ch_delete": ("Sil", "Delete"),
    "plan_all_today": ("Hepsi bugün", "All today"), "plan_all_tomorrow": ("Hepsi yarın", "All tomorrow"),
    "plan_all_someday": ("Hepsi tarihsiz", "All someday"),
    "plan_carried": ("{n} iş düzenlendi", "{n} tasks sorted"),
    "plan_today_tasks": ("Bugünün işleri", "Today's tasks"),
    "plan_no_today_tasks": ("Bugüne yazılmış iş yok", "No tasks for today"),
    "plan_soon": ("Yaklaşanlar", "Coming up"),
    "plan_focus_title": ("Odak işleri", "Focus tasks"),
    "plan_focus_sub": ("{n}/{m} seçildi · seçmek için tıkla", "{n}/{m} picked · click to pick"),
    "plan_focus_none": ("Açık iş yok. Bir önceki adımda ekleyebilirsin.",
                        "No open tasks. You can add some in the previous step."),
    "plan_focus_max": ("En fazla {n} odak iş seçebilirsin", "You can pick at most {n} focus tasks"),
    "plan_focus_empty": ("Odak seçilmedi", "No focus picked"),
    "plan_intention": ("Günün hedefi", "Today's intention"),
    "plan_intention_sub": ("Akşam baktığında “bugün iyi geçti” demeni ne sağlar?",
                           "What would make you say “today went well” tonight?"),
    "plan_intention_ph": ("ör. Sunumu bitir, spora git", "e.g. Finish the deck, hit the gym"),
    "plan_ready_title": ("Bugünün planı", "Today's plan"),
    "plan_first": ("ilki {s} {x}", "first {s} {x}"),
    "plan_ready_hint": ("Planı gün içinde Bugün sayfasından veya widget menüsünden yeniden açabilirsin.",
                        "Reopen the plan any time from the Today page or the widget menu."),
    "plan_back": ("Geri", "Back"), "plan_next": ("İleri", "Next"), "plan_start_day": ("Güne başla", "Start the day"),
    "plan_done_toast": ("Plan hazır — iyi günler!", "Plan ready — have a great day!"),
    "plan_banner_title": ("Günü planla", "Plan your day"),
    "plan_banner_sub": ("2 dakika: dünden kalanlar, bugünün programı, odak ve günün hedefi.",
                        "2 minutes: leftovers, today's schedule, focus and an intention."),
    "plan_banner_go": ("Planla", "Plan"), "plan_banner_not_today": ("Bugün değil", "Not today"),
    "focus": ("Odak", "Focus"),
    "pref_morning_plan": ("Sabah planlama ekranı", "Morning planning screen"),
    "pref_morning_plan_sub": ("Günün ilk açılışında (öğleden önce) plan ekranı gelsin",
                              "Show the plan screen on the first open of the day (before noon)"),
    "shortcuts": ("Kısayollar", "Shortcuts"),
    "about": ("Hakkında", "About"),
    "about_text": ('alpha {v}  ·  Geliştirici: {a}  ·  GPL-3.0  ·  <a href="{u}" style="color:#3ea6ff">GitHub</a>',
                   'alpha {v}  ·  Developer: {a}  ·  GPL-3.0  ·  <a href="{u}" style="color:#3ea6ff">GitHub</a>'),
    "shortcuts_text": ("Ctrl+N  hızlı ekle   ·   Ctrl+1…9  sayfalar   ·   Ctrl+B  menü   ·   F11  tam ekran   ·   "
                       "Ctrl+,  seçenekler",
                       "Ctrl+N  quick add   ·   Ctrl+1…9  pages   ·   Ctrl+B  menu   ·   F11  full screen   ·   "
                       "Ctrl+,  preferences"),

    # --- hayat hedefleri
    "nav_goals": ("Hedefler", "Goals"),
    "goals_sub": ("Büyük resim: hayat hedefin, sütunları ve bugün attığın adımlar",
                  "The big picture: your life goal, its pillars and the steps you take today"),
    "add_goal": ("Hedef ekle", "Add goal"), "new_goals": ("Hedef ekle", "Add goal"),
    "edit_goals": ("Hedefi düzenle", "Edit goal"),
    "f_goal_title": ("Hedef", "Goal"), "f_area": ("Alan", "Area"), "f_horizon": ("Zaman ufku", "Horizon"),
    "f_parent": ("Üst hedef", "Parent goal"), "f_target_date": ("Hedef tarihi", "Target date"),
    "f_links": ("Bağlı kayıtlar", "Linked items"), "f_image": ("Görsel", "Image"),
    "f_goal_done": ("Ulaşıldı", "Achieved"),
    "area_education": ("Eğitim", "Education"), "area_career": ("Kariyer", "Career"),
    "area_venture": ("İş", "Venture"), "area_body": ("Beden", "Body"), "area_mind": ("Zihin", "Mind"),
    "area_finance": ("Ekonomi", "Finance"), "area_growth": ("Kişisel gelişim", "Personal growth"),
    "hz_life": ("Hayat hedefi", "Life goal"), "hz_y10": ("10 yıl", "10 years"), "hz_y3": ("3 yıl", "3 years"),
    "hz_year": ("Bu yıl", "This year"), "hz_term": ("Bu dönem", "This term"), "hz_action": ("Eylem", "Action"),
    "links_none": ("Bağlantı yok — seç", "None — choose"),
    "links_empty": ("Önce alışkanlık, ders ya da proje ekle", "Add a habit, course or project first"),
    "pick_image": ("Görsel seç…", "Choose image…"), "change_image": ("Görseli değiştir…", "Change image…"),
    "clear_image": ("Kaldır", "Remove"),
    "gv_board": ("Vision board", "Vision board"), "gv_wheel": ("Denge ve yol haritası", "Balance and roadmap"),
    "bal_title": ("Denge", "Balance"),
    "bal_sub": ("Son 30 gün · puanları alpha senin verilerinden hesaplar · çizgi: son 6 ay",
                "Last 30 days · scored from your alpha data · line: last 6 months"),
    "bal_no_data": ("Veri yok", "No data"),
    "bal_no_data_hint": ("Bu alana bir hedef ekle ya da alışkanlık bağla", "Add a goal or link a habit to this area"),
    "bal_avg": ("Ortalama", "Average"),
    "bal_best": ("En güçlü: {a} {v}", "Strongest: {a} {v}"), "bal_worst": ("En zayıf: {a} {v}", "Weakest: {a} {v}"),
    "bal_add_weak": ("+ {a} için hedef ekle", "+ Add a goal for {a}"),
    "bal_study": ("Ders çalışma: haftada {n} gün", "Study: {n} days a week"),
    "bal_grades": ("Notlar hedefin %{p}'i", "Grades at {p}% of target"),
    "bal_work_tasks": ("Biten iş görevi: {n}", "Work tasks done: {n}"),
    "bal_sport": ("Spor: haftada {n} gün (hedef {g})", "Sport: {n} days a week (goal {g})"),
    "bal_protein": ("Protein hedefi: {n}/{m} gün", "Protein goal: {n}/{m} days"),
    "bal_saving": ("Birikim oranı: %{p}", "Savings rate: {p}%"), "bal_no_income": ("Bu dönem gelir yok", "No income"),
    "bal_debt": ("Açık borç: {v}", "Open debt: {v}"), "bal_no_debt": ("Açık borç yok", "No open debt"),
    "bal_habits": ("Alışkanlıklar: %{p} dolu", "Habits: {p}% filled"),
    "bal_plans": ("Günü planladın: {n}/{m} gün", "Planned the day: {n}/{m} days"),
    "bal_goal_days": ("Hedeflere emek: 30 günde {n} gün", "Effort on goals: {n} of 30 days"),
    "pin_add": ("Hedef ekle", "Add goal"),
    "pin_add_sub": ("ya da bir görseli buraya sürükle / kopyala → Ctrl+V", "or drag an image here / copy → Ctrl+V"),
    "pin_image_set": ("Görsel eklendi", "Image added"),
    "goals_empty_title": ("Hayat hedeflerini planla", "Plan your life goals"),
    "goals_empty": ("Büyük hedefini, onu taşıyan alt hedefleri ve bunları hatırlatan görselleri tek panoda topla. "
                    "Alışkanlıkları ve dersleri bağla: çalıştıkça ilerlemen görünür.",
                    "Collect your big goal, the goals that carry it and images that remind you of them on one board. "
                    "Link habits and courses to see your progress as you work."),
    "goals_sample": ("Örnek hedeflerle doldur", "Fill with sample goals"),
    "goals_sample_del": ("Örnekleri sil", "Remove samples"),
    "goals_sample_added": ("Örnek hedefler eklendi — bakıp sonra silebilirsin", "Sample goals added"),
    "goals_sample_removed": ("Örnekler silindi", "Samples removed"),
    "goal_mark_today": ("Bugün bunun için çalıştım", "Worked on this today"),
    "goal_unmark_today": ("Bugünkü işareti kaldır", "Remove today's mark"),
    "goal_add_child": ("Alt hedef ekle", "Add sub-goal"),
    "board_hint": ("Pinterest'ten bir görseli kopyala, kartın üstüne gel → Ctrl+V",
                   "Copy an image (e.g. from Pinterest), hover a card → Ctrl+V"),
    "roadmap_title": ("Yol haritası", "Roadmap"),
    "roadmap_sub": ("Hayat hedefinden bu döneme: her adım bir üsttekine hizmet eder",
                    "From life goal to this term: every level serves the one above"),
    "roadmap_empty": ("Bu ufukta hedef yok", "No goals on this horizon"),
    "goal_days_30": ("30 günde {n} gün", "{n} days in 30"),
}


def apply_locale():
    """Tarih seçicilerde ay / gün adları seçilen dilde olsun (pencereler oluşmadan çağır)."""
    from PyQt6.QtCore import QLocale
    if _tr():
        QLocale.setDefault(QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey))
    else:
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))


def t(key, **kw):
    v = S.get(key)
    if v is None:
        return key
    s = v[0] if prefs.get("language", "tr") == "tr" else v[1]
    return s.format(**kw) if kw else s


def _tr():
    return prefs.get("language", "tr") == "tr"


def WEEKDAYS_SHORT():
    return ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if _tr() else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
                                                                          "Sun"]


def WEEKDAYS_LONG():
    return (["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"] if _tr() else
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])


def MONTHS_SHORT():
    return (["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"] if _tr() else
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])


def MONTHS_LONG():
    return (["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
             "Aralık"] if _tr() else
            ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"])


# ------------------------------------------------------------ biçimler
def fmt_num(v, digits=2):
    """Türkçe ondalık (virgül), gereksiz sıfırlar atılır."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{f:,.{digits}f}"
    if digits:
        s = s.rstrip("0").rstrip(".")
    if _tr():
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def fmt_money(v, sign=False):
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        f = 0.0
    cur = prefs.get("currency", "₺") or ""
    body = fmt_num(abs(f), 2)
    if "," in body and _tr():
        a, b = body.split(",")
        body = a + "," + b.ljust(2, "0")
    elif "." in body and not _tr():
        a, b = body.split(".")
        body = a + "." + b.ljust(2, "0")
    pre = ("+" if f > 0 else "−" if f < 0 else "") if sign else ("−" if f < 0 else "")
    if cur in ("₺", "TL"):
        return f"{pre}{body} {cur}"
    return f"{pre}{cur}{body}"


def fmt_day_month(d: date, short=False):
    if short:
        return f"{d.day} {MONTHS_SHORT()[d.month - 1]}"
    return f"{d.day} {MONTHS_SHORT()[d.month - 1]}"


def fmt_month(y, m):
    return f"{MONTHS_LONG()[m - 1]} {y}"


def fmt_long_date(d: date):
    return f"{d.day} {MONTHS_LONG()[d.month - 1]} {d.year}, {WEEKDAYS_LONG()[d.weekday()]}"


def fmt_day(d: date):
    """Göreli kısa tarih: Bugün · Yarın · Dün · Cuma (bu hafta içi) · 14 Kas · 14 Kas 2027."""
    if d is None:
        return ""
    td = day_today()
    diff = (d - td).days
    if diff == 0:
        return t("today")
    if diff == 1:
        return t("tomorrow")
    if diff == -1:
        return t("yesterday")
    if 1 < diff < 7:
        return WEEKDAYS_LONG()[d.weekday()]
    s = f"{d.day} {MONTHS_SHORT()[d.month - 1]}"
    if d.year != td.year:
        s += f" {d.year}"
    return s


def due_badge(d: date):
    """(metin, tür) — geciken kırmızı, bugün/yarın kırmızı-turuncu, 3 güne kadar turuncu."""
    diff = (d - day_today()).days
    if diff < 0:
        return t("overdue_n", n=-diff), "bad"
    if diff == 0:
        return t("today"), "bad"
    if diff == 1:
        return t("tomorrow"), "warn"
    if diff <= 3:
        return t("in_n_days", n=diff), "warn"
    return t("in_n_days", n=diff), None


def fmt_stamp(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    d = dt.date()
    hm = dt.strftime("%H:%M")
    diff = (day_today() - d).days
    if diff == 0:
        return f"{t('today')} {hm}"
    if diff == 1:
        return f"{t('yesterday')} {hm}"
    return fmt_day(d)
