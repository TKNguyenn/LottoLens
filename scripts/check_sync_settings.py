"""Offline UI checks for daily schedules and foreground incremental retention."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
from threading import Event
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTime
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.ui import Desktop
from app.storage import Store
from app.rules import get_rule
from check_analysis_core import history
from check_preferences import wait_idle
from check_redesign import check_page


def main():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send") as ai:
        folder = Path(directory)
        with patch("app.ui.OfficialSource.fetch_history") as fetch:
            window = Desktop(folder / "history.sqlite3", folder / "config.json")
            try:
                window.show(); app.processEvents()
                assert not any(toggle.isChecked() for toggle in window.auto_update_inputs.values())
                assert all(not clock.isEnabled() for clock in window.auto_time_inputs.values())
                assert all(clock.time().toString("HH:mm") == "20:00" for clock in window.auto_time_inputs.values())
                fetch.assert_not_called()
                window.auto_update_inputs["mega"].click()
                window.auto_time_inputs["mega"].setTime(QTime(21, 15))
                assert window.auto_time_inputs["mega"].isEnabled()
                with patch("app.ui.configure_schedules", return_value=Mock()) as configure:
                    window.preferences_save_button.click()
                    assert configure.call_count == 1
                    assert configure.call_args.args[0]["auto_updates"]["mega"] == {"enabled": True, "time": "21:15"}
                body = json.loads((folder / "ui_preferences.json").read_text())
                window.auto_update_inputs["power"].click()
                with patch("app.ui.configure_schedules", side_effect=RuntimeError("task denied")):
                    window.preferences_save_button.click()
                    assert "task denied" in window.notice.text()
                    assert json.loads((folder / "ui_preferences.json").read_text()) == body
                undo = Mock()
                with patch("app.ui.configure_schedules", return_value=undo), patch("app.ui.save_preferences", side_effect=OSError("disk failed")):
                    window.preferences_save_button.click(); undo.assert_called_once()
                    assert json.loads((folder / "ui_preferences.json").read_text()) == body
                window.auto_update_inputs["power"].click()
                release = Event()
                window.start_task(lambda cancel, progress, delta: (release.wait(2), {"status": "completed"})[1], lambda result: None, "fixture")
                assert all(not toggle.isEnabled() for toggle in window.auto_update_inputs.values())
                assert all(not clock.isEnabled() for clock in window.auto_time_inputs.values())
                release.set(); wait_idle(window)
                assert window.auto_time_inputs["mega"].isEnabled() and not window.auto_time_inputs["power"].isEnabled()
                for language in ("vi", "en"):
                    window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                    for theme in ("light", "dark"):
                        window.set_theme(theme)
                        for compact in (False, True):
                            window.set_sidebar_collapsed(compact, animate=False)
                            for size in ((1000, 700), (1920, 1080)):
                                window.resize(*size); window.nav.setCurrentRow(7); check_page(window)
                fetch.assert_not_called()
            finally:
                window.close()
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            window.show()
            assert window.auto_update_inputs["mega"].isChecked()
            assert window.auto_time_inputs["mega"].time().toString("HH:mm") == "21:15"
            rule = get_rule("mega")
            window.store.apply_sync(rule, {"status": "requested_limit", "draws": history(100)}, 100)
            window.refresh()
            window.method.setCurrentIndex(window.method.findData("uniform_v1")); window.make_suggestions()
            generated = window.generated
            window.answer.setPlainText("raw AI"); window.report.setPlainText('{"fixture":true}')
            with closing(Store(folder / "history.sqlite3")) as external:
                external.apply_sync(rule, {"status": "requested_limit", "draws": history(101)[1:]}, 100)
            window.poll_background_updates()
            assert len(window.draws) == 100 and window.draws[-1].draw_id == "101"
            assert window.generated is generated and window.answer.toPlainText() == "raw AI" and window.report.toPlainText() == '{"fixture":true}'
            with patch("app.ui.OfficialSource.fetch_history", return_value={"status": "known_boundary", "draws": history(102)[-2:], "note": "fixture"}) as fetch:
                window.sync(); wait_idle(window)
                assert len(fetch.call_args.kwargs["known_draws"]) == 100
                assert len(window.store.list_draws(rule)) == 100 and window.draws[-1].draw_id == "102"
            ai.assert_not_called()
        finally:
            window.close()
    print("Sync settings OK: opt-in time per game, schedule/save rollback, persistence, VI/EN/themes/rail/layout, background DB refresh preserves results, manual incremental+cap, no startup/AI requests.")


if __name__ == "__main__":
    main()
