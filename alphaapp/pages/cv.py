"""Hedefler > CV: solda şu anki CV, sağda hayalimdeki CV — ikisi de gerçek bir CV sayfası gibi (CvSheet).

cv koleksiyonu: side ("now" | "dream"), section (profile | SECTIONS), title, org, when, detail (satır satır →
madde işaretleri), note, done (hayaldeki madde gerçekleşti), goal (hayalden açılan hedefin id'si), now_id.
section "profile" = sayfanın başı: title = ad soyad, org = bilgi satırı (yaş · ehliyet · şehir),
detail = iletişim satırı, note = Hakkımda. Fotoğraf DATA_DIR\\cv\\ altında (prefs cv_photo), iki sayfada da aynı.
Hayaldeki sayfada şu anki maddeler soluk görünür; aynı bölümde aynı kurumda hayaldeki bir madde varsa gizlenir
(ör. "4. sınıf 2.70" yerine "mezun 3.00"). Şu anki CV'nin PDF'i DATA_DIR\\cv\\ altına kopyalanır (prefs cv_file).
Telefon sayfasına GİTMEZ.
"""
import os
import shutil

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QFrame, QPushButton,
                             QSizePolicy)

from ..components import Card, ResponsiveRow, FlowLayout
from ..config import prefs, DATA_DIR
from ..forms import edit_item, item_menu
from ..i18n import t
from ..theme import theme, color
from ..widgets import IconButton

SECTIONS = ("education", "experience", "projects", "publications", "volunteer", "skills", "languages", "certs",
            "courses", "awards")
ALL_SECTIONS = ("profile",) + SECTIONS
CV_DIR = os.path.join(DATA_DIR, "cv")


def section_name(k):
    return t("cv_s_" + k)


def progress(store):
    """(gerçekleşen, toplam) hayaldeki maddeler (üst bilgi sayılmaz)."""
    dream = [x for x in store.all("cv") if x.get("side") == "dream" and x.get("section") != "profile"]
    return sum(1 for x in dream if x.get("done")), len(dream)


def realize(store, item):
    """Hayaldeki madde gerçekleşti: şu anki CV'ye kopyası eklenir, hayaldeki işaretlenir."""
    new = store.add("cv", {k: item.get(k) for k in ("section", "title", "org", "when", "detail", "note")
                           if item.get(k)} | {"side": "now"})
    store.update("cv", item["id"], done=True, now_id=new["id"])
    return new


def to_goal(store, item, horizon="y3", due=None):
    """Hayaldeki maddeden hedef açar (kariyer / eğitim alanında)."""
    area = "education" if item.get("section") in ("education", "languages", "certs", "courses",
                                                  "publications") else "career"
    title = item.get("title") or ""
    if item.get("org") and item.get("section") in ("experience", "education", "certs"):
        title = f"{item['org']} — {title}"
    g = {"title": title, "area": area, "horizon": horizon,
         "note": " · ".join(x for x in (item.get("org"), item.get("when"), item.get("detail")) if x)}
    if due:
        g["due"] = due
    g = store.add("goals", g)
    store.update("cv", item["id"], goal=g["id"])
    return g


def attach_pdf(path):
    os.makedirs(CV_DIR, exist_ok=True)
    name = "cv" + (os.path.splitext(path)[1].lower() or ".pdf")
    shutil.copy2(path, os.path.join(CV_DIR, name))
    prefs.set("cv_file", name)
    return name


def pdf_path():
    n = prefs.get("cv_file")
    p = os.path.join(CV_DIR, n) if n else None
    return p if p and os.path.exists(p) else None


def set_photo(path):
    os.makedirs(CV_DIR, exist_ok=True)
    name = "photo" + (os.path.splitext(path)[1].lower() or ".jpg")
    shutil.copy2(path, os.path.join(CV_DIR, name))
    prefs.set("cv_photo", name)
    return name


def photo_path():
    n = prefs.get("cv_photo")
    p = os.path.join(CV_DIR, n) if n else None
    return p if p and os.path.exists(p) else None


