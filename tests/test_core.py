import unittest
from datetime import datetime, timezone
from fractions import Fraction
from random import Random

from app.domain import Draw, Ticket, validate_draw, validate_ticket
from app.rules import get_rule
from app.probability import overlap_probabilities, probabilities
from app.evaluation import evaluate
from app.generation import generate
from app.generation import generation_profile, explain_ticket
from app.statistics import describe, wilson95, holm_adjust


def draw(game="mega", numbers=(1, 2, 3, 4, 5, 6), *, identifier="1", special=None):
    rule = get_rule(game)
    payload = {"main": list(numbers)}
    if special is not None:
        payload["special"] = special
    return Draw(game, rule.mode_id, rule.rule_version, identifier,
                "2026-11-01T11:30:00+00:00", payload,
                "https://vietlott.vn/example", "2026-11-09T00:00:00+00:00", "a" * 64,
                verification_status="rule_verified")


class DomainTests(unittest.TestCase):
    def test_reject_duplicate_out_of_range_and_boolean(self):
        rule = get_rule("mega")
        for numbers in ([1, 1, 2, 3, 4, 5], [1, 2, 3, 4, 5, 46], [True, 2, 3, 4, 5, 6]):
            with self.subTest(numbers=numbers), self.assertRaises(ValueError):
                validate_ticket(rule, Ticket("mega", "normal", rule.rule_version, {"main": numbers}))

    def test_bonus_cannot_repeat_power_main_but_lotto_can(self):
        with self.assertRaises(ValueError):
            validate_draw(get_rule("power"), draw("power", special=6))
        validate_draw(get_rule("lotto"), draw("lotto", (1, 2, 3, 4, 5), special=5))

    def test_naive_datetime_and_empty_identity_rejected(self):
        item = draw()
        item.draw_at_utc = "2026-11-01T18:30:00"
        with self.assertRaises(ValueError):
            validate_draw(get_rule("mega"), item)
        item = draw(identifier="")
        with self.assertRaises(ValueError):
            validate_draw(get_rule("mega"), item)

    def test_triple_leading_zero_survives(self):
        rule = get_rule("max3d")
        validate_ticket(rule, Ticket("max3d", "normal", rule.rule_version, {"main": ["007"]}))
        with self.assertRaises(ValueError):
            validate_ticket(rule, Ticket("max3d", "normal", rule.rule_version, {"main": [7]}))


class ProbabilityTests(unittest.TestCase):
    def test_tiny_distribution_is_exact(self):
        self.assertEqual(overlap_probabilities(5, 2, 2),
                         {0: Fraction(3, 10), 1: Fraction(6, 10), 2: Fraction(1, 10)})
        self.assertEqual(overlap_probabilities(45, 6, 6)[6], Fraction(1, 8_145_060))
        self.assertEqual(sum(overlap_probabilities(55, 6, 6).values()), 1)

    def test_boundaries_and_invalid_values(self):
        self.assertEqual(overlap_probabilities(5, 0, 2), {0: Fraction(1)})
        self.assertEqual(overlap_probabilities(5, 2, 0), {0: Fraction(1)})
        for args in ((0, 0, 0), (5, 6, 1), (5, -1, 2), (5, 1, True)):
            with self.assertRaises(ValueError):
                overlap_probabilities(*args)

    def test_power_bonus_excludes_first_prize(self):
        rule = get_rule("power")
        ticket = Ticket("power", "normal", rule.rule_version, {"main": [1, 2, 3, 4, 5, 7]})
        dist = probabilities(rule, ticket)
        self.assertEqual(dist["Jackpot 1"], Fraction(1, 28_989_675))
        self.assertEqual(dist["Jackpot 2"], Fraction(6, 28_989_675))
        self.assertEqual(dist["Giải Nhất"], Fraction(288, 28_989_675))
        self.assertEqual(sum(dist.values()), 1)

    def test_lotto_special_probabilities_partition(self):
        rule = get_rule("lotto")
        ticket = Ticket("lotto", "normal", rule.rule_version, {"main": [1, 2, 3, 4, 5], "special": 1})
        dist = probabilities(rule, ticket)
        self.assertEqual(dist["Độc Đắc"], Fraction(1, 3_895_584))
        self.assertEqual(sum(dist.values()), 1)


