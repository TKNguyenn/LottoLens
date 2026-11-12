"""Offline regression checks for retained incremental history; uses temporary databases."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain import Draw, Ticket
from app.rules import get_rule
from app.sources import CancelledError, OfficialSource, parse_results
from app.storage import Store

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def draw(number, rule=None):
    rule = rule or get_rule("mega")
    payload = {"main": list(range(1, rule.drawn + 1))}
    if rule.special_max:
        payload["special"] = rule.population
    return Draw(rule.game_id, rule.mode_id, rule.rule_version, str(number),
                "2026-11-09T00:00:00+00:00", payload, "https://vietlott.vn/",
                "2026-11-09T01:00:00+00:00", "a" * 64)


class IncrementalChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "history.sqlite3"
        self.store = Store(self.path)
        self.rule = get_rule("mega")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def seed(self):
        self.store.add_draws(self.rule, [draw(i) for i in range(1, 5)], keep_latest=3)

    def ids(self, rule=None):
        return [d.draw_id for d in self.store.list_draws(rule or self.rule)]

    def test_new_api_exists(self):
        self.assertTrue(callable(getattr(self.store, "sync_window", None)))

    def test_cap_proof_and_expansion(self):
        self.seed()
        self.assertEqual(self.ids(), ["2", "3", "4"])
        self.assertEqual(len(self.store.sync_window(self.rule, 3)), 3)
        self.assertEqual(self.store.sync_window(self.rule, 4), [])
        self.assertEqual(self.store.db.execute("PRAGMA user_version").fetchone()[0], 2)

    def test_manual_or_sql_edit_invalidates_proof(self):
        self.seed()
        self.store.add_draws(self.rule, [draw(6)])
        self.assertEqual(self.store.sync_window(self.rule, 3), [])
        self.seed()
        self.store.db.execute("DELETE FROM draw_revisions WHERE draw_id='3'")
        self.store.db.commit()
        self.assertEqual(self.store.sync_window(self.rule, 2), [])

    def test_known_overlap_revised_and_old_all_revisions_pruned(self):
        self.seed()
        old = replace(draw(2), payload={"main": [1, 2, 3, 4, 5, 7]})
        self.store.add_draws(self.rule, [old], keep_latest=3)
        corrected = replace(draw(4), payload={"main": [1, 2, 3, 4, 5, 8]})
        counts = self.store.apply_sync(self.rule, {"draws": [draw(5), corrected], "status": "known_boundary"}, 3)
        self.assertEqual(counts["added"], 1)
        self.assertEqual(counts["revised"], 1)
        self.assertEqual(self.ids(), ["3", "4", "5"])
        self.assertEqual(self.store.revisions("mega", "normal", "2"), [])
        self.assertEqual(len(self.store.sync_window(self.rule, 3)), 3)

    def test_failed_bad_batch_and_cancel_rollback(self):
        self.seed()
        before = self.store.db.iterdump()
        before = list(before)
        bad = replace(draw(6), payload={"main": [1]})
        with self.assertRaises(ValueError):
            self.store.add_draws(self.rule, [draw(5), bad], keep_latest=2)
        self.assertEqual(list(self.store.db.iterdump()), before)
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            if calls == 6:
                raise CancelledError("cancel")
        with self.assertRaises(CancelledError):
            self.store.add_draws(self.rule, [draw(5), draw(6)], keep_latest=2, check_cancel=cancel)
        self.assertEqual(list(self.store.db.iterdump()), before)
        self.store.db.execute("CREATE TRIGGER deny_prune BEFORE DELETE ON draw_revisions BEGIN SELECT RAISE(ABORT,'deny'); END")
        self.store.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.add_draws(self.rule, [draw(5)], keep_latest=2)
        self.assertEqual(self.ids(), ["2", "3", "4"])

    def test_incomplete_empty_and_unproven_do_not_prune(self):
        self.seed()
        for receipt in ({"draws": [], "status": "source_boundary"},
                        {"draws": [draw(5)], "status": "incomplete"},
                        {"draws": [draw(5)], "status": "requested_limit"}):
            with self.assertRaises(ValueError):
                self.store.apply_sync(self.rule, receipt, 3)
            self.assertEqual(self.ids(), ["2", "3", "4"])
        self.store.apply_sync(self.rule, {"draws": [draw(5)], "status": "partial"}, 2)
        self.assertEqual(self.ids(), ["2", "3", "4", "5"])
        with self.assertRaises(ValueError):
            self.store.apply_sync(self.rule, {"draws": [draw(6), draw(5)], "status": "known_boundary"}, 2)

    def test_other_scopes_and_saved_artifacts_survive(self):
        self.seed()
        snapshot = self.store.snapshot(self.rule)
        self.store.save_suggestions(self.rule, [Ticket("mega", "normal", self.rule.rule_version,
                                                      {"main": [1, 2, 3, 4, 5, 6]})], "10", "fixture", snapshot)
        self.store.save_report({"status": "fixture", "manifest": {"input_snapshot": snapshot}})
        for rule in (get_rule("power"), get_rule("keno", "pick1"), get_rule("keno", "pick2")):
            self.store.add_draws(rule, [draw(1, rule)])
        old_rule = replace(self.rule, rule_version="older")
        self.store.add_draws(old_rule, [draw(99, old_rule)])
        self.store.add_draws(self.rule, [draw(5)], keep_latest=1)
        self.assertEqual(self.ids(), ["5"])
        self.assertEqual(self.ids(old_rule), ["99"])
        for rule in (get_rule("power"), get_rule("keno", "pick1"), get_rule("keno", "pick2")):
            self.assertEqual(self.ids(rule), ["1"])
        self.assertEqual(len(self.store.get_snapshot(snapshot["hash"])["draws"]), 3)
        self.assertEqual(len(self.store.reports()), 1)
        self.assertEqual(len(self.store.suggestions(self.rule)), 1)

    def test_initial_and_source_boundary_fill(self):
        self.store.apply_sync(self.rule, {"draws": [draw(1), draw(2)], "status": "source_boundary"}, 3)
        self.assertEqual(self.ids(), ["1", "2"])
        self.assertEqual(self.store.sync_window(self.rule, 3), [])
        self.assertEqual(len(self.store.sync_window(self.rule, 2)), 2)
        self.store.apply_sync(self.rule, {"draws": [draw(i) for i in range(1, 6)], "status": "requested_limit"}, 5)
        self.assertEqual(len(self.store.sync_window(self.rule, 5)), 5)

    def test_invalid_limits_never_write(self):
        for value in (0, -1, True, 2001, "3"):
            with self.assertRaises(ValueError):
                self.store.add_draws(self.rule, [draw(1)], keep_latest=value)
        self.assertEqual(self.ids(), [])

    def test_once_daily_concurrent_claim_and_record_failure(self):
        def claim(_):
            store = Store(self.path)
            try:
                return store.claim_auto_update("mega", "2026-11-11")
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(claim, range(4))), 1)
        self.store.finish_auto_update("mega", "2026-11-11", "failed", "offline")
        self.assertFalse(self.store.claim_auto_update("mega", "2026-11-11"))
        self.assertTrue(self.store.claim_auto_update("power", "2026-11-11"))
        self.assertTrue(self.store.claim_auto_update("mega", "2026-11-12"))
        row = self.store.auto_update_runs()[0]
        self.assertTrue({"game_id", "day", "status", "message"} <= row.keys())
        self.assertTrue(any(r["status"] == "failed" and r["message"] == "offline" for r in self.store.auto_update_runs()))

    def test_multi_mode_failure_rolls_back_every_mode_and_proof(self):
        rules = [get_rule("keno", "pick1"), get_rule("keno", "pick2")]
        for rule in rules:
            self.store.add_draws(rule, [draw(1, rule), draw(2, rule)], keep_latest=2)
        batches = [(rule, {"draws": [draw(3, rule), draw(2, rule)], "status": "known_boundary"})
                   for rule in rules]
        before = list(self.store.db.iterdump())
        first_written_checks = 0
        def cancel_after_first_mode():
            nonlocal first_written_checks
            if self.ids(rules[0]) == ["2", "3"]:
                first_written_checks += 1
                if first_written_checks == 2:
                    raise CancelledError("disabled after first mode")
        with self.assertRaises(CancelledError):
            self.store.apply_sync_many(batches, 2, check_cancel=cancel_after_first_mode)
        self.assertEqual(list(self.store.db.iterdump()), before)
        for rule in rules:
            self.assertEqual(len(self.store.sync_window(rule, 2)), 2)
        self.store.db.execute("CREATE TRIGGER deny_second_mode BEFORE INSERT ON draw_revisions WHEN NEW.mode_id='pick2' BEGIN SELECT RAISE(ABORT,'deny'); END")
        self.store.db.commit()
        before = list(self.store.db.iterdump())
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.apply_sync_many(batches, 2)
        self.assertEqual(list(self.store.db.iterdump()), before)
        self.store.db.execute("DROP TRIGGER deny_second_mode")
        self.store.db.commit()
        counts = self.store.apply_sync_many(batches, 2)
        self.assertEqual([row["added"] for row in counts], [1, 1])
        for rule in rules:
            self.assertEqual(self.ids(rule), ["2", "3"])
            self.assertEqual(len(self.store.sync_window(rule, 2)), 2)

    def source(self):
        source = OfficialSource()
        raw = (FIXTURES / "mega_results.html").read_bytes()
        previous = (FIXTURES / "mega_01585.html").read_text(encoding="utf-8")
        older = (FIXTURES / "mega_01584.html").read_text(encoding="utf-8")
        calls = []
        def ajax(path, method, payload, cancel):
            if method == "ServerSideFrontEndCreateRenderInfo":
                return {}
            calls.append(payload["DrawId"])
            return {"RetExtraParam1": previous if payload["DrawId"] == "01585" else older, "RetExtraParam2": ""}
        return source, raw, ajax, calls

    def test_source_one_new_and_overlap_stops_and_revalidates(self):
        source, raw, ajax, calls = self.source()
        known = [replace(draw(i), draw_id=f"{i:05}") for i in range(1486, 1586)]
        with patch.object(source, "_request", return_value=raw), patch.object(source, "_ajax", side_effect=ajax), patch("app.sources.time.sleep"):
            receipt = source.fetch_history(self.rule, 100, known_draws=known)
        self.assertEqual(calls, ["01585"])
        self.assertEqual(receipt["status"], "known_boundary")
        self.assertEqual([d.draw_id for d in receipt["draws"]], ["01586", "01585"])
        self.assertEqual(receipt["draws"][1].payload["main"], [1, 10, 37, 38, 39, 45])

    def test_source_initial_expanded_and_default_fill(self):
        for known in ((), [replace(draw(1585), draw_id="01585")]):
            source, raw, ajax, calls = self.source()
            with patch.object(source, "_request", return_value=raw), patch.object(source, "_ajax", side_effect=ajax), patch("app.sources.time.sleep"):
                receipt = source.fetch_history(self.rule, 3, known_draws=known)
            self.assertEqual(calls, ["01585", "01584"])
            self.assertEqual(receipt["status"], "requested_limit")
            self.assertEqual(len(receipt["draws"]), 3)

    def test_source_head_already_known_and_page_overlap(self):
        rule = get_rule("keno")
        raw = (FIXTURES / "keno_results.html").read_bytes()
        parsed = parse_results(raw, rule, "https://vietlott.vn/")
        source = OfficialSource()
        with patch.object(source, "_request", return_value=raw), patch.object(source, "_ajax", side_effect=AssertionError("extra request")):
            receipt = source.fetch_history(rule, 5, known_draws=parsed)
        self.assertEqual(receipt["status"], "known_boundary")
        self.assertEqual([d.draw_id for d in receipt["draws"]], ["0302343"])

    def test_source_sorts_head_before_overlap(self):
        rule = get_rule("keno")
        raw = (FIXTURES / "keno_results.html").read_bytes()
        import re
        rows = re.findall(rb"<tr\b[^>]*>.*?</tr>", raw, re.S | re.I)
        result_rows = [r for r in rows if re.search(rb"#\s*\d+", r)]
        replacement = iter(reversed(result_rows))
        unordered = re.sub(rb"<tr\b[^>]*>.*?</tr>", lambda m: next(replacement) if m[0] in result_rows else m[0], raw, flags=re.S | re.I)
        known = parse_results(raw, rule, "https://vietlott.vn/")
        source = OfficialSource()
        with patch.object(source, "_request", return_value=unordered):
            receipt = source.fetch_history(rule, 5, known_draws=known[1:])
        self.assertEqual([d.draw_id for d in receipt["draws"]], ["0302343", "0302342"])

    def test_scheduled_single_attempt_does_not_retry_http(self):
        source = OfficialSource(max_attempts=1)
        with patch("app.sources.urlopen", side_effect=URLError("offline")) as request:
            with self.assertRaises(ValueError):
                source._request("https://vietlott.vn/")
        self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
