"""Offline regression for the verification-only history adjustment."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.ui import Desktop
from app.rules import get_rule
from check_analysis_core import history
from check_preferences import wait_idle
from check_redesign import check_page


def main():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send") as ai, patch("app.ui.OfficialSource.fetch_history") as fetch:
        folder = Path(directory)
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            window.show(); rule = get_rule("mega")
            window.store.add_draws(rule, history(100)); window.refresh()
            window.analysis_window_input.setValue(100)
            assert window.backtest_history_window == 99
            assert window.analysis_window == window.analysis_window_input.value() == 100
            assert "99" in window.verify_method.itemText(window.verify_method.findData("bayes90_v1"))
            assert "100" in window.method.itemText(window.method.findData("bayes90_v1"))
            window.nav.setCurrentRow(5); app.processEvents()
            assert window.verify_adjustment.isVisible() and "99" in window.verify_adjustment.text()
            assert "1" in window.verify_requirements.text()
            window.method.setCurrentIndex(window.method.findData("bayes90_v1"))
            window.backtest(); wait_idle(window)
            report = window.store.reports()[0]
            assert report["status"] == "completed" and report["manifest"]["warmup"] == 99
            assert report["manifest"]["config"]["history_window"] == 99
            assert len(report["rows"]) == 1 and report["rows"][0]["target_draw_id"] == "100"
            assert report["rows"][0]["history_cutoff"] == "99"
            window.preferences_save_button.click()
            assert json.loads((folder / "ui_preferences.json").read_text())["analysis_window"] == 100
            for language in ("vi", "en"):
                window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                for theme in ("light", "dark"):
                    window.set_theme(theme)
                    for compact in (False, True):
                        window.set_sidebar_collapsed(compact, animate=False)
                        for size in ((1000, 700), (1920, 1080)):
                            window.resize(*size); check_page(window)
                if language == "en":
                    assert "draws" in window.verify_adjustment.text()
                    assert "kỳ" not in window.verify_requirements.text()
            window.analysis_window_input.setValue(120)
            assert window.backtest_history_window == 99
            window.store.add_draws(rule, [history(101)[-1]]); window.refresh()
            assert window.backtest_history_window == 100
            window.analysis_window_input.setValue(100)
            assert window.backtest_history_window == 100 and not window.verify_adjustment.isVisible()
            window.game.setCurrentIndex(window.game.findData("power"))
            assert window.backtest_history_window == 1 and window.verify_adjustment.isVisible()
            assert "2" in window.verify_requirements.text()
            assert len(window.store.list_draws(rule)) == 101
            ai.assert_not_called(); fetch.assert_not_called()
        finally:
            window.close()
    print("Verification window OK: 100/100 ->99 +one real target, local metadata/config, global100 retained, shortage/extra data, VI/EN/themes/sizes/rail, no network/pruning.")


if __name__ == "__main__":
    main()