class EvaluationTests(unittest.TestCase):
    def test_mega_fixed_and_unknown_jackpot(self):
        rule = get_rule("mega")
        result = evaluate(rule, Ticket("mega", "normal", rule.rule_version, {"main": [1, 2, 3, 7, 8, 9]}), draw())
        self.assertEqual(result.prize_tiers, ["Giải Ba"])
        self.assertEqual(result.payout_vnd, 30_000)
        result = evaluate(rule, Ticket("mega", "normal", rule.rule_version, {"main": [1, 2, 3, 4, 5, 6]}), draw())
        self.assertIsNone(result.payout_vnd)

    def test_power_five_and_bonus_is_jackpot_two(self):
        rule = get_rule("power")
        ticket = Ticket("power", "normal", rule.rule_version, {"main": [1, 2, 3, 4, 5, 7]})
        result = evaluate(rule, ticket, draw("power", special=7))
        self.assertEqual(result.prize_tiers, ["Jackpot 2"])
        self.assertIsNone(result.payout_vnd)

    def test_wrong_game_cannot_be_evaluated(self):
        rule = get_rule("mega")
        with self.assertRaises(ValueError):
            evaluate(rule, Ticket("mega", "normal", rule.rule_version, {"main": [1, 2, 3, 4, 5, 6]}), draw("power", special=7))

    def test_manual_and_unverified_historical_money_stays_unknown(self):
        rule = get_rule("mega")
        ticket = Ticket("mega", "normal", rule.rule_version, {"main": [1, 2, 3, 7, 8, 9]})
        for status in ("manual_unverified", "source_snapshot", "historical_rule_unverified"):
            item = draw(); item.verification_status = status
            with self.subTest(status=status):
                self.assertIsNone(evaluate(rule, ticket, item).payout_vnd)


class StatisticsAndGenerationTests(unittest.TestCase):
    def test_bayesian_generation_shrinks_frequency_towards_fair_prior(self):
        rule = get_rule("mega")
        records = [draw(identifier=str(i)) for i in range(90)]
        profile = generation_profile(rule, records, "bayes90_v1")
        self.assertAlmostEqual(profile["main"][1]["historical_rate"], 1.)
        self.assertAlmostEqual(profile["main"][1]["model_rate"], 17/30)
        self.assertAlmostEqual(profile["main"][7]["model_rate"], 1/15)
        tickets = generate(rule, records, 3, "bayes90_v1", Random(77))
        for ticket in tickets:
            validate_ticket(rule, ticket)
        detail = explain_ticket(rule, records, tickets[0], "bayes90_v1")
        self.assertEqual(detail["history_used"], 90)
        self.assertEqual(detail["jackpot_probability"], {"numerator": 1, "denominator": 8_145_060})
        self.assertEqual(len(detail["selected_number_stats"]), 6)

    def test_probability_statistics_needs_real_history_and_uses_last_ninety(self):
        rule = get_rule("mega")
        with self.assertRaises(ValueError):
            generate(rule, [], 1, "bayes90_v1", Random(1))
        records = [draw(identifier=f"{i:05}") for i in range(90)]
        older = draw(numbers=(7, 8, 9, 10, 11, 12), identifier="older")
        older.draw_at_utc = "2020-01-01T00:00:00+00:00"
        self.assertEqual(generation_profile(rule, records, "bayes90_v1"),
                         generation_profile(rule, [older]+records, "bayes90_v1"))

    def test_wilson_and_holm_independent_oracles(self):
        lo, hi = wilson95(0, 10)
        self.assertAlmostEqual(lo, 0, places=12)
        self.assertAlmostEqual(hi, .2775328, places=6)
        self.assertEqual(holm_adjust([]), [])
        for actual, expected in zip(holm_adjust([.01, .04, .03]), [.03, .06, .06]):
            self.assertAlmostEqual(actual, expected)
        with self.assertRaises(ValueError):
            wilson95(1, 0)

    def test_counts_exclude_special_and_use_draw_denominator(self):
        rule = get_rule("power")
        data = [draw("power", identifier="1", special=7),
                draw("power", (1, 2, 3, 4, 5, 8), identifier="2", special=7)]
        stats = describe(rule, data)
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["frequencies"][1], 2)
        self.assertEqual(stats["frequencies"][7], 0)
        self.assertEqual(stats["special_frequencies"][7], 2)

    def test_generator_valid_unique_and_reproducible(self):
        rule = get_rule("mega")
        first = generate(rule, [], 10, "uniform_v1", Random(123))
        second = generate(rule, [], 10, "uniform_v1", Random(123))
        self.assertEqual([t.selections for t in first], [t.selections for t in second])
        self.assertEqual(len({tuple(t.selections["main"]) for t in first}), 10)
        for ticket in first:
            validate_ticket(rule, ticket)

    def test_frequency_requires_ninety_draws(self):
        rule = get_rule("mega")
        with self.assertRaises(ValueError):
            generate(rule, [draw(identifier=str(i)) for i in range(89)], 1,
                     "frequency90_laplace1_v1", Random(0))
        tickets = generate(rule, [draw(identifier=str(i)) for i in range(90)], 2,
                           "frequency90_laplace1_v1", Random(0))
        self.assertEqual(len(tickets), 2)


if __name__ == "__main__":
    unittest.main()
