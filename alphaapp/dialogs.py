"""Seçenekler penceresi."""
import json
import os
import sys
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QScrollArea,
                             QWidget, QSpinBox, QFileDialog)

from .config import prefs, BASE_DIR, DATA_DIR
from .i18n import t
from .theme import theme, VARIANTS, variant_label, current_variant
from .widgets import ThemedDialog, ToggleSwitch, Divider


def _row(label, widget, sub=None):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 6, 0, 6)
    lay.setSpacing(16)
    box = QVBoxLayout()
    box.setSpacing(2)
    lbl = QLabel(label)
    lbl.setWordWrap(True)
    box.addWidget(lbl)
    if sub:
        s = QLabel(sub)
        s.setObjectName("Secondary")
        s.setWordWrap(True)
        box.addWidget(s)
    lay.addLayout(box, 1)
    if isinstance(widget, QWidget):
        lay.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
    else:
        lay.addLayout(widget)
    return w


def _combo(items, current):
    c = QComboBox()
    c.setMinimumWidth(180)
    for key, label in items:
        c.addItem(label, key)
    i = c.findData(current)
    c.setCurrentIndex(max(0, i))
    return c


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --widget'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.join(BASE_DIR, "main.py")}" --widget'


def set_autostart(on):
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "alpha", 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, "alpha")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


