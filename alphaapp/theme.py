"""Karanlık / aydınlık tema (gamma ile birebir aynı paletler), Qt stil sayfası ve temaya duyarlı ikonlar."""
import re
import weakref

from PyQt6.QtCore import QObject, pyqtSignal, QSize
from PyQt6.QtWidgets import QApplication

from . import icons
from .config import prefs

ACCENTS = {
    "gray": "#c4c4c4",
    "red": "#ff0033",
    "blue": "#3ea6ff",
    "green": "#2ecc71",
    "orange": "#ff8a1f",
    "pink": "#ff4fa3",
    "teal": "#1fc7b6",
}

# Anlam renkleri (gelir/gider, hedefin altı/üstü). Mor/eflatun yok.
GOOD = "#2ba640"
BAD = "#ff4e45"
# haftalık programda kutu türleri (mor yok): spor, ders, toplantı / etkinlik, yapılacak
BLOCK_KINDS = {"sport": "#4f9d74", "lesson": "#5b8fd9", "meeting": "#d1a04a", "task": "#45a5a5"}


def _block_kinds_qss(dark):
    out = []
    for k, hx in BLOCK_KINDS.items():
        r, g, b = int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)
        a = "0.13" if dark else "0.10"
        out.append(f'#Block[kind="{k}"] {{ background: rgba({r},{g},{b},{a}); border: 1px solid rgba({r},{g},{b},0.45);'
                   f' border-left: 3px solid {hx}; border-radius: 8px; }}')
        out.append(f'#Block[kind="{k}"]:hover {{ background: rgba({r},{g},{b},0.22); }}')
    return chr(10).join(out)
WARN = "#f2a33a"
INFO = "#3ea6ff"


def accent() -> str:
    v = str(prefs.get("accent", "gray") or "gray")
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v.lower()
    return ACCENTS.get(v, ACCENTS["gray"])


PALETTES = {
    "dark": {
        "bg": "#000000",        # AMOLED siyah
        "bg2": "#000000",
        "surface": "#272727",
        "surface_hover": "#3f3f3f",
        "card": "#121212",
        "card_hover": "#1c1c1c",
        "text": "#f1f1f1",
        "text2": "#aaaaaa",
        "text3": "#717171",
        "divider": "rgba(255,255,255,0.10)",
        "hover": "rgba(255,255,255,0.10)",
        "pressed": "rgba(255,255,255,0.18)",
        "selected": "rgba(255,255,255,0.14)",
        "chip_active_bg": "#f1f1f1",
        "chip_active_fg": "#0f0f0f",
        "input_bg": "#121212",
        "input_border": "#303030",
        "button_bg": "#f1f1f1",
        "button_fg": "#0f0f0f",
        "scroll": "rgba(255,255,255,0.22)",
        "track": "#2a2a2a",
    },
    "light": {
        "bg": "#ffffff",
        "bg2": "#f9f9f9",
        "surface": "#f2f2f2",
        "surface_hover": "#e5e5e5",
        "card": "#f7f7f7",
        "card_hover": "#efefef",
        "text": "#0f0f0f",
        "text2": "#606060",
        "text3": "#909090",
        "divider": "rgba(0,0,0,0.10)",
        "hover": "rgba(0,0,0,0.05)",
        "pressed": "rgba(0,0,0,0.10)",
        "selected": "rgba(0,0,0,0.07)",
        "chip_active_bg": "#0f0f0f",
        "chip_active_fg": "#ffffff",
        "input_bg": "#ffffff",
        "input_border": "#d3d3d3",
        "button_bg": "#0f0f0f",
        "button_fg": "#ffffff",
        "scroll": "rgba(0,0,0,0.25)",
        "track": "#e3e3e3",
    },
}

