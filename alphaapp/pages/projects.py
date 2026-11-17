"""Projeler: iş ve ders projeleri. Logo, zaman çizelgesi (başlangıç → teslim, bugün çizgisi, görev noktaları),
proje kartlarında projeye atanmış görevler (task.project) ve hızlı görev ekleme.

Proje kaydı: name, category (work / education / ...), status, start, due, progress (görev yoksa elle), logo
(DATA_DIR\\images içindeki dosya adı), note.
"""
import os
from datetime import date, timedelta

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap, QPainterPath, QPen, QFont, QFontMetrics, QColor
from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QSizePolicy, QVBoxLayout

from ..config import day_today, IMAGES_DIR
from ..components import Page, Card, Row, ProgressBar, ResponsiveRow, StatTile, TileGrid
from ..forms import edit_item, bind_row
from ..i18n import t, due_badge, fmt_day, MONTHS_SHORT
from ..store import parse_date
from ..theme import theme, qcolor
from . import task_row

STATUS_ORDER = {"doing": 0, "waiting": 1, "todo": 2, "done": 3}


def sorted_projects(store, category=None, include_done=True):
    ps = [p for p in store.all("projects") if (category is None or (p.get("category") or "work") == category)
          and (include_done or p.get("status") != "done")]
    return sorted(ps, key=lambda p: (STATUS_ORDER.get(p.get("status"), 9), parse_date(p.get("due")) or date.max,
                                     (p.get("name") or "").lower()))


# ============================================================ logo
_cache = {}


def logo_pixmap(p, size):
    """Proje logosu (yuvarlatılmış kare). Logo yoksa adın baş harfi gri karo üstünde. Tema rengi değişebilir,
    önbellek anahtarına renk de girer."""
    name = (p.get("name") or "?").strip() or "?"
    logo = p.get("logo")
    path = os.path.join(IMAGES_DIR, logo) if logo else None
    bg, fg = qcolor("surface_hover"), qcolor("text")
    key = (path, name[:1], size, bg.name(), fg.name(), os.path.getmtime(path) if path and os.path.exists(path) else 0)
    if key in _cache:
        return _cache[key]
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    qp = QPainter(pm)
    qp.setRenderHint(QPainter.RenderHint.Antialiasing)
    qp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    qp.setClipPath(clip)
    img = QPixmap(path) if path and os.path.exists(path) else QPixmap()
    if not img.isNull():
        qp.fillRect(QRectF(0, 0, size, size), QColor("#ffffff"))
        sc = img.scaled(size * dpr, size * dpr, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
        sc.setDevicePixelRatio(dpr)
        w, h = sc.width() / dpr, sc.height() / dpr
        qp.drawPixmap(QPointF((size - w) / 2, (size - h) / 2), sc)
    else:
        qp.fillRect(QRectF(0, 0, size, size), bg)
        f = QFont("Segoe UI")          # değişken yazı tipinin kalını pixmap'te bozuk çıkıyordu
        f.setPixelSize(int(size * 0.5))
        f.setWeight(QFont.Weight.DemiBold)
        # harf yol olarak çizilir: yüksek DPI pixmap'e drawText bazı yazı motorlarında bozuk çıkıyordu
        path = QPainterPath()
        path.addText(0, 0, f, name[:1].upper())
        br = path.boundingRect()
        path.translate(size / 2 - br.center().x(), size / 2 - br.center().y())
        qp.setPen(Qt.PenStyle.NoPen)
        qp.setBrush(fg)
        qp.drawPath(path)
    qp.end()
    if len(_cache) > 200:
        _cache.clear()
    _cache[key] = pm
    return pm


class Logo(QLabel):
    def __init__(self, p, size=28):
        super().__init__()
        self.setFixedSize(size, size)
        theme.bind(self, lambda l, p=p, s=size: l.setPixmap(logo_pixmap(p, s)))


def project_row(win, p, show_cat=False):
    """İş / Eğitim sayfalarındaki kısa proje satırı: logo, ad, durum · teslim, ilerleme çubuğu."""
    s = win.store
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 6)
    v.setSpacing(0)
    d = parse_date(p.get("due"))
    sub = [t("status_" + (p.get("status") or "doing"))]
    if show_cat:
        sub.insert(0, t("cat_" + (p.get("category") or "work")))
    n_open, n_all = s.project_task_counts(p["id"])
    if n_all:
        sub.append(t("n_of_tasks", d=n_all - n_open, n=n_all))
    if d:
        sub.append(fmt_day(d))
    badges = [due_badge(d)] if d and p.get("status") != "done" else []
    prog = s.project_progress(p)
    r = Row(p.get("name", ""), " · ".join(sub), value=f"%{int(prog)}", lead=Logo(p, 28), badges=badges)
    extra = [(t("add_task_to_project"), lambda: edit_item(win, "tasks", preset=project_task_preset(p)))]
    if p.get("status") != "done":
        extra.append((t("mark_project_done"), lambda: s.update("projects", p["id"], status="done")))
    bind_row(win, r, "projects", p, extra)
    v.addWidget(r)
    wrap = QWidget()
    wl = QVBoxLayout(wrap)
    wl.setContentsMargins(44, 0, 10, 0)
    wl.addWidget(ProgressBar(prog / 100, "good" if p.get("status") == "done" else "text", height=4))
    v.addWidget(wrap)
    return box


