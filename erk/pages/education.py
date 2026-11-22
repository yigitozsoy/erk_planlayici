"""Eğitim: üç sekme (ChipBar, her açılışta ev).

  home      ev ikonu: kutular (çalışma kareleri, AGNO / hedef, sıradaki sınav), yaklaşan sınavlar (tüm sınav / quiz /
            sunum, haftalara bölünmüş, tarihsizler sonda), Derslerim (her ders + sınav çubuğu; tıkla → derse git),
            ödevler & görevler, ders projeleri
  courses   Dersler: solda ders listesi, sağda seçili dersin kartı (kronometre, ortalama, sınavlar + her sınavın
            çalışma kareleri = konu satırları (edu_study), çalışma günleri DayGrid)
  grades    Notlar: not çubukları (GradesCard) + transkript
"""
from datetime import timedelta

from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout

from ..config import day_today, prefs
from ..components import (Page, Card, Row, StatTile, TileGrid, ProgressBar, clear_layout, sub_label,
                          ChipBar)
from ..forms import edit_item, bind_row, item_menu
from ..i18n import t, due_badge, fmt_day, fmt_day_month, fmt_num, is_tr, WEEKDAYS_SHORT
from ..store import parse_date, num, week_start
from ..theme import theme
from ..widgets import IconButton
from . import task_row, QuickTask, drop_task_to_exam
from .projects import project_row, sorted_projects
from .grades_view import GradesCard, TranscriptCard, ExamBar, course_exams
from .edu_study import ExamStudy, wants_blocks, goal_of, done_of
from .. import grades

TABS = ("home", "courses", "grades")

# ders adına göre ikon: mekanik → dişli, ısı / akış → ateş, temel bilimler → mikroskop (sıra önemli: ilk eşleşen)
COURSE_ICONS = (
    ("course_fire", ("akışkan", "akis", "ısı", "isi ", "termo", "thermo", "fluid", "heat", "yanma", "enerji",
                     "energy", "combust")),
    ("course_science", ("fizik", "physics", "kimya", "chem", "matematik", "math", "diferansiyel", "differential",
                        "kalkülüs", "calculus", "analiz", "lineer", "linear", "cebir", "algebra", "olasılık",
                        "istatistik", "statistic", "biyoloji", "biology", "sayısal", "numeric")),
    ("course_gear", ("makine", "mekani", "mechan", "tasarım", "design", "dinamik", "dynamic", "statik", "static",
                     "mukavemet", "imalat", "manufact", "malzeme", "material", "kalite", "quality", "ölçme",
                     "measure", "cad", "bitirme", "robot", "otomasyon", "titreşim", "vibration", "kontrol")),
)


def course_icon(name):
    n = (name or "").casefold()
    for ic, keys in COURSE_ICONS:
        if any(k in n for k in keys):
            return ic
    return "cat_education"


class EducationPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_education"), t("education_sub"))
        self.action(t("add_exam"), lambda: edit_item(win, "exams"))
        self.action(t("add_course"), lambda: edit_item(win, "courses"), primary=True, icon="add")
        self.sel = None              # Dersler sekmesinde seçili ders id'si

        self.tabs = ChipBar([("home", ""), ("courses", t("tab_courses")), ("grades", t("tab_grades"))], "home")
        self.tabs.btns["home"].setToolTip(t("tab_edu_home"))
        self.tabs.changed.connect(self._tab)
        self.add(self.tabs)
        self.tab_widgets = {k: [] for k in TABS}
        home, crs = self.tab_widgets["home"], self.tab_widgets["courses"]

        # --- ev
        self.t_study = StatTile(t("study_tile"))
        self.t_study.setToolTip(t("study_tile_tip"))
        self.t_avg = StatTile(t("overall_avg"))
        self.t_next = StatTile(t("next_exam"))
        home.append(self.add(TileGrid([self.t_study, self.t_avg, self.t_next])))
        self.c_exams = Card(t("upcoming_exams"), add_tip=t("add_exam"))
        self.c_exams.add_clicked.connect(lambda: edit_item(win, "exams"))
        self.c_exams.accept_drop(("tasks",), drop_task_to_exam(win))   # görevi buraya sürükle → sınav
        self.c_over = Card(t("my_courses"), t("my_courses_sub"), add_tip=t("add_course"))
        self.c_over.add_clicked.connect(lambda: edit_item(win, "courses"))
        home.append(self.row(self.c_exams, self.c_over))
        self.c_tasks = Card(t("edu_tasks"), add_tip=t("add_task"))
        self.c_tasks.add_clicked.connect(lambda: edit_item(win, "tasks", preset={"category": "education"}))
        self.c_tasks.layout().addSpacing(6)
        self.c_tasks.layout().addWidget(QuickTask(win, "education", due_today=False, placeholder=t("quick_task_ph2")))
        self.c_proj = Card(t("edu_projects"), add_tip=t("add_project"))
        self.c_proj.add_clicked.connect(lambda: edit_item(win, "projects", preset={"category": "education"}))
        home.append(self.row(self.c_tasks, self.c_proj))

        # --- dersler: liste + seçili ders
        self.c_list = Card(t("courses"), add_tip=t("add_course"))
        self.c_list.add_clicked.connect(lambda: edit_item(win, "courses"))
        self.detail_host = QWidget()
        self.detail_v = QVBoxLayout(self.detail_host)
        self.detail_v.setContentsMargins(0, 0, 0, 0)
        self.detail_v.setSpacing(16)
        crs.append(self.row(self.c_list, self.detail_host, stretches=[1, 2], breakpoint=900))
        self.courses_v = self.detail_v          # eski adı (testler / dış kod)

        # --- notlar
        self.c_grades = GradesCard(store, win)      # ANO / AGNO (Excel hesaplayıcısı)
        self.c_transcript = TranscriptCard(store, win)
        self.tab_widgets["grades"] += [self.add(self.c_grades), self.add(self.c_transcript)]
        self._tab("home", save=False)

    # ------------------------------------------------------------ sekmeler
    def _tab(self, key, save=True):
        key = key if key in self.tab_widgets else "home"
        if self.tabs.current != key:
            self.tabs.select(key, emit=False)
        # seçili çip açık zemin: ev ikonu koyu olsun
        theme.icon(self.tabs.btns["home"], "home", "button_fg" if key == "home" else "text", 18)
        for k, ws in self.tab_widgets.items():
            for w in ws:
                w.setVisible(k == key)
        if save:
            self.verticalScrollBar().setValue(0)

    def show_course(self, cid):
        """Dersler sekmesine geç, bu dersi seç."""
        self.sel = cid
        self._tab("courses")
        self._fill_courses()

    # ------------------------------------------------------------ yenile
    def refresh(self):
        s, win = self.store, self.win
        td = day_today()
        courses = sorted(s.all("courses"), key=lambda x: (x.get("name") or "").lower())

        # --- kutular
        ids = {c["id"] for c in courses}
        sq = [e for e in s.all("exams") if e.get("course") in ids and wants_blocks(e, td)]
        g, dn = sum(goal_of(e) for e in sq), sum(done_of(e) for e in sq)
        self.t_study.set(f"{dn} / {g}" if sq else "—",
                         t("study_tile_note", n=len(sq), p=round(100 * dn / g)) if g else t("study_tile_none"),
                         "good" if g and dn >= g else None)
        # AGNO: transkript + bu dönemin kesinleşen harfleri; yanında sabit hedef (prefs agno_goal)
        goal = float(prefs.get("agno_goal") or 3.0)
        sem = grades.semester(courses, s.all("transcript"))
        avgs = []
        for c in courses:
            avg, _w, _t = s.course_average(c["id"])
            if avg is not None:
                avgs.append((avg, num(c.get("credits")) or 1.0))
        if sem["agno"] is not None:
            self.t_avg.set(f"{sem['agno']:.2f} / {goal:.1f}",
                           t("ano") + " " + (f"{sem['ano']:.2f}" if sem["ano"] is not None else "—"),
                           "good" if sem["agno"] >= goal else None)
        elif avgs:
            w = sum(x[1] for x in avgs)
            self.t_avg.set(fmt_num(sum(a * cr for a, cr in avgs) / w, 1), t("avg_note"))
        else:
            self.t_avg.set("—", t("no_scores"))
        exams = [d for d in s.deadlines(365, "education") if d["kind"] == "exam" and d["date"] >= td]
        if exams:
            nx = exams[0]
            txt, _ = due_badge(nx["date"])
            self.t_next.set(txt, nx["title"])
        else:
            self.t_next.set("—", t("no_upcoming_exam"))

        # --- yaklaşan sınavlar: tüm sınav / quiz / sunum, haftalara bölünmüş, tarihsizler sonda
        self._fill_calendar(td)

        # --- derslerim: ad + sınav çubuğu, tıkla → Dersler sekmesinde o ders
        self.c_over.clear()
        for c in courses:
            self.c_over.add(self._over_item(c, td))
        if not courses:
            self.c_over.empty(t("no_courses"))

        # --- ders projeleri
        self.c_proj.clear()
        eprojects = sorted_projects(s, "education", include_done=False)
        for p in eprojects:
            self.c_proj.add(project_row(win, p))
        if not eprojects:
            self.c_proj.empty(t("no_projects"))

        # --- görevler
        self.c_tasks.clear()
        tasks = s.open_tasks("education")
        for tk in tasks[:10]:
            self.c_tasks.add(task_row(win, tk, show_cat=False))
        if not tasks:
            self.c_tasks.empty(t("no_tasks"))

        self._fill_courses()
        self.c_grades.refresh()
        self.c_transcript.refresh()

    def _next_text(self, c, td):
        """Ders listesindeki alt satır: sıradaki sınav (ya da sonuç bekleyen / ortalama)."""
        ex = course_exams(self.store, c["id"])
        nxt = sorted((e for e in ex if e.get("score") in (None, "") and parse_date(e.get("date"))
                      and parse_date(e.get("date")) >= td), key=lambda e: e["date"])
        bits = []
        if nxt:
            e = nxt[0]
            bits.append(f"{grades.exam_label(e.get('name'), is_tr())} · {fmt_day_month(parse_date(e['date']))}")
            if wants_blocks(e, td):
                bits.append(t("exam_study_short", d=done_of(e), g=goal_of(e)))
        pend = sum(1 for e in ex if e.get("score") in (None, "") and parse_date(e.get("date"))
                   and parse_date(e.get("date")) < td)
        if pend:
            bits.append(t("pending_n", n=pend))
        avg, _w, _t = self.store.course_average(c["id"])
        if avg is not None:
            bits.append(t("now_avg", v=fmt_num(avg, 1)))
        return " · ".join(bits) or t("course_empty_hint")

    def _over_item(self, c, td):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 4)
        v.setSpacing(2)
        sub = " · ".join(x for x in (self._next_text(c, td),
                                     t("target_letter", l=c["target"]) if c.get("target") else "") if x)
        r = Row(c.get("name") or "—", sub, icon=course_icon(c.get("name")))
        r.clicked.connect(lambda cid=c["id"]: self.show_course(cid))
        r.setToolTip(t("go_course"))
        v.addWidget(r)
        ex = course_exams(self.store, c["id"])
        if ex:
            bar = ExamBar(ex, lambda e: edit_item(self.win, "exams", e))
            bar.setContentsMargins(0, 0, 0, 0)
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(44, 0, 8, 0)
            bl.addWidget(bar)
            v.addWidget(box)
        return w

    # ------------------------------------------------------------ dersler sekmesi
    def _fill_courses(self):
        s, win, td = self.store, self.win, day_today()
        courses = sorted(s.all("courses"), key=lambda x: (x.get("name") or "").lower())
        ids = [c["id"] for c in courses]
        if self.sel not in ids:
            # varsayılan: sınavı en yakın olan ders
            best = None
            for c in courses:
                for e in s.all("exams"):
                    d = parse_date(e.get("date"))
                    if e.get("course") == c["id"] and d and d >= td and e.get("score") in (None, ""):
                        if best is None or d < best[0]:
                            best = (d, c["id"])
            self.sel = best[1] if best else (ids[0] if ids else None)
        self.c_list.clear()
        for c in courses:
            r = Row(c.get("name") or "—", self._next_text(c, td), icon=course_icon(c.get("name")),
                    icon_role="text" if c["id"] == self.sel else "text3")
            if c["id"] == self.sel:
                r.setProperty("sel", True)
            r.clicked.connect(lambda cid=c["id"]: self.show_course(cid))
            r.menu_requested.connect(lambda pos, x=c: item_menu(win, "courses", x, pos))
            self.c_list.add(r)
        if not courses:
            self.c_list.empty(t("no_courses"))
        self.c_list.set_sub(t("n_credits", n=fmt_num(sum(num(c.get("credits")) for c in courses)))
                            if courses else "")
        clear_layout(self.detail_v)
        sel = s.get("courses", self.sel) if self.sel else None
        if sel is not None:
            card, _b, _a = self._course_card(sel)
            self.detail_v.addWidget(card)
        else:
            c = Card(t("courses"))
            c.empty(t("no_courses"))
            self.detail_v.addWidget(c)

    def _course_card(self, c):
        s, win = self.store, self.win
        sub = " · ".join(x for x in (c.get("code"), t("n_credits", n=fmt_num(c["credits"])) if c.get("credits") else "",
                                     t("target_letter", l=c["target"]) if c.get("target") else "") if x)
        card = Card(c.get("name") or "—", sub, add_tip=t("add_exam_for"))
        card.add_clicked.connect(lambda cid=c["id"]: edit_item(win, "exams", preset={"course": cid}))
        card.accept_drop(("tasks",), drop_task_to_exam(win, c["id"]))
        more = IconButton("more_vert", t("course_menu"), 32, 20)
        more.clicked.connect(lambda _=False, b=more: item_menu(win, "courses", c, b.mapToGlobal(b.rect().bottomLeft())))
        card.head_widget(more)

        avg, w_done, tavg = s.course_average(c["id"])
        # üstteki not çubuğuyla aynı sıra: vizeler, quiz / lab / ödev …, final
        exams = course_exams(s, c["id"])
        w_all = sum(num(e.get("weight")) for e in exams)

        is_below = avg is not None and tavg is not None and avg < tavg
        bar = ProgressBar((avg or 0) / 100, "bad" if is_below else "good" if avg is not None else "text",
                          marker=(tavg / 100) if tavg is not None else None, height=6)
        info = QLabel()
        info.setObjectName("RowSub")
        info.setWordWrap(True)
        bits = []
        if avg is not None:
            bits.append(t("now_avg", v=fmt_num(avg, 1)))
        if tavg is not None:
            bits.append(t("target_avg", v=fmt_num(tavg, 1)))
        if w_all:
            bits.append(t("weight_done", d=fmt_num(w_done), a=fmt_num(w_all)))
        # hedefe ulaşmak için kalan sınavlardan gereken ortalama
        rem_w = sum(num(e.get("weight")) for e in exams if e.get("score") in (None, ""))
        if tavg is not None and rem_w > 0:
            achieved = sum(num(e.get("score")) * num(e.get("weight")) for e in exams if e.get("score") not in (None, ""))
            need = (tavg * w_all - achieved) / rem_w
            if need > 100:
                bits.append(t("need_impossible", v=fmt_num(need, 0)))
            elif need <= 0:
                bits.append(t("need_done"))
            else:
                bits.append(t("need_avg", v=fmt_num(need, 0)))
        info.setText("  ·  ".join(bits) if bits else t("course_empty_hint"))
        from ..clock_ui import CourseClock
        card.add(CourseClock(win, c))
        card.add(bar)
        card.add(info)
        card.body.addSpacing(4)
        td = day_today()
        for e in exams:
            card.add(self._exam_row(e))
            card.add(ExamStudy(s, e))          # geçmiş sınavlara da kare atanabilir
        # ders görevleri (bu derse bağlı: başlıkta ders adı geçen açık eğitim görevleri)
        name = (c.get("name") or "").casefold()
        ctasks = [tk for tk in s.open_tasks("education") if name and name in (tk.get("title") or "").casefold()]
        if ctasks:
            lbl = sub_label(t("course_tasks"))
            lbl.setContentsMargins(4, 10, 0, 0)
            card.add(lbl)
            for tk in ctasks[:6]:
                card.add(task_row(win, tk, show_cat=False))
        # çalışma günleri: son 2 ay + önümüzdeki 1 ay, tıkla = o gün çalıştım
        from ..components import DayGrid
        from ..i18n import MONTHS_SHORT
        from ..store import day_set, streaks
        days = day_set(c.get("study_days"))
        ws = week_start(td)
        cur, _best = streaks(days, td)
        # kronometre süresi: 1 saat ve üstü tam kare, daha azı yarım; süresiz (elle) işaret tam
        mins = {}
        for se in s.all("sessions"):
            if se.get("kind") == "study" and se.get("course") == c["id"]:
                d = parse_date(se.get("date"))
                if d:
                    mins[d] = mins.get(d, 0.0) + num(se.get("minutes"))
        vals = {td - timedelta(days=k): 0.0 for k in range(-45, 100)}
        vals.update({d: (1.0 if mins.get(d, 60) >= 60 else 0.5) for d in days})
        wk_min = sum(m for d, m in mins.items() if ws <= d <= ws + timedelta(days=6))
        info_txt = t("study_info", w=sum(1 for d in days if ws <= d <= ws + timedelta(days=6)), s=cur, n=len(days))
        if wk_min:
            info_txt += " · " + t("study_week_time", h=int(wk_min // 60), m=int(wk_min % 60))
        head = sub_label(t("study_title") + " · " + info_txt)
        head.setContentsMargins(4, 12, 0, 0)
        card.add(head)
        grid = DayGrid(WEEKDAYS_SHORT(), MONTHS_SHORT(), span=(2, 1))
        grid.set_values(vals, [])
        grid.day_toggled.connect(lambda d, cid=c["id"]: self.store.toggle_day("courses", cid, d, "study_days"))
        card.add(grid)
        card.grid = grid
        return card, is_below, avg

    def _exam_row(self, e, with_course=False, icon=None):
        d = parse_date(e.get("date"))
        sub = [t("weight_pct", w=fmt_num(e.get("weight") or 0))]
        if d:
            sub.append(fmt_day(d) if not with_course else f"{WEEKDAYS_SHORT()[d.weekday()]} {fmt_day_month(d)}")
        if e.get("time"):
            sub.append(e["time"])
        score, target = e.get("score"), e.get("target")
        badges = []
        value, role = "", None
        if score not in (None, ""):
            value = fmt_num(score)
            if target not in (None, ""):
                value += f" / {fmt_num(target)}"
                role = "good" if num(score) >= num(target) else "bad"
        else:
            if target not in (None, ""):
                sub.append(t("target_score", v=fmt_num(target)))
            if d and d < day_today():
                # girdin, sonuç açıklanmadı: gri "?" (tıkla = notu gir)
                value, role = "?", "text3"
            elif d:
                badges.append(due_badge(d))
        r = Row(grades.exam_label(e.get("name"), is_tr()) or t("exam"), " · ".join(x for x in sub if x),
                value=value, value_role=role, badges=badges, icon=icon)
        if value == "?":
            r.setToolTip(t("exam_pending"))
        return bind_row(self.win, r, "exams", e)

    # ------------------------------------------------------------ yaklaşan sınavlar (ev)
    def _fill_calendar(self, td):
        s, c = self.store, self.c_exams
        c.clear()
        ids = {x["id"] for x in s.all("courses")}
        ex = [e for e in s.all("exams") if e.get("course") in ids and e.get("score") in (None, "")
              and (parse_date(e.get("date")) is None or parse_date(e.get("date")) >= td)]
        dated = sorted((e for e in ex if parse_date(e.get("date"))),
                       key=lambda e: (e["date"], e.get("time") or "", grades.exam_order(e.get("name"))))
        undated = [e for e in ex if not parse_date(e.get("date"))]
        week = None
        for e in dated:
            d = parse_date(e["date"])
            ws = week_start(d)
            if ws != week:
                week = ws
                lbl = sub_label(t("cal_week", n=d.isocalendar()[1], a=fmt_day_month(ws),
                                  b=fmt_day_month(ws + timedelta(days=6)))
                                + (" · " + t("this_week") if ws <= td <= ws + timedelta(days=6) else ""))
                lbl.setObjectName("FieldLabel")
                lbl.setContentsMargins(6, 12, 0, 2)
                c.add(lbl)
            c.add(self._cal_row(e))
        if undated:
            lbl = sub_label(t("cal_undated"))
            lbl.setObjectName("FieldLabel")
            lbl.setContentsMargins(6, 12, 0, 2)
            c.add(lbl)
            for e in sorted(undated, key=lambda e: (grades.exam_order(e.get("name")), e.get("course") or "")):
                c.add(self._cal_row(e))
        if not ex:
            c.empty(t("no_upcoming_exam"))
        up = sum(1 for e in dated if parse_date(e["date"]) >= td and e.get("score") in (None, ""))
        c.set_sub(t("cal_sub", n=up, u=len(undated)) if ex else "")

    def _cal_row(self, e):
        c = self.store.get("courses", e.get("course"))
        r = self._exam_row(e, with_course=True, icon=course_icon(c.get("name") if c else ""))
        if wants_blocks(e) and done_of(e):
            r.setToolTip(t("exam_study_info", d=done_of(e), g=goal_of(e)))
        # başlık: "Ders · Sınav"
        if c is not None:
            r.title_lbl.setText(f"{c.get('name') or '—'} · {grades.exam_label(e.get('name'), is_tr()) or t('exam')}")
        return r

