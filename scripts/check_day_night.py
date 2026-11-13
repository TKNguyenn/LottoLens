"""Offline integration check for the sidebar sun/moon switch."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.components import DayNightToggle, ThemeToggle
from app.ui import Desktop
from check_redesign import check_page


def main():
    app = QApplication([])
    if not QFontDatabase.families():
        for name in ("segoeui.ttf", "seguisb.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    with TemporaryDirectory() as directory, patch("app.ai._send") as ai, patch("app.ui.OfficialSource.fetch_history") as fetch:
        folder = Path(directory)
        window = Desktop(folder / "history.db", folder / "config.json")
        try:
            window.resize(1000, 700)
            window.set_theme("light")
            window.show()
            window.activateWindow()
            assert QTest.qWaitForWindowActive(window, 1500)
            button = window.theme_button
            assert isinstance(button, DayNightToggle)
            for toggle in window.auto_update_inputs.values():
                assert type(toggle) is ThemeToggle
            for compact in (False, True):
                window.set_sidebar_collapsed(compact, animate=False)
                app.processEvents()
                before = button.grab().toImage()
                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                QTest.qWait(100)
                assert button.animation.state() == QAbstractAnimation.State.Running
                assert 0 < button._position < 1
                QTest.qWait(250)
                assert window.theme_name == "dark" and button.isChecked() and button._position == 1
                assert before != button.grab().toImage()
                assert json.loads((folder / "theme.json").read_text()) == {"theme": "dark"}
                window.nav.setFocus()
                button.setFocus(Qt.FocusReason.TabFocusReason)
                assert button.hasFocus() and button.property("keyboardFocus")
                QTest.keyClick(button, Qt.Key.Key_Space)
                QTest.qWait(350)
                assert window.theme_name == "light" and button._position == 0
                button.click()
                QTest.qWait(80)
                button.click()
                QTest.qWait(350)
                assert window.theme_name == "light" and button._position == 0
                assert window.sidebar_collapsed == compact
                check_page(window)
            assert not (folder / "config.json").exists()
            ai.assert_not_called()
            fetch.assert_not_called()
        finally:
            window.close()
        restored = Desktop(folder / "history.db", folder / "config.json")
        try:
            assert restored.theme_name == "light" and restored.theme_button._position == 0
        finally:
            restored.close()
    print("Day/night switch passed: animated sun/moon, compact sidebar, keyboard, rapid reversal, theme persistence and offline.")


if __name__ == "__main__":
    main()
