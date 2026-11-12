"""Offline illustrated first-run tour, matching the approved HTML preview."""
import json
from html import escape
from pathlib import Path

from PySide6.QtCore import QIODevice, QRectF, QSaveFile, QSize, Qt
from PySide6.QtGui import QColor, QImageReader, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .policy import PolicyBackdrop
from .storage import data_directory
from .theme import apply_theme
from .widgets import label

ASSETS = Path(__file__).resolve().parents[1] / "docs" / "redesign" / "onboarding" / "assets"
SCREENS = ("overview", "history", "stats", "odds", "suggest", "verify", "ai", "auto")


class GuidePicture(QWidget):
    def __init__(self, tokens):
        super().__init__()
        self.tokens = tokens
        self.pixmap = QPixmap()
        self.marks = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_picture(self, path, marks, title):
        self.pixmap = QPixmap(str(path))
        if self.pixmap.isNull():
            raise ValueError("Missing tutorial image")
        self.marks = marks
        self.setAccessibleName(title)
        self.updateGeometry()
        self.update()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return min(310, round(width * self.pixmap.height() / max(1, self.pixmap.width()))) + 20

    def sizeHint(self):
        return QSize(740, self.heightForWidth(740))

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        size = self.pixmap.size().toSizeF()
        size.scale(self.width() - 20, self.height() - 20, Qt.AspectRatioMode.KeepAspectRatio)
        # Do not upscale raster content beyond its native pixel count on high-DPI displays.
        if size.width() * self.devicePixelRatioF() > self.pixmap.width():
            size = self.pixmap.size().toSizeF() / self.devicePixelRatioF()
        target = QRectF((self.width() - size.width()) / 2, 10, size.width(), size.height())
        painter.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))
        scale = size.width() / self.pixmap.width()
        for number, (x, y, width, height) in enumerate(self.marks, 1):
            rect = QRectF(target.x() + x*scale, target.y() + y*scale, width*scale, height*scale)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self.tokens["red"]), 1.5))
            painter.drawRoundedRect(rect, 4, 4)
            marker = QRectF(rect.x() - 8, rect.y() - 8, 19, 19)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.tokens["red"]))
            painter.drawEllipse(marker)
            painter.setPen(QColor(self.tokens["on_red"]))
            painter.drawText(marker, Qt.AlignmentFlag.AlignCenter, str(number))


