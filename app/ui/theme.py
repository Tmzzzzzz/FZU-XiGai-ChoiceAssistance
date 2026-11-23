# -*- coding: utf-8 -*-
"""配色、字体与全局样式表。

浅色 / 深色两套调色板，键名一致；`set_mode()` 切换后调用 `qss()` 重新套用样式，
自定义绘制的组件通过模块级 `__getattr__` 始终取到当前调色板的颜色。
"""
from __future__ import annotations

import weakref

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

FONT_FAMILY = "Microsoft YaHei UI"

# ------------------------------------------------------------------ 调色板
LIGHT = {
    "BG": "#F3F5FA",
    "SURFACE": "#FFFFFF",
    "SURFACE_SOFT": "#F7F9FD",
    "BORDER": "#E4E9F2",
    "BORDER_STRONG": "#D3DBEA",
    "TEXT": "#141C2E",
    "TEXT_SECOND": "#43506A",
    "MUTED": "#7C889E",
    "PRIMARY": "#3D5CE5",
    "PRIMARY_DARK": "#2C46C0",
    "PRIMARY_PRESSED": "#2C46C0",
    "PRIMARY_SOFT": "#EDF1FF",
    "PRIMARY_LINE": "#C7D3FF",
    "SUCCESS": "#0E9E70",
    "SUCCESS_SOFT": "#E9F8F2",
    "SUCCESS_LINE": "#BFE9DA",
    "DANGER": "#DB3F55",
    "DANGER_SOFT": "#FDEEF1",
    "DANGER_LINE": "#F7C9D1",
    "AMBER": "#B97A12",
    "AMBER_SOFT": "#FCF3E3",
    "AMBER_LINE": "#F0DCB4",
    "GRAD_A": "#4A6BF0",
    "GRAD_B": "#6A5AE8",
    "GRAD_A_HOVER": "#5878FF",
    "GRAD_B_HOVER": "#7A69F5",
    "OPTION_HOVER_BG": "#FAFBFF",
    "OPTION_SELECTED_BG": "#F2F5FF",
    "CORRECT_BG": "#EEFAF5",
    "WRONG_BG": "#FEF1F3",
    "MISSED_BG": "#F8FDFB",
    "BADGE_BG": "#F0F3FA",
    "BADGE_TEXT": "#5A6785",
    "BADGE_READONLY_BG": "#EAEFF8",
    "BADGE_READONLY_TEXT": "#98A4B8",
    "TEXT_DIM": "#94A0B4",
    "TEXT_READONLY": "#6F7C92",
    "SEG_HOVER": "#EEF2FB",
    "SEG_CHECKED_BG": "#FFFFFF",
    "SELECT_HOVER_BG": "#FCFDFF",
    "SELECT_DISABLED_TEXT": "#A6B0C2",
    "BTN_DISABLED_BG": "#DEE4F0",
    "BTN_DISABLED_TEXT": "#A3AEC2",
    "GHOST_HOVER_BG": "#F7FAFF",
    "GHOST_PRESSED_BG": "#EEF3FE",
    "GHOST_DISABLED_TEXT": "#B4BDCD",
    "LIST_HOVER_BG": "#F5F8FF",
    "PLACEHOLDER_BG": "#FCFDFF",
    "PLACEHOLDER_BORDER": "#E3E9F4",
    "PLACEHOLDER_TITLE": "#97A3B8",
    "PLACEHOLDER_TEXT": "#B3BDCD",
    "TRACK": "#EBEFF8",
    "RING_TRACK": "#E8EDF7",
    "SCROLL_HANDLE": "#D3DBEA",
    "SCROLL_HANDLE_HOVER": "#B7C3D8",
    "TOOLTIP_BG": "#1B2437",
    "TOOLTIP_TEXT": "#F4F6FB",
    "SEARCH_BG": "#FAFBFE",
    "SHADOW_RGB": (23, 43, 99),
    "SHADOW_ALPHA": 26,
    "SUN": "#E0A94A",
}

