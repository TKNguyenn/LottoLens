"""Offline settings/language regression; original tests/ remains immutable."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import sys
import tempfile
from threading import Event
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.ui import Desktop
from app.domain import Draw
from app.rules import get_rule, BASE
from check_redesign import check_page


def wait_idle(window):
    for _ in range(300):
        QApplication.processEvents()
        if window.worker is None:
            return
        QTest.qWait(10)
    raise AssertionError("Worker did not finish")


def main():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send") as ai, patch("app.ui.OfficialSource.fetch_history") as fetch:
        folder = Path(directory)
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            window.show(); app.processEvents()
            assert window.pages.count() == window.nav.count() == 8
            assert window.nav.item(7).text() == "Cài đặt"
            assert all(spin.value() == 100 for spin in window.draw_limit_inputs.values())
            assert not window.github_button.isEnabled()
            assert window.jackpot_card.title.text() == "Jackpot"
            rule = get_rule("mega")
            at = "2026-11-01T11:00:00+00:00"
            window.store.add_draws(rule, [Draw("mega", rule.mode_id, rule.rule_version, str(i), at, {"main": [1, 2, 3, 4, 5, i]}, BASE + rule.result_path, at, "a" * 64) for i in (6, 7)])
            window.draw_limit_inputs["mega"].setValue(1); window.preferences_save_button.click()
            assert len(window.store.list_draws(rule)) == 2, "Fetch count must never prune stored history"
            window.draw_limit_inputs["mega"].setValue(100)
            window.nav.setCurrentRow(4); window.method.setCurrentIndex(window.method.findData("uniform_v1")); window.make_suggestions()
            state = window.generated, window.explanation.toPlainText()
            window.target.setText("123"); window.query.setText("Dữ liệu người dùng"); window.key.setText("temporary-test-key")
            window.answer.setPlainText("Tổng quan")
            window.report.setPlainText('{"note":"Tổng quan"}')
            window.set_sidebar_collapsed(True, animate=False)
            window.nav.setCurrentRow(7)
            window.draw_limit_inputs["mega"].setValue(175)
            window.draw_limit_inputs["power"].setValue(250)
            window.language_choice.setCurrentIndex(window.language_choice.findData("en"))
            assert window.nav.item(7).text() == "Settings", "Language must change immediately"
            assert "Thống kê" not in window.stats_note.text()
            assert "chưa có" not in window.distribution_detail.text() and "Chưa áp dụng" not in window.distribution_detail.text()
            assert state[0] == window.generated
            assert window.sidebar_collapsed and window.nav.currentRow() == 7
            assert window.target.text() == "123" and window.query.text() == "Dữ liệu người dùng" and window.key.text() == "temporary-test-key"
            assert window.answer.toPlainText() == "Tổng quan" and window.report.toPlainText() == '{"note":"Tổng quan"}'
            assert "Uniform" in window.explanation.toPlainText()
            window.language_choice.setCurrentIndex(window.language_choice.findData("vi"))
            assert window.nav.item(7).text() == "Cài đặt"
            assert window.jackpot_card.title.text() == "Jackpot", "Game-specific prize identity must survive round trip"
            assert "Past statistics" not in window.stats_note.text() and "no baseline" not in window.distribution_detail.text()
            window.language_choice.setCurrentIndex(window.language_choice.findData("en"))
            state = window.generated, window.explanation.toPlainText()
            window.preferences_save_button.click()
            assert state == (window.generated, window.explanation.toPlainText())
            assert window.history_limit.value() == 175
            window.game.setCurrentIndex(window.game.findData("power")); assert window.history_limit.value() == 250
            window.game.setCurrentIndex(window.game.findData("lotto")); assert window.history_limit.value() == 100
            body = json.loads((folder / "ui_preferences.json").read_text())
            assert body["language"] == "en" and body["history_limits"]["mega"] == 175
            assert not (folder / "config.json").exists()
            with patch("app.ui.save_preferences", side_effect=OSError("disk unavailable")):
                window.draw_limit_inputs["mega"].setValue(180); window.preferences_save_button.click()
                assert "disk unavailable" in window.notice.text()
                assert json.loads((folder / "ui_preferences.json").read_text()) == body
            ai.assert_not_called(); fetch.assert_not_called()
        finally:
            window.close()
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            window.show(); app.processEvents()
            assert window.nav.item(0).text() == "Overview" and window.nav.item(7).text() == "Settings"
            assert window.history_table.horizontalHeaderItem(0).text() == "DRAW"
            assert window.draw_limit_inputs["mega"].value() == 175
            for game, caption in (("lotto", "Jackpot"), ("keno", "Match 6 numbers")):
                window.game.setCurrentIndex(window.game.findData(game))
                assert caption in window.suggestion_odds.text(), window.suggestion_odds.text()
                window.language_choice.setCurrentIndex(window.language_choice.findData("vi"))
                window.language_choice.setCurrentIndex(window.language_choice.findData("en"))
                assert caption in window.suggestion_odds.text(), window.suggestion_odds.text()
            for language in ("vi", "en"):
                window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                window.refresh_statistics()
                for theme in ("light", "dark"):
                    window.set_theme(theme)
                    for compact in (False, True):
                        window.set_sidebar_collapsed(compact, animate=False)
                        for size in ((1000, 700), (1920, 1080)):
                            window.resize(*size)
                            for page in range(8):
                                window.nav.setCurrentRow(page)
                                try:
                                    check_page(window)
                                except AssertionError as error:
                                    raise AssertionError((language, theme, compact, size, page, str(error))) from error
            with patch("app.ui.OfficialSource.fetch_history", return_value={"draws": [], "note": "fixture", "status": "completed"}) as request:
                window.game.setCurrentIndex(window.game.findData("mega")); window.sync(); wait_idle(window)
                assert request.call_args.args[1] == 175
            release = Event()
            window.start_task(lambda cancel, progress, delta: (release.wait(2), {"status": "completed"})[1], lambda result: None, "fixture")
            assert not window.language_choice.isEnabled()
            assert all(not spin.isEnabled() for spin in window.draw_limit_inputs.values())
            release.set(); wait_idle(window)
            assert window.language_choice.isEnabled() and not window.github_button.isEnabled()
            assert all(spin.isEnabled() for spin in window.draw_limit_inputs.values())
            window.answer.setPlainText("Không dịch phản hồi AI {raw}")
            assert window.answer.toPlainText() == "Không dịch phản hồi AI {raw}"
        finally:
            window.close()
        from app.preferences import load_preferences, save_preferences
        with patch("pathlib.Path.replace", side_effect=OSError("replace failed")):
            try:
                save_preferences(folder / "ui_preferences.json", {**body, "language": "vi"})
            except OSError:
                pass
            else:
                raise AssertionError("Write failure swallowed")
        assert json.loads((folder / "ui_preferences.json").read_text()) == body
        for bad in ({"language": "xx", "history_limits": {}}, {"language": "vi", "history_limits": {"mega": True}}, {"language": "en", "history_limits": {"mega": 0}}, []):
            (folder / "ui_preferences.json").write_text(json.dumps(bad))
            try:
                load_preferences(folder / "ui_preferences.json")
            except ValueError:
                pass
            else:
                raise AssertionError("Malformed UI preferences accepted")
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            assert all(spin.value() == 100 for spin in window.draw_limit_inputs.values())
            assert "cài đặt" in window.notice.text()
            assert json.loads((folder / "ui_preferences.json").read_text()) == []
        finally:
            window.close()
    print("Settings OK: 8 pages, per-game counts/default100, live VI/EN and persistence, write failure, worker locking, disabled GitHub, both themes/languages/sizes/rail states, inputs/generated/raw AI/report retained, no automatic network.")


if __name__ == "__main__":
    main()
