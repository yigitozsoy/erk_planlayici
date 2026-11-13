"""Üst çubuk (gamma ile aynı düzen): solda menü + logo + alpha + •••, sağda hızlı ekle / tema / pencere düğmeleri."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton

from .i18n import t
from .theme import theme, tinted_logo, current_name
from .widgets import IconButton


class TitleBar(QWidget):
    prefs_clicked = pyqtSignal()
    menu_clicked = pyqtSignal()
    quick_add = pyqtSignal()
    theme_clicked = pyqtSignal()
    desk_clicked = pyqtSignal()
    minimize = pyqtSignal()
    maximize = pyqtSignal()
    close = pyqtSignal()

    HEIGHT = 56

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(self.HEIGHT)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(4)

        self.btn_menu = IconButton("menu", t("toggle_nav"), 40, 24)
        self.btn_menu.clicked.connect(self.menu_clicked.emit)
        lay.addWidget(self.btn_menu)

        brand = QWidget(self)
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(8, 0, 4, 0)
        bl.setSpacing(5)
        self.logo = QLabel()
        theme.bind(self.logo, lambda l: l.setPixmap(tinted_logo(24, l.devicePixelRatioF())))
        bl.addWidget(self.logo)
        self.wordmark = QLabel("alpha")
        self.wordmark.setObjectName("Wordmark")
        bl.addWidget(self.wordmark)
        lay.addWidget(brand)
        self.btn_prefs = IconButton("more_horiz", t("preferences"), 36, 24)
        self.btn_prefs.clicked.connect(self.prefs_clicked.emit)
        box = QHBoxLayout()
        box.setContentsMargins(0, 6, 0, 0)  # "alpha" küçük harflerinin görsel ortasıyla hizalı
        box.addWidget(self.btn_prefs)
        lay.addLayout(box)

        lay.addStretch(1)
        self.btn_add = IconButton("add", t("quick_add") + " (Ctrl+N)", 40, 24)
        self.btn_add.clicked.connect(self.quick_add.emit)
        self.btn_desk = IconButton("widgets", t("desk_tip"), 40, 22, checkable=True)
        self.btn_desk.clicked.connect(self.desk_clicked.emit)
        self.btn_theme = IconButton("moon", t("theme"), 40, 22)
        self.btn_theme.clicked.connect(self.theme_clicked.emit)
        for b in (self.btn_add, self.btn_desk, self.btn_theme):
            lay.addWidget(b)
        lay.addSpacing(10)
        self.btn_min = self._win_btn("win_min", "WinBtn", self.minimize)
        self.btn_max = self._win_btn("win_max", "WinBtn", self.maximize)
        self.btn_close = self._win_btn("close", "WinClose", self.close)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
        self.update_theme_icon()
        theme.changed.connect(lambda _: self.update_theme_icon())

    def is_drag_area(self, widget):
        return widget is self or widget is None or widget is self.wordmark or widget is self.logo

    def _win_btn(self, icon_name, obj, sig):
        b = QToolButton(self)
        b.setObjectName(obj)
        b.setFixedSize(46, 34)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        theme.icon(b, icon_name, "text", 16)
        b.clicked.connect(sig.emit)
        return b

    def update_theme_icon(self):
        dark = current_name() == "dark"
        self.btn_theme.set_icon_name("sun" if dark else "moon")
        self.btn_theme.setToolTip(t("light_mode") if dark else t("dark_mode"))

    def set_desk(self, on):
        self.btn_desk.setChecked(on)
        self.btn_desk.setToolTip(t("desk_tip_on") if on else t("desk_tip"))

    def set_maximized(self, on):
        theme.icon(self.btn_max, "win_restore" if on else "win_max", "text", 16)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self.window().isFullScreen():
            h = self.window().windowHandle()
            if h:
                h.startSystemMove()
                return
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.maximize.emit()
            return
        super().mouseDoubleClickEvent(e)