# Tema çeşitleri: kimlik -> (Türkçe ad, İngilizce ad, aile, temel paletin üzerine yazılan renkler)
VARIANTS = {
    "amoled": ("AMOLED siyah", "AMOLED black", "dark", {}),
    "dark_gray": ("Koyu gri", "Dark gray", "dark", {"bg": "#0f0f0f", "bg2": "#181818", "card": "#1a1a1a",
                                                   "card_hover": "#232323"}),
    "graphite": ("Grafit", "Graphite", "dark", {
        "bg": "#1c1c1e", "bg2": "#232326", "surface": "#2f2f33", "surface_hover": "#45454a", "card": "#26262a",
        "card_hover": "#2e2e33", "input_bg": "#18181a", "input_border": "#3a3a3e", "track": "#38383d"}),
    "midnight": ("Gece mavisi", "Midnight blue", "dark", {
        "bg": "#0d1117", "bg2": "#111723", "surface": "#1f2733", "surface_hover": "#2d3846", "card": "#141b26",
        "card_hover": "#1a2330", "input_bg": "#0b0f16", "input_border": "#2a3442", "text2": "#9aa6b4",
        "track": "#222c3a"}),
    "mocha": ("Sıcak koyu", "Mocha", "dark", {
        "bg": "#17130f", "bg2": "#1e1914", "surface": "#2c251e", "surface_hover": "#3d342a", "card": "#211b16",
        "card_hover": "#29221b", "input_bg": "#120f0c", "input_border": "#3a3128", "text2": "#b0a594",
        "track": "#352d25"}),
    "white": ("Beyaz", "White", "light", {}),
    "light_gray": ("Açık gri", "Light gray", "light", {
        "bg": "#f1f1f3", "bg2": "#e9e9ec", "surface": "#e2e2e6", "surface_hover": "#d5d5da", "card": "#fafafa",
        "card_hover": "#ffffff"}),
    "cream": ("Krem", "Cream", "light", {
        "bg": "#faf6ef", "bg2": "#f3eee4", "surface": "#ece5d8", "surface_hover": "#e0d7c6", "card": "#fffdf8",
        "card_hover": "#f6f1e7", "input_bg": "#fffdf8", "text2": "#6b6258", "track": "#e6dece"}),
    "ice": ("Buz mavisi", "Ice blue", "light", {
        "bg": "#f3f7fb", "bg2": "#e9f0f7", "surface": "#e1e9f2", "surface_hover": "#d3deea", "card": "#fbfdff",
        "card_hover": "#eef4fa", "text2": "#56657a", "track": "#dae3ee"}),
    "mint": ("Nane", "Mint", "light", {
        "bg": "#f2f8f4", "bg2": "#e7f2eb", "surface": "#dcebe2", "surface_hover": "#cde0d4", "card": "#fbfefc",
        "card_hover": "#eef6f1", "text2": "#56695e", "track": "#d6e6dc"}),
}
_LEGACY = {"dark": "amoled", "light": "white"}


def current_variant() -> str:
    v = prefs.get("theme", "amoled")
    v = _LEGACY.get(v, v)
    return v if v in VARIANTS else "amoled"


def current_name() -> str:
    """Tema ailesi: "dark" veya "light"."""
    return VARIANTS[current_variant()][2]


def is_dark() -> bool:
    return current_name() == "dark"


def variant_label(v):
    name = VARIANTS[v]
    return name[0] if prefs.get("language", "tr") == "tr" else name[1]


def pal() -> dict:
    v = VARIANTS[current_variant()]
    d = dict(PALETTES[v[2]])
    d.update(v[3])
    return d


def color(role: str) -> str:
    if role == "accent":
        return accent()
    if role == "white":
        return "#ffffff"
    if role == "good":
        return GOOD
    if role == "bad":
        return BAD
    if role == "warn":
        return WARN
    if role == "info":
        return INFO
    return pal().get(role, role)


def qcolor(role: str):
    """Rol adını (veya #hex / rgba(...) metnini) QColor'a çevirir."""
    from PyQt6.QtGui import QColor
    c = color(role)
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)", c)
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return QColor(r, g, b, int(round(a * 255 if a <= 1 else a)))
    return QColor(c)