DARK = {
    "BG": "#0D1320",
    "SURFACE": "#161E2D",
    "SURFACE_SOFT": "#1B2434",
    "BORDER": "#26314A",
    "BORDER_STRONG": "#35425C",
    "TEXT": "#E9EEF9",
    "TEXT_SECOND": "#BAC6DA",
    "MUTED": "#8592A9",
    "PRIMARY": "#6C8BFF",
    "PRIMARY_DARK": "#A9BAFF",
    "PRIMARY_PRESSED": "#3D55C8",
    "PRIMARY_SOFT": "#1E2A48",
    "PRIMARY_LINE": "#394C82",
    "SUCCESS": "#35C79A",
    "SUCCESS_SOFT": "#12302A",
    "SUCCESS_LINE": "#215546",
    "DANGER": "#F2707F",
    "DANGER_SOFT": "#381C24",
    "DANGER_LINE": "#5A2A33",
    "AMBER": "#E0AA4C",
    "AMBER_SOFT": "#352815",
    "AMBER_LINE": "#54401D",
    "GRAD_A": "#4E6FE8",
    "GRAD_B": "#6E5CE2",
    "GRAD_A_HOVER": "#5C7BF5",
    "GRAD_B_HOVER": "#7C6BEE",
    "OPTION_HOVER_BG": "#1D2738",
    "OPTION_SELECTED_BG": "#1B2542",
    "CORRECT_BG": "#12302A",
    "WRONG_BG": "#361C24",
    "MISSED_BG": "#142C26",
    "BADGE_BG": "#232E42",
    "BADGE_TEXT": "#A6B4CB",
    "BADGE_READONLY_BG": "#1F293A",
    "BADGE_READONLY_TEXT": "#7B899E",
    "TEXT_DIM": "#6B788D",
    "TEXT_READONLY": "#95A2B7",
    "SEG_HOVER": "#222C3F",
    "SEG_CHECKED_BG": "#29344B",
    "SELECT_HOVER_BG": "#1C2637",
    "SELECT_DISABLED_TEXT": "#6A778C",
    "BTN_DISABLED_BG": "#232C3C",
    "BTN_DISABLED_TEXT": "#6E7B90",
    "GHOST_HOVER_BG": "#1E2838",
    "GHOST_PRESSED_BG": "#222D40",
    "GHOST_DISABLED_TEXT": "#5A6577",
    "LIST_HOVER_BG": "#1E2838",
    "PLACEHOLDER_BG": "#151D2B",
    "PLACEHOLDER_BORDER": "#2A3448",
    "PLACEHOLDER_TITLE": "#7E8CA3",
    "PLACEHOLDER_TEXT": "#6B7A91",
    "TRACK": "#26303F",
    "RING_TRACK": "#26303F",
    "SCROLL_HANDLE": "#2C3749",
    "SCROLL_HANDLE_HOVER": "#42506C",
    "TOOLTIP_BG": "#E9EEF9",
    "TOOLTIP_TEXT": "#111A28",
    "SEARCH_BG": "#1A2333",
    "SHADOW_RGB": (0, 0, 0),
    "SHADOW_ALPHA": 110,
    "SUN": "#F0BE69",
}

FONT_SCALES = {"small": 0.84, "medium": 1.0, "large": 1.30}
FONT_LABELS = {"small": "小", "medium": "中", "large": "大"}

_current = dict(LIGHT)
_mode = "light"
_font_scale = 1.0
_font_level = "medium"
_shadows: list[tuple[weakref.ref, QGraphicsDropShadowEffect, int]] = []


def mode() -> str:
    return _mode


def is_dark() -> bool:
    return _mode == "dark"


def font_level() -> str:
    return _font_level


def font_scale() -> float:
    return _font_scale


def layout_scale() -> float:
    """固定宽度控件（侧栏、统计面板）随字号放大，但只放大一半幅度。"""
    return 1.0 + max(0.0, _font_scale - 1.0) * 0.5


def set_font_scale(level: str) -> None:
    global _font_scale, _font_level
    _font_level = level if level in FONT_SCALES else "medium"
    _font_scale = FONT_SCALES[_font_level]


def set_mode(value: str) -> None:
    global _current, _mode
    _mode = "dark" if value == "dark" else "light"
    _current = dict(DARK if _mode == "dark" else LIGHT)


