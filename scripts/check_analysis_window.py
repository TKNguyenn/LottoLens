"""Offline UI regression for the selected analysis window."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
from threading import Event
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.domain import Draw
from app.rules import get_rule, BASE
from app.ui import Desktop
from check_redesign import check_page
from check_preferences import wait_idle


def main():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send") as ai, patch("app.ui.OfficialSource.fetch_history") as fetch:
        folder = Path(directory)
        legacy = {"language": "vi", "history_limits": {game: 100 for game in ("mega", "power", "lotto", "keno", "max3d", "max3dpro", "bingo18")}}
        (folder / "ui_preferences.json").write_text(json.dumps(legacy))
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            window.show(); app.processEvents()
            assert window.analysis_window_input.value() == 90
            rule = get_rule("mega"); at = "2026-11-01T11:00:00+00:00"
            draws = [Draw("mega", rule.mode_id, rule.rule_version, str(i), at, {"main": [1, 2, 3, 4, 5, 6] if i <= 120 else [7, 8, 9, 10, 11, 12]}, BASE + rule.result_path, at, "a" * 64) for i in range(1, 151)]
            window.store.add_draws(rule, draws); window.refresh()
            window.analysis_window_input.setValue(30)
            assert "30 kỳ" in window.explanation.toPlainText(), "Idle help must use the newly selected window"
            assert window.analysis_window == 30
            assert window.window_size.itemData(0) == 30
            assert window.heatmap.frequencies[7] == 30 and window.heatmap.frequencies[1] == 0
            assert "30" in window.hot_card.hint.text()
            assert "30" in window.method.itemText(window.method.findData("bayes90_v1"))
            window.method.setCurrentIndex(window.method.findData("bayes90_v1")); window.make_suggestions()
            assert window.generated[4]["history_window"] == 30
            assert "30 kỳ" in window.explanation.toPlainText()
            generated = window.generated
            window.analysis_window_input.setValue(120)
            assert window.generated is generated, "Changing future window must preserve current result provenance"
            assert window.heatmap.frequencies[1] == 90 and window.heatmap.frequencies[7] == 30
            window.target.setText("151"); window.save_generated()
            assert window.store.suggestions(rule)[0]["metadata"]["history_window"] == 30
            window.make_suggestions(); assert window.generated[4]["history_window"] == 120
            for language in ("en", "vi"):
                window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                for theme in ("light", "dark"):
                    window.set_theme(theme)
                    for size in ((1000, 700), (1920, 1080)):
                        window.resize(*size)
                        for page in range(8):
                            window.nav.setCurrentRow(page); check_page(window)
                assert "120" in window.method.itemText(window.method.findData("ai_history90_v1"))
                assert "120" in window.verify_method.itemText(window.verify_method.findData("bayes90_v1"))
                assert "121" in window.verify_requirements.text()
                if language == "en":
                    assert "120 draws" in window.method_note.text()
                    assert "120 draws" in window.ai_history_callout.text.text()
                    assert "kỳ" not in window.suggestion_description.text()
            window.preferences_save_button.click()
            assert json.loads((folder / "ui_preferences.json").read_text())["analysis_window"] == 120
            window.analysis_window_input.setValue(30); window.key.setText("offline-test-key"); window.count.setValue(1)
            window.method.setCurrentIndex(window.method.findData("ai_history90_v1"))
            started, release = Event(), Event()
            def transport(url, headers, body, **kwargs):
                started.set(); release.wait(2)
                return {"status": "completed", "output_text": json.dumps({"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "offline AI fixture"})}
            with patch("app.ai._send", side_effect=transport) as request:
                window.make_suggestions(); assert started.wait(2)
                assert not window.analysis_window_input.isEnabled()
                release.set(); wait_idle(window)
                assert request.call_count == 1 and len(json.loads(request.call_args.args[2]["input"])["history"]) == 30
                assert window.generated[4]["history_window"] == window.generated[4]["history_used"] == 30
                assert "offline-test-key" not in json.dumps(window.generated[4])
            assert window.analysis_window_input.isEnabled()
            window.method.setCurrentIndex(window.method.findData("bayes90_v1"))
            with patch.object(window, "start_task") as task, patch("app.ui.run_backtest") as backtest:
                window.backtest(); task.call_args.args[0](lambda: False, lambda done, total: None, lambda text: None)
                assert backtest.call_args.args[2]["history_window"] == 30
            window.analysis_window_input.setValue(151)
            window.make_suggestions(); assert window.generated is None and "151" in window.notice.text()
            window.analysis_window_input.setValue(2000)
            window.language_choice.setCurrentIndex(window.language_choice.findData("en")); window.resize(1000, 700)
            for page in range(8):
                window.nav.setCurrentRow(page); check_page(window)
            assert len(window.store.list_draws(rule)) == 150
            ai.assert_not_called(); fetch.assert_not_called()
        finally:
            window.close()
        from app.preferences import validate_preferences
        for value in (True, 0, -1, 2001, 30.5, "30", None):
            try:
                validate_preferences({**legacy, "analysis_window": value})
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid analysis window accepted")
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            assert window.analysis_window == window.analysis_window_input.value() == 120
        finally:
            window.close()
    print("Analysis window UI OK: legacy/default90, live30/120 math+copy, stored batch provenance, insufficient-history/no HTTP, VI/EN/themes/layouts, persistence and no pruning.")


if __name__ == "__main__":
    main()
