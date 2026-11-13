"""Presentation tokens from the approved redesign; no application settings here."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QObject, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton, QTextBrowser

ASSETS = Path(__file__).resolve().parents[1] / "docs" / "redesign" / "assets"
LIGHT = dict(
    page="#F1F1F3", bg="#FFFFFF", bg_sunken="#FAFAFA", bg_elevated="#FFFFFF",
    fg="#101014", fg_muted="#5F5F6B", fg_subtle="#6F6D7A",
    border="#E3E3E8", border_strong="#D2D2DA",
    red="#C81E33", red_hover="#A8162A", red_bright="#F0394E",
    red_soft="#FCEDEF", red_ink="#8E1224", gold="#A9761D", gold_soft="#FBF3E2",
    green="#0F7A57", green_soft="#E8F6F0", amber="#9A6A0B", amber_soft="#FDF4E3",
    ball_bg="#FFFFFF", ball_ring="#E4DEE7", ball_hit="#C81E33", on_red="#FFFFFF",
    card_top="#FFFFFF", card_mid="#FFFFFF", card_end="#F5F4F8",
    edge_top="#FFFFFF", edge_mid="#E4DCE3", edge_end="#DFDFE8",
    hero_top="#FFF7F7", hero_mid="#FFFFFF", hero_end="#F5F2F6",
    cta_top="#D9324C", cta_mid="#C71D38", cta_end="#A5122E",
    cta_hover_top="#CE2F48", cta_hover_mid="#BD1C35", cta_hover_end="#9D112C",
    active_top="#F8DFE5", active_mid="#FBEDEF", active_end="#FFF6F7",
    ball_top="#FFFFFF", ball_mid="#F5F2F6", ball_end="#E9E6EE",
    rail_end="#FFF6F7", page_glow="#F7EDEF",
)
DARK = dict(
    page="#06060A", bg="#0F0F13", bg_sunken="#0A0A0D", bg_elevated="#16161C",
    fg="#F4F4F6", fg_muted="#B3AFBE", fg_subtle="#9A96A7",
    border="#232329", border_strong="#33333D",
    red="#FF3B4E", red_hover="#FF5F70", red_bright="#FF6B7B",
    red_soft="#2A1116", red_ink="#FF8A96", gold="#F2C05C", gold_soft="#2A2314",
    green="#34D399", green_soft="#0F2A22", amber="#F0B84E", amber_soft="#2A2213",
    ball_bg="#1A1A20", ball_ring="#45404F", ball_hit="#FF3B4E", on_red="#18050B",
    card_top="#1B1A24", card_mid="#14141C", card_end="#101117",
    edge_top="#4B3544", edge_mid="#34303F", edge_end="#24252E",
    hero_top="#2A1924", hero_mid="#19151E", hero_end="#12131B",
    cta_top="#FF7385", cta_mid="#FF4D67", cta_end="#F23554",
    cta_hover_top="#FF788A", cta_hover_mid="#FF506B", cta_hover_end="#FC3757",
    active_top="#481E2B", active_mid="#2A1721", active_end="#1F151D",
    ball_top="#35313E", ball_mid="#24232D", ball_end="#16171F",
    rail_end="#161017", page_glow="#24101A",
)


@lru_cache(maxsize=256)
def themed_icon(name, color, size=20):
    path = ASSETS / ("icon-" + name + ".svg")
    svg = path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


class KeyboardFocusStyle(QObject):
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FocusIn:
            if event.reason() in (Qt.FocusReason.ActiveWindowFocusReason, Qt.FocusReason.PopupFocusReason):
                return False
            visible = event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason,
                                         Qt.FocusReason.ShortcutFocusReason)
        elif event.type() == QEvent.Type.MouseButtonPress:
            visible = False
        else:
            return False
        # Text browser clicks arrive at its viewport even when the browser already has focus.
        control = watched if isinstance(watched, (QPushButton, QTextBrowser)) else watched.parentWidget()
        if bool(control.property("keyboardFocus")) != visible:
            control.setProperty("keyboardFocus", visible)
            style = control.style()
            style.unpolish(control)
            style.polish(control)
            control.update()
        return False


def build_qss(tokens):
    return """
    QWidget {{ font-family:'Segoe UI Variable Text','Segoe UI'; font-size:12px; color:{fg}; }}
    QMainWindow, QWidget#workspace, QStackedWidget, QScrollArea {{ background:{page}; }}
    QDialog#policyDialog, QDialog#gameGuide, QDialog#onboardingDialog {{ background:{bg}; border:1px solid {border_strong}; }}
    QWidget#tourDetail {{ background:{bg}; }}
    QLabel#tourStepTitle {{ font-size:24px; font-weight:650; }}
    QListWidget#tourNavigation {{ background:{bg_elevated}; border:0; border-right:1px solid {border}; padding:12px 8px; outline:0; }}
    QListWidget#tourNavigation::item {{ border:1px solid transparent; padding:0 8px; border-radius:8px; }}
    QListWidget#tourNavigation::item:selected {{ background:{red_soft}; color:{red_ink}; border-color:{border_strong}; font-weight:650; }}
    QWidget#canvas {{ background:qradialgradient(cx:0.8, cy:0, radius:0.85, fx:0.8, fy:0, stop:0 {page_glow}, stop:0.58 {page}, stop:1 {page}); }}
    QLabel {{ background:transparent; border:0; }}
    QLabel#title {{ font-size:21px; font-weight:650; }}
    QLabel#brand {{ font-size:14px; font-weight:650; }}
    QLabel#subtle, QLabel#description {{ color:{fg_muted}; font-size:12px; }}
    QLabel#caption {{ color:{fg_subtle}; font-size:10px; }}
    QLabel#sectionTitle {{ font-size:13px; font-weight:650; }}
    QLabel#statValue {{ font-size:27px; font-weight:650; }}
    QLabel#mono {{ font-family:'Cascadia Mono','Consolas'; font-size:11px; }}
    QLabel#metric {{ font-size:19px; font-weight:650; }}
    QFrame#sidebar {{ background:qlineargradient(x1:0, y1:0, x2:0.15, y2:1, stop:0 {bg}, stop:0.65 {bg}, stop:1 {rail_end}); border-right:1px solid {border}; }}
    QFrame#topline {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0.1, stop:0.3 {bg}, stop:1 {bg_elevated}); border-bottom:1px solid {border}; }}
    QFrame#contextDot {{ background:{green}; border:0; border-radius:3px; }}
    QFrame#statusbar {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {bg}, stop:1 {bg_elevated}); border-top:1px solid {border}; }}
    QFrame#card, QFrame#surface {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {card_top}, stop:0.48 {card_mid}, stop:1 {card_end});
      border:1px solid; border-color:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {edge_top}, stop:0.4 {edge_mid}, stop:1 {edge_end}); border-radius:14px; }}
    QFrame#card[hero="true"] {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {hero_top}, stop:0.45 {hero_mid}, stop:1 {hero_end}); }}
    QFrame#separator {{ background:{border}; border:0; max-height:1px; }}
    QFrame#footer {{ border-top:1px solid {border}; background:transparent; }}
    QFrame#segmented {{ background:{bg_sunken}; border:1px solid {border}; border-radius:8px; }}
    QPushButton {{ background:{bg}; border:1px solid {border_strong}; border-radius:8px;
      padding:0 12px; min-height:32px; font-size:12px; font-weight:550; }}
    QPushButton:hover {{ background:{bg_sunken}; border-color:{fg_subtle}; }}
    QPushButton:pressed {{ background:{red_soft}; }}
    QPushButton#primary {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0.55, stop:0 {cta_top}, stop:0.55 {cta_mid}, stop:1 {cta_end}); border-color:transparent; color:{on_red}; font-weight:650; }}
    QPushButton#primary:hover {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0.55, stop:0 {cta_hover_top}, stop:0.55 {cta_hover_mid}, stop:1 {cta_hover_end}); }}
    QPushButton#primary:pressed {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0.55, stop:0 {cta_end}, stop:1 {cta_mid}); }}
    QPushButton#quiet {{ border-color:transparent; background:transparent; color:{fg_muted}; padding:0 6px; }}
    QPushButton#quiet:hover {{ background:{bg_sunken}; color:{red}; }}
    QPushButton:disabled {{ background:{bg_sunken}; color:{fg_subtle}; border-color:{border}; }}
    QPushButton#primary:disabled {{ background:{bg_sunken}; color:{fg_subtle}; border-color:{border}; }}
    QPushButton#segment {{ border:0; background:transparent; min-height:26px; padding:0 10px; color:{fg_muted}; font-size:11px; border-radius:6px; }}
    QPushButton#segment:checked {{ background:{bg_elevated}; color:{fg}; font-weight:650; }}
    QPushButton#themeToggle {{ background:{bg_sunken}; color:{fg_muted}; border-color:{border}; text-align:left; font-size:11px; min-height:30px; }}
    QPushButton#sidebarToggle {{ background:transparent; border:1px solid transparent; padding:0; min-height:30px; border-radius:8px; }}
    QPushButton#sidebarToggle:hover {{ background:{bg_sunken}; border-color:{border}; }}
    QPushButton#dayNightToggle {{ background:transparent; border:1px solid transparent; padding:0; min-height:30px; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {{ border:1px solid {red}; }}
    QComboBox, QLineEdit, QSpinBox, QTimeEdit {{ background:{bg}; border:1px solid {border_strong};
      border-radius:8px; padding:0 10px; min-height:32px; selection-background-color:{red}; selection-color:{on_red}; }}
    QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QTimeEdit:hover {{ border-color:{fg_subtle}; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QTimeEdit:disabled {{ color:{fg_subtle}; background:{bg_sunken}; }}
    QComboBox {{ padding-right:26px; }}
    QComboBox::drop-down {{ width:24px; border:0; }}
    QComboBox::down-arrow, QSpinBox::up-arrow, QSpinBox::down-arrow {{ image:none; }}
    QComboBox QAbstractItemView {{ background:{bg_elevated}; color:{fg}; selection-background-color:{red_soft}; selection-color:{red_ink}; border:1px solid {border}; padding:4px; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width:18px; border:0; }}
    QTableWidget {{ background:{bg}; alternate-background-color:{bg}; border:0; border-radius:8px; gridline-color:{border};
      selection-background-color:{red_soft}; selection-color:{fg}; outline:0; }}
    QTableWidget::item {{ border-bottom:1px solid {border}; padding:4px 12px; }}
    QTableWidget::item:hover {{ background:{bg_sunken}; }}
    QTableWidget::item:selected {{ background:{red_soft}; color:{fg}; }}
    QHeaderView {{ background:{bg_sunken}; }}
    QHeaderView::section {{ background:{bg_sunken}; color:{fg_subtle}; font-size:10px; font-weight:650;
      border:0; border-bottom:1px solid {border}; padding:9px 12px; text-align:left; }}
    QTableCornerButton::section {{ background:{bg_sunken}; border:0; }}
    QTextBrowser {{ background:{bg_sunken}; border:1px solid {border}; border-radius:8px; padding:12px; color:{fg_muted}; selection-background-color:{red_soft}; }}
    QTextBrowser#report {{ font-family:'Cascadia Mono','Consolas'; font-size:11px; }}
    QPushButton[keyboardFocus="true"]:focus, QTextBrowser[keyboardFocus="true"]:focus,
    QPushButton#primary[keyboardFocus="true"]:focus, QPushButton#quiet[keyboardFocus="true"]:focus,
    QPushButton#segment[keyboardFocus="true"]:focus, QPushButton#themeToggle[keyboardFocus="true"]:focus,
    QPushButton#sidebarToggle[keyboardFocus="true"]:focus,
    QPushButton#dayNightToggle[keyboardFocus="true"]:focus {{ border:1px solid {red}; }}
    QListWidget#navigation {{ background:transparent; border:0; outline:0; }}
    QProgressBar {{ background:{bg_sunken}; border:0; border-radius:2px; height:4px; max-height:4px; }}
    QProgressBar::chunk {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {cta_top}, stop:1 {cta_end}); border-radius:2px; }}
    QScrollBar:vertical {{ background:transparent; width:8px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{border_strong}; min-height:28px; border-radius:3px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
    QToolTip {{ background:{bg_elevated}; color:{fg}; border:1px solid {border}; padding:6px; }}
    QLabel#badge {{ background:{bg_sunken}; color:{fg_muted}; border:1px solid {border}; border-radius:6px; padding:0 7px; font-size:10px; font-weight:600; }}
    QLabel#badge[variant="red"] {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {red_soft}, stop:1 {bg_elevated}); color:{red_ink}; border-color:{red_soft}; }}
    QLabel#badge[variant="gold"] {{ background:{gold_soft}; color:{gold}; border-color:transparent; }}
    QLabel#badge[variant="green"] {{ background:{green_soft}; color:{green}; border-color:transparent; }}
    QLabel#badge[variant="amber"] {{ background:{amber_soft}; color:{amber}; border-color:transparent; }}
    QFrame#callout {{ background:{amber_soft}; border:1px solid transparent; border-radius:8px; }}
    QFrame#callout QLabel {{ color:{amber}; font-size:11px; }}
    QFrame#callout[variant="info"] {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0.3, stop:0 {bg_sunken}, stop:1 {bg_elevated}); border-color:{border}; }}
    QFrame#callout[variant="info"] QLabel {{ color:{fg_muted}; }}
    QFrame#callout[variant="success"] {{ background:{green_soft}; }}
    QFrame#callout[variant="success"] QLabel {{ color:{green}; }}
    """.format(**tokens)


def apply_theme(widget, name):
    tokens = DARK if name == "dark" else LIGHT
    widget.setStyleSheet(build_qss(tokens))
    if not hasattr(widget, "_keyboard_focus_style"):
        widget._keyboard_focus_style = KeyboardFocusStyle(widget)
    focus_style = widget._keyboard_focus_style
    for button in widget.findChildren(QPushButton):
        button.installEventFilter(focus_style)
    for browser in widget.findChildren(QTextBrowser):
        browser.installEventFilter(focus_style)
        browser.viewport().installEventFilter(focus_style)
    palette = widget.palette()
    for role, token in ((QPalette.ColorRole.Window, "bg"), (QPalette.ColorRole.Base, "bg"),
                        (QPalette.ColorRole.Text, "fg"), (QPalette.ColorRole.WindowText, "fg"),
                        (QPalette.ColorRole.ButtonText, "fg"), (QPalette.ColorRole.Button, "bg"),
                        (QPalette.ColorRole.Highlight, "red"), (QPalette.ColorRole.HighlightedText, "on_red"),
                        (QPalette.ColorRole.PlaceholderText, "fg_subtle")):
        palette.setColor(role, QColor(tokens[token]))
    widget.setPalette(palette)
    widget.setFont(QFont(["Segoe UI Variable Text", "Segoe UI"], 9))
    return tokens
