"""Ana pencere: çerçevesiz (gamma gibi, Windows Snap çalışır), solda menü, sağda sayfalar."""
import ctypes
from ctypes import wintypes
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QByteArray
from PyQt6.QtGui import QCursor, QKeySequence, QShortcut, QGuiApplication, QAction
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                             QMenu, QButtonGroup)

from .config import day_today
from .config import prefs
from .i18n import t, fmt_num
from .theme import theme, current_name
from .titlebar import TitleBar
from .widgets import Toast

user32 = ctypes.windll.user32
user32.GetWindowLongW.restype = ctypes.c_long
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
GWL_STYLE = -16
WS_THICKFRAME, WS_CAPTION, WS_MAXIMIZEBOX, WS_MINIMIZEBOX, WS_SYSMENU = 0x40000, 0xC00000, 0x10000, 0x20000, 0x80000
WM_NCCALCSIZE, WM_NCHITTEST = 0x0083, 0x0084


class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


class Nav(QWidget):
    """Sol menü. Düzen navmenu'den gelir (göster / gizle, sıra, ad: sağ tık > Menüyü düzenle)."""

    def __init__(self, on_select, on_edit, parent=None):
        super().__init__(parent)
        self.setObjectName("Nav")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(232)
        self.on_select, self.on_edit = on_select, on_edit
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 12)
        v.setSpacing(2)
        self.items = QVBoxLayout()
        self.items.setContentsMargins(0, 0, 0, 0)
        self.items.setSpacing(2)
        v.addLayout(self.items)
        v.addStretch(1)
        self.foot = QLabel("")
        self.foot.setObjectName("NavFoot")
        self.foot.setWordWrap(True)
        v.addWidget(self.foot)
        self.group = None
        self.btns = {}
        self.rebuild()

    def rebuild(self):
        from . import navmenu
        from .components import _clear_layout
        _clear_layout(self.items)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.btns = {}
        for key in navmenu.visible():
            if key == "-":
                self.items.addSpacing(6)
                d = QWidget()
                d.setObjectName("Divider")
                d.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                d.setFixedHeight(1)
                self.items.addWidget(d)
                self.items.addSpacing(6)
                continue
            b = QPushButton("   " + navmenu.label(key).replace("&", "&&"))
            b.setObjectName("NavItem")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setFixedHeight(40)
            theme.icon(b, navmenu.icon(key), "text", 22)
            b.clicked.connect(lambda _=False, k=key: self.on_select(k))
            self.group.addButton(b)
            self.items.addWidget(b)
            self.btns[key] = b

    def keys(self):
        return list(self.btns)

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction(t("nav_edit"), self.on_edit)
        m.exec(e.globalPos())

    def set_current(self, key):
        b = self.btns.get(key)
        if b:
            b.setChecked(True)
        else:   # menüde olmayan sayfa (sabah planı): hiçbiri seçili görünmesin
            self.group.setExclusive(False)
            for x in self.btns.values():
                x.setChecked(False)
            self.group.setExclusive(True)


