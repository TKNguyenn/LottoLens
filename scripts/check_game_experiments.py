"""Offline regressions for the Keno, Max and Bingo18 experiment paths."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from random import Random
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backtest import run_backtest
from app.domain import Ticket, validate_draw
from app.evaluation import evaluate
from app.rules import get_rule
from app.simulation import random_draw, simulate


def ticket(rule, main, play=None):
    selections = {"main": main}
    if play is not None:
        selections["play"] = play
    return Ticket(rule.game_id, rule.mode_id, rule.rule_version, selections, cost_vnd=rule.price_vnd)


def check_keno():
    thresholds = (1, 2, 2, 2, 3, 3, 3, 4, 4, 5)
    for size, minimum in enumerate(thresholds, start=1):
        rule = get_rule("keno", f"pick{size}")
        entry = ticket(rule, list(range(1, size+1)))
        draw = random_draw(rule, Random(1), 1)
        for count in range(size+1):
            draw.payload["main"] = list(range(1, count+1)) + list(range(21, 41-count))
            result = evaluate(rule, entry, draw)
            wins = count >= minimum or size >= 8 and count == 0
            assert result.prize_tiers == ([f"Trùng {count} số"] if wins else [])
            assert result.payout_vnd == (None if wins else 0)


def check_max():
    groups = {"special": ["007", "123"], "first": ["007", "001", "002", "003"],
              "second": ["007", "007", "004", "005", "006", "008"],
              "third": ["123", "007", "010", "011", "012", "013", "014", "015"]}
    for game, main, tiers in (
        ("max3d", ["007"], ["Giải Đặc biệt", "Giải Nhất", "Giải Nhì", "Giải Ba"]),
        ("max3dpro", ["123", "007"], ["Giải phụ Đặc biệt", "Giải Ba", "Giải Tư", "Giải Năm", "Giải Sáu"]),
        ("max3dpro", ["007", "007"], ["Giải Nhì", "Giải Tư", "Giải Năm", "Giải Sáu"]),
    ):
        rule = get_rule(game)
        draw = replace(random_draw(rule, Random(1), 1), payload={"groups": groups})
        result = evaluate(rule, ticket(rule, main), draw)
        assert result.prize_tiers == tiers and result.payout_vnd is None
    draw = replace(draw, payload={"groups": {**groups, "special": ["007", "007"]}})
    assert evaluate(rule, ticket(rule, ["007", "007"]), draw).prize_tiers[:2] == ["Giải Đặc biệt", "Giải phụ Đặc biệt"]


def check_bingo():
    rule = get_rule("bingo18")
    draw = random_draw(rule, Random(1), 1)
    for play, selection, main, tiers in (
        ("single", [4], [4, 4, 4], ["Xuất hiện 3 lần"]),
        ("double", [4], [4, 4, 4], ["Trúng"]),
        ("triple", [4], [4, 4, 6], []),
        ("any_triple", [], [4, 4, 4], ["Trúng"]),
        ("sum", [18], [6, 6, 6], ["Trúng"]),
        ("size", ["small"], [1, 2, 6], ["Trúng"]),
        ("size", ["tie"], [1, 3, 6], ["Trúng"]),
        ("size", ["tie"], [2, 3, 6], ["Trúng"]),
        ("size", ["big"], [3, 4, 5], ["Trúng"]),
    ):
        draw.payload["main"] = main
        assert evaluate(rule, ticket(rule, selection, play), draw).prize_tiers == tiers


def check_experiments():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for game, mode, entry, play, count in (
        ("keno", "pick8", list(range(1, 9)), None, 5),
        ("max3d", None, ["007"], None, 5),
        ("max3dpro", None, ["007", "007"], None, 5),
        ("bingo18", None, ["tie"], "size", 3),
        ("bingo18", None, [], "any_triple", 1),
    ):
        rule = get_rule(game, mode)
        selection = ticket(rule, entry, play)
        report = simulate(rule, selection, 2000, 42)
        assert report == simulate(rule, selection, 2000, 42)
        assert report["status"] == "completed" and report["completed_trials"] == 2000
        prize_tiers = report.get("prize_tiers", report["tiers"])
        assert report["winning_trials"] + prize_tiers.get("Không trúng", 0) == 2000
        if game == "keno":
            assert sum(report["tiers"].values()) == 2000
        assert simulate(rule, selection, 100, 42, cancel=lambda: True)["status"] == "incomplete"
        rng = Random(123)
        draws = [replace(random_draw(rule, rng, i+1), draw_at_utc=(start+timedelta(days=i)).isoformat())
                 for i in range(5)]
        for draw in draws:
            validate_draw(rule, draw)
        config = {"history_window": 2, "baseline_runs": 5, "play_context": play}
        backtest = run_backtest(rule, draws, config)
        assert backtest == run_backtest(rule, list(reversed(draws)), config)
        assert backtest["status"] == "completed" and len(backtest["rows"]) == 3
        assert backtest["manifest"]["config"]["tickets_per_draw"] == count
        assert backtest["rows"][0]["tickets"] == run_backtest(rule, draws[:3], config)["rows"][0]["tickets"]
        assert all(row["history_cutoff"] == str(i-1) for i, row in enumerate(backtest["rows"], 3))
        assert all(len(row["tickets"]) == count for row in backtest["rows"])
        if play:
            assert all(t["play"] == play for row in backtest["rows"] for t in row["tickets"])
        if play == "any_triple":
            assert all(row["strategy_wins"] == row["baseline_mean_wins"] for row in backtest["rows"])
        summary = backtest["summary"]["development"]
        assert summary["tickets"] == 3 * count
        for name, totals in summary["prize_tiers"].items():
            assert totals["strategy_hits"] == sum(row["strategy_prize_tiers"].get(name, 0) for row in backtest["rows"])
            assert totals["baseline_mean_hits"] == sum(row["baseline_prize_tiers"].get(name, 0) for row in backtest["rows"])/5
        assert run_backtest(rule, draws, config, cancel=lambda: True)["status"] == "incomplete"


def check_desktop():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication, QPushButton
    from app.i18n import tr
    from app.ui import Desktop
    from check_preferences import wait_idle
    from check_redesign import check_page

    app = QApplication([])
    if not QFontDatabase.families():
        for name in ("segoeui.ttf", "seguisb.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))
    with (TemporaryDirectory() as directory, patch("app.ai._send") as ai,
          patch("app.ui.OfficialSource.fetch_history") as fetch):
        folder = Path(directory)
        window = Desktop(folder / "history.db", folder / "config.json")
        try:
            window.resize(1000, 700)
            window.show()
            window.nav.setCurrentRow(5)
            controls = window.ticket_controls[-1]
            for game in ("keno", "max3d", "max3dpro", "bingo18"):
                window.game.setCurrentIndex(window.game.findData(game))
                if game == "keno":
                    window.mode.setCurrentIndex(window.mode.findData("pick10"))
                rule = window.rule
                rng = Random(42)
                start = datetime(2025, 1, 1, tzinfo=timezone.utc)
                draws = [replace(random_draw(rule, rng, i+1), draw_at_utc=(start+timedelta(days=i)).isoformat())
                         for i in range(3)]
                window.store.add_draws(rule, draws)
                window.refresh()
                if game == "bingo18":
                    controls["play"].setCurrentIndex(controls["play"].findData("size"))
                    controls["choice"].setCurrentIndex(controls["choice"].findData({"play": "size", "main": ["tie"]}))
                if game.startswith("max3d"):
                    controls["first"].setText("009")
                    controls["first"].editingFinished.emit()
                for language, theme in (("vi", "light"), ("en", "dark")):
                    window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                    window.set_theme(theme)
                    check_page(window)
                buttons = {button.text(): button for button in window.verify_setup.findChildren(QPushButton)}
                buttons[tr("Chạy mô phỏng")].click()
                if game == "bingo18":
                    assert not controls["play"].isEnabled()
                wait_idle(window)
                sim = json.loads(window.report.toPlainText())
                assert sim["status"] == "completed" and sim["completed_trials"] == 10_000
                assert sim["ticket"] == window.sample_ticket().selections
                assert window.report.isHidden() and window.report_table.isVisible()
                assert "10,000" in window.report_detail.text()
                assert "Ticket tested" in window.report_detail.text()
                if game == "bingo18":
                    assert sim["ticket"] == {"play": "size", "main": ["tie"]}
                    assert controls["play"].isEnabled()
                    assert "3 distinct" in window.verify_play_note.text()
                buttons[tr("Chạy kiểm chứng")].click()
                wait_idle(window)
                report = window.store.reports()[0]
                assert report["status"] == "completed" and report["tested_draws"] == 1
                assert report["manifest"]["game_id"] == game
                assert report["manifest"]["config"]["tickets_per_draw"] == (3 if game == "bingo18" else 5)
                assert window.report.isHidden()
                assert window.report_table.horizontalHeaderItem(2).text() == "Random selection"
                assert window.report_table.rowCount() == 1
                window.report_json_button.click()
                assert window.report.isVisible()
                window.report_json_button.click()
                assert window.report.isHidden()
                assert len(window.store.list_draws(rule)) == 3
            window.language_choice.setCurrentIndex(window.language_choice.findData("vi"))
            window.report.setPlainText(json.dumps({
                "status": "completed", "warmup": 90,
                "summary": {"development": {"draws": 10, "tickets": 50, "strategy_win_rate": .06,
                                             "baseline_mean_win_rate": .0958, "difference": -.0358}},
            }))
            assert window.report_metric.text() == "6,00%"
            assert "3/50 vé trúng trong 10 kỳ" in window.report_detail.text()
            assert "90 kỳ đầu" in window.report_detail.text()
            assert window.report_table.item(0, 2).text() == "9,58%"
            assert window.report_table.item(0, 3).text() == "-3,58"
            check_page(window)
            window.language_choice.setCurrentIndex(window.language_choice.findData("en"))
            assert window.report_metric.text() == "6.00%"
            assert window.report_table.item(0, 3).text() == "-3.58"
            window.report_json_button.click()
            window.report.clear()
            assert window.report.isHidden() and window.report_panel.isHidden()
            window.report.setPlainText(json.dumps({
                "status": "incomplete", "ticket": {"main": ["007"]},
                "completed_trials": 0, "requested_trials": 10_000, "tiers": {},
            }))
            assert window.report_metric.isHidden() and window.report_table.isHidden()
            assert "0/10,000" in window.report_detail.text()
            assert window.report_badge.text() == "Incomplete"
            window.change_play("any_triple")
            window.nav.setCurrentRow(4)
            suggestion = window.ticket_controls[1]
            assert suggestion["play"].findData("any_triple") == -1
            assert suggestion["play"].currentData() == "draw"
            assert suggestion["choice"].isHidden()
            assert window.count.isVisible() and window.count.maximum() == 100
            assert window.method_box.isVisible()
            window.method.setCurrentIndex(window.method.findData("uniform_v1"))
            window.count.setValue(3)
            with patch("app.ui.SystemRandom", return_value=Random(42)):
                window.suggest_button.click()
            assert window.suggestion_table.rowCount() == 3 and window.suggestion_table.isVisible()
            assert window.suggestion_table.item(0, 1).text().split() == ["04", "01", "02"]
            assert window.suggestion_table.item(1, 1).text().split() == ["02", "05", "05"]
            assert window.generated is None and window.save_button.isHidden() and window.worker is None
            assert window.store.suggestions(window.rule) == [] and len(window.store.list_draws(window.rule)) == 3
            check_page(window)
            window.analysis_window_input.setValue(2)
            for method in ("frequency90_laplace1_v1", "bayes90_v1"):
                window.method.setCurrentIndex(window.method.findData(method))
                window.suggest_button.click()
                assert window.suggestion_table.rowCount() == 3
            window.method.setCurrentIndex(window.method.findData("ai_history90_v1"))
            ai.return_value = {"status": "completed", "output_text": json.dumps({
                "results": [[6, 3, 4], [5, 1, 5], [1, 2, 3]], "explanation": "offline fixture",
            })}
            window.key.setText("temporary-offline-test-key")
            window.suggest_button.click()
            assert not window.method.isEnabled()
            wait_idle(window)
            ai.assert_called_once()
            assert window.suggestion_table.item(0, 1).text().split() == ["06", "03", "04"]
            assert window.suggestion_table.item(1, 1).text().split() == ["05", "01", "05"]
            context = json.loads(ai.call_args.args[2]["input"])
            assert len(context["history"]) == 2 and "tools" not in ai.call_args.args[2]
            ai.return_value = {"status": "incomplete"}
            window.suggest_button.click()
            wait_idle(window)
            assert window.suggestion_table.rowCount() == 0 and window.worker is None and window.method.isEnabled()
            ai.reset_mock()
            window.nav.setCurrentRow(5)
            window.run_simulation()
            wait_idle(window)
            assert json.loads(window.report.toPlainText())["ticket"] == {"play": "any_triple", "main": []}
            assert window.verify_run_button.text() == "Run validation"
            window.verify_run_button.click()
            wait_idle(window)
            fixed_report = window.store.reports()[0]
            assert fixed_report["manifest"]["config"]["method"] == "uniform_v1"
            assert fixed_report["rows"][0]["strategy_wins"] == fixed_report["rows"][0]["baseline_mean_wins"]
            ai.assert_not_called()

            window.nav.setCurrentRow(4)
            suggestion["play"].setCurrentIndex(suggestion["play"].findData("triple"))
            assert window.play_context() == "any_triple" and window.generated is None
            assert window.count.isVisible() and window.count.maximum() == 6
            assert window.suggestion_table.rowCount() == 0 and window.method_box.isVisible()
            assert suggestion["choice"].isHidden()
            window.method.setCurrentIndex(window.method.findData("uniform_v1"))
            window.count.setValue(6)
            window.make_suggestions()
            assert {ticket.selections["main"][0] for ticket in window.generated[2]} == set(range(1, 7))
            from app.components import BallDelegate
            for index, ticket in enumerate(window.generated[2]):
                value = ticket.selections["main"][0]
                groups = BallDelegate.groups(window.suggestion_table.item(index, 1).text())
                assert groups[0][1] == [(f"{value:02}", "normal")] * 3
            check_page(window)
            window.nav.setCurrentRow(3)
            odds = window.ticket_controls[0]
            odds["play"].setCurrentIndex(odds["play"].findData("sum"))
            assert odds["choice"].isVisible() and odds["choice"].count() == 16
            assert window.odds_table.item(0, 1).text() == "1/216"
            odds["choice"].setCurrentIndex(odds["choice"].findData({"play": "sum", "main": [10]}))
            assert window.odds_table.item(0, 1).text() == "1/8"
            assert suggestion["play"].currentData() == "triple"

            window.nav.setCurrentRow(5)
            window.game.setCurrentIndex(window.game.findData("max3d"))
            window.method.setCurrentIndex(window.method.findData("ai_history90_v1"))
            window.key.setText("temporary-offline-test-key")
            ai.return_value = {"status": "completed", "output_text": json.dumps({
                "tickets": [{"main": [f"{n:03}"]} for n in range(5)], "explanation": "offline fixture",
            })}
            assert window.verify_run_button.text() == "Run AI validation"
            assert "may incur charges" in window.verify_run_note.text()
            window.verify_run_button.click()
            wait_idle(window)
            ai.assert_called_once()
            context = json.loads(ai.call_args.args[2]["input"])
            assert [row[0] for row in context["history"]] == ["1", "2"]
            assert ai.call_args.args[2].get("tools") in ([], None)
            result = window.store.reports()[0]
            assert result["status"] == "completed" and result["tested_draws"] == 1
            assert result["manifest"]["config"]["method"] == "ai_history90_v1"
            assert result["rows"][0]["target_draw_id"] == "3"
            assert result["rows"][0]["history_cutoff"] == "2"
            assert "temporary-offline-test-key" not in json.dumps(result)
            assert window.store.suggestions(window.rule) == [] and len(window.store.list_draws(window.rule)) == 3
            report_count = len(window.store.reports())
            ai.return_value = {"status": "incomplete"}
            window.verify_run_button.click()
            wait_idle(window)
            assert ai.call_count == 2 and len(window.store.reports()) == report_count
            fetch.assert_not_called()
        finally:
            window.close()
            app.processEvents()


if __name__ == "__main__":
    check_keno()
    check_max()
    check_bingo()
    check_experiments()
    check_desktop()
    print("Keno, Max 3D, Max 3D Pro and Bingo18 experiment checks passed.")