class OnboardingDialog(QDialog):
    def __init__(self, window, from_help=False):
        super().__init__(window, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        data = json.loads((ASSETS / "guide.json").read_text(encoding="utf-8"))
        self.copy = data["copy"][window.language]
        self.steps = self.copy["steps"]
        self.shots = data["shots"]
        self.prefix = window.language + "-" + window.theme_name + "-"
        if any(not QImageReader(str(ASSETS / (self.prefix + screen + ".webp"))).canRead() for screen in SCREENS):
            raise ValueError("Missing tutorial images")
        self.from_help = from_help
        self.setObjectName("onboardingDialog")
        self.setWindowTitle(self.copy["tour"])
        self.setAccessibleName(self.copy["tour"])
        available = window.screen().availableGeometry()
        self.resize(min(1120, available.width() - 40, max(920, window.width() - 32)),
                    min(670, available.height() - 48))
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        header = QHBoxLayout(); header.setContentsMargins(22, 16, 22, 16); header.setSpacing(12)
        logo = QLabel(); logo.setPixmap(window.windowIcon().pixmap(32, 32)); header.addWidget(logo)
        title = label(self.copy["tour"], "title", reserve_wrapped_height=False)
        header.addWidget(title); header.addStretch()
        self.counter = label("", "subtle", reserve_wrapped_height=False); header.addWidget(self.counter)
        root.addLayout(header)
        self.progress = QProgressBar(); self.progress.setRange(0, 8); self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3); root.addWidget(self.progress)
        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)
        self.nav = QListWidget(); self.nav.setObjectName("tourNavigation"); self.nav.setFixedWidth(210)
        self.nav.setAccessibleName(self.copy["tour"])
        for index, name in enumerate(self.copy["nav"], 1):
            item = QListWidgetItem(f"{index}   {name}"); item.setSizeHint(QSize(190, 43)); self.nav.addItem(item)
        body.addWidget(self.nav)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail = QWidget(); detail.setObjectName("tourDetail")
        layout = QVBoxLayout(detail); layout.setContentsMargins(22, 18, 22, 18); layout.setSpacing(10)
        self.title = label("", "tourStepTitle", reserve_wrapped_height=False)
        self.lead = label("", "description", reserve_wrapped_height=False)
        layout.addWidget(self.title); layout.addWidget(self.lead)
        self.picture = GuidePicture(window.tokens); layout.addWidget(self.picture)
        self.instructions = label("", reserve_wrapped_height=False)
        self.instructions.setTextFormat(Qt.TextFormat.RichText); layout.addWidget(self.instructions)
        self.note = label("", "caption", reserve_wrapped_height=False); layout.addWidget(self.note); layout.addStretch()
        self.scroll.setWidget(detail); body.addWidget(self.scroll, 1); root.addLayout(body, 1)
        footer = QHBoxLayout(); footer.setContentsMargins(22, 14, 22, 14); footer.setSpacing(8)
        close_text = ("Đóng" if window.language == "vi" else "Close") if from_help else self.copy["skip"]
        self.skip = QPushButton(close_text); self.skip.setObjectName("quiet"); self.skip.clicked.connect(self.reject)
        footer.addWidget(self.skip); footer.addStretch()
        self.previous = QPushButton(self.copy["back"]); self.next = QPushButton(); self.next.setObjectName("primary")
        for button in (self.skip, self.previous, self.next):
            button.setAutoDefault(False)
        self.previous.clicked.connect(lambda: self.nav.setCurrentRow(self.nav.currentRow() - 1))
        self.next.clicked.connect(self.advance)
        footer.addWidget(self.previous); footer.addWidget(self.next); root.addLayout(footer)
        self.nav.currentRowChanged.connect(self.show_step)
        self.nav.setCurrentRow(0)
        apply_theme(self, window.theme_name)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus); self.setFocus()

    def show_step(self, index):
        title, lead, actions, note = self.steps[index]
        self.title.setText(title); self.lead.setText(lead); self.note.setText(note)
        color = self.parentWidget().tokens["red"]
        self.instructions.setText("<br>".join(
            f'<span style="color:{color}">{number}.</span>  <b>{escape(action)}</b>'
            for number, action in enumerate(actions, 1)))
        key = self.prefix + SCREENS[index]
        self.picture.set_picture(ASSETS / (key + ".webp"), self.shots[key]["marks"], title)
        self.counter.setText(f"{self.copy['step']} {index+1} / 8")
        self.progress.setValue(index+1)
        self.previous.setEnabled(index > 0)
        done = ("Hoàn tất" if self.prefix.startswith("vi-") else "Done") if self.from_help else self.copy["done"]
        self.next.setText(done if index == 7 else self.copy["next"])
        self.scroll.verticalScrollBar().setValue(0)

    def advance(self):
        if self.nav.currentRow() == 7:
            self.accept()
        else:
            self.nav.setCurrentRow(self.nav.currentRow() + 1)


def show_onboarding(window, *, first_run=False, receipt_path=None):
    receipt_path = Path(receipt_path) if receipt_path is not None else data_directory() / "onboarding-v1.txt"
    if first_run:
        try:
            if receipt_path.read_text(encoding="utf-8") == "1":
                return
        except (OSError, UnicodeError):
            pass
    try:
        dialog = OnboardingDialog(window, from_help=not first_run)
    except (OSError, ValueError, KeyError):
        QMessageBox.warning(window, "LottoLens", "Không mở được ảnh hướng dẫn. Hãy khôi phục thư mục docs/redesign/onboarding/assets.\n"
                            "Could not open tutorial images. Restore docs/redesign/onboarding/assets.")
        return
    backdrop = PolicyBackdrop(); backdrop.setBlurRadius(7)
    central = window.centralWidget(); central.setGraphicsEffect(backdrop)
    try:
        dialog.exec()
    finally:
        central.setGraphicsEffect(None)
        dialog.deleteLater()
    if first_run:
        try:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            file = QSaveFile(str(receipt_path))
            if file.open(QIODevice.OpenModeFlag.WriteOnly) and file.write(b"1") == 1 and file.commit():
                return
        except OSError:
            pass
        QMessageBox.warning(window, "LottoLens", "Chưa lưu được trạng thái hướng dẫn; lần mở sau sẽ hiện lại.\n"
                            "Could not save tutorial completion; it will appear again next launch.")
