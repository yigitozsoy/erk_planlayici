"""Eğitim sayfasındaki not ortalaması kartları (hesap: grades.py, Excel hesaplayıcısının karşılığı).

GradesCard      bu dönemin dersleri: adın altında ExamBar (her sınav ağırlığı kadar yer kaplar, dolu kısım notu,
                hedef puan ipucunda; tıkla = sınavı düzenle), AKTS, sınav ağırlıklı puan, gerçek / hedef harf
                (yerinde seçilir), eski not (tekrar). Kalem düğmesi sınav çiplerini ve + düğmesini açar; "Dönemi bitir"
                ⋮ menüsünde. Üstte gerçek ve hedefin ANO / AGNO'su. İhtimal senaryosu gösterilmez.
TranscriptCard  dönem dönem transkript (tıkla aç / kapat), Excel'den al, + ile ders ekle.
"""
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QPainterPath
from PyQt6.QtWidgets import (QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton,
                             QInputDialog, QMessageBox, QFileDialog, QMenu, QToolTip)

from .. import grades
from ..components import Card, Row
from ..forms import edit_item, bind_row
from ..config import prefs
from ..i18n import t, fmt_num, is_tr
from ..store import num, parse_date
from ..theme import theme, qcolor
from ..widgets import IconButton


SHOWN = ("letter", "target")      # ihtimal senaryosu kullanıcı isteğiyle gösterilmiyor (grades.py hâlâ hesaplar)


def _g(v):
    return "—" if v is None else f"{v:.2f}"


class _Combo(QComboBox):
    """Satır içi harf seçimi. Kayıt sayfayı yeniden kurar: değişiklik sinyal bittikten sonra yazılır."""

    def __init__(self, value, letters, on_pick):
        super().__init__()
        self.setObjectName("GradeCombo")
        self.setStyleSheet("min-width: 0px;")
        self.setFixedWidth(68)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)   # tekerlek yalnızca odaktayken değiştirsin
        self.addItem("—", "")
        for x in letters:
            self.addItem(x, x)
        i = self.findData((value or "").strip().upper())
        self.setCurrentIndex(max(0, i))
        self.activated.connect(lambda _i: QTimer.singleShot(0, lambda: on_pick(self.currentData())))

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


def _lbl(text, obj="RowSub", align=None):
    lb = QLabel(text)
    lb.setObjectName(obj)
    if align is not None:
        lb.setAlignment(align)
    return lb


def _short(name):
    """Sınav adının kısası: kelimelerin büyük baş harfi, sayılar aynen ("Vize 1" → "V1", "Ödev" → "Ö")."""
    return "".join(w if w.isdigit() else w[:1].upper() for w in (name or "").split()) or "?"


def course_exams(store, cid):
    """Dersin sınavları sırayla: vizeler, quiz / lab / ödev …, final, bütünleme; aynı türde tarihe göre."""
    from datetime import date
    return sorted((e for e in store.all("exams") if e.get("course") == cid),
                  key=lambda e: (grades.exam_order(e.get("name")), parse_date(e.get("date")) or date.max,
                                 e.get("name") or ""))


