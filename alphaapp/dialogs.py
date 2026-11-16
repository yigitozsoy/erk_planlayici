"""Seçenekler penceresi."""
import json
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QScrollArea,
                             QWidget, QSpinBox, QFileDialog, QSlider, QStackedWidget, QButtonGroup, QFrame)

from .config import day_today
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
    """Seçenekler: solda kategoriler (YouTube ayarları gibi), sağda seçilen kategorinin sayfası."""
    CATS = (("pcat_general", "settings"), ("pcat_today", "today"), ("rem_section", "clock"),
            ("pcat_sport_food", "cat_sport"), ("desk_section", "widgets"), ("pcat_phone", "phone"),
            ("data", "folder_open"), ("about", "info"))

    def __init__(self, win, start=None):
        super().__init__(win, t("preferences"))
        self.win = win
        self.resize(860, 640)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)
        navw = QWidget()
        navw.setObjectName("Nav")
        navw.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        navw.setFixedWidth(232)
        nav = QVBoxLayout(navw)
        nav.setContentsMargins(12, 16, 12, 12)
        nav.setSpacing(2)
        body.addWidget(navw)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.cat_keys = []
        lay = None
        first = True

        def category(key):
            """Yeni kategori sayfası; sonraki satırlar bu sayfaya eklenir."""
            nonlocal lay, first
            if lay is not None:
                lay.addStretch(1)
            icon = dict(self.CATS)[key]
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            page = QWidget()
            lay = QVBoxLayout(page)
            lay.setContentsMargins(28, 18, 28, 20)
            lay.setSpacing(2)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)
            h = QLabel(t(key))
            h.setObjectName("PageTitle")
            lay.addWidget(h)
            lay.addSpacing(8)
            first = True
            b = QPushButton("   " + t(key))
            b.setObjectName("NavItem")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setFixedHeight(40)
            theme.icon(b, icon, "text", 22)
            i = self.stack.count() - 1
            b.clicked.connect(lambda _=False, i=i: self.stack.setCurrentIndex(i))
            self.group.addButton(b, i)
            nav.addWidget(b)
            self.cat_keys.append(key)

        def section(title):
            nonlocal first
            if not first:
                lay.addSpacing(10)
                lay.addWidget(Divider())
                lay.addSpacing(6)
            first = False
            l = QLabel(title)
            l.setObjectName("SubTitle")
            lay.addWidget(l)

        def note(text):
            s = QLabel(text)
            s.setObjectName("Secondary")
            s.setWordWrap(True)
            lay.addWidget(s)
            return s

        # ============================================================ Genel
        category("pcat_general")
        section(t("personal"))
        self.name = QLineEdit(prefs.get("name", ""))
        self.name.setFixedWidth(200)
        self.name.editingFinished.connect(lambda: prefs.set("name", self.name.text().strip()))
        lay.addWidget(_row(t("your_name"), self.name, t("your_name_sub")))
        cur = _combo([("₺", "₺  Türk lirası"), ("$", "$  Dolar"), ("€", "€  Euro"), ("£", "£  Sterlin")],
                     prefs.get("currency", "₺"))
        cur.currentIndexChanged.connect(lambda: prefs.set("currency", cur.currentData()))
        lay.addWidget(_row(t("currency"), cur))

        section(t("appearance"))
        self.c_theme = _combo([(v, variant_label(v)) for v in VARIANTS], current_variant())
        self.c_theme.currentIndexChanged.connect(lambda: theme.apply(self.c_theme.currentData()))
        lay.addWidget(_row(t("theme"), self.c_theme))
        c_lang = _combo([("tr", "Türkçe"), ("en", "English")], prefs.get("language", "tr"))
        c_lang.currentIndexChanged.connect(lambda: prefs.set("language", c_lang.currentData()))
        lay.addWidget(_row(t("language"), c_lang, t("language_sub")))

        section(t("behavior"))
        st = _combo([("today", t("nav_today")), ("last", t("start_last"))], prefs.get("start_page", "today"))
        st.currentIndexChanged.connect(lambda: prefs.set("start_page", st.currentData()))
        lay.addWidget(_row(t("start_page"), st))
        sw = ToggleSwitch(prefs.get("autostart", False))
        sw.toggled.connect(self._autostart)
        lay.addWidget(_row(t("autostart"), sw, t("autostart_sub") + ". " + t("desk_autostart_note")))

        # ============================================================ Bugün ve program
        category("pcat_today")
        section(t("today_page"))
        sp = QSpinBox()
        sp.setRange(3, 90)
        sp.setSuffix(" " + t("days"))
        sp.setValue(int(prefs.get("deadline_days", 14)))
        sp.setFixedWidth(110)
        sp.valueChanged.connect(lambda v: prefs.set("deadline_days", int(v)))
        lay.addWidget(_row(t("deadline_days"), sp))
        de = _combo([(h, t("day_end_midnight") if h == 0 else f"{h:02d}:00") for h in (0, 1, 2, 3, 4, 5, 6)],
                    int(prefs.get("day_end_hour", 4) or 0))
        de.setMinimumWidth(140)
        de.currentIndexChanged.connect(lambda: prefs.set("day_end_hour", int(de.currentData())))
        lay.addWidget(_row(t("day_end"), de, t("day_end_sub")))
        sw = ToggleSwitch(prefs.get("morning_plan", True))
        sw.toggled.connect(lambda v: prefs.set("morning_plan", v))
        lay.addWidget(_row(t("pref_morning_plan"), sw, t("pref_morning_plan_sub")))
        sw = ToggleSwitch(prefs.get("show_sport_on_today", True))
        sw.toggled.connect(lambda v: prefs.set("show_sport_on_today", v))
        lay.addWidget(_row(t("show_sport"), sw))
        sw = ToggleSwitch(prefs.get("show_finance_on_today", True))
        sw.toggled.connect(lambda v: prefs.set("show_finance_on_today", v))
        lay.addWidget(_row(t("show_finance"), sw))

        section(t("schedule_section"))
        sw = ToggleSwitch(prefs.get("show_place", True))
        sw.toggled.connect(lambda v: prefs.set("show_place", v))
        lay.addWidget(_row(t("pref_show_place"), sw, t("pref_show_place_sub")))
        sw = ToggleSwitch(prefs.get("habits_in_schedule", False))
        sw.toggled.connect(lambda v: prefs.set("habits_in_schedule", v))
        lay.addWidget(_row(t("pref_habits_sched"), sw, t("pref_habits_sched_sub")))

        # ============================================================ Hatırlatıcılar
        from .sounds import SOUNDS
        category("rem_section")
        sw = ToggleSwitch(prefs.get("reminders_on", True))
        sw.toggled.connect(lambda v: prefs.set("reminders_on", v))
        lay.addWidget(_row(t("rem_on"), sw, t("rem_on_sub")))
        sp = QSpinBox()
        sp.setRange(0, 180)
        sp.setSingleStep(5)
        sp.setSuffix(" " + t("dur_m", m="").strip())
        sp.setValue(int(prefs.get("reminder_lead", 10)))
        sp.setFixedWidth(110)
        sp.valueChanged.connect(lambda v: prefs.set("reminder_lead", int(v)))
        lay.addWidget(_row(t("rem_lead"), sp))
        snd = _combo([(k, t("snd_" + k)) for k in SOUNDS], prefs.get("reminder_sound", "chime"))
        snd.currentIndexChanged.connect(lambda: (prefs.set("reminder_sound", snd.currentData()), self._try_sound()))
        b_try = QPushButton(t("rem_try"))
        b_try.setObjectName("Pill")
        b_try.clicked.connect(lambda: win.reminders.test())
        box = QHBoxLayout()
        box.setSpacing(8)
        box.addWidget(snd)
        box.addWidget(b_try)
        lay.addWidget(_row(t("rem_sound"), box))
        vol = QSlider(Qt.Orientation.Horizontal)
        vol.setRange(5, 100)
        vol.setFixedWidth(180)
        vol.setValue(int(prefs.get("reminder_volume", 70)))
        vol.valueChanged.connect(lambda v: prefs.set("reminder_volume", int(v)))
        vol.sliderReleased.connect(self._try_sound)
        lay.addWidget(_row(t("rem_volume"), vol))
        sw = ToggleSwitch(prefs.get("important_alarm", True))
        sw.toggled.connect(lambda v: prefs.set("important_alarm", v))
        lay.addWidget(_row(t("rem_important"), sw))
        sw = ToggleSwitch(prefs.get("remind_routine", True))
        sw.toggled.connect(lambda v: prefs.set("remind_routine", v))
        lay.addWidget(_row(t("rem_routine"), sw))

        # ============================================================ Spor ve beslenme
        category("pcat_sport_food")
        section(t("nav_sport"))
        sp = QSpinBox()
        sp.setRange(1, 7)
        sp.setSuffix(" " + t("days_per_week"))
        sp.setValue(int(prefs.get("sport_weekly_goal", 4) or 4))
        sp.setFixedWidth(110)
        sp.valueChanged.connect(lambda v: prefs.set("sport_weekly_goal", int(v)))
        lay.addWidget(_row(t("weekly_goal"), sp))
        section(t("nutrition_goals"))
        for key, hi, step in (("kcal", 6000, 50), ("protein", 400, 5), ("carbs", 800, 5), ("fat", 300, 5)):
            sp = QSpinBox()
            sp.setRange(0, hi)
            sp.setSingleStep(step)
            sp.setValue(int(prefs.get("goal_" + key) or 0))
            sp.setFixedWidth(110)
            sp.valueChanged.connect(lambda v, k=key: prefs.set("goal_" + k, int(v)))
            lay.addWidget(_row(t("goal_" + key), sp))

        # ============================================================ Masaüstü widget'ı
        category("desk_section")
        sw = ToggleSwitch(prefs.get("desk_widget", False))
        sw.toggled.connect(lambda v: win.set_desk(v))
        lay.addWidget(_row(t("desk_show"), sw, t("desk_show_sub")))
        dm = _combo([("bottom", t("desk_mode_bottom")), ("top", t("desk_mode_top"))], prefs.get("desk_mode", "bottom"))
        dm.setMinimumWidth(240)
        dm.currentIndexChanged.connect(lambda: self._desk_mode(dm.currentData()))
        lay.addWidget(_row(t("desk_mode"), dm))

        # ============================================================ Telefonda aç
        category("pcat_phone")
        note(t("web_sub"))
        lay.addSpacing(6)
        sw = ToggleSwitch(prefs.get("web_on", False))
        sw.toggled.connect(self._web_on)
        lay.addWidget(_row(t("web_on"), sw, t("web_on_sub")))
        b = QPushButton(t("web_copy"))
        b.setObjectName("Pill")
        b.clicked.connect(self._web_copy)
        self.web_link_sub = None
        lay.addWidget(_row(t("web_link"), b, t("web_link_sub", u=self._web_page_host())))
        b = QPushButton(t("web_send"))
        b.setObjectName("Pill")
        b.clicked.connect(self._web_send)
        self.web_status_row = _row(t("web_status"), b, " ")
        self.web_status = self.web_status_row.findChildren(QLabel)[1]
        lay.addWidget(self.web_status_row)
        section(t("web_setup"))
        self.web_url = QLineEdit(prefs.get("web_url", ""))
        self.web_url.setPlaceholderText("https://…/api/alpha.php")
        self.web_url.setMinimumWidth(300)
        self.web_url.editingFinished.connect(lambda: prefs.set("web_url", self.web_url.text().strip()))
        lay.addWidget(_row(t("web_url"), self.web_url, t("web_url_sub")))
        bx = QHBoxLayout()
        bx.setSpacing(8)
        for key, fn in (("web_keyfile", self._web_keyfile), ("web_new_key", self._web_new_key)):
            b = QPushButton(t(key))
            b.setObjectName("Pill")
            b.clicked.connect(fn)
            bx.addWidget(b)
        lay.addWidget(_row(t("web_key"), bx, t("web_key_sub")))
        self._web_update()
        win.web.status.connect(self._web_update)

        # ============================================================ Veriler
        category("data")
        note(t("data_sub"))
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
        lay.addSpacing(8)
        lay.addLayout(bx)
        lay.addSpacing(6)
        path = QLabel(DATA_DIR)
        path.setObjectName("Secondary")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(path)

        # ============================================================ Hakkında
        from . import __version__, __author__, REPO_URL
        category("about")
        ab = note(t("about_text", v=__version__, a=__author__, u=REPO_URL))
        ab.setOpenExternalLinks(True)
        section(t("shortcuts"))
        note(t("shortcuts_text"))
        lay.addStretch(1)

        nav.addStretch(1)
        idx = self.cat_keys.index(start) if start in self.cat_keys else 0
        self.group.button(idx).setChecked(True)
        self.stack.setCurrentIndex(idx)

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

    def _try_sound(self):
        from .sounds import play
        play(prefs.get("reminder_sound", "chime"), int(prefs.get("reminder_volume", 70)) / 100)

    def _desk_mode(self, m):
        prefs.set("desk_mode", m)
        if self.win.desk is not None:
            self.win.desk.set_mode(m)

    def _autostart(self, on):
        if set_autostart(on):
            prefs.set("autostart", on)

    # ------------------------------------------------------------ web
    def _web_key(self):
        from .web import new_key
        if not prefs.get("web_key"):
            prefs.set("web_key", new_key())
        return prefs.get("web_key")

    def _web_on(self, on):
        prefs.set("web_url", self.web_url.text().strip())
        if on:
            self._web_key()
        prefs.set("web_on", on)
        if on:
            self.win.web.push()
        self._web_update()

    def _web_page_host(self):
        from .web import page_url
        u = page_url(prefs.get("web_url")) or "…/alpha/"
        return u.split("://", 1)[-1].rstrip("/")

    def _web_update(self, *_a):
        from .i18n import fmt_stamp
        from .web import url_ok
        if not prefs.get("web_on", False):
            txt = t("web_off")
        elif not url_ok(prefs.get("web_url")):
            txt = t("web_need_url")
        elif prefs.get("web_error"):
            txt = t("web_err", e=prefs.get("web_error"))
        elif prefs.get("web_last_ok"):
            txt = t("web_last", d=fmt_stamp(prefs.get("web_last_ok")))
        else:
            txt = t("web_never")
        try:
            self.web_status.setText(txt)
        except RuntimeError:          # pencere kapandı
            pass

    def _web_copy(self):
        from PyQt6.QtWidgets import QApplication
        from .web import page_url
        prefs.set("web_url", self.web_url.text().strip())
        url = page_url(prefs.get("web_url"))
        if not url:
            self.win.toast(t("web_need_url"))
            return
        QApplication.clipboard().setText(f"{url}#k={self._web_key()}")
        self.win.toast(t("web_copied"))

    def _web_keyfile(self):
        """api/_alpha_key.php'yi sitenin yerel klasörüne yazar (sonra siteye yüklenir)."""
        from .web import key_file_text
        start = prefs.get("web_site_dir") or os.path.expanduser("~")
        d = QFileDialog.getExistingDirectory(self, t("web_keyfile_pick"), start)
        if not d:
            return
        prefs.set("web_site_dir", d)
        target = os.path.join(d, "api") if os.path.isdir(os.path.join(d, "api")) else d
        path = os.path.join(target, "_alpha_key.php")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(key_file_text(self._web_key()))
        self.win.toast(t("web_keyfile_saved", p=path))

    def _web_send(self):
        prefs.set("web_url", self.web_url.text().strip())
        if not self.win.web.enabled():
            self.win.toast(t("web_need_url") if prefs.get("web_on") else t("web_off"))
            return
        self.win.web.push()

    def _web_new_key(self):
        from .web import new_key
        prefs.set("web_key", new_key())
        prefs.set("web_last_hash", "")
        self.win.toast(t("web_new_key_done"))
        if prefs.get("web_site_dir"):
            from .web import key_file_text
            d = prefs.get("web_site_dir")
            target = os.path.join(d, "api") if os.path.isdir(os.path.join(d, "api")) else d
            try:
                with open(os.path.join(target, "_alpha_key.php"), "w", encoding="utf-8", newline="\n") as f:
                    f.write(key_file_text(prefs.get("web_key")))
            except OSError:
                pass

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, t("export_json"),
                                              os.path.join(os.path.expanduser("~"), "Documents",
                                                           f"alpha-{day_today():%Y-%m-%d}.json"), "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.win.store.snapshot(), f, ensure_ascii=False, indent=1)
            self.win.toast(t("exported", p=os.path.basename(path)))