def project_task_preset(p):
    return {"category": p.get("category") or "work", "project": p["id"]}


class ProjectQuickTask(QLineEdit):
    """Proje kartının altında: yaz, Enter → projeye görev."""

    def __init__(self, win, p):
        super().__init__()
        self.win, self.p = win, p
        self.setPlaceholderText(t("quick_project_task_ph"))
        self.setObjectName("Search")
        self.returnPressed.connect(self._add)

    def _add(self):
        text = self.text().strip()
        if not text:
            return
        self.win.store.add("tasks", dict(project_task_preset(self.p), title=text, priority="normal", done=False,
                                         due=None))
        self.clear()


# ============================================================ zaman çizelgesi
class Timeline(QWidget):
    """Gantt benzeri: her proje bir satır (logo + ad | başlangıç → teslim çubuğu). Bugün dikey çizgi; projeye
    atanmış tarihli görevler çubuk üstünde nokta (biten dolu). Satıra tıkla → projeyi düzenle."""
    clicked = pyqtSignal(str)
    ROW, HEAD, LEFT = 40, 26, 190

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.projects = []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hover = -1
        theme.bind(self, lambda w: w.update())

    def set_projects(self, projects):
        self.projects = projects
        self.setFixedHeight(self.HEAD + max(1, len(projects)) * self.ROW + 6)
        self.update()

    def _span(self, p):
        td = day_today()
        st = parse_date(p.get("start")) or parse_date((p.get("created") or "")[:10]) or td
        en = parse_date(p.get("due"))
        return st, en

    def _range(self):
        td = day_today()
        a, b = td - timedelta(days=14), td + timedelta(days=45)
        for p in self.projects:
            st, en = self._span(p)
            a = min(a, st)
            if en:
                b = max(b, en + timedelta(days=7))
        a = a.replace(day=1)
        return a, b

    def _x(self, d, a, b, w):
        span = max(1, (b - a).days)
        return self.LEFT + (d - a).days / span * (w - self.LEFT - 8)

    def paintEvent(self, e):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        td = day_today()
        a, b = self._range()
        text, text2, text3 = qcolor("text"), qcolor("text2"), qcolor("text3")
        divider, track = qcolor("divider"), qcolor("track")
        f = QFont(self.font())
        f.setPixelSize(11)
        qp.setFont(f)
        # ay çizgileri ve adları
        m = date(a.year, a.month, 1)
        months = MONTHS_SHORT()
        while m <= b:
            x = self._x(m, a, b, w)
            if x >= self.LEFT:
                qp.setPen(QPen(divider, 1))
                qp.drawLine(QPointF(x, self.HEAD - 4), QPointF(x, self.height()))
                qp.setPen(text3)
                qp.drawText(QPointF(x + 4, 14), f"{months[m.month - 1]}" + (f" {m.year}" if m.month == 1 else ""))
            m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        if not self.projects:
            qp.setPen(text3)
            qp.drawText(QRectF(0, self.HEAD, w, self.ROW), Qt.AlignmentFlag.AlignCenter, t("no_projects"))
            return
        fn = QFont(self.font())
        fn.setPixelSize(13)
        fm = QFontMetrics(fn)
        for i, p in enumerate(self.projects):
            y = self.HEAD + i * self.ROW
            if i == self._hover:
                qp.fillRect(QRectF(0, y, w, self.ROW), qcolor("hover"))
            qp.drawPixmap(QPointF(4, y + (self.ROW - 24) / 2), logo_pixmap(p, 24))
            qp.setFont(fn)
            qp.setPen(text if p.get("status") != "done" else text3)
            qp.drawText(QRectF(36, y, self.LEFT - 44, self.ROW), Qt.AlignmentFlag.AlignVCenter,
                        fm.elidedText(p.get("name") or "—", Qt.TextElideMode.ElideRight, self.LEFT - 44))
            st, en = self._span(p)
            x0 = max(self.LEFT, self._x(st, a, b, w))
            x1 = self._x(en, a, b, w) if en else w - 8
            if x1 < x0 + 6:
                x1 = x0 + 6
            bar = QRectF(x0, y + 12, x1 - x0, self.ROW - 24)
            qp.setPen(Qt.PenStyle.NoPen)
            qp.setBrush(track)
            qp.drawRoundedRect(bar, 4, 4)
            prog = self.store.project_progress(p) / 100
            done_col = qcolor("good") if p.get("status") == "done" else text2
            if prog > 0:
                qp.setBrush(done_col)
                qp.drawRoundedRect(QRectF(bar.x(), bar.y(), max(6.0, bar.width() * prog), bar.height()), 4, 4)
            late = en and en < td and p.get("status") != "done"
            if en:   # teslim işareti
                qp.setBrush(qcolor("bad") if late else text)
                qp.drawEllipse(QPointF(x1, bar.center().y()), 4, 4)
            # görev noktaları
            for tk in self.store.all("tasks"):
                if tk.get("project") != p["id"]:
                    continue
                d = parse_date(tk.get("due"))
                if not d or d < a or d > b:
                    continue
                x = self._x(d, a, b, w)
                if tk.get("done"):
                    qp.setPen(Qt.PenStyle.NoPen)
                    qp.setBrush(text)
                else:
                    qp.setPen(QPen(text, 1.5))
                    qp.setBrush(qcolor("card"))
                qp.drawEllipse(QPointF(x, y + 7), 3, 3)
            qp.setPen(Qt.PenStyle.NoPen)
        # bugün
        xt = self._x(td, a, b, w)
        qp.setPen(QPen(qcolor("bad"), 1.5))
        qp.drawLine(QPointF(xt, self.HEAD - 6), QPointF(xt, self.height()))
        qp.setPen(qcolor("bad"))
        qp.drawText(QPointF(xt + 4, self.HEAD - 2), t("today"))

    def _row_at(self, pos):
        i = int((pos.y() - self.HEAD) // self.ROW)
        return i if pos.y() >= self.HEAD and 0 <= i < len(self.projects) else -1

    def mouseMoveEvent(self, e):
        i = self._row_at(e.position())
        if i != self._hover:
            self._hover = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0 else Qt.CursorShape.ArrowCursor)
            if i >= 0:
                p = self.projects[i]
                st, en = self._span(p)
                self.setToolTip(f"{p.get('name', '')}\n{fmt_day(st)} → {fmt_day(en) if en else '—'}")
            self.update()

    def leaveEvent(self, e):
        self._hover = -1
        self.update()

    def mouseReleaseEvent(self, e):
        i = self._row_at(e.position())
        if i >= 0 and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.projects[i]["id"])


