"""Native review images for the selected analysis window; synthetic temporary data."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root)); sys.path.insert(0, str(root / "scripts"))
from PySide6.QtWidgets import QApplication
from app.ui import Desktop
from app.rules import get_rule
from check_analysis_core import history
from check_preferences import wait_idle

app = QApplication([])
adjustment = "--backtest-adjustment" in sys.argv
selected = 100 if adjustment else 120
output = Path(__file__).resolve().parent / "reviews" / ("backtest-adjustment" if adjustment else "analysis-window")
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as directory, patch("app.ai._send", side_effect=AssertionError("Capture AI")), patch("app.ui.OfficialSource.fetch_history", side_effect=AssertionError("Capture fetch")):
    folder = Path(directory)
    window = Desktop(folder / "history.sqlite3", folder / "config.json")
    try:
        window.store.add_draws(get_rule("mega"), history(100 if adjustment else 150)); window.refresh()
        window.resize(1440, 960); window.show(); window.nav.setFocus()
        window.analysis_window_input.setValue(selected)
        if adjustment:
            window.backtest(); wait_idle(window)
        for language in ("vi", "en"):
            window.language_choice.setCurrentIndex(window.language_choice.findData(language))
            for theme in ("light", "dark"):
                window.set_theme(theme)
                for page, name in ((7, "settings"), (0, "overview"), (4, "suggestions"), (5, "verification")):
                    window.nav.setCurrentRow(page)
                    window.notice.setText("Dữ liệu giả lập để review giao diện · không gọi mạng hoặc ghi vào database người dùng.")
                    for _ in range(3):
                        app.processEvents()
                    window.grab().save(str(output / f"{name}-{language}-{theme}-{selected}.png"))
        window.nav.setCurrentRow(7); window.resize(1000, 700)
        for _ in range(3):
            app.processEvents()
        window.grab().save(str(output / f"settings-en-small-{selected}.png"))
        print(f"Captured N{selected} settings/overview/generation/verification in VI/EN+light/dark and small window; synthetic temporary DB, no network.")
    finally:
        window.close()