class ExamBar(QWidget):
    """Bir dersin sınavları tek çubukta: her sınav ağırlığı kadar yer kaplar (toplam %100'ün altındaysa kalan boş
    kalır), aldığın not o parçanın içinde soldan dolar; dar parçada ad baş harfe iner. Üstüne gel = ayrıntı, tıkla = düzenle."""
    H = 20
    GAP = 3

    def __init__(self, exams, on_click):
        super().__init__()
        self.exams, self.on_click = exams, on_click
        self.setFixedHeight(self.H)
        self.setMinimumWidth(120)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hover = -1
        theme.bind(self, lambda w: w.update())

    def _rects(self):
        total = sum(num(e.get("weight")) for e in self.exams)
        scale = max(total, 100.0)
        w = self.width() - self.GAP * max(0, len(self.exams) - 1)
        out, x = [], 0.0
        for e in self.exams:
            ew = w * num(e.get("weight")) / scale if total else w / len(self.exams)
            out.append(QRectF(x, 0, max(ew, 4.0), self.H))
            x += ew + self.GAP
        return out

    def _at(self, pos):
        for i, r in enumerate(self._rects()):
            if r.contains(pos):
                return i
        return -1

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track, fill, text = qcolor("track"), qcolor("text3"), qcolor("text")
        f = QFont(self.font())
        f.setPixelSize(11)
        p.setFont(f)
        fm = QFontMetrics(f)
        tr = is_tr()
        for i, (r, e) in enumerate(zip(self._rects(), self.exams)):
            clip = QPainterPath()
            clip.addRoundedRect(r, 4, 4)
            p.save()
            p.setClipPath(clip)
            p.fillRect(r, track.lighter(130) if i == self.hover else track)
            sc = e.get("score")
            scored = sc not in (None, "")
            if scored:
                fr = QRectF(r.x(), 0, r.width() * max(0.0, min(100.0, num(sc))) / 100.0, self.H)
                p.fillRect(fr, fill.lighter(115) if i == self.hover else fill)
            name = grades.exam_label(e.get("name"), tr) or t("exam")
            tail = f" {fmt_num(num(sc))}" if scored else ""
            room = int(r.width()) - 10
            # sığmazsa baş harf(ler): "Vize 1" → "V1", "Laboratuvar" → "L"
            for label in (name + tail, _short(name) + tail, _short(name)):
                if fm.horizontalAdvance(label) <= room:
                    p.setPen(text if scored else qcolor("text2"))
                    p.drawText(r.adjusted(5, 0, -5, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               label)
                    break
            p.restore()
        p.end()

    def _tip(self, e):
        name = grades.exam_label(e.get("name"), is_tr()) or t("exam")
        lines = [t("exam_bar_tip", n=name, w=fmt_num(num(e.get("weight"))))]
        sc = e.get("score")
        if sc not in (None, ""):
            lines.append(t("exam_bar_score", s=fmt_num(num(sc)), p=fmt_num(num(sc) * num(e.get("weight")) / 100, 1)))
        else:
            lines.append(t("exam_bar_none"))
        if e.get("target") not in (None, ""):
            lines.append(t("exam_bar_target", s=fmt_num(num(e["target"]))))
        if e.get("date"):
            lines.append(e["date"] + (f" {e['time']}" if e.get("time") else ""))
        return "\n".join(lines)

    def mouseMoveEvent(self, ev):
        i = self._at(ev.position())
        if i != self.hover:
            self.hover = i
            self.update()
            if i >= 0:
                QToolTip.showText(ev.globalPosition().toPoint(), self._tip(self.exams[i]), self)
            else:
                QToolTip.hideText()

    def leaveEvent(self, _e):
        self.hover = -1
        self.update()

    def mouseReleaseEvent(self, ev):
        i = self._at(ev.position())
        if i >= 0 and ev.button() == Qt.MouseButton.LeftButton:
            e = self.exams[i]
            QTimer.singleShot(0, lambda: self.on_click(e))


class GradesCard(Card):
    def __init__(self, store, win):
        super().__init__(t("grades_title"), t("grades_sub"))
        self.store, self.win = store, win
        self.editing = False
        self.pen = IconButton("edit", t("exams_edit_mode"), 32, 18, checkable=True)
        self.pen.toggled.connect(self._toggle_edit)
        self.head_widget(self.pen)
        self.more = IconButton("more_vert", "", 32, 18)
        self.more.clicked.connect(self._more)
        self.head_widget(self.more)

    def _toggle_edit(self, on):
        self.editing = on
        self.refresh()

    def _more(self):
        m = QMenu(self)
        m.addAction(t("finish_sem"), self._finish)
        m.exec(self.more.mapToGlobal(self.more.rect().bottomLeft()))

    def refresh(self):
        s = self.store
        self.clear()
        courses = sorted(s.all("courses"), key=lambda c: (c.get("name") or "").lower())
        tr = s.all("transcript")
        base_pts, base_akts = grades.totals(tr)
        res = {sc: grades.semester(courses, tr, sc) for sc in SHOWN}

        # --- gerçek ve hedef özeti
        strip = QWidget()
        h = QHBoxLayout(strip)
        h.setContentsMargins(0, 4, 0, 8)
        h.setSpacing(10)
        base = grades.gpa(base_pts, base_akts)
        goal = float(prefs.get("agno_goal") or 3.0)
        for sc in SHOWN:
            r = res[sc]
            if sc == "target":
                h.addWidget(self._goal_box(courses, tr, goal, res), 1)
                continue
            box = QWidget()
            box.setObjectName("CardToday")
            box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            v = QVBoxLayout(box)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(2)
            v.addWidget(_lbl(t("sc_" + sc), "StatLabel"))
            big = _lbl(_g(r["agno"]), "StatValue")
            v.addWidget(big)
            delta = ""
            if r["agno"] is not None and base is not None and r["n"]:
                d = r["agno"] - base
                delta = f"  ({'+' if d >= 0 else ''}{d:.2f})"
            v.addWidget(_lbl(f"{t('agno')}{delta} · {t('ano')} {_g(r['ano'])}" if r["n"] else
                             f"{t('agno')} · {t('no_letter_yet')}"))
            h.addWidget(box, 1)
        self.add(strip)
        if tr:
            self.add(_lbl(t("agno_base", v=_g(base), a=fmt_num(base_akts))))

        # --- ders tablosu
        if not courses:
            self.empty(t("no_courses"))
            return
        grid_w = QWidget()
        g = QGridLayout(grid_w)
        g.setContentsMargins(0, 8, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(4)
        heads = [t("col_course"), t("col_akts"), t("col_score"), t("sc_letter"), t("sc_target"), t("col_old")]
        for i, x in enumerate(heads):
            g.addWidget(_lbl(x, "StatLabel"), 0, i)
        for row, c in enumerate(courses, start=1):
            g.addWidget(self._course_cell(c), row, 0)
            g.addWidget(_lbl(fmt_num(num(c.get("credits"))) if c.get("credits") else "—"), row, 1)
            avg, w_done, _tavg = s.course_average(c["id"])
            hint = grades.suggest_letter(avg)
            sc_lbl = _lbl(f"{fmt_num(avg, 1)} · ~{hint}" if avg is not None else "—")
            sc_lbl.setToolTip(t("score_hint"))
            g.addWidget(sc_lbl, row, 2)
            for col, key, letters in ((3, "letter", grades.LETTERS + grades.EXTRA_LETTERS),
                                      (4, "target", grades.LETTERS)):
                cb = _Combo(c.get(key), letters, lambda v, cid=c["id"], k=key: self.store.update(
                    "courses", cid, **{k: v or None}))
                if key != "letter" and grades.point(c.get("letter")) is not None:
                    cb.setEnabled(False)          # kesinleşen not tahmin edilmez
                g.addWidget(cb, row, col)
            old = grades.match_retake(c, s.all("transcript"))
            g.addWidget(_lbl(f"{old.get('letter') or 'XX'}" if old else "—"), row, 5)
            if old:
                g.itemAtPosition(row, 5).widget().setToolTip(f"{old.get('term')} · {old.get('name')}")
        g.setColumnStretch(0, 1)
        self.add(grid_w)

    def _goal_box(self, courses, tr, goal, res):
        """Sabit AGNO hedefi (prefs agno_goal, tıkla = değiştir) ve ona ulaşmak için bu dönem gereken ortalama."""
        box = QWidget()
        box.setObjectName("CardToday")
        box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        box.setCursor(Qt.CursorShape.PointingHandCursor)
        box.setToolTip(t("goal_change"))
        box.mousePressEvent = lambda _e: QTimer.singleShot(0, self._set_goal)
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(2)
        v.addWidget(_lbl(t("goal_agno"), "StatLabel"))
        v.addWidget(_lbl(f"{goal:.2f}", "StatValue"))
        need = grades.needed_point(courses, tr, goal)
        if need is None:
            line = t("agno_goal_reached") if (res["letter"]["agno"] or 0) >= goal else "—"
            v.addWidget(_lbl(line))
        elif need > 4.0:
            v.addWidget(_lbl(t("goal_out"), "StatBad"))
        else:
            v.addWidget(_lbl(t("goal_need", v=_g(max(0.0, need)))))
        if res["target"]["n"]:
            v.addWidget(_lbl(t("goal_letters", a=_g(res["target"]["ano"]))))
        return box

    def _set_goal(self):
        cur = float(prefs.get("agno_goal") or 3.0)
        val, ok = QInputDialog.getDouble(self.win, t("goal_agno"), t("goal_q"), cur, 0.0, 4.0, 2)
        if ok:
            prefs.set("agno_goal", round(val, 2))
            self.refresh()

    def _course_cell(self, c):
        """Ders adı (tıkla = dersi düzenle), altında sınav çubuğu. Düzenleme kipinde (kalem) sınav çipleri ve +;
        ağırlıklar %100 etmiyorsa toplam uyarısı."""
        from ..components import FlowLayout
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 4, 0, 6)
        v.setSpacing(5)
        name = _lbl(c.get("name") or "—", "RowTitle")
        name.setCursor(Qt.CursorShape.PointingHandCursor)
        name.mousePressEvent = lambda e, c=c: edit_item(self.win, "courses", c)
        v.addWidget(name)
        exams = course_exams(self.store, c["id"])
        if exams:
            v.addWidget(ExamBar(exams, lambda e: edit_item(self.win, "exams", e)))
        total = sum(num(e.get("weight")) for e in exams)
        bad = exams and abs(total - 100) > 0.01
        if not self.editing:
            if bad:
                v.addWidget(_lbl(t("weights_total", w=fmt_num(total)), "StatBad"))
            return box
        chips = QWidget()
        fl = FlowLayout(chips, spacing=6)
        tr = is_tr()
        for e in exams:
            w = num(e.get("weight"))
            text = grades.exam_label(e.get("name"), tr) or t("exam")
            if w:
                text += f"  %{fmt_num(w)}"
            b = QPushButton(text.replace("&", "&&"))
            b.setObjectName("Chip")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("padding: 2px 9px; font-size: 11px;")
            b.clicked.connect(lambda _=False, e=e: edit_item(self.win, "exams", e))
            fl.addWidget(b)
        add = IconButton("add", t("add_exam"), 26, 16)
        add.clicked.connect(lambda _=False, cid=c["id"]: edit_item(self.win, "exams", preset={"course": cid}))
        fl.addWidget(add)
        if bad:
            fl.addWidget(_lbl(t("weights_total", w=fmt_num(total)), "StatBad"))
        v.addWidget(chips)
        return box

    def _finish(self):
        s = self.store
        if not any(grades.point(c.get("letter")) is not None for c in s.all("courses")):
            self.win.toast(t("finish_sem_none"))
            return
        terms = [term for term, _ in grades.by_term(s.all("transcript"))]
        default = terms[-1] if terms else "1.1"
        term, ok = QInputDialog.getText(self.win, t("finish_sem"), t("finish_sem_q"), text=default)
        if not ok or not term.strip():
            return
        added, changed = grades.finish_semester(s, term.strip())

        def undo():
            for a in added:
                s.delete("transcript", a["id"])
            for old in changed:
                s.update("transcript", old["id"], **{k: old.get(k) for k in ("letter", "old_letter", "credits")})
        self.win.toast(t("finish_sem_done", n=len(added) + len(changed)), t("undo"), undo)


class TranscriptCard(Card):
    def __init__(self, store, win):
        super().__init__(t("transcript"), add_tip=t("add_transcript"))
        self.store, self.win = store, win
        self.open_terms = set()
        self.add_clicked.connect(lambda: edit_item(win, "transcript"))
        b = QPushButton(t("import_xlsx"))
        b.setObjectName("Pill")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(self._import)
        self.head_widget(b)

    def refresh(self):
        s = self.store
        self.clear()
        tr = s.all("transcript")
        pts, akts = grades.totals(tr)
        tp, ta = grades.totals(tr, "target")
        self.set_sub(t("transcript_sub", n=len(tr), a=fmt_num(akts), v=_g(grades.gpa(pts, akts)),
                       g=_g(grades.gpa(tp, ta))) if tr else "")
        if not tr:
            self.empty(t("no_transcript"))
            return
        for term, rows in grades.by_term(tr):
            p, a = grades.totals(rows)
            opened = term in self.open_terms
            head = Row(grades.term_label(term), t("term_row", v=_g(grades.gpa(p, a)), a=fmt_num(a), n=len(rows)),
                       icon="chevron_right" if not opened else "arrow_down")
            head.clicked.connect(lambda term=term: self._toggle(term))
            self.add(head)
            if not opened:
                continue
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(28, 0, 0, 6)
            v.setSpacing(0)
            for e in rows:
                letter = (e.get("letter") or "XX").upper()
                badges = [(letter, grades.letter_kind(letter))]
                if e.get("target") and grades.point(e["target"]) is not None:
                    badges.insert(0, ("→ " + e["target"], None))
                sub = " · ".join(x for x in (e.get("code"), f"{fmt_num(num(e.get('credits')))} AKTS",
                                             e.get("lang"),
                                             f"{t('col_old')} {e['old_letter']}" if e.get("old_letter") else "") if x)
                r = Row(e.get("name") or "—", sub, badges=badges)
                bind_row(self.win, r, "transcript", e)
                v.addWidget(r)
            self.add(box)

    def _toggle(self, term):
        self.open_terms ^= {term}
        QTimer.singleShot(0, self.refresh)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self.win, t("import_xlsx"), "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            rows = grades.read_transcript_xlsx(path)
        except Exception:
            rows = []
        if not rows:
            self.win.toast(t("import_none"))
            return
        s = self.store
        old = list(s.all("transcript"))
        if old and QMessageBox.question(self.win, t("import_xlsx"), t("import_q", n=len(old))) \
                != QMessageBox.StandardButton.Yes:
            return
        removed = [s.delete("transcript", e["id"]) for e in old]
        added = [s.add("transcript", r) for r in rows]

        def undo():
            for a in added:
                s.delete("transcript", a["id"])
            for r in removed:
                s.restore(r)
        self.win.toast(t("imported", n=len(added)), t("undo"), undo)
