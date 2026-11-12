"""Capture settings in native Qt using temporary preferences/database and no network."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication
from app.ui import Desktop

app = QApplication([])
output = Path(__file__).resolve().parent / "reviews"
if "--daily-sync" in sys.argv:
    output = output / "daily-sync"
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as directory, patch("app.ai._send", side_effect=AssertionError("Capture AI")), patch("app.ui.OfficialSource.fetch_history", side_effect=AssertionError("Capture history")):
    folder = Path(directory)
    window = Desktop(folder / "history.sqlite3", folder / "config.json")
    try:
        window.resize(1440, 960); window.show(); window.nav.setCurrentRow(7); window.nav.setFocus()
        if "--daily-sync" in sys.argv:
            for game, hour, minute in (("mega", 20, 30), ("power", 21, 45)):
                window.auto_update_inputs[game].setChecked(True)
                window.auto_time_inputs[game].setTime(QTime(hour, minute))
            window.notice.setText("Xem trước cài đặt chưa lưu · không đăng ký lịch Windows hoặc gọi mạng.")
        for language in ("vi", "en"):
            window.language_choice.setCurrentIndex(window.language_choice.findData(language))
            assert window.nav.currentRow() == 7
            for theme in ("light", "dark"):
                window.set_theme(theme)
                for compact in (False, True):
                    window.set_sidebar_collapsed(compact, animate=False)
                    window.pages.currentWidget().verticalScrollBar().setValue(0)
                    for _ in range(3):
                        app.processEvents()
                    window.grab().save(str(output / f"settings-{language}-{theme}-{'compact' if compact else 'expanded'}.png"))
                if "--daily-sync" in sys.argv:
                    window.pages.currentWidget().verticalScrollBar().setValue(window.pages.currentWidget().verticalScrollBar().maximum())
                    for _ in range(3):
                        app.processEvents()
                    window.grab().save(str(output / f"settings-{language}-{theme}-bottom.png"))
            window.set_sidebar_collapsed(False, animate=False); window.resize(1000, 700)
            for _ in range(3):
                app.processEvents()
            window.grab().save(str(output / f"settings-{language}-small.png")); window.resize(1440, 960)
        window.nav.setCurrentRow(4)
        window.method.setCurrentIndex(window.method.findData("uniform_v1")); window.make_suggestions()
        for _ in range(3):
            app.processEvents()
        window.grab().save(str(output / "suggestions-en-dark.png"))
        print("Captured 8 settings theme/language/rail states, 2 small windows, English suggestions; temporary DB/config, no network.")
    finally:
        window.close()