class PrefsDialog(ThemedDialog):
    def __init__(self, win):
        super().__init__(win, t("preferences"))
        self.win = win
        self.resize(600, 680)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(2)
        scroll.setWidget(page)
        outer.addWidget(scroll, 1)

        def section(title):
            if lay.count():
                lay.addSpacing(10)
                lay.addWidget(Divider())
                lay.addSpacing(6)
            l = QLabel(title)
            l.setObjectName("SubTitle")
            lay.addWidget(l)

        # --- Kişisel
        section(t("personal"))
        self.name = QLineEdit(prefs.get("name", ""))
        self.name.setFixedWidth(200)
        self.name.editingFinished.connect(lambda: prefs.set("name", self.name.text().strip()))
        lay.addWidget(_row(t("your_name"), self.name, t("your_name_sub")))
        cur = _combo([("₺", "₺  Türk lirası"), ("$", "$  Dolar"), ("€", "€  Euro"), ("£", "£  Sterlin")],
                     prefs.get("currency", "₺"))
        cur.currentIndexChanged.connect(lambda: prefs.set("currency", cur.currentData()))
        lay.addWidget(_row(t("currency"), cur))

        # --- Görünüm
        section(t("appearance"))
        self.c_theme = _combo([(v, variant_label(v)) for v in VARIANTS], current_variant())
        self.c_theme.currentIndexChanged.connect(lambda: theme.apply(self.c_theme.currentData()))
        lay.addWidget(_row(t("theme"), self.c_theme))
        c_lang = _combo([("tr", "Türkçe"), ("en", "English")], prefs.get("language", "tr"))
        c_lang.currentIndexChanged.connect(lambda: prefs.set("language", c_lang.currentData()))
        lay.addWidget(_row(t("language"), c_lang, t("language_sub")))

        # --- Bugün sayfası
        section(t("today_page"))
        sp = QSpinBox()
        sp.setRange(3, 90)
        sp.setSuffix(" " + t("days"))
        sp.setValue(int(prefs.get("deadline_days", 14)))
        sp.setFixedWidth(110)
        sp.valueChanged.connect(lambda v: prefs.set("deadline_days", int(v)))
        lay.addWidget(_row(t("deadline_days"), sp))
        sw = ToggleSwitch(prefs.get("morning_plan", True))
        sw.toggled.connect(lambda v: prefs.set("morning_plan", v))
        lay.addWidget(_row(t("pref_morning_plan"), sw, t("pref_morning_plan_sub")))
        sw = ToggleSwitch(prefs.get("show_sport_on_today", True))
        sw.toggled.connect(lambda v: prefs.set("show_sport_on_today", v))
        lay.addWidget(_row(t("show_sport"), sw))
        sw = ToggleSwitch(prefs.get("show_finance_on_today", True))
        sw.toggled.connect(lambda v: prefs.set("show_finance_on_today", v))
        lay.addWidget(_row(t("show_finance"), sw))

        # --- Beslenme hedefleri
        section(t("nutrition_goals"))
        for key, hi, step in (("kcal", 6000, 50), ("protein", 400, 5), ("carbs", 800, 5), ("fat", 300, 5)):
            sp = QSpinBox()
            sp.setRange(0, hi)
            sp.setSingleStep(step)
            sp.setValue(int(prefs.get("goal_" + key) or 0))
            sp.setFixedWidth(110)
            sp.valueChanged.connect(lambda v, k=key: prefs.set("goal_" + k, int(v)))
            lay.addWidget(_row(t("goal_" + key), sp))

        # --- Masaüstü widget'ı
        section(t("desk_section"))
        sw = ToggleSwitch(prefs.get("desk_widget", False))
        sw.toggled.connect(lambda v: win.set_desk(v))
        lay.addWidget(_row(t("desk_show"), sw, t("desk_show_sub")))
        dm = _combo([("bottom", t("desk_mode_bottom")), ("top", t("desk_mode_top"))], prefs.get("desk_mode", "bottom"))
        dm.setMinimumWidth(240)
        dm.currentIndexChanged.connect(lambda: self._desk_mode(dm.currentData()))
        lay.addWidget(_row(t("desk_mode"), dm))

        # --- Davranış
        section(t("behavior"))
        st = _combo([("today", t("nav_today")), ("last", t("start_last"))], prefs.get("start_page", "today"))
        st.currentIndexChanged.connect(lambda: prefs.set("start_page", st.currentData()))
        lay.addWidget(_row(t("start_page"), st))
        sw = ToggleSwitch(prefs.get("autostart", False))
        sw.toggled.connect(self._autostart)
        lay.addWidget(_row(t("autostart"), sw, t("autostart_sub") + " " + t("desk_autostart_note")))

        # --- Veriler
        section(t("data"))
        sub = QLabel(t("data_sub"))
        sub.setObjectName("Secondary")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        bx = QHBoxLayout()
        b1 = QPushButton(t("open_folder"))
        b1.setObjectName("Pill")
        b1.clicked.connect(lambda: os.startfile(DATA_DIR))
        b2 = QPushButton(t("export_json"))
        b2.setObjectName("Pill")
        b2.clicked.connect(self._export)
        bx.addWidget(b1)
        bx.addWidget(b2)
        bx.addStretch(1)
        lay.addSpacing(6)
        lay.addLayout(bx)
        path = QLabel(DATA_DIR)
        path.setObjectName("Secondary")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(path)

        section(t("shortcuts"))
        sc = QLabel(t("shortcuts_text"))
        sc.setObjectName("Secondary")
        sc.setWordWrap(True)
        lay.addWidget(sc)

        # --- Hakkında
        from . import __version__, __author__, REPO_URL
        section(t("about"))
        ab = QLabel(t("about_text", v=__version__, a=__author__, u=REPO_URL))
        ab.setObjectName("Secondary")
        ab.setWordWrap(True)
        ab.setOpenExternalLinks(True)
        lay.addWidget(ab)
        lay.addStretch(1)

        foot = QHBoxLayout()
        foot.setContentsMargins(20, 10, 20, 16)
        foot.addStretch(1)
        ok = QPushButton(t("done"))
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        foot.addWidget(ok)
        outer.addLayout(foot)

    def accept(self):
        prefs.set("name", self.name.text().strip())
        super().accept()

    def _desk_mode(self, m):
        prefs.set("desk_mode", m)
        if self.win.desk is not None:
            self.win.desk.set_mode(m)

    def _autostart(self, on):
        if set_autostart(on):
            prefs.set("autostart", on)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, t("export_json"),
                                              os.path.join(os.path.expanduser("~"), "Documents",
                                                           f"alpha-{date.today():%Y-%m-%d}.json"), "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.win.store.snapshot(), f, ensure_ascii=False, indent=1)
            self.win.toast(t("exported", p=os.path.basename(path)))
