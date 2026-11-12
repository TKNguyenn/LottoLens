from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import unittest

from app.backtest import run_backtest
from app.domain import Draw, Ticket
from app.rules import get_rule
from app.simulation import simulate
from app.generation import generate as real_generate


def history(count):
    rule = get_rule("mega")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [Draw("mega", "normal", rule.rule_version, str(i+1),
                 (start+timedelta(days=i)).isoformat(), {"main": [1, 2, 3, 4, 5, 6]},
                 "synthetic:test", start.isoformat(), "b"*64)
            for i in range(count)]


class ExperimentTests(unittest.TestCase):
    def test_simulation_reproduces_and_cancellation_is_incomplete(self):
        rule = get_rule("mega")
        ticket = Ticket("mega", "normal", rule.rule_version, {"main": [1, 2, 3, 4, 5, 6]})
        first = simulate(rule, ticket, 100, 42, lambda: False, lambda *_: None)
        second = simulate(rule, ticket, 100, 42, lambda: False, lambda *_: None)
        self.assertEqual(first["tiers"], second["tiers"])
        self.assertEqual(first["completed_trials"], 100)
        cancelled = simulate(rule, ticket, 100, 42, lambda: True, lambda *_: None)
        self.assertEqual(cancelled["status"], "incomplete")
        self.assertEqual(cancelled["completed_trials"], 0)

    def test_backtest_uses_only_prior_draws_and_freezes_results(self):
        records = []
        def spy(rule, previous, count, method, rng):
            records.append([int(d.draw_id) for d in previous])
            return real_generate(rule, previous, count, method, rng)
        config = {"tickets_per_draw": 2, "baseline_runs": 3, "seed": 123, "bootstrap_runs": 20}
        with patch("app.backtest.generate", side_effect=spy):
            first = run_backtest(get_rule("mega"), history(93), config, lambda: False, lambda *_: None)
        self.assertTrue(records)
        self.assertTrue(all(max(ids) <= 92 for ids in records))
        self.assertEqual(first["rows"][0]["target_draw_id"], "91")
        second = run_backtest(get_rule("mega"), history(94), config, lambda: False, lambda *_: None)
        self.assertEqual(first["rows"][0]["tickets"], second["rows"][0]["tickets"])
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["assessment"], "exploratory_only")

    def test_holdout_is_last_fifty_and_report_is_reproducible(self):
        config = {"tickets_per_draw": 1, "baseline_runs": 2, "seed": 2, "bootstrap_runs": 20}
        first = run_backtest(get_rule("mega"), history(190), config, lambda: False, lambda *_: None)
        second = run_backtest(get_rule("mega"), history(190), config, lambda: False, lambda *_: None)
        self.assertEqual(first["manifest"], second["manifest"])
        self.assertEqual(first["rows"], second["rows"])
        self.assertEqual(first["manifest"]["holdout_count"], 50)
        self.assertEqual(first["rows"][-50]["phase"], "holdout")
        self.assertEqual(first["rows"][-51]["phase"], "development")

    def test_backtest_cancel_and_duplicate_draws(self):
        result = run_backtest(get_rule("mega"), history(91), {}, lambda: True, lambda *_: None)
        self.assertEqual(result["status"], "incomplete")
        with self.assertRaises(ValueError):
            run_backtest(get_rule("mega"), history(91)+history(1), {}, lambda: False, lambda *_: None)


if __name__ == "__main__":
    unittest.main()
