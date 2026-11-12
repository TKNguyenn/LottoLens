"""Offline regression checks for configurable analysis history; no provider calls."""
from datetime import datetime, timedelta, timezone
from dataclasses import asdict
import json
from pathlib import Path
from random import Random
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai import AIConfig
from app.ai_generation import build_generation_request, generate_with_ai
from app.backtest import run_backtest
from app.domain import Draw, digest
from app.generation import METHODS, explain_ticket, generate, generation_profile
from app.rules import get_rule
from app.sources import CancelledError


def history(count, game="mega"):
    rule = get_rule(game)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [Draw(game, rule.mode_id, rule.rule_version, str(i + 1),
                 (start + timedelta(days=i)).isoformat(),
                 {"main": list(range(1, rule.drawn + 1)),
                  **({"special": rule.special_max} if rule.special_max else {})},
                 "synthetic:analysis-window", start.isoformat(), "a" * 64)
            for i in range(count)]


def rejects(action, error=ValueError):
    try:
        action()
    except error as exc:
        return str(exc)
    raise AssertionError(f"Expected {error.__name__}")


def main():
    rule, records = get_rule("mega"), history(130)
    # Removing configurable slicing or changing prior strength must fail here.
    for window in (30, 120):
        profile = generation_profile(rule, list(reversed(records)), "bayes90_v1", history_window=window)
        assert profile["history_used"] == profile["history_window"] == window
        assert profile["prior_equivalent_draws"] == 90
        assert profile["cutoff_draw_id"] == "130"
        assert profile["main"][1]["count"] == window
        assert abs(profile["main"][1]["model_rate"] - (window + 12) / (window + 90)) < 1e-12
        assert abs(profile["main"][7]["model_rate"] - 12 / (window + 90)) < 1e-12
        changed = history(130)
        for item in changed[:-window]:
            item.payload["main"] = [7, 8, 9, 10, 11, 12]
        assert generation_profile(rule, changed, "bayes90_v1", window) == profile
        tickets = generate(rule, records, 2, "bayes90_v1", Random(9), window)
        detail = explain_ticket(rule, records, tickets[0], "bayes90_v1", window)
        assert detail["history_window"] == detail["history_used"] == window
        assert detail["prior_equivalent_draws"] == 90
        assert f"({window} + 90)" in detail["formula"]
        freq = generation_profile(rule, records, "frequency90_laplace1_v1", window)
        assert abs(freq["main"][1]["model_rate"] - (window + 1) / (window + 45)) < 1e-12
    assert generation_profile(rule, history(1), "bayes90_v1", 1)["history_used"] == 1
    assert generation_profile(rule, history(2000), "bayes90_v1", 2000)["history_used"] == 2000
    assert generate(rule, [], 3, "uniform_v1", Random(7), 30) == generate(rule, [], 3, "uniform_v1", Random(7), 120)

    baseline = json.loads((ROOT / "docs/redesign/settings/analysis-defaults.json").read_text())
    for game in ("mega", "power", "lotto", "keno"):
        current_rule, current_history = get_rule(game), history(baseline["history_count"], game)
        for method in METHODS:
            expected = baseline["cases"][game][method]
            assert digest([asdict(ticket) for ticket in generate(current_rule, current_history, 4, method, Random(baseline["seed"]))]) == expected["tickets_hash"]
            current = generation_profile(current_rule, current_history, method)
            assert digest({k: v for k, v in current.items() if k != "history_window"}) == expected["profile_hash"]

    config = AIConfig(api_key="offline-test")
    for invalid in (True, False, 0, -1, 2001, 30.0, "30", None):
        actions = [lambda: generation_profile(rule, records, "uniform_v1", invalid),
                   lambda: explain_ticket(rule, records, generate(rule, [], 1, "uniform_v1", Random(1))[0], "uniform_v1", invalid),
                   lambda: generate(rule, records, 1, "uniform_v1", Random(1), invalid),
                   lambda: build_generation_request(config, rule, records, 1, invalid),
                   lambda: generate_with_ai(config, rule, records, 1, history_window=invalid),
                   lambda: run_backtest(rule, records, {"history_window": invalid})]
        with patch("app.ai._send") as send:
            for action in actions:
                rejects(action)
            assert send.call_count == 0
    for window in (30, 120):
        short = history(window - 1)
        with patch("app.ai._send") as send:
            rejects(lambda: generate(rule, short, 1, "bayes90_v1", Random(1), window))
            rejects(lambda: generate_with_ai(config, rule, short, 1, history_window=window))
            rejects(lambda: run_backtest(rule, history(window), {"history_window": window}))
            assert send.call_count == 0

    # Transport is the only external side effect mocked; the actual builder/guard/parser run.
    answer = {"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "Offline fixture"}
    sent, deltas = [], []
    cancel = lambda: False
    def transport(url, headers, body, **kwargs):
        assert kwargs["cancel"] is cancel
        sent.append(body)
        kwargs["on_delta"]("fixture delta")
        return {"status": "completed", "output_text": json.dumps(answer), "model": "fixture", "id": "offline"}
    for window in (30, 120):
        with patch("app.ai._send", side_effect=transport) as send:
            result = generate_with_ai(config, rule, records, 1, cancel, deltas.append, window)
            assert send.call_count == 1
        body = sent[-1]
        context = json.loads(body["input"])
        assert len(context["history"]) == window
        assert context["history"][0][0] == str(131 - window)
        assert context["history"][-1][0] == context["cutoff_draw_id"] == "130"
        assert context["frequencies"]["1"] == window
        assert f"{window} kỳ" in body["instructions"]
        assert "tools" not in body and body["reasoning"] == {"effort": "high"} and body["stream"]
        assert len(body["input"]) <= 10_000
        assert result["metadata"]["history_used"] == result["metadata"]["history_window"] == window
        assert result["metadata"]["instructions_hash"] == digest(body["instructions"])
        assert result["metadata"]["input_hash"] == digest(context)
    assert deltas == ["fixture delta", "fixture delta"]
    with patch("app.ai._send", side_effect=CancelledError("fixture cancel")) as send:
        rejects(lambda: generate_with_ai(config, rule, records, 1, history_window=30), CancelledError)
        assert send.call_count == 1
    with patch("app.ai._send") as send:
        message = rejects(lambda: generate_with_ai(config, rule, history(2000), 1, history_window=2000))
        assert "10.000" in message and send.call_count == 0

    calls, progress = [], []
    def track(current_rule, previous, count, method, rng, history_window=90):
        calls.append((method, history_window, [int(d.draw_id) for d in previous]))
        return generate(current_rule, previous, count, method, rng, history_window)
    backtest_config = {"history_window": 30, "tickets_per_draw": 1, "baseline_runs": 2, "bootstrap_runs": 2}
    with patch("app.backtest.generate", side_effect=track):
        report = run_backtest(rule, history(33), backtest_config, progress=lambda done, total: progress.append((done, total)))
    assert report["status"] == "completed"
    assert report["manifest"]["warmup"] == report["manifest"]["config"]["history_window"] == 30
    assert [row["target_draw_id"] for row in report["rows"]] == ["31", "32", "33"]
    assert progress == [(1, 3), (2, 3), (3, 3)]
    assert len(calls) == 9
    for index, (_, window, ids) in enumerate(calls):
        assert window == 30 and max(ids) == 30 + index // 3
    assert {method for method, _, _ in calls} == {"frequency90_laplace1_v1", "uniform_v1"}
    extended = run_backtest(rule, history(34), backtest_config)
    assert report["rows"][0] == extended["rows"][0]
    default = run_backtest(rule, history(91), {"tickets_per_draw": 1, "baseline_runs": 1, "bootstrap_runs": 1})
    assert default["manifest"]["warmup"] == default["manifest"]["config"]["history_window"] == 90
    print("Analysis core checks passed: N=1/30/120/2000, prior=90, seeded baseline parity, AI guard/no-retry, backtest isolation.")


if __name__ == "__main__":
    main()