class MainWindow(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window |
                            Qt.WindowType.WindowMinMaxButtonsHint)
        self.setWindowTitle("alpha")
        self.setMinimumSize(760, 520)

        root = QWidget(self)
        root.setObjectName("Root")
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.titlebar = TitleBar(root)
        v.addWidget(self.titlebar)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.nav = Nav(self.show_page, self.edit_nav, root)
        body.addWidget(self.nav)
        self.stack = QStackedWidget(root)
        body.addWidget(self.stack, 1)
        v.addLayout(body, 1)
        self.setCentralWidget(root)
        self.toast_w = Toast(root)

        from .clock import Clock
        self.clock = Clock(store, self)          # kronometre / zamanlayıcı (ders, meditasyon)
        self.clock.finished.connect(self._clock_done)
        from .clock_ui import ClockPill
        self.clock_pill = ClockPill(self)
        self.titlebar.layout().insertWidget(self.titlebar.layout().indexOf(self.titlebar.btn_add), self.clock_pill)

        from .pages import build_pages
        self.pages = build_pages(store, self)
        for key, page in self.pages.items():
            self.stack.addWidget(page)

        tb = self.titlebar
        tb.minimize.connect(self.showMinimized)
        tb.maximize.connect(self.toggle_maximize)
        tb.close.connect(self.close)
        tb.prefs_clicked.connect(self.show_prefs)
        tb.menu_clicked.connect(lambda: self.set_nav(not self.nav.isVisible()))
        tb.theme_clicked.connect(self.toggle_theme)
        tb.quick_add.connect(self.quick_add_menu)
        tb.desk_clicked.connect(lambda: self.set_desk(not (self.desk is not None and self.desk.isVisible())))
        self.desk = None

        self._ensure_pages()
        for i in range(9):   # Ctrl+1..9: menüdeki sıraya göre
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda i=i: self._nth_page(i))
        for seq, fn in (("Ctrl+N", self.quick_add_menu), ("Ctrl+,", self.show_prefs), ("F11", self.toggle_fullscreen),
                        ("Ctrl+B", lambda: self.set_nav(not self.nav.isVisible())),
                        ("F5", self.refresh_all)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(fn)

        self.set_nav(bool(prefs.get("nav_visible", True)), save=False)
        self._restore_geometry()
        start = prefs.get("start_page", "today")
        if start == "last":
            start = prefs.get("last_page", "today")
        if start == "plan":
            start = "today"
        self.show_page(start if start in self.pages else "today")
        self.maybe_plan()
        from . import navmenu
        if navmenu.should_onboard(self.store):        # ilk açılış: hangi bölümler kullanılacak?
            QTimer.singleShot(500, lambda: navmenu.open_sections(self, first=True))

        # gece yarısı geçince "Bugün" ve geri sayımlar yenilensin
        self._day = day_today()
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(30_000)

        from .reminders import ReminderManager
        self.reminders = ReminderManager(store, self)
        from .web import WebSync
        self.web = WebSync(store, self)      # telefondan bakmak için gündemi siteye gönderir (Seçenekler > Web)

    # ============================================================ sayfalar
    def show_page(self, key):
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.nav.set_current(key)
        if key != "plan":
            prefs.set("last_page", key)
        self.current = key

    def _nth_page(self, i):
        keys = self.nav.keys()
        if i < len(keys):
            self.show_page(keys[i])

    def _ensure_pages(self):
        """Eklenen kategorilerin sayfaları (navmenu.custom_cats) yoksa kurulur, silinenler kaldırılır."""
        from . import navmenu
        from .pages.category import CategoryPage
        ids = {c["id"] for c in navmenu.custom_cats()}
        for cid in ids - set(self.pages):
            page = CategoryPage(self.store, self, cid)
            self.pages[cid] = page
            self.stack.addWidget(page)
        for key in [k for k in self.pages if k.startswith("c_") and k not in ids]:
            page = self.pages.pop(key)
            if getattr(self, "current", None) == key:
                self.show_page("today")
            self.stack.removeWidget(page)
            page.deleteLater()

    def edit_nav(self):
        from .navmenu import NavEditor
        if NavEditor(self).exec():
            self._ensure_pages()
            self.nav.rebuild()
            for page in self.pages.values():   # kategori adları yenilensin
                if hasattr(page, "mark_dirty"):
                    page.mark_dirty()
            self._rename_titles()
            self.nav.set_current(getattr(self, "current", "today"))
            self.toast(t("nav_saved"))

    def _rename_titles(self):
        from . import navmenu
        for key, page in self.pages.items():
            if key in navmenu.BUILTIN or key.startswith("c_"):
                page.title_lbl.setText(navmenu.label(key))

    def open_plan(self):
        """Sabah planı ekranını baştan açar."""
        self.pages["plan"].start()
        if not self.isVisible() or self.isMinimized():
            self.bring_front()
        self.show_page("plan")

    def maybe_plan(self):
        """Günün ilk açılışında (öğleden önce) plan yapılmadıysa plan ekranını getirir."""
        today = day_today().isoformat()
        if (not prefs.get("morning_plan", True) or prefs.get("last_plan") == today
                or prefs.get("plan_skipped") == today or getattr(self, "current", None) == "plan"):
            return
        if datetime.now().hour >= 12:
            return
        self.pages["plan"].start()
        self.show_page("plan")

    def refresh_all(self):
        for p in self.pages.values():
            p.mark_dirty()

    def _tick(self):
        if day_today() != self._day:
            self._day = day_today()
            self.refresh_all()
            if self.isVisible():
                self.maybe_plan()

    def toast(self, text, action=None, callback=None):
        self.toast_w.show_text(text, action, callback)

    def _clock_done(self, rec):
        if rec:
            self.toast(t("clock_saved", m=fmt_num(rec.get("minutes"), 0),
                         x=t("clock_" + (rec.get("kind") or "study"))))

    def quick_add_menu(self):
        from .forms import edit_item
        m = QMenu(self)
        items = [("tasks", "qa_task"), ("routine", "qa_routine"), ("habits", "qa_habit"), None, ("exams", "qa_exam"),
                 ("workouts", "qa_workout"), ("sleep", "qa_sleep"), ("events", "qa_event"), None,
                 ("transactions", "qa_tx"), ("debts", "qa_debt"), None]
        for it in items:
            if it is None:
                m.addSeparator()
                continue
            coll, key = it
            a = QAction(t(key), m)
            a.triggered.connect(lambda _=False, c=coll: edit_item(self, c))
            m.addAction(a)
        a = QAction(t("qa_note"), m)
        a.triggered.connect(self.new_note)
        m.addAction(a)
        b = self.titlebar.btn_add
        m.exec(b.mapToGlobal(b.rect().bottomLeft()))

    # ============================================================ masaüstü widget'ı
    def set_desk(self, on):
        from .desk_widget import DeskWidget
        if on:
            if self.desk is None:
                self.desk = DeskWidget(self.store, self)
                self.desk.closed.connect(self._desk_closed)
            prefs.set("desk_widget", True)
            self.desk.refresh()
            self.desk.show()
        elif self.desk is not None:
            self.desk.remove()
        self.titlebar.set_desk(on)

    def _desk_closed(self):
        self.titlebar.set_desk(False)
        if not self.isVisible():   # ana pencere de kapalıysa uygulama kapansın
            QApplication.quit()

    def new_note(self):
        self.show_page("notes")
        self.pages["notes"].new_note()

    # ============================================================ görünüm
    def set_nav(self, on, save=True):
        self.nav.setVisible(on)
        if save:
            prefs.set("nav_visible", on)

    def toggle_theme(self):
        theme.apply("light" if current_name() == "dark" else "dark")

    def show_prefs(self):
        from .dialogs import PrefsDialog
        PrefsDialog(self).exec()
        self.refresh_all()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.titlebar.show()
        else:
            self.titlebar.hide()
            self.showFullScreen()

    def changeEvent(self, e):
        if e.type() == e.Type.WindowStateChange:
            self.titlebar.set_maximized(self.isMaximized())
        super().changeEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.toast_w.isVisible():
            self.toast_w.reposition()
        # dar pencerede menü kendiliğinden gizlensin (kullanıcı tercihi bozulmadan)
        if prefs.get("nav_visible", True):
            self.nav.setVisible(self.width() >= 900)

    def bring_front(self):
        if self.isMinimized():
            self.showNormal()
        self.maybe_plan()
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            user32.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

    def _restore_geometry(self):
        g = prefs.get("window_geometry")
        ok = False
        if g:
            try:
                ok = self.restoreGeometry(QByteArray.fromBase64(g.encode("ascii")))
            except Exception:
                ok = False
        if not ok:
            scr = QGuiApplication.primaryScreen().availableGeometry()
            w, h = min(1360, scr.width() - 80), min(880, scr.height() - 80)
            self.resize(w, h)
            self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)

    def save_state(self):
        notes = self.pages.get("notes")
        if notes is not None:
            notes.commit()
        self.store.flush()
        prefs.set("window_geometry", bytes(self.saveGeometry().toBase64()).decode("ascii"))

    def closeEvent(self, e):
        self.save_state()
        e.accept()
        # widget masaüstündeyse uygulama arka planda yaşamaya devam eder (widget'tan tekrar açılır)
        if not (self.desk is not None and self.desk.isVisible()):
            QTimer.singleShot(0, QApplication.quit)

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_native_frame()

    # ============================================================ Windows Snap
    def _apply_native_frame(self):
        """Çerçevesiz pencereye Windows'un boyutlandırma / Snap / animasyon stillerini geri verir."""
        if self.isFullScreen():
            return
        try:
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            want = style | WS_THICKFRAME | WS_CAPTION | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_SYSMENU
            if want != style:
                user32.SetWindowLongW(hwnd, GWL_STYLE, want)
                user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0010 | 0x0020)
        except Exception:
            pass

    def nativeEvent(self, event_type, message):
        try:
            msg = wintypes.MSG.from_address(int(message))
        except Exception:
            return False, 0
        if msg.message == WM_NCCALCSIZE and msg.wParam:
            if user32.IsZoomed(msg.hWnd) and not self.isFullScreen():
                params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                mon = user32.MonitorFromWindow(msg.hWnd, 2)
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                    params.rgrc[0] = mi.rcWork
            return True, 0
        if msg.message == WM_NCHITTEST and not self.isFullScreen():
            gp = QCursor.pos()
            if not self.isMaximized():
                g = self.frameGeometry()
                m = 6
                left, right = gp.x() <= g.left() + m, gp.x() >= g.right() - m
                top, bottom = gp.y() <= g.top() + m, gp.y() >= g.bottom() - m
                code = {(True, False, True, False): 13, (False, True, True, False): 14,
                        (True, False, False, True): 16, (False, True, False, True): 17}.get((left, right, top, bottom))
                if code is None:
                    code = 10 if left else 11 if right else 12 if top else 15 if bottom else None
                if code is not None:
                    return True, code
            tb = self.titlebar
            if tb.isVisible():
                local = tb.mapFromGlobal(gp)
                if tb.rect().contains(local):
                    child = tb.childAt(local)
                    if tb.is_drag_area(child):
                        return True, 2  # HTCAPTION
        return False, 0
