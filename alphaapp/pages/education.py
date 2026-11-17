"""Eğitim: dersler, sınav/ödev notları (hedef ↔ aldığım), gereken not, yaklaşan sınavlar, ders görevleri."""
from datetime import date

from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout

from ..config import day_today
from ..components import Page, Card, Row, StatTile, TileGrid, ProgressBar, ResponsiveRow
from ..forms import edit_item, bind_row, item_menu
from ..i18n import t, due_badge, fmt_day, fmt_num, is_tr
from ..store import parse_date, num
from ..widgets import IconButton
from . import task_row, deadline_row, QuickTask, drop_task_to_exam
from .projects import project_row, sorted_projects
from .grades_view import GradesCard, TranscriptCard
from .. import grades


class EducationPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_education"), t("education_sub"))
        self.action(t("add_exam"), lambda: edit_item(win, "exams"))
        self.action(t("add_course"), lambda: edit_item(win, "courses"), primary=True, icon="add")

        self.t_courses = StatTile(t("courses"))
        self.t_avg = StatTile(t("overall_avg"))
        self.t_below = StatTile(t("below_target"))
        self.t_next = StatTile(t("next_exam"))
        self.add(TileGrid([self.t_courses, self.t_avg, self.t_below, self.t_next]))
        self.c_grades = GradesCard(store, win)      # ANO / AGNO (Excel hesaplayıcısı)
        self.add(self.c_grades)

        self.c_exams = Card(t("upcoming_exams"), add_tip=t("add_exam"))
        self.c_exams.add_clicked.connect(lambda: edit_item(win, "exams"))
        self.c_exams.accept_drop(("tasks",), drop_task_to_exam(win))   # görevi buraya sürükle → sınav
        self.c_tasks = Card(t("edu_tasks"), add_tip=t("add_task"))
        self.c_tasks.add_clicked.connect(lambda: edit_item(win, "tasks", preset={"category": "education"}))
        self.c_tasks.layout().addSpacing(6)
        self.c_tasks.layout().addWidget(QuickTask(win, "education", due_today=False, placeholder=t("quick_task_ph2")))
        self.row(self.c_exams, self.c_tasks)
        self.c_proj = Card(t("edu_projects"), add_tip=t("add_project"))
        self.c_proj.add_clicked.connect(lambda: edit_item(win, "projects", preset={"category": "education"}))
        self.add(self.c_proj)

        self.courses_host = QWidget()
        self.courses_v = QVBoxLayout(self.courses_host)
        self.courses_v.setContentsMargins(0, 0, 0, 0)
        self.courses_v.setSpacing(16)
        self.add(self.courses_host)
        self.c_transcript = TranscriptCard(store, win)
        self.add(self.c_transcript)

    def refresh(self):
        s, win = self.store, self.win
        td = day_today()
        courses = s.all("courses")

        # --- dersler
        while self.courses_v.count():
            it = self.courses_v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        below = 0
        avgs = []
        cards = []
        for c in sorted(courses, key=lambda x: (x.get("name") or "").lower()):
            card, is_below, avg = self._course_card(c)
            cards.append(card)
            below += is_below
            if avg is not None:
                avgs.append((avg, num(c.get("credits")) or 1.0))
        for i in range(0, len(cards), 2):
            r = ResponsiveRow(860)
            r.add(cards[i], 1)
            if i + 1 < len(cards):
                r.add(cards[i + 1], 1)
            else:
                spacer = QWidget()
                r.add(spacer, 1)
            self.courses_v.addWidget(r)
        if not courses:
            c = Card(t("courses"))
            c.empty(t("no_courses"))
            self.courses_v.addWidget(c)

        # --- kutular
        self.t_courses.set(str(len(courses)), t("n_credits", n=fmt_num(sum(num(c.get("credits")) for c in courses)))
                           if any(c.get("credits") for c in courses) else "")
        # AGNO: transkript + bu dönemin kesinleşen harfleri; yoksa sınav puanlarının kredi ağırlıklı ortalaması
        sem = grades.semester(courses, s.all("transcript"))
        if sem["agno"] is not None:
            self.t_avg.set(f"{sem['agno']:.2f}", t("ano") + " " + (f"{sem['ano']:.2f}" if sem["ano"] is not None
                                                                   else "—"))
        elif avgs:
            w = sum(x[1] for x in avgs)
            self.t_avg.set(fmt_num(sum(a * cr for a, cr in avgs) / w, 1), t("avg_note"))
        else:
            self.t_avg.set("—", t("no_scores"))
        self.c_grades.refresh()
        self.c_transcript.refresh()
        self.t_below.set(str(below), t("courses_below_note") if below else t("all_on_track"),
                         "bad" if below else "good" if avgs else None)
        exams = [d for d in s.deadlines(365, "education") if d["kind"] == "exam" and d["date"] >= td]
        if exams:
            nx = exams[0]
            txt, _ = due_badge(nx["date"])
            self.t_next.set(txt, nx["title"])
        else:
            self.t_next.set("—", t("no_upcoming_exam"))

        # --- yaklaşan sınavlar
        self.c_exams.clear()
        for d in exams[:8]:
            self.c_exams.add(deadline_row(win, d, show_cat=False))
        if not exams:
            self.c_exams.empty(t("no_upcoming_exam"))

        # --- ders projeleri (yoksa kart gizli; + ile eklenir)
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
        exams = [e for e in s.all("exams") if e.get("course") == c["id"]]
        exams.sort(key=lambda e: (parse_date(e.get("date")) or date.max, e.get("name") or ""))
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
        for e in exams:
            card.add(self._exam_row(e))
        return card, is_below, avg

    def _exam_row(self, e):
        d = parse_date(e.get("date"))
        sub = [t("weight_pct", w=fmt_num(e.get("weight") or 0))]
        if d:
            sub.append(fmt_day(d))
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
                badges.append((t("enter_score"), "warn"))
            elif d:
                badges.append(due_badge(d))
        r = Row(grades.exam_label(e.get("name"), is_tr()) or t("exam"), " · ".join(sub), value=value, value_role=role, badges=badges)
        return bind_row(self.win, r, "exams", e)