def __getattr__(name: str):
    """让 `theme.TEXT` 之类的常量访问始终返回当前调色板的颜色。"""
    if name in _current:
        return _current[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def app_palette() -> QPalette:
    """全局 QPalette：让 QMessageBox、菜单勾选标记、输入框光标等原生控件跟随主题。"""
    p = _current
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(p["BG"]))
    pal.setColor(QPalette.WindowText, QColor(p["TEXT"]))
    pal.setColor(QPalette.Base, QColor(p["SURFACE"]))
    pal.setColor(QPalette.AlternateBase, QColor(p["SURFACE_SOFT"]))
    pal.setColor(QPalette.Text, QColor(p["TEXT"]))
    pal.setColor(QPalette.Button, QColor(p["SURFACE"]))
    pal.setColor(QPalette.ButtonText, QColor(p["TEXT"]))
    pal.setColor(QPalette.BrightText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase, QColor(p["TOOLTIP_BG"]))
    pal.setColor(QPalette.ToolTipText, QColor(p["TOOLTIP_TEXT"]))
    pal.setColor(QPalette.Highlight, QColor(p["PRIMARY"]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.PlaceholderText, QColor(p["MUTED"]))
    pal.setColor(QPalette.Link, QColor(p["PRIMARY"]))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        pal.setColor(QPalette.Disabled, role, QColor(p["GHOST_DISABLED_TEXT"]))
    return pal


def base_font(size: int = 10, weight: int = 400) -> QFont:
    f = QFont()
    f.setFamilies([FONT_FAMILY, "Microsoft YaHei", "Segoe UI", "PingFang SC"])
    f.setPointSizeF(size * _font_scale)
    f.setWeight(QFont.Weight(weight))
    f.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    return f


def _shadow_color(alpha: int) -> QColor:
    r, g, b = _current["SHADOW_RGB"]
    return QColor(r, g, b, alpha)


def apply_shadow(widget: QWidget, blur: int = 26, dy: int = 6, alpha: int = 26) -> None:
    """给卡片加一层柔和投影（Qt 无 box-shadow，用图形效果实现）。"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(_shadow_color(alpha))
    widget.setGraphicsEffect(effect)
    _shadows.append((weakref.ref(widget), effect, alpha))


def refresh_shadows() -> None:
    """切换主题后按当前调色板刷新投影颜色。"""
    alive = []
    for ref, effect, alpha in _shadows:
        widget = ref()
        if widget is None:
            continue
        effect.setColor(_shadow_color(alpha))
        widget.update()
        alive.append((ref, effect, alpha))
    _shadows[:] = alive


# ------------------------------------------------------------------ 样式表
def qss() -> str:
    p = _current

    def fs(value: float) -> str:
        scaled = round(value * _font_scale, 1)
        return (f"{scaled:.1f}").rstrip("0").rstrip(".")

    return f"""
    QWidget {{
        color: {p['TEXT']};
        font-family: "{FONT_FAMILY}", "Microsoft YaHei", "Segoe UI";
        font-size: {fs(10)}pt;
    }}
    QMainWindow, QWidget#root {{ background: {p['BG']}; }}
    QWidget#sidebar {{ background: {p['SURFACE']}; border-right: 1px solid {p['BORDER']}; }}

    QFrame#card {{
        background: {p['SURFACE']};
        border: 1px solid {p['BORDER']};
        border-radius: 18px;
    }}
    QFrame#softCard {{
        background: {p['SURFACE_SOFT']};
        border: 1px solid {p['BORDER']};
        border-radius: 16px;
    }}
    QFrame#hline {{ background: {p['BORDER']}; border: none; max-height: 1px; min-height: 1px; }}

    QLabel#brandTitle {{ font-size: {fs(19)}pt; font-weight: 700; color: {p['TEXT']}; }}
    QLabel#brandSub {{ color: {p['MUTED']}; font-size: {fs(9)}pt; }}
    QLabel#sectionLabel {{
        color: {p['MUTED']}; font-size: {fs(9)}pt; font-weight: 600;
        letter-spacing: 0.6px;
    }}
    QLabel#stem {{ font-size: {fs(13)}pt; color: {p['TEXT']}; }}
    QLabel#qmeta {{ color: {p['MUTED']}; font-size: {fs(9)}pt; }}
    QLabel#hint {{ color: {p['MUTED']}; font-size: {fs(9)}pt; }}
    QLabel#feedbackTitle {{ font-size: {fs(11)}pt; font-weight: 700; }}
    QLabel#feedbackTitle[result="ok"] {{ color: {p['SUCCESS']}; }}
    QLabel#feedbackTitle[result="bad"] {{ color: {p['DANGER']}; }}
    QLabel#feedbackLine {{ color: {p['TEXT_SECOND']}; font-size: {fs(9.5)}pt; }}
    QLabel#explainTitle {{ color: {p['MUTED']}; font-size: {fs(9)}pt; font-weight: 600; }}
    QLabel#explainText {{ color: {p['TEXT_SECOND']}; font-size: {fs(10)}pt; }}
    QLabel#scheduleText {{ color: {p['MUTED']}; font-size: {{fs(9)}}pt; }}
    QLabel#glossaryTerm {{ color: {p['PRIMARY_DARK']}; font-size: {fs(9.5)}pt; font-weight: 600; }}
    QLabel#glossaryText {{ color: {p['TEXT_SECOND']}; font-size: {fs(9.5)}pt; }}
    QLabel#bigNum {{ font-size: {fs(20)}pt; font-weight: 700; color: {p['TEXT']}; }}
    QLabel#tileName {{ color: {p['MUTED']}; font-size: {fs(9)}pt; }}
    QLabel#emptyTitle {{ color: {p['TEXT_SECOND']}; font-size: {fs(12)}pt; font-weight: 600; }}
    QLabel#emptyText {{ color: {p['MUTED']}; font-size: {fs(9.5)}pt; }}
    QLabel#emptyMark {{
        background: {p['SURFACE_SOFT']};
        border: 1px solid {p['BORDER']};
        border-radius: 23px;
        color: {p['MUTED']};
        font-size: {fs(16)}pt;
        font-weight: 700;
    }}
    QLabel#fbNote {{
        color: {p['AMBER']};
        background: {p['AMBER_SOFT']};
        border: 1px solid {p['AMBER_LINE']};
        border-radius: 8px;
        padding: 8px 10px;
    }}

    QLabel#chip {{
        border-radius: 9px;
        padding: 0px 10px;
        font-size: {fs(9)}pt;
        background: {p['SURFACE_SOFT']};
        color: {p['TEXT_SECOND']};
        border: 1px solid {p['BORDER']};
    }}
    QLabel#chip[kind="primary"] {{
        background: {p['PRIMARY_SOFT']}; color: {p['PRIMARY_DARK']}; border-color: {p['PRIMARY_LINE']};
    }}
    QLabel#chip[kind="success"] {{
        background: {p['SUCCESS_SOFT']}; color: {p['SUCCESS']}; border-color: {p['SUCCESS_LINE']};
    }}
    QLabel#chip[kind="danger"] {{
        background: {p['DANGER_SOFT']}; color: {p['DANGER']}; border-color: {p['DANGER_LINE']};
    }}
    QLabel#chip[kind="amber"] {{
        background: {p['AMBER_SOFT']}; color: {p['AMBER']}; border-color: {p['AMBER_LINE']};
    }}

    QFrame#segment {{ background: {p['SURFACE_SOFT']}; border: 1px solid {p['BORDER']}; border-radius: 13px; }}
    QPushButton#segBtn {{
        background: transparent; border: none; border-radius: 10px;
        padding: 7px 6px; color: {p['TEXT_SECOND']}; font-size: {fs(9.5)}pt;
    }}
    QPushButton#segBtn:hover {{ background: {p['SEG_HOVER']}; }}
    QPushButton#segBtn:checked {{
        background: {p['SEG_CHECKED_BG']}; color: {p['PRIMARY_DARK']}; font-weight: 700;
        border: 1px solid {p['PRIMARY_LINE']};
    }}

    QFrame#select {{ background: {p['SURFACE']}; border: 1px solid {p['BORDER_STRONG']}; border-radius: 12px; }}
    QFrame#select:hover {{ border-color: {p['PRIMARY_LINE']}; background: {p['SELECT_HOVER_BG']}; }}
    QFrame#select[open="true"] {{ border-color: {p['PRIMARY']}; }}
    QFrame#select[disabled="true"] {{ background: {p['SURFACE_SOFT']}; border-color: {p['BORDER']}; }}
    QLabel#selectValue {{ color: {p['TEXT']}; font-size: {fs(9.5)}pt; }}
    QLabel#selectValue[disabled="true"] {{ color: {p['SELECT_DISABLED_TEXT']}; }}
    QLabel#selectArrow {{ color: {p['MUTED']}; font-size: {fs(9)}pt; }}

    QFrame#option {{ background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; border-radius: 14px; }}
    QFrame#option[state="hover"] {{ border-color: {p['PRIMARY_LINE']}; background: {p['OPTION_HOVER_BG']}; }}
    QFrame#option[state="selected"] {{ border: 2px solid {p['PRIMARY']}; background: {p['OPTION_SELECTED_BG']}; }}
    QFrame#option[state="correct"] {{ border: 2px solid {p['SUCCESS']}; background: {p['CORRECT_BG']}; }}
    QFrame#option[state="wrong"] {{ border: 2px solid {p['DANGER']}; background: {p['WRONG_BG']}; }}
    QFrame#option[state="missed"] {{ border: 2px dashed {p['SUCCESS']}; background: {p['MISSED_BG']}; }}
    QFrame#option[state="readonly"] {{ background: {p['SURFACE_SOFT']}; border-color: {p['BORDER']}; }}

    QLabel#badge {{
        border-radius: 13px; background: {p['BADGE_BG']}; color: {p['BADGE_TEXT']};
        font-size: {fs(10)}pt; font-weight: 700;
    }}
    QLabel#badge[state="selected"] {{ background: {p['PRIMARY']}; color: #FFFFFF; }}
    QLabel#badge[state="correct"] {{ background: {p['SUCCESS']}; color: #FFFFFF; }}
    QLabel#badge[state="wrong"] {{ background: {p['DANGER']}; color: #FFFFFF; }}
    QLabel#badge[state="missed"] {{ background: {p['SURFACE']}; color: {p['SUCCESS']}; border: 1px solid {p['SUCCESS']}; }}
    QLabel#badge[state="readonly"] {{ background: {p['BADGE_READONLY_BG']}; color: {p['BADGE_READONLY_TEXT']}; }}

    QLabel#optionText {{ font-size: {fs(10.5)}pt; color: {p['TEXT']}; }}
    QLabel#optionText[state="dim"] {{ color: {p['TEXT_DIM']}; }}
    QLabel#optionText[state="readonly"] {{ color: {p['TEXT_READONLY']}; }}

    QFrame#placeholder {{
        background: {p['PLACEHOLDER_BG']};
        border: 1px dashed {p['PLACEHOLDER_BORDER']};
        border-radius: 14px;
    }}
    QLabel#placeholderTitle {{ color: {p['PLACEHOLDER_TITLE']}; font-size: {fs(10)}pt; }}
    QLabel#placeholderText {{ color: {p['PLACEHOLDER_TEXT']}; font-size: {fs(9)}pt; }}
    QFrame#feedback {{ border-radius: 14px; border: 1px solid {p['BORDER']}; background: {p['SURFACE_SOFT']}; }}
    QFrame#feedback[result="ok"] {{ background: {p['SUCCESS_SOFT']}; border-color: {p['SUCCESS_LINE']}; }}
    QFrame#feedback[result="bad"] {{ background: {p['DANGER_SOFT']}; border-color: {p['DANGER_LINE']}; }}

    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p['GRAD_A']}, stop:1 {p['GRAD_B']});
        color: #FFFFFF; border: none; border-radius: 12px;
        padding: 10px 24px; font-size: {fs(10.5)}pt; font-weight: 700;
    }}
    QPushButton#primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p['GRAD_A_HOVER']}, stop:1 {p['GRAD_B_HOVER']});
    }}
    QPushButton#primary:pressed {{ background: {p['PRIMARY_PRESSED']}; }}
    QPushButton#primary:disabled {{ background: {p['BTN_DISABLED_BG']}; color: {p['BTN_DISABLED_TEXT']}; }}

    QPushButton#ghost {{
        background: {p['SURFACE']}; color: {p['TEXT_SECOND']};
        border: 1px solid {p['BORDER_STRONG']}; border-radius: 12px;
        padding: 9px 18px; font-size: {fs(10)}pt;
    }}
    QPushButton#ghost:hover {{
        background: {p['GHOST_HOVER_BG']}; border-color: {p['PRIMARY_LINE']}; color: {p['PRIMARY_DARK']};
    }}
    QPushButton#ghost:pressed {{ background: {p['GHOST_PRESSED_BG']}; }}
    QPushButton#ghost:checked {{
        background: {p['PRIMARY_SOFT']}; border-color: {p['PRIMARY_LINE']}; color: {p['PRIMARY_DARK']};
    }}
    QPushButton#ghost:disabled {{
        color: {p['GHOST_DISABLED_TEXT']}; border-color: {p['BORDER']}; background: {p['SURFACE_SOFT']};
    }}

    QPushButton#chipBtn {{
        background: {p['SURFACE']}; border: 1px solid {p['BORDER_STRONG']};
        border-radius: 11px; color: {p['TEXT_SECOND']};
        font-size: {{fs(10)}}pt; font-weight: 700;
    }}
    QPushButton#chipBtn:hover {{
        background: {p['PRIMARY_SOFT']}; border-color: {p['PRIMARY_LINE']}; color: {p['PRIMARY_DARK']};
    }}

    QPushButton#link {{
        background: transparent; border: none; color: {p['MUTED']};
        padding: 4px 2px; font-size: {fs(9)}pt;
    }}
    QPushButton#link:hover {{ color: {p['PRIMARY']}; }}

    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px 2px 2px 0; }}
    QScrollBar::handle:vertical {{
        background: {p['SCROLL_HANDLE']}; border-radius: 4px; min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['SCROLL_HANDLE_HOVER']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{ height: 0; }}

    QMenu {{
        background: {p['SURFACE']}; border: 1px solid {p['BORDER']};
        border-radius: 12px; padding: 6px;
    }}
    QMenu::item {{
        padding: 8px 30px 8px 12px; border-radius: 8px;
        color: {p['TEXT_SECOND']}; font-size: {fs(9.5)}pt;
    }}
    QMenu::item:selected {{ background: {p['PRIMARY_SOFT']}; color: {p['PRIMARY_DARK']}; }}
    QMenu::separator {{ height: 1px; background: {p['BORDER']}; margin: 5px 8px; }}

    QFrame#popupCard {{
        background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; border-radius: 14px;
    }}
    QLineEdit#popupSearch {{
        background: {p['SEARCH_BG']}; border: 1px solid {p['BORDER']}; border-radius: 9px;
        padding: 6px 10px; color: {p['TEXT']}; font-size: {fs(9.5)}pt;
        selection-background-color: {p['PRIMARY_SOFT']}; selection-color: {p['PRIMARY_DARK']};
    }}
    QLineEdit#popupSearch:focus {{ border-color: {p['PRIMARY_LINE']}; background: {p['SURFACE']}; }}
    QListWidget#popupList {{
        border: none; background: transparent; outline: none; font-size: {fs(9.5)}pt;
    }}
    QListWidget#popupList::item {{
        padding: 6px 9px; border-radius: 8px; color: {p['TEXT_SECOND']};
    }}
    QListWidget#popupList::item:hover {{ background: {p['LIST_HOVER_BG']}; }}
    QListWidget#popupList::item:selected {{
        background: {p['PRIMARY_SOFT']}; color: {p['PRIMARY_DARK']};
    }}

    QToolTip {{
        background: {p['TOOLTIP_BG']}; color: {p['TOOLTIP_TEXT']}; border: none;
        padding: 6px 9px; border-radius: 6px; font-size: {fs(9)}pt;
    }}

    QFrame#wrongItem {{ background: transparent; border: none; border-radius: 10px; margin: 0; }}
    QFrame#wrongItem:hover {{ background: {p['PRIMARY_SOFT']}; }}
    QLabel#wrongStem {{ color: {p['TEXT_SECOND']}; font-size: {fs(9)}pt; }}
    QLabel#wrongMeta {{ color: {p['MUTED']}; font-size: {fs(8.5)}pt; }}
    """
