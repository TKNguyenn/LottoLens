"""Exercise the policy gate at the real GUI entry point, using local test files."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QGraphicsBlurEffect, QPushButton, QTextBrowser

from app import policy, ui
from app.preferences import default_preferences, save_preferences


def main():
    application = QApplication([])
    if not QFontDatabase.families():
        for name in ("segoeui.ttf", "seguisb.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))

    with TemporaryDirectory() as directory:
        folder = Path(directory)
        config, db = folder / "config.json", folder / "test.sqlite3"
        policy_file = folder / "POLICY.md"
        original_policy = policy.POLICY_PATH.read_text(encoding="utf-8")
        policy_file.write_text(original_policy, encoding="utf-8")
        receipt = folder / "VietlottDesktop" / "policy-acceptance.txt"
        errors = []

        def inspect(callback):
            try:
                callback()
            except Exception as error:
                errors.append(error)
                for window in application.topLevelWidgets():
                    if window.isVisible():
                        window.close()
                application.quit()

        def launch(callback):
            QTimer.singleShot(0, lambda: inspect(callback))
            assert ui.main(db) == 0
            if errors:
                raise errors.pop()

        def desktop():
            return next((w for w in application.topLevelWidgets() if isinstance(w, ui.Desktop) and w.isVisible()), None)

        def red_outline(control):
            image = control.grab().toImage()
            return image.pixelColor(image.width() // 2, 0) == QColor(desktop().tokens["red"])

        def policy_dialog():
            dialog = application.activeModalWidget()
            window = desktop()
            assert window is not None, "Desktop must be visible behind the policy dialog"
            assert dialog is not None and dialog.parentWidget() is window
            effect = window.centralWidget().graphicsEffect()
            assert isinstance(effect, QGraphicsBlurEffect) and effect.isEnabled() and effect.blurRadius() > 0
            content = dialog.findChild(QTextBrowser).toPlainText()
            assert "Chính sách sử dụng LottoLens" in content and "LottoLens usage policy" in content
            return dialog

        def reject():
            dialog = policy_dialog()
            assert QTest.qWaitForWindowActive(dialog, 1500)
            content = dialog.findChild(QTextBrowser)
            QTest.mouseClick(content.viewport(), Qt.MouseButton.LeftButton)
            assert not red_outline(content), "Clicking policy text must not leave a red border"
            assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
            QTest.keyClick(dialog, Qt.Key.Key_Escape)

        def close_desktop():
            assert application.activeModalWidget() is None
            window = desktop()
            assert window is not None and window.centralWidget().graphicsEffect() is None
            assert db.is_file() and receipt.is_file()
            window.close()

        def accept(write_fails=False):
            dialog = policy_dialog()
            read, agree = dialog.findChildren(QCheckBox)
            assert "đã đọc" in read.text() and "I have read" in read.text()
            assert "chấp nhận" in agree.text() and "I accept" in agree.text()
            proceed = next(button for button in dialog.findChildren(QPushButton) if "Continue" in button.text())
            assert not read.isChecked() and not agree.isChecked() and not proceed.isEnabled()
            agree.setChecked(True)
            assert not proceed.isEnabled()
            agree.setChecked(False)
            read.setFocus()
            QTest.keyClick(read, Qt.Key.Key_Space)
            assert read.isChecked() and not proceed.isEnabled()
            agree.setChecked(True)
            assert proceed.isEnabled()
            read.setChecked(False)
            assert not proceed.isEnabled()
            read.setChecked(True)
            proceed.click()
            if write_fails:
                assert dialog.isVisible() and receipt.is_dir(), "A failed write must keep the user at the policy"
                dialog.reject()
            else:
                QTimer.singleShot(0, lambda: inspect(close_desktop))

        def view_settings_policy():
            window = desktop()
            window.nav.setCurrentRow(7)
            button = next(b for b in window.pages.currentWidget().findChildren(QPushButton) if b.text() == "Usage policy")
            before = (receipt.read_bytes(), receipt.stat().st_mtime_ns)

            def close_viewer():
                dialog = policy_dialog()
                assert QTest.qWaitForWindowActive(dialog, 1500)
                assert not dialog.findChildren(QCheckBox)
                buttons = dialog.findChildren(QPushButton)
                assert len(buttons) == 1 and "Close" in buttons[0].text()
                content = dialog.findChild(QTextBrowser)
                assert not red_outline(content), "Initial reading focus must not show a red border"
                QTest.keyClick(dialog, Qt.Key.Key_Tab)
                assert content.hasFocus() and red_outline(content)
                QTest.keyClick(content, Qt.Key.Key_Tab)
                assert buttons[0].hasFocus() and red_outline(buttons[0])
                QTest.keyClick(buttons[0], Qt.Key.Key_Backtab)
                assert content.hasFocus() and red_outline(content)
                QTest.mouseClick(content.viewport(), Qt.MouseButton.LeftButton)
                assert content.hasFocus() and not red_outline(content)
                QTest.keyClick(content, Qt.Key.Key_Tab)
                QTest.keyClick(buttons[0], Qt.Key.Key_Space)

            QTimer.singleShot(0, lambda: inspect(close_viewer))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            if errors:
                return
            window.activateWindow()
            assert QTest.qWaitForWindowActive(window, 1500)
            assert not red_outline(button), "A click must not leave a red border after closing the viewer"
            assert (receipt.read_bytes(), receipt.stat().st_mtime_ns) == before
            assert window.nav.currentRow() == 7
            window.nav.setCurrentRow(6)
            reveal = window.reveal_button
            reveal.setFocus(Qt.FocusReason.TabFocusReason)
            assert red_outline(reveal)
            QTest.mouseClick(reveal, Qt.MouseButton.LeftButton)
            assert not red_outline(reveal) and reveal.isChecked()
            close_desktop()

        with (patch.dict(os.environ, {"LOCALAPPDATA": directory}), patch.object(ui, "CONFIG_PATH", config),
              patch.object(ui, "show_onboarding"),
              patch.object(policy, "POLICY_PATH", policy_file),
              patch("app.ai._send", side_effect=AssertionError("Unexpected AI request")) as ai_request,
              patch.object(ui.OfficialSource, "fetch_history", side_effect=AssertionError("Unexpected history request")) as history_request):
            launch(reject)
            assert not receipt.exists() and desktop() is None
            save_preferences(folder / "ui_preferences.json", {**default_preferences(), "language": "en"})
            (folder / "theme.json").write_text('{"theme":"dark"}', encoding="utf-8")
            receipt.mkdir(parents=True)
            launch(lambda: accept(write_fails=True))
            receipt.rmdir()
            launch(accept)
            accepted_version = receipt.read_bytes()
            launch(view_settings_policy)
            (folder / "theme.json").write_text('{"theme":"light"}', encoding="utf-8")
            launch(view_settings_policy)
            policy_file.write_text(original_policy + "\nA new policy paragraph.\n", encoding="utf-8")
            launch(accept)
            assert receipt.read_bytes() != accepted_version
            ai_request.assert_not_called()
            history_request.assert_not_called()
    print("Policy gate passed")


if __name__ == "__main__":
    main()