def tinted_logo(height: int, dpr: float = 1.0, role: str = "text"):
    """Logoyu tema metin rengine boyar (aydınlık temada görünür olsun diye)."""
    from PyQt6.QtGui import QPixmap, QPainter
    from PyQt6.QtCore import Qt
    from .config import asset
    pm = QPixmap(asset("logo.png"))
    if pm.isNull():
        return pm
    pm = pm.scaledToHeight(int(height * dpr), Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(out.rect(), qcolor(role))
    p.end()
    out.setDevicePixelRatio(dpr)
    return out


def spin_img(kind):
    """Sayı kutusu oku (assets/spin_*.svg); QSS url'si için düz eğik çizgili yol."""
    from .config import asset
    from PyQt6.QtGui import QColor
    tone = "light" if QColor(pal()["bg"]).lightness() > 128 else "dark"
    return asset(f"spin_{kind}_{tone}.svg").replace("\\", "/")


def stylesheet() -> str:
    c = pal()
    dark = current_name() == "dark"
    return f"""
* {{
    font-family: "Segoe UI Variable Text", "Segoe UI", "Roboto", sans-serif;
    font-size: 13px;
    outline: none;
}}
QMainWindow, #Root, #PageHost, QDialog#ThemedDialog {{
    background: {c['bg']};
    color: {c['text']};
}}
QWidget {{ color: {c['text']}; }}
QToolTip {{
    background: rgba(97,97,97,0.92);
    color: #ffffff;
    border: none;
    padding: 5px 8px;
    border-radius: 4px;
    font-size: 12px;
}}
#TitleBar {{ background: {c['bg']}; }}
#Wordmark {{ font-size: 19px; font-weight: 700; letter-spacing: -0.6px; color: {c['text']}; }}

QToolButton#IconBtn, QPushButton#IconBtn {{
    background: transparent; border: none; border-radius: 18px; padding: 0px;
}}
QToolButton#IconBtn:hover, QPushButton#IconBtn:hover {{ background: {c['hover']}; }}
QToolButton#IconBtn:pressed, QPushButton#IconBtn:pressed {{ background: {c['pressed']}; }}
QToolButton#IconBtn:checked {{ background: {c['selected']}; }}
QToolButton#WinBtn {{ background: transparent; border: none; border-radius: 0px; }}
QToolButton#WinBtn:hover {{ background: {c['hover']}; }}
QToolButton#WinClose {{ background: transparent; border: none; border-radius: 0px; }}
QToolButton#WinClose:hover {{ background: #e81123; }}

/* Sol menü (YouTube rehberi gibi) */
#Nav {{ background: {c['bg']}; }}
QPushButton#NavItem {{
    background: transparent; color: {c['text']}; border: none; border-radius: 10px;
    padding: 0px 12px; height: 40px; text-align: left; font-size: 14px; font-weight: 400;
}}
QPushButton#NavItem:hover {{ background: {c['hover']}; }}
QPushButton#NavItem:checked {{ background: {c['surface']}; font-weight: 600; }}
QPushButton#NavItem:checked:hover {{ background: {c['surface_hover']}; }}
#NavSection {{ color: {c['text']}; font-size: 15px; font-weight: 600; padding: 4px 12px; }}
#NavFoot {{ color: {c['text3']}; font-size: 11px; padding: 0px 12px; }}

/* Sayfa başlığı */
#PageTitle {{ font-size: 24px; font-weight: 700; letter-spacing: -0.4px; color: {c['text']}; }}
#PageSub {{ font-size: 13px; color: {c['text2']}; }}

/* Kartlar */
#Card {{ background: {c['card']}; border-radius: 12px; }}
#Card[drop="true"] {{ border: 1px dashed {c['text2']}; }}
#CardToday {{ background: {c['surface']}; border-radius: 12px; }}
#Reminder {{ background: {c['card']}; border: 1px solid {c['input_border']}; border-radius: 12px; }}
#ReminderImportant {{ background: {c['card']}; border: 1px solid rgba(255,78,69,0.6);
    border-left: 4px solid {BAD}; border-radius: 12px; }}
#RemindWhen {{ font-size: 12px; color: {c['text2']}; font-weight: 600; }}
#RemindTitle {{ font-size: 15px; font-weight: 700; color: {c['text']}; }}
#RemindTitleBad {{ font-size: 15px; font-weight: 700; color: {BAD if dark else '#d0241b'}; }}
#CardDrop {{ background: {c['surface_hover']}; border: 1px dashed {c['text2']}; border-radius: 12px; }}
#CardTitle {{ font-size: 15px; font-weight: 700; color: {c['text']}; }}
#CardSub {{ font-size: 12px; color: {c['text2']}; }}
#Row {{ background: transparent; border-radius: 8px; }}
#Row:hover {{ background: {c['hover']}; }}
#RowTitle {{ font-size: 13px; color: {c['text']}; }}
#RowTitleDone {{ font-size: 13px; color: {c['text3']}; text-decoration: line-through; }}
#RowSub {{ font-size: 12px; color: {c['text2']}; }}
#RowValue {{ font-size: 13px; font-weight: 600; color: {c['text']}; }}
#Empty {{ color: {c['text3']}; font-size: 12px; padding: 8px 6px; }}
#Block {{ background: {c['bg'] if dark else c['bg']}; border: 1px solid {c['divider']}; border-radius: 8px; }}
#Block:hover {{ background: {c['hover']}; }}
#BlockImportant {{ background: rgba(255,78,69,{'0.14' if dark else '0.10'}); border: 1px solid rgba(255,78,69,0.55);
    border-left: 3px solid {BAD}; border-radius: 8px; }}
#BlockImportant:hover {{ background: rgba(255,78,69,0.22); }}
#BlockTitleImportant {{ font-size: 13px; font-weight: 600; color: {BAD if dark else '#d0241b'}; }}
#BlockTimeImportant {{ font-size: 12px; font-weight: 600; color: {BAD if dark else '#d0241b'}; }}
#CarryRow {{ background: transparent; border-radius: 10px; }}
#CarryRowCurrent {{ background: {c['surface']}; border-radius: 10px; }}
#ProgFill {{ background: {c['text']}; border-radius: 2px; }}
#ProgTrack {{ background: {c['track']}; border-radius: 2px; }}
QPushButton#CatChip {{ background: {c['surface']}; border: 1px solid transparent; border-radius: 10px;
    padding: 0px; min-width: 40px; max-width: 40px; min-height: 34px; max-height: 34px; }}
QPushButton#CatChip:hover {{ background: {c['surface_hover']}; }}
QPushButton#CatChip:checked {{ background: {c['selected']}; border: 1px solid {c['text']}; }}
#Badge {{
    background: {c['surface']}; color: {c['text']}; border-radius: 4px;
    padding: 1px 6px; font-size: 11px; font-weight: 600;
}}
#BadgeBad {{ background: rgba(255,78,69,0.18); color: {BAD}; border-radius: 4px; padding: 1px 6px;
    font-size: 11px; font-weight: 600; }}
#BadgeWarn {{ background: rgba(242,163,58,0.18); color: {WARN if dark else '#a35f00'}; border-radius: 4px; padding: 1px 6px;
    font-size: 11px; font-weight: 600; }}
#BadgeGood {{ background: rgba(43,166,64,0.18); color: {GOOD if dark else '#1e7a30'}; border-radius: 4px; padding: 1px 6px;
    font-size: 11px; font-weight: 600; }}
#TimeLbl {{ font-size: 13px; font-weight: 600; color: {c['text']}; font-family: "Segoe UI Variable Display", "Segoe UI"; }}
#ClockBig {{ font-size: 46px; font-weight: 700; letter-spacing: -1px; color: {c['text']}; }}
#StatValue {{ font-size: 22px; font-weight: 700; letter-spacing: -0.4px; color: {c['text']}; }}
#StatLabel {{ font-size: 12px; color: {c['text2']}; }}
#StatGood {{ font-size: 12px; color: {GOOD}; font-weight: 600; }}
#StatBad {{ font-size: 12px; color: {BAD}; font-weight: 600; }}
#Greeting {{ font-size: 28px; font-weight: 700; letter-spacing: -0.6px; color: {c['text']}; }}
#Intention {{ font-size: 18px; font-weight: 600; color: {c['text']}; }}
#TodayIntention {{ font-size: 14px; font-style: italic; color: {c['text2']}; }}

#WishCard {{ background: {c['surface']}; border-radius: 14px; }}
#WishCard:hover {{ background: {c['surface_hover']}; }}
#WishName {{ font-size: 13px; font-weight: 600; color: {c['text']}; }}
#WishPrice {{ font-size: 13px; font-weight: 700; color: {c['text']}; }}
QPushButton#WishBtn {{ background: {c['chip_active_bg']}; color: {c['chip_active_fg']}; border: none; border-radius: 13px;
    padding: 0px 10px; min-width: 0px; height: 26px; font-size: 12px; font-weight: 600; }}
QPushButton#WishBtnOn {{ background: transparent; color: {c['text2']}; border: 1px solid {c['surface_hover']};
    border-radius: 13px; padding: 0px 10px; min-width: 0px; height: 24px; font-size: 12px; }}

QPushButton#PickField {{
    background: {c['input_bg']}; color: {c['text']}; border: 1px solid {c['input_border']}; border-radius: 8px;
    padding: 6px 10px; min-height: 20px; text-align: left; font-size: 13px; min-width: 0px;
}}
QPushButton#PickField:hover {{ border: 1px solid {c['text3']}; }}
QPushButton#PickField:focus {{ border: 1px solid #1c62b9; }}
QPushButton#PickField:disabled, QPushButton#PickField[off="true"] {{ color: {c['text3']}; }}
QPushButton#PickTitle {{ background: transparent; color: {c['text']}; border: none; border-radius: 8px;
    padding: 4px 8px; font-size: 14px; font-weight: 600; min-width: 0px; text-align: left; }}
QPushButton#PickTitle:hover {{ background: {c['surface']}; }}
#PickPopup {{ background: {'#212121' if dark else '#ffffff'}; border: 1px solid {c['divider']}; border-radius: 12px; }}
QPushButton#PickChip {{
    background: {c['surface']}; color: {c['text']}; border: none; border-radius: 8px;
    padding: 0px 8px; min-width: 38px; height: 30px; font-size: 13px;
}}
QPushButton#PickChip:hover {{ background: {c['surface_hover']}; }}
QPushButton#PickChip:checked {{ background: {c['chip_active_bg']}; color: {c['chip_active_fg']}; font-weight: 600; }}

QPushButton#Chip {{
    background: {c['surface']}; color: {c['text']}; border: none;
    border-radius: 8px; padding: 6px 12px; font-size: 13px; font-weight: 500;
}}
QPushButton#Chip:hover {{ background: {c['surface_hover']}; }}
QPushButton#Chip:checked {{ background: {c['chip_active_bg']}; color: {c['chip_active_fg']}; }}
QPushButton#Pill {{
    background: {c['surface']}; color: {c['text']}; border: none;
    border-radius: 18px; padding: 0px 14px; height: 36px; font-size: 13px; font-weight: 500;
}}
QPushButton#Pill:hover {{ background: {c['surface_hover']}; }}
QPushButton#SmallPill {{
    background: {c['surface']}; color: {c['text']}; border: none;
    border-radius: 15px; padding: 0px 12px; height: 30px; font-size: 12px; font-weight: 500;
}}
QPushButton#SmallPill:hover {{ background: {c['surface_hover']}; }}
QPushButton#Primary {{
    background: {c['button_bg']}; color: {c['button_fg']}; border: none;
    border-radius: 18px; padding: 0px 18px; height: 36px; font-size: 14px; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {'#d9d9d9' if dark else '#272727'}; }}
QPushButton#Flat {{
    background: transparent; color: {c['text']}; border: none; border-radius: 18px;
    padding: 0px 14px; height: 36px; font-weight: 500;
}}
QPushButton#Flat:hover {{ background: {c['hover']}; }}
QPushButton#Danger {{
    background: transparent; color: {BAD}; border: none; border-radius: 18px;
    padding: 0px 14px; height: 36px; font-weight: 500;
}}
QPushButton#Danger:hover {{ background: rgba(255,78,69,0.12); }}

#Secondary {{ color: {c['text2']}; font-size: 12px; }}
#SubTitle {{ font-size: 14px; font-weight: 700; color: {c['text']}; padding-top: 6px; }}
#FieldLabel {{ font-size: 12px; color: {c['text2']}; font-weight: 600; }}
#Divider {{ background: {c['divider']}; }}
#Toast {{
    background: {'#f1f1f1' if dark else '#212121'}; border-radius: 8px;
}}
#ToastText {{ color: {'#0f0f0f' if dark else '#ffffff'}; font-size: 13px; font-weight: 500; }}
QPushButton#ToastBtn {{
    background: transparent; border: none; color: {'#065fd4' if dark else '#3ea6ff'};
    font-weight: 600; padding: 4px 8px; border-radius: 14px;
}}
QPushButton#ToastBtn:hover {{ background: {'rgba(0,0,0,0.08)' if dark else 'rgba(255,255,255,0.12)'}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit {{
    background: {c['input_bg']}; color: {c['text']};
    border: 1px solid {c['input_border']}; border-radius: 8px; padding: 6px 8px; min-height: 20px;
    selection-background-color: #3ea6ff;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    border: 1px solid #1c62b9;
}}
QLineEdit:disabled, QDateEdit:disabled, QTimeEdit:disabled {{ color: {c['text3']}; }}
QLineEdit#Search {{ border-radius: 18px; padding: 6px 14px; }}
QTimeEdit::up-button, QTimeEdit::down-button {{ width: 0px; border: none; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 18px; border: none; background: transparent; border-radius: 4px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{ background: {c['divider']}; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{spin_img('up')}"); width: 12px; height: 11px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{spin_img('down')}"); width: 12px; height: 11px; }}
QDateEdit::drop-down {{ border: none; width: 22px; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {c['card'] if not dark else '#212121'}; color: {c['text']}; border: 1px solid {c['divider']};
    selection-background-color: {c['surface_hover']}; selection-color: {c['text']}; padding: 4px;
}}
QCalendarWidget QWidget {{ alternate-background-color: {c['surface']}; }}
QCalendarWidget QToolButton {{
    background: transparent; color: {c['text']}; border: none; border-radius: 6px; padding: 4px 8px;
    font-weight: 600;
}}
QCalendarWidget QToolButton:hover {{ background: {c['hover']}; }}
QCalendarWidget QMenu {{ background: {c['card']}; }}
QCalendarWidget QSpinBox {{ background: {c['input_bg']}; }}
QCalendarWidget #qt_calendar_navigationbar {{ background: {'#212121' if dark else '#f2f2f2'}; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: {'#212121' if dark else '#ffffff'}; color: {c['text']};
    selection-background-color: {c['chip_active_bg']}; selection-color: {c['chip_active_fg']};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {c['text3']}; }}

QPlainTextEdit#NoteBody, QTextEdit#NoteBody {{
    background: transparent; color: {c['text']}; border: none; font-size: 14px;
    selection-background-color: #3ea6ff;
}}
QLineEdit#NoteTitleEdit {{
    background: transparent; border: none; font-size: 22px; font-weight: 700; padding: 0px;
}}
QPlainTextEdit {{
    background: {c['input_bg']}; color: {c['text']}; border: 1px solid {c['input_border']}; border-radius: 8px;
    padding: 4px; selection-background-color: #3ea6ff;
}}

QSlider::groove:horizontal {{ height: 4px; background: {c['surface_hover']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {c['text']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {c['text']}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; border-radius: 4px; min-height: 30px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {c['text3']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {c['scroll']}; border-radius: 4px; min-width: 30px; margin: 2px; }}

QMenu {{
    background: {'#212121' if dark else '#ffffff'}; color: {c['text']}; border: 1px solid {c['divider']};
    border-radius: 12px; padding: 8px 0px;
}}
QMenu::item {{ padding: 8px 36px 8px 16px; font-size: 13px; }}
QMenu::item:selected {{ background: {c['hover']}; }}
QMenu::item:disabled {{ color: {c['text3']}; }}
QMenu::separator {{ height: 1px; background: {c['divider']}; margin: 6px 0px; }}
QMenu::icon {{ padding-left: 12px; }}
QMenu::indicator {{ width: 0px; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QMessageBox {{ background: {c['bg']}; }}
QDialog QPushButton {{
    background: {c['surface']}; color: {c['text']}; border: none; border-radius: 16px;
    padding: 7px 16px; font-weight: 500; min-width: 64px;
}}
QDialog QPushButton:hover {{ background: {c['surface_hover']}; }}
QDialog QPushButton#Chip {{ min-width: 0px; padding: 6px 10px; }}
""" + _block_kinds_qss(dark)


class ThemeManager(QObject):
    changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._bindings = []  # (weakref(widget), callable)

    def apply(self, name: str = None):
        """name: tema çeşidi kimliği ya da "dark"/"light" (o ailenin son seçilen çeşidi)."""
        if name in ("dark", "light"):
            name = prefs.get(name + "_variant") or ("amoled" if name == "dark" else "white")
        if name in VARIANTS:
            prefs.set("theme", name)
            prefs.set(VARIANTS[name][2] + "_variant", name)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet())
        alive = []
        for ref, fn in self._bindings:
            w = ref()
            if w is None:
                continue
            try:
                fn(w)
                alive.append((ref, fn))
            except RuntimeError:
                pass
        self._bindings = alive
        self.changed.emit(current_name())

    def bind(self, widget, fn):
        """Tema her değiştiğinde fn(widget) çağrılır (ilk çağrı hemen yapılır)."""
        self._bindings.append((weakref.ref(widget), fn))
        fn(widget)

    def icon(self, button, name: str, role: str = "text", size: int = 20):
        """Butona temaya duyarlı ikon atar; tekrar çağrılırsa ikonu günceller."""
        button._ticon = (name, role, size)

        def _apply(b):
            n, r, s = b._ticon
            b.setIcon(icons.icon(n, color(r), s))
            b.setIconSize(QSize(s, s))

        if getattr(button, "_tbound", False):
            _apply(button)
        else:
            button._tbound = True
            self.bind(button, _apply)


theme = ThemeManager()