def _photo_pixmap(w, h):
    p = photo_path()
    img = QPixmap(p) if p else QPixmap()
    dpr = 2
    pm = QPixmap(w * dpr, h * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    if img.isNull():
        return None
    qp = QPainter(pm)
    qp.setRenderHint(QPainter.RenderHint.Antialiasing)
    qp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
    qp.setClipPath(clip)
    sc = img.scaled(w * dpr, h * dpr, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
    sc.setDevicePixelRatio(dpr)
    qp.drawPixmap(int((w - sc.width() / dpr) / 2), int((h - sc.height() / dpr) / 2), sc)
    qp.end()
    return pm


# ============================================================ sayfa parçaları
class Clickable(QFrame):
    """Tıkla = düzenle, sağ tık = menü; üzerine gelince hafif vurgu."""
    clicked = pyqtSignal()
    menu_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CvEntry")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.menu_requested.emit(e.globalPos())


def _lbl(text, name, wrap=False, sel=False):
    lb = QLabel(text)
    lb.setObjectName(name)
    lb.setWordWrap(wrap)
    if wrap:
        lb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    lb.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    return lb


class CvSheet(QFrame):
    """Bir CV sayfası: üst bilgi (fotoğraf, ad, bilgi, iletişim), Hakkımda, bölümler (başlık + çizgi + maddeler)."""

    def __init__(self, view, side):
        super().__init__()
        self.view, self.side = view, side
        self.setObjectName("CvSheet")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(34, 30, 34, 30)
        self.v.setSpacing(4)

    def build(self, items, now_items):
        lay = self.v
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        dream = self.side == "dream"
        prof = next((x for x in items if x.get("section") == "profile"), None)
        if prof is None and dream:
            prof = next((x for x in now_items if x.get("section") == "profile"), None)
        lay.addWidget(self._header(prof))
        about = (prof or {}).get("note")
        if about:
            lay.addWidget(self._sec_head(t("cv_about")))
            lay.addWidget(_lbl(about, "CvText", wrap=True))
        for sec in SECTIONS:
            mine = [x for x in items if (x.get("section") or "experience") == sec]
            ghosts = []
            if dream:
                orgs = {(x.get("org") or "").strip().lower() for x in mine if x.get("org")}
                realized = {x.get("now_id") for x in mine if x.get("now_id")}
                ghosts = [x for x in now_items if (x.get("section") or "experience") == sec and
                          x["id"] not in realized and not x.get("hide_dream") and
                          not ((x.get("org") or "").strip().lower() in orgs and x.get("org"))]
            if not mine and not ghosts:
                continue
            lay.addWidget(self._sec_head(section_name(sec), sec))
            rows = [(x, False) for x in mine] + [(x, True) for x in ghosts]
            rows.sort(key=lambda r: (r[0].get("order") or 0, -_year(r[0].get("when"))))
            for x, ghost in rows:
                lay.addWidget(self._entry(x, ghost))
        lay.addSpacing(10)
        lay.addWidget(self.view._add_bar(self.side, {x.get("section") for x in items}))

    # ---------------------------------------------------------------- üst bilgi
    def _header(self, prof):
        box = Clickable()
        h = QHBoxLayout(box)
        h.setContentsMargins(6, 6, 6, 10)
        h.setSpacing(18)
        ph = QLabel()
        ph.setObjectName("CvPhoto")
        pm = _photo_pixmap(84, 100)
        ph.setFixedSize(84, 100)
        if pm is not None:
            ph.setPixmap(pm)
        else:
            ph.setText(t("cv_photo_add"))
            ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ph.setWordWrap(True)
        h.addWidget(ph, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        p = prof or {}
        col.addWidget(_lbl(p.get("title") or t("cv_name_ph"), "CvName"))
        if p.get("org"):
            col.addWidget(_lbl(p["org"], "CvInfo", wrap=True))
        if p.get("detail"):
            col.addWidget(_lbl(p["detail"].replace("\n", "  ·  ").replace("-", "‑"), "CvMuted", wrap=True))
        col.addStretch(1)
        h.addLayout(col, 1)
        if prof and prof.get("side") == self.side:
            box.clicked.connect(lambda: edit_item(self.view.win, "cv", prof))
            box.menu_requested.connect(lambda pos: self.view._profile_menu(prof, pos))
        else:
            box.clicked.connect(lambda: self.view._add(self.side, "profile", prof))
            box.menu_requested.connect(lambda pos: self.view._profile_menu(None, pos))
        return box

    def _sec_head(self, text, sec=None):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 14, 0, 4)
        v.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(4)
        row.addWidget(_lbl(text.upper(), "CvSection"))
        row.addStretch(1)
        if sec:
            b = IconButton("add", t("cv_add_in", s=section_name(sec)), 22, 14)
            b.clicked.connect(lambda: self.view._add(self.side, sec))
            row.addWidget(b)
        v.addLayout(row)
        line = QFrame()
        line.setObjectName("CvRule")
        line.setFixedHeight(2)
        v.addWidget(line)
        return w

    def _entry(self, x, ghost):
        box = Clickable()
        box.setProperty("ghost", ghost)
        v = QVBoxLayout(box)
        v.setContentsMargins(6, 5, 6, 5)
        v.setSpacing(1)
        top = QHBoxLayout()
        top.setSpacing(8)
        title = x.get("title") or "—"
        if x.get("section") in ("languages", "skills") and x.get("detail") and "\n" not in x["detail"]:
            title += ": " + x["detail"]
        tl = _lbl(title, "CvGhostTitle" if ghost else "CvTitle", wrap=True)
        top.addWidget(tl, 1)
        if not ghost and self.side == "dream":
            if x.get("done"):
                top.addWidget(_lbl("✓ " + t("cv_done"), "CvBadgeGood"))
            elif x.get("goal") and self.view.store.get("goals", x["goal"]):
                top.addWidget(_lbl(t("cv_is_goal"), "CvBadge"))
        if x.get("when"):
            top.addWidget(_lbl(x["when"], "CvMuted"), 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(top)
        if x.get("org"):
            v.addWidget(_lbl(x["org"], "CvOrg", wrap=True))
        det = "" if ghost else (x.get("detail") or "")    # soluk (şu anki) maddeler kısa: ayrıntısız
        if det and not (x.get("section") in ("languages", "skills") and "\n" not in det):
            lines = [ln.strip() for ln in det.split("\n") if ln.strip()]
            for ln in lines:
                txt = ("•  " + ln) if len(lines) > 1 or len(ln) < 160 else ln
                v.addWidget(_lbl(txt, "CvGhostText" if ghost else "CvText", wrap=True))
        if ghost:
            box.setToolTip(t("cv_ghost_tip"))
            box.clicked.connect(lambda: edit_item(self.view.win, "cv", x))
            box.menu_requested.connect(lambda pos: item_menu(self.view.win, "cv", x, pos, self.view._extra(x)))
        else:
            box.clicked.connect(lambda: edit_item(self.view.win, "cv", x))
            box.menu_requested.connect(lambda pos: item_menu(self.view.win, "cv", x, pos, self.view._extra(x)))
        return box


def _year(s):
    """"2021 – Günümüz" → 9999 (devam eden en üstte), "Haziran 2024 – Eylül 2024" → 2024."""
    s = str(s or "")
    if "günümüz" in s.lower() or "present" in s.lower() or "now" in s.lower():
        return 9999
    ys = [int(w) for w in s.replace("–", " ").replace("-", " ").split() if w.isdigit() and len(w) == 4]
    return max(ys) if ys else 0


# ============================================================ görünüm
class CvView(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win, self.store = win, win.store
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        self.summary = QLabel("")
        self.summary.setObjectName("RowSub")
        self.summary.setWordWrap(True)
        v.addWidget(self.summary)
        self.c_now = Card(t("cv_now"), t("cv_now_sub"), add_tip=t("new_cv"))
        self.c_now.add_clicked.connect(lambda: self._add("now"))
        self.b_pdf = IconButton("open_in", t("cv_pdf_open"), 32, 20)
        self.b_pdf.clicked.connect(self._open_pdf)
        self.c_now.head_widget(self.b_pdf)
        b = IconButton("folder_open", t("cv_pdf_attach"), 32, 20)
        b.clicked.connect(self._attach)
        self.c_now.head_widget(b)
        self.c_dream = Card(t("cv_dream"), t("cv_dream_sub"), add_tip=t("new_cv"))
        self.c_dream.add_clicked.connect(lambda: self._add("dream"))
        self.s_now, self.s_dream = CvSheet(self, "now"), CvSheet(self, "dream")
        self.c_now.layout().addWidget(self.s_now)
        self.c_dream.layout().addWidget(self.s_dream)
        row = ResponsiveRow(1000)
        row.add(self.c_now, 1)
        row.add(self.c_dream, 1)
        v.addWidget(row)
        theme.bind(self, lambda w: w._style())

    def _style(self):
        c = color
        self.setStyleSheet(f"""
            #CvSheet {{ background: {c('bg')}; border: 1px solid {c('divider')}; border-radius: 6px; }}
            #CvEntry {{ background: transparent; border-radius: 6px; }}
            #CvEntry:hover {{ background: {c('hover')}; }}
            #CvName {{ font-size: 22px; font-weight: 700; color: {c('text')}; }}
            #CvInfo {{ font-size: 13px; color: {c('text')}; }}
            #CvMuted {{ font-size: 12px; color: {c('text2')}; }}
            #CvSection {{ font-size: 12px; font-weight: 700; letter-spacing: 1.5px; color: {c('text')}; }}
            #CvRule {{ background: {c('text3')}; border: none; }}
            #CvTitle {{ font-size: 13px; font-weight: 700; color: {c('text')}; }}
            #CvOrg {{ font-size: 12px; font-style: italic; color: {c('text2')}; }}
            #CvText {{ font-size: 12px; color: {c('text2')}; }}
            #CvGhostTitle {{ font-size: 13px; font-weight: 600; color: {c('text3')}; }}
            #CvGhostText {{ font-size: 12px; color: {c('text3')}; }}
            #CvBadge {{ font-size: 11px; color: {c('text2')}; border: 1px solid {c('divider')}; border-radius: 8px;
                        padding: 0px 6px; }}
            #CvBadgeGood {{ font-size: 11px; color: #4f9d74; border: 1px solid #4f9d74; border-radius: 8px;
                            padding: 0px 6px; }}
            #CvPhoto {{ background: {c('surface')}; border-radius: 8px; color: {c('text3')}; font-size: 11px; }}
        """)

    def _extra(self, x):
        out = []
        if x.get("side") == "now":
            hid = bool(x.get("hide_dream"))
            out.append((t("cv_show_dream" if hid else "cv_hide_dream"),
                        lambda: self.store.update("cv", x["id"], hide_dream=not hid)))
        if x.get("side") == "dream" and not x.get("done"):
            out.append((t("cv_realize"), lambda: (realize(self.store, x), self.win.toast(t("cv_realized")))))
            if not (x.get("goal") and self.store.get("goals", x["goal"])):
                out.append((t("cv_to_goal"), lambda: (to_goal(self.store, x), self.win.toast(t("cv_goal_made")))))
        return out

    def _profile_menu(self, prof, pos):
        extra = [(t("cv_photo_pick"), self._pick_photo)]
        if prof:
            item_menu(self.win, "cv", prof, pos, extra)
        else:
            from PyQt6.QtWidgets import QMenu
            m = QMenu(self.win)
            m.addAction(t("cv_photo_pick"), self._pick_photo)
            m.exec(pos)

    def _pick_photo(self):
        path, _ = QFileDialog.getOpenFileName(self.win, t("cv_photo_pick"), "", "* (*.jpg *.jpeg *.png *.webp)")
        if path:
            set_photo(path)
            self.refresh()

    def _add(self, side, section=None, copy_from=None):
        pr = {"side": side, "section": section or "experience"}
        if copy_from:
            pr.update({k: copy_from.get(k) for k in ("title", "org", "detail", "note") if copy_from.get(k)})
        edit_item(self.win, "cv", preset=pr)

    def _attach(self):
        path, _ = QFileDialog.getOpenFileName(self.win, t("cv_pdf_attach"), "",
                                              "CV (*.pdf *.docx *.doc);;* (*.*)")
        if path:
            attach_pdf(path)
            self.win.toast(t("cv_pdf_saved"))
            self.refresh()

    def _open_pdf(self):
        p = pdf_path()
        if p:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))

    def refresh(self):
        items = self.store.all("cv")
        done, total = progress(self.store)
        self.summary.setText(t("cv_progress", d=done, n=total) if total else t("cv_hint"))
        self.b_pdf.setVisible(pdf_path() is not None)
        self.c_now.set_sub(t("cv_now_sub_pdf") if pdf_path() else t("cv_now_sub"))
        now = [x for x in items if x.get("side") == "now"]
        dream = [x for x in items if x.get("side") == "dream"]
        self.s_now.build(now, [])
        self.s_dream.build(dream, now)

    def _add_bar(self, side, used):
        """Henüz boş bölümler: tek tıkla o bölüme ekle."""
        free = [s for s in ALL_SECTIONS if s not in used]
        w = QWidget()
        if not free:
            w.hide()
            return w
        fl = FlowLayout(w, 6)
        fl.setContentsMargins(0, 4, 0, 0)
        for s in free:
            b = QPushButton("+ " + section_name(s))
            b.setObjectName("Chip")
            b.setStyleSheet("min-width: 0px; padding: 2px 10px;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, s=s: self._add(side, s))
            fl.addWidget(b)
        return w
