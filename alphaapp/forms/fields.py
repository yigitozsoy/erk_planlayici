"""Form alan bileşenleri: tarih / saat, kategori, bağlantı, görsel, gün seçiciler; sayı biçimleri."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget, QMenu, QButtonGroup

from ..config import day_today
from ..components import button
from ..i18n import t, WEEKDAYS_SHORT
from ..store import parse_date, num
from ..theme import theme
from ..widgets import ToggleSwitch


# ============================================================ alan bileşenleri
class OptDate(QWidget):
    def __init__(self, value, optional, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.sw = None
        if optional:
            self.sw = ToggleSwitch(bool(value))
            self.sw.toggled.connect(self._sync)
            lay.addWidget(self.sw)
        from ..pickers import DateButton
        self.ed = DateButton(parse_date(value) or day_today())
        if self.sw is not None:
            self.ed.picked.connect(lambda: self.sw.setChecked(True))
        lay.addWidget(self.ed, 1)
        self._sync()

    def _sync(self, *_):
        self.ed.set_off(self.sw is not None and not self.sw.isChecked())

    def value(self):
        if self.sw is not None and not self.sw.isChecked():
            return None
        return self.ed.value().isoformat()


class OptTime(QWidget):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.sw = ToggleSwitch(bool(value))
        self.sw.toggled.connect(lambda v: self.ed.set_off(not v))
        lay.addWidget(self.sw)
        from ..pickers import TimeButton
        self.ed = TimeButton(value or "09:00")
        self.ed.set_off(not value)
        self.ed.picked.connect(lambda: self.sw.setChecked(True))
        lay.addWidget(self.ed, 1)

    def value(self):
        return self.ed.value() if self.sw.isChecked() else None


CAT_ICONS = {"sport": "cat_sport", "work": "cat_work", "education": "cat_education", "social": "group",
             "finance": "wallet", "personal": "person"}
CAT_ORDER = ("sport", "work", "education", "social", "finance", "personal")
# hayat alanları (hedefler, çark): store.LIFE_AREAS sırasıyla
AREA_ICONS = {"education": "cat_education", "career": "work_bag", "venture": "lightbulb", "body": "cat_sport",
              "mind": "spa", "finance": "wallet", "growth": "star"}


class CategoryPicker(QWidget):
    """Kategori: tek tıkla seçilen ikon düğmeleri (spor, iş, eğitim, sosyal, ekonomi, kişisel).
    areas=True → hayat alanları (eğitim, kariyer, iş, beden, zihin, ekonomi, kişisel gelişim)."""

    def __init__(self, value, parent=None, areas=False):
        super().__init__(parent)
        from ..store import LIFE_AREAS, life_area
        order, ic, self.prefix, self.default = ((LIFE_AREAS, AREA_ICONS, "area_", "growth") if areas else
                                                (CAT_ORDER, CAT_ICONS, "cat_", "personal"))
        if areas:
            value = life_area(value)
        else:   # Menüyü düzenle'den eklenen kategoriler de seçilebilsin
            from ..navmenu import custom_cats
            extra = custom_cats()
            order = tuple(order) + tuple(c["id"] for c in extra)
            ic = dict(ic, **{c["id"]: c.get("icon") or "star" for c in extra})
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.btns = {}
        for c in order:
            b = QPushButton()
            b.setObjectName("CatChip")
            b.setCheckable(True)
            b.setFixedSize(40, 36)
            b.setToolTip(t(self.prefix + c))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            theme.icon(b, ic[c], "text", 20)
            self.group.addButton(b)
            self.btns[c] = b
            lay.addWidget(b)
            b.toggled.connect(self._label)
        self.lbl = QLabel("")
        self.lbl.setObjectName("Secondary")
        lay.addSpacing(4)
        lay.addWidget(self.lbl)
        lay.addStretch(1)
        self.btns.get(value if value in self.btns else self.default).setChecked(True)
        self._label()

    def _label(self, *_):
        self.lbl.setText(t(self.prefix + self.value()))

    def value(self):
        for c, b in self.btns.items():
            if b.isChecked():
                return c
        return self.default


class LinksPicker(QPushButton):
    """Hedefe bağlı alışkanlık / ders / projeler: tıkla → işaretlenebilir menü. Değer: ["habits:id", ...]."""

    def __init__(self, store, value, parent=None):
        super().__init__(parent)
        self.store = store
        self.links = [x for x in (value or []) if store.link_item(x)[1] is not None]
        self.setObjectName("Pill")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._menu)
        self._label()

    def _label(self):
        names = [(self.store.link_item(x)[1] or {}).get("name") or "—" for x in self.links]
        txt = ", ".join(names[:3]) + (f" +{len(names) - 3}" if len(names) > 3 else "") if names else t("links_none")
        self.setText(txt.replace("&", "&&"))
        self.setToolTip("\n".join(names))

    def _menu(self):
        m = QMenu(self)
        any_item = False
        for coll, key in (("habits", "nav_habits"), ("courses", "courses"), ("projects", "projects")):
            items = sorted(self.store.all(coll), key=lambda x: (x.get("name") or "").lower())
            if not items:
                continue
            any_item = True
            m.addSection(t(key))
            for x in items:
                ln = f"{coll}:{x['id']}"
                a = QAction(x.get("name") or "—", m)
                a.setCheckable(True)
                a.setChecked(ln in self.links)
                a.toggled.connect(lambda on, ln=ln: self._toggle(ln, on))
                m.addAction(a)
        if not any_item:
            a = QAction(t("links_empty"), m)
            a.setEnabled(False)
            m.addAction(a)
        m.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _toggle(self, ln, on):
        if on and ln not in self.links:
            self.links.append(ln)
        elif not on and ln in self.links:
            self.links.remove(ln)
        self._label()

    def value(self):
        return list(self.links)


class ImagePicker(QWidget):
    """Hedef görseli: dosya seç → DATA_DIR\\images'a kopyalanır, değer dosya adıdır."""

    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.val = value or None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.btn = QPushButton()
        self.btn.setObjectName("Pill")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._pick)
        lay.addWidget(self.btn)
        self.clear_btn = button(t("clear_image"), kind="Flat")
        self.clear_btn.setStyleSheet("min-width: 0px;")
        self.clear_btn.clicked.connect(self._clear)
        lay.addWidget(self.clear_btn)
        lay.addStretch(1)
        self._label()

    def _label(self):
        self.btn.setText(t("change_image") if self.val else t("pick_image"))
        self.clear_btn.setVisible(bool(self.val))

    def _pick(self):
        import os
        import shutil
        import uuid
        from PyQt6.QtWidgets import QFileDialog
        from ..config import IMAGES_DIR
        path, _ = QFileDialog.getOpenFileName(self, t("pick_image"), "",
                                              "Görseller (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if not path:
            return
        os.makedirs(IMAGES_DIR, exist_ok=True)
        name = uuid.uuid4().hex[:12] + os.path.splitext(path)[1].lower()
        try:
            shutil.copy2(path, os.path.join(IMAGES_DIR, name))
        except OSError:
            return
        self.val = name
        self._label()

    def _clear(self):
        self.val = None
        self._label()

    def value(self):
        return self.val


class DaysPicker(QWidget):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.btns = []
        sel = set(value or [])
        for i, name in enumerate(WEEKDAYS_SHORT()):
            b = QPushButton(name)
            b.setObjectName("Chip")
            b.setCheckable(True)
            b.setChecked(i in sel)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(b)
            self.btns.append(b)
        lay.addStretch(1)

    def value(self):
        return [i for i, b in enumerate(self.btns) if b.isChecked()]


def _fmt_num(v):
    if v in (None, ""):
        return ""
    f = num(v)
    s = f"{f:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _parse_num(s):
    s = (s or "").strip().replace(" ", "")
    if not s:
        return None
    # 12.345,67 → 12345.67 · 12,5 → 12.5 · 12.5 → 12.5
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
