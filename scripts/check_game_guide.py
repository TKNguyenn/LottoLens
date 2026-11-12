"""Check the game guide at its desktop entry point using temporary data."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QTextBrowser

from app.ui import Desktop


def main():
    app = QApplication([])
    if not QFontDatabase.families():
        for name in ("segoeui.ttf", "seguisb.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))
    with (TemporaryDirectory() as directory, patch("app.ai._send") as ai,
          patch("app.ui.OfficialSource.fetch_history") as fetch,
          patch("app.game_guide.QDesktopServices.openUrl") as open_url):
        folder = Path(directory)
        window = Desktop(folder / "history.db", folder / "config.json")
        try:
            window.resize(1000, 700)
            window.show()
            assert QTest.qWaitForWindowActive(window, 1500)
            expected = {
                "mega": "01–45", "power": "Jackpot 2", "lotto": "01–12", "keno": "01–80",
                "max3d": "Max 3D+", "max3dpro": "000–999", "bingo18": "12–18",
            }
            for language, button_text, heading in (
                ("vi", "Hướng dẫn trò chơi", "Điều kiện trúng giải"),
                ("en", "Game guide", "Winning conditions"),
            ):
                window.apply_language(language)
                window.set_theme("dark" if language == "en" else "light")
                button = next((b for b in window.findChildren(QPushButton) if b.text() == button_text), None)
                assert button is not None and button.isVisible(), "Missing guide for the currently selected game"
                for game_id, detail in expected.items():
                    window.game.setCurrentIndex(window.game.findData(game_id))
                    if game_id == "keno":
                        window.mode.setCurrentIndex(window.mode.findData("pick10"))
                    app.processEvents()
                    parent = button.parentWidget()
                    assert parent.rect().contains(button.geometry())
                    errors = []
                    open_url.reset_mock()

                    def inspect():
                        dialog = app.activeModalWidget()
                        try:
                            assert dialog is not None and dialog.parentWidget() is window
                            assert window.rule.name in dialog.accessibleName()
                            browser = dialog.findChild(QTextBrowser)
                            content = browser.toPlainText()
                            assert heading in content and detail in content, (language, game_id)
                            open_url.assert_not_called()
                            source = next(b for b in dialog.findChildren(QPushButton) if b.text().endswith("↗"))
                            source.click()
                            assert open_url.call_count == 1
                            url = open_url.call_args.args[0]
                            assert url.scheme() == "https" and url.host() in {"vietlott.vn", "info.vietlott-sms.vn"}
                            if game_id == "keno":
                                assert ("Bậc đang chọn: 10" if language == "vi" else "Selected tier: 10") in content
                        except Exception as error:
                            errors.append(error)
                        finally:
                            if dialog is not None:
                                QTest.keyClick(dialog, Qt.Key.Key_Escape)

                    QTimer.singleShot(0, inspect)
                    button.click()
                    if errors:
                        raise errors[0]
                    assert window.rule.game_id == game_id
            ai.assert_not_called()
            fetch.assert_not_called()
        finally:
            window.close()
    print("Game guides OK: all seven games, Vietnamese and English, local content and source links")


if __name__ == "__main__":
    main()
