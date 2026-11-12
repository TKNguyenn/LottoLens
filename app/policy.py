"""Display the bilingual usage policy over the desktop window."""
from hashlib import sha256
from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QGraphicsBlurEffect, QHBoxLayout, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout,
)

from .theme import apply_theme
from .widgets import label

POLICY_PATH = Path(__file__).resolve().parents[1] / "POLICY.md"


class PolicyBackdrop(QGraphicsBlurEffect):
    def draw(self, painter):
        super().draw(painter)
        painter.fillRect(self.sourceBoundingRect(), QColor(0, 0, 0, 105))


def show_policy(window, receipt_path=None):
    title = "Chính sách sử dụng / Usage policy"
    try:
        policy = POLICY_PATH.read_text(encoding="utf-8")
        vi, _, en = policy.partition("\n---\n")
        if not vi.strip() or not en.strip():
            raise ValueError("Missing policy translation")
    except (OSError, ValueError):
        QMessageBox.critical(window, title, "Không mở được file POLICY.md. Hãy khôi phục file rồi thử lại.\n"
                             "Could not open POLICY.md. Restore the file and try again.")
        return False

    if receipt_path is not None:
        receipt = sha256(policy.encode("utf-8")).hexdigest().encode("ascii")
        try:
            if receipt_path.read_bytes() == receipt:
                return True
        except OSError:
            pass

    dialog = QDialog(window, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
    dialog.setObjectName("policyDialog")
    dialog.setWindowTitle(title)
    dialog.setAccessibleName(title)
    dialog.resize(680, 560)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(22, 18, 22, 18)
    layout.setSpacing(10)
    layout.addWidget(label("Tiếng Việt ở trên · Scroll down for English", "caption"))
    content = QTextBrowser()
    content.setAccessibleName(title)
    content.setMarkdown(policy)
    layout.addWidget(content, 1)
    buttons = QHBoxLayout()
    buttons.addStretch()
    if receipt_path is None:
        close = QPushButton("Đóng / Close")
        close.clicked.connect(dialog.accept)
        buttons.addWidget(close)
    else:
        read = QCheckBox("Tôi đã đọc chính sách sử dụng. / I have read the usage policy.")
        agree = QCheckBox("Tôi chấp nhận chính sách sử dụng. / I accept the usage policy.")
        layout.addWidget(read)
        layout.addWidget(agree)
        error = label("Không lưu được xác nhận. Hãy kiểm tra quyền ghi rồi thử lại.\n"
                      "Could not save acceptance. Check write permissions and try again.", "description")
        error.hide()
        layout.addWidget(error)
        exit_button = QPushButton("Thoát / Exit")
        proceed = QPushButton("Tiếp tục / Continue")
        proceed.setObjectName("primary")
        proceed.setEnabled(False)
        for button in (exit_button, proceed):
            button.setAutoDefault(False)
            buttons.addWidget(button)

        def update_button():
            proceed.setEnabled(read.isChecked() and agree.isChecked())

        def accept_policy():
            try:
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                file = QSaveFile(str(receipt_path))
                if file.open(QIODevice.OpenModeFlag.WriteOnly) and file.write(receipt) == len(receipt) and file.commit():
                    dialog.accept()
                    return
            except OSError:
                pass
            error.show()

        read.toggled.connect(update_button)
        agree.toggled.connect(update_button)
        exit_button.clicked.connect(dialog.reject)
        proceed.clicked.connect(accept_policy)

    layout.addLayout(buttons)
    apply_theme(dialog, window.theme_name)
    dialog.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
    dialog.setFocus()
    backdrop = PolicyBackdrop()
    backdrop.setBlurRadius(7)
    central = window.centralWidget()
    central.setGraphicsEffect(backdrop)
    try:
        return dialog.exec() == QDialog.DialogCode.Accepted
    finally:
        central.setGraphicsEffect(None)