# ============================================================ sayfa
class ProjectsPage(Page):
    def __init__(self, store, win):
        super().__init__(store, win, t("nav_projects"), t("projects_sub"))
        self.action(t("add_project"), lambda: edit_item(win, "projects"), primary=True, icon="add")
        self.t_active = StatTile(t("active_projects"))
        self.t_open = StatTile(t("open_tasks"))
        self.t_next = StatTile(t("next_project_due"))
        self.t_late = StatTile(t("late_tasks"))
        self.add(TileGrid([self.t_active, self.t_open, self.t_next, self.t_late]))
        self.c_time = Card(t("timeline"), t("timeline_sub"), add_tip=t("add_project"))
        self.c_time.add_clicked.connect(lambda: edit_item(win, "projects"))
        self.timeline = Timeline(store)
        self.timeline.clicked.connect(lambda pid: edit_item(win, "projects", store.get("projects", pid)))
        self.c_time.layout().addWidget(self.timeline)
        self.add(self.c_time)
        self.cards_host = QWidget()
        self.cards_v = QVBoxLayout(self.cards_host)
        self.cards_v.setContentsMargins(0, 0, 0, 0)
        self.cards_v.setSpacing(16)
        self.add(self.cards_host)

    def refresh(self):
        s = self.store
        td = day_today()
        projects = sorted_projects(s)
        active = [p for p in projects if p.get("status") != "done"]
        self.timeline.set_projects(active)
        ptasks = [x for x in s.all("tasks") if x.get("project") and not x.get("done")]
        self.t_active.set(str(len(active)), t("n_total", n=len(projects)) if projects else "")
        self.t_open.set(str(len(ptasks)))
        dues = sorted((parse_date(p.get("due")), p) for p in active if parse_date(p.get("due")) and
                      parse_date(p.get("due")) >= td)
        if dues:
            self.t_next.set(due_badge(dues[0][0])[0], dues[0][1].get("name", ""))
        else:
            self.t_next.set("—", "")
        late = [x for x in ptasks if (parse_date(x.get("due")) or date.max) < td]
        self.t_late.set(str(len(late)), "", "bad" if late else None)

        from ..components import _clear_layout
        _clear_layout(self.cards_v)
        cards = [self._card(p) for p in projects]
        for i in range(0, len(cards), 2):
            r = ResponsiveRow(860)
            r.add(cards[i], 1)
            r.add(cards[i + 1] if i + 1 < len(cards) else QWidget(), 1)
            self.cards_v.addWidget(r)
        if not projects:
            c = Card(t("projects"))
            c.empty(t("no_projects_hint"))
            self.cards_v.addWidget(c)

    def _card(self, p):
        s, win = self.store, self.win
        d = parse_date(p.get("due"))
        sub = [t("cat_" + (p.get("category") or "work")), t("status_" + (p.get("status") or "doing"))]
        if d:
            sub.append(t("due_on", d=fmt_day(d)))
        card = Card(p.get("name") or "—", " · ".join(sub), add_tip=t("add_task_to_project"))
        card.add_clicked.connect(lambda: edit_item(win, "tasks", preset=project_task_preset(p)))
        card.head.insertWidget(0, Logo(p, 40), 0, Qt.AlignmentFlag.AlignTop)
        card.head.insertSpacing(1, 10)
        from ..widgets import IconButton
        from ..forms import item_menu
        more = IconButton("more_vert", t("edit"), 32, 20)
        more.clicked.connect(lambda _=False, b=more: item_menu(win, "projects", p, b.mapToGlobal(b.rect().bottomLeft())))
        card.head_widget(more)
        prog = s.project_progress(p)
        n_open, n_all = s.project_task_counts(p["id"])
        info = QLabel(f"%{int(prog)}" + (" · " + t("n_of_tasks", d=n_all - n_open, n=n_all) if n_all else ""))
        info.setObjectName("RowSub")
        card.add(ProgressBar(prog / 100, "good" if p.get("status") == "done" else "text", height=6))
        card.add(info)
        card.body.addSpacing(4)
        tasks = sorted((x for x in s.all("tasks") if x.get("project") == p["id"] and not x.get("done")),
                       key=lambda x: (parse_date(x.get("due")) or date.max, x.get("time") or ""))
        for tk in tasks[:8]:
            card.add(task_row(win, tk, show_cat=False))
        if not tasks:
            card.empty(t("no_project_tasks"))
        if p.get("note"):
            n = QLabel(p["note"].splitlines()[0][:140])
            n.setObjectName("RowSub")
            n.setWordWrap(True)
            card.add(n)
        card.layout().addSpacing(6)
        card.layout().addWidget(ProjectQuickTask(win, p))
        card.accept_drop(("tasks",), lambda coll, iid, pid=p["id"]: s.update("tasks", iid, project=pid))
        return card
