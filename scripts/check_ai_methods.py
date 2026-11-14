"""Offline regressions for AI portfolio optimization and held-out signals."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from random import Random
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai import AIConfig
from app.ai_methods import ANY_PRIZE, EXACT_RESULT, OPTIMIZE, SIGNAL, optimize_prize, prize_targets, test_signal
from app.generation import generate
from app.rules import RULES, get_rule
from app.simulation import random_draw
from app.sources import CancelledError


def history(rule, count=40):
    rng = Random(12)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    draws = [random_draw(rule, rng, index + 1) for index in range(count)]
    for index, draw in enumerate(draws):
        draw.draw_at_utc = (start + timedelta(days=index)).isoformat()
    return draws


def check_ui():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from app.ui import Desktop
    from check_redesign import check_page

    application = QApplication([])
    if not QFontDatabase.families():
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    with TemporaryDirectory() as directory:
        root = Path(directory)
        window = Desktop(root / "history.sqlite3", root / "config.json")
        try:
            window.resize(1000, 700)
            window.show()
            window.nav.setCurrentRow(4)
            window.game.setCurrentIndex(window.game.findData("bingo18"))
            rule = window.rule
            window.store.add_draws(rule, history(rule, 100))
            window.refresh()
            window.analysis_window_input.setValue(100)
            window.count.setValue(2)
            window.key.setText("test-key")

            def response(_url, _headers, body, **kwargs):
                payload = json.loads(body["input"])
                if "signal_options" in payload:
                    result = {"method": "recent_cold", "lookback": 5}
                elif payload.get("game_id") == "mega":
                    tickets = generate(window.rule, [], payload["count"], "uniform_v1", Random(3))
                    result = {"tickets": [ticket.selections for ticket in tickets], "explanation": "Example"}
                else:
                    result = {"results": [[1, 1, 2]] * payload["count"], "explanation": "Example"}
                return {"status": "completed", "output_text": json.dumps(result)}

            with patch("app.ai._send", side_effect=response) as send:
                for method in (OPTIMIZE, SIGNAL):
                    window.method.setCurrentIndex(window.method.findData(method))
                    check_page(window)
                    assert "100 kỳ" in window.method.currentText()
                    assert window.prize_target_box.isVisible() == (method == OPTIMIZE)
                    if method == OPTIMIZE:
                        assert window.prize_target.currentData() == EXACT_RESULT
                        assert "100 kỳ" in window.ai_history_callout.text.text()
                    else:
                        assert "75 kỳ" in window.method_note.text() and "25 kỳ" in window.method_note.text()
                    window.suggest_button.click()
                    assert window.worker and not window.method.isEnabled()
                    for _ in range(600):
                        if window.worker is None:
                            break
                        QTest.qWait(10)
                    assert window.worker is None and window.suggestion_table.rowCount() == 2, window.notice.text()
                    assert window.generated is None and not window.save_button.isVisible()
                    assert not window.store.suggestions(rule) and len(window.store.list_draws(rule)) == 100
                assert send.call_count == 2
                window.apply_language("en")
                assert "AI signal discovery and validation" in window.explanation.toPlainText()
                assert "Exact ordered three-number match" in window.explanation.toPlainText()
                assert "Tested on 25 saved draws" in window.explanation.toPlainText()
                assert "Sent to AI: 75 draws" in window.explanation.toPlainText()
                check_page(window)
                window.game.setCurrentIndex(window.game.findData("mega"))
                rule = window.rule
                window.store.add_draws(rule, history(rule))
                window.refresh()
                window.method.setCurrentIndex(window.method.findData(OPTIMIZE))
                window.prize_target.setCurrentIndex(window.prize_target.findData("Jackpot"))
                window.suggest_button.click()
                for _ in range(600):
                    if window.worker is None:
                        break
                    QTest.qWait(10)
                assert window.worker is None and window.generated, window.notice.text()
                rates = window.generated[4]["rates"]
                assert all(abs(rate - 2 / 8145060) < 1e-12 for rate in rates.values())
                assert window.generated[4]["target"] == "Jackpot"
                assert not window.store.suggestions(rule)
                assert send.call_count == 3
        finally:
            window.close()


def main():
    config = AIConfig("https://api.example.invalid/v1", "synthetic-model", "test-key")
    bingo = get_rule("bingo18")
    with patch("app.ai._send", return_value={
        "status": "completed", "output_text": json.dumps({"results": [[1, 2, 3]] * 16, "explanation": "Example"})
    }) as send:
        optimized = optimize_prize(config, bingo, history(bingo, 140), 2, 100, "draw", EXACT_RESULT)
        payload = json.loads(send.call_args.args[2]["input"])
        assert optimized["history_used"] == 100
        assert [row[0] for row in payload["history"]] == [str(i) for i in range(41, 141)]
        send.return_value = {"status": "completed", "output_text": '{"method":"bayes90_v1","lookback":100}'}
        signal = test_signal(config, bingo, history(bingo, 140), 2, 100, "draw")
        payload = json.loads(send.call_args.args[2]["input"])
        assert signal["holdout"] == 35 and signal["history_used"] == 100
        assert 100 in payload["signal_options"]["lookbacks"]
        assert [row[0] for row in payload["history"]] == [str(i) for i in range(6, 106)]
        try:
            optimize_prize(config, bingo, history(bingo, 1000), 2, 1000, "draw", EXACT_RESULT)
        except ValueError as error:
            assert "10.000" in str(error) and send.call_count == 2
        else:
            raise AssertionError("Oversized window should fail before the provider call")
    for game in RULES:
        rule = get_rule(game)
        context = "sum" if rule.kind == "dice" else None
        draws = history(rule, 140)

        def response(_url, _headers, body, **kwargs):
            payload = json.loads(body["input"])
            assert not body.get("tools")
            if "signal_options" in payload:
                assert [row[0] for row in payload["history"]] == [str(i) for i in range(6, 106)]
                output = {"method": "frequency90_laplace1_v1", "lookback": 5}
            else:
                assert [row[0] for row in payload["history"]] == [str(i) for i in range(41, 141)]
                tickets = generate(rule, [], payload["count"], "uniform_v1", Random(1), play_context=context)
                output = {"tickets": [ticket.selections for ticket in tickets], "explanation": "Example"}
            return {"status": "completed", "output_text": json.dumps(output)}

        with patch("app.ai._send", side_effect=response) as send:
            result = optimize_prize(config, rule, draws, 2, 100, context, ANY_PRIZE)
            assert len(result["tickets"]) == 2 and send.call_count == 1
            assert all(0 <= rate <= 1 for rate in result["rates"].values())
            signal = test_signal(config, rule, draws, 2, 100, context)
            assert len(signal["tickets"]) == 2 and send.call_count == 2
            assert signal["holdout"] == 35 and signal["cutoff"] == "105"
            assert set(signal["rates"]) == {"ai", "uniform", "bayes", "local"}
    assert prize_targets(bingo, "draw") == (EXACT_RESULT,)
    assert "Trùng 0 số" in prize_targets(get_rule("keno", "pick8"), None)
    assert "Trùng 0 số" not in prize_targets(get_rule("keno", "pick7"), None)
    mega = get_rule("mega")
    with patch("app.ai._send") as send:
        try:
            optimize_prize(config, mega, history(mega), 2, 30, None, ANY_PRIZE, cancel=lambda: True)
        except CancelledError:
            send.assert_not_called()
        else:
            raise AssertionError("Canceled optimization reached the provider")
        send.return_value = {"status": "completed", "output_text": '{"method":"exec","lookback":5}'}
        try:
            test_signal(config, mega, history(mega), 2, 30, None)
        except ValueError:
            send.assert_called_once()
        else:
            raise AssertionError("Accepted a rule outside the allowlist")
    check_ui()
    print("AI prize optimization, holdout isolation, cancellation and bilingual GUI passed across all seven games.")


if __name__ == "__main__":
    main()
