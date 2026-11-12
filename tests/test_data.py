from dataclasses import asdict
from pathlib import Path
import hashlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.domain import Draw
from app.rules import get_rule
from app.sources import OfficialSource, parse_results, import_csv
from app.storage import Store
from test_core import draw

FIXTURES = Path(__file__).parent / "fixtures"


class SourceTests(unittest.TestCase):
    def parse(self, fixture, game):
        rule = get_rule(game)
        return parse_results((FIXTURES / (fixture + ".html")).read_bytes(), rule,
                             "https://vietlott.vn" + rule.result_path)

    def test_mega_real_three_snapshots(self):
        expectations = [("mega_results", "01586", [1, 2, 14, 20, 23, 36]),
                        ("mega_01585", "01585", [1, 10, 37, 38, 39, 45]),
                        ("mega_01584", "01584", [7, 14, 20, 30, 34, 40])]
        for name, identifier, numbers in expectations:
            item, = self.parse(name, "mega")
            self.assertEqual(item.draw_id, identifier)
            self.assertEqual(item.payload["main"], numbers)
            self.assertIsNone(item.published_at_utc)

    def test_power_and_lotto_special_separated(self):
        power, = self.parse("power_results", "power")
        self.assertEqual(power.payload["main"], [5, 19, 20, 26, 44, 53])
        self.assertEqual(power.payload["special"], 39)
        lotto, = self.parse("lotto_results", "lotto")
        self.assertEqual(lotto.payload["main"], [4, 16, 26, 27, 29])
        self.assertEqual(lotto.payload["special"], 6)

    def test_lotto_ajax_heading_uses_535_without_slash(self):
        previous, = self.parse("lotto_previous", "lotto")
        self.assertEqual(previous.draw_id, "00996")
        self.assertEqual(len(previous.payload["main"]), 5)

    def test_keno_pagination_does_not_filter_to_odd_small_results(self):
        raw = (FIXTURES/"keno_results.html").read_bytes()
        next_page = raw
        for old, new in zip(range(302338, 302344), range(302332, 302338)):
            next_page = next_page.replace(f"{old:07}".encode(), f"{new:07}".encode())
        calls = []
        def ajax(path, method, payload, cancel):
            if method == "ServerSideFrontEndCreateRenderInfo":
                return {}
            calls.append(payload)
            return {"HtmlContent": (raw if payload["PageIndex"] == 0 else next_page).decode(), "RetNumber": 65}
        source = OfficialSource()
        with patch.object(source, "_request", return_value=raw), patch.object(source, "_ajax", side_effect=ajax):
            result = source.fetch_history(get_rule("keno"), limit=8)
        self.assertEqual(len(result["draws"]), 8)
        self.assertEqual((calls[0]["OddEven"], calls[0]["UpperLower"]), (2, 2))
        self.assertEqual(calls[0]["DrawDate"], "09/11/2026")
        self.assertEqual(calls[0]["PageIndex"], 0)
        self.assertEqual(calls[1]["TotalRow"], 65)

    def test_max_groups_preserve_zero_and_order(self):
        item, = self.parse("max_results", "max3d")
        self.assertEqual(item.payload["groups"]["special"], ["962", "391"])
        self.assertIn("068", item.payload["groups"]["third"])
        pro, = self.parse("pro_results", "max3dpro")
        self.assertEqual(pro.payload["groups"]["special"], ["810", "193"])

    def test_keno_and_bingo_preserve_multiple_draws(self):
        keno = self.parse("keno_results", "keno")
        self.assertEqual(len(keno), 6)
        self.assertEqual(keno[0].draw_id, "0302343")
        self.assertEqual(len(keno[0].payload["main"]), 20)
        bingo = self.parse("bingo_results", "bingo18")
        self.assertEqual(bingo[0].payload["main"], [6, 6, 3])
        self.assertEqual(len(bingo), 6)

    def test_changed_or_empty_page_is_not_empty_success(self):
        for raw in (b"<html>maintenance</html>", b"", b"<html><script>captcha</script></html>"):
            with self.assertRaises(ValueError):
                parse_results(raw, get_rule("mega"), "https://vietlott.vn/")

    def test_ajax_draw_hash_identifies_an_actual_cached_file(self):
        initial = (FIXTURES/"mega_results.html").read_bytes()
        previous = (FIXTURES/"mega_01585.html").read_text(encoding="utf-8")
        def ajax(path, method, payload, cancel):
            return {} if method == "ServerSideFrontEndCreateRenderInfo" else {"RetExtraParam1": previous, "RetExtraParam2": ""}
        with tempfile.TemporaryDirectory() as directory:
            source = OfficialSource(directory)
            with patch.object(source, "_request", return_value=initial), patch.object(source, "_ajax", side_effect=ajax):
                result = source.fetch_history(get_rule("mega"), limit=2)
            for item in result["draws"]:
                evidence = Path(directory)/(item.raw_sha256+".bin")
                self.assertTrue(evidence.is_file())
                self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), item.raw_sha256)

    def test_new_draw_arriving_during_fetch_is_sorted_before_limit(self):
        raw = (FIXTURES/"keno_results.html").read_bytes()
        shifted = raw
        older = raw
        for old in reversed(range(302338, 302344)):
            shifted = shifted.replace(f"{old:07}".encode(), f"{old+1:07}".encode())
        for old in range(302338, 302344):
            older = older.replace(f"{old:07}".encode(), f"{old-6:07}".encode())
        def ajax(path, method, payload, cancel):
            if method == "ServerSideFrontEndCreateRenderInfo":
                return {}
            return {"HtmlContent": (shifted if payload["PageIndex"] == 0 else older).decode(), "RetNumber": 65}
        source = OfficialSource()
        with patch.object(source, "_request", return_value=raw), patch.object(source, "_ajax", side_effect=ajax):
            result = source.fetch_history(get_rule("keno"), limit=8)
        self.assertEqual([int(d.draw_id) for d in result["draws"]], list(range(302344, 302336, -1)))

    def test_csv_validates_entire_file(self):
        text = 'draw_id,draw_date,main,special\n1,2026-11-08,01 02 03 04 05 06,\n'
        items = import_csv(text.encode(), get_rule("mega"))
        self.assertEqual(items[0].payload["main"], [1, 2, 3, 4, 5, 6])
        with self.assertRaises(ValueError):
            import_csv((text + '2,2026-11-09,1 1 2 3 4 5,\n').encode(), get_rule("mega"))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "data.sqlite3"
        self.store = Store(self.path)
        self.rule = get_rule("mega")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_idempotent_revision_and_snapshot(self):
        self.assertEqual(self.store.add_draws(self.rule, [draw()])["added"], 1)
        before = self.store.snapshot(self.rule)
        self.assertEqual(self.store.add_draws(self.rule, [draw()])["unchanged"], 1)
        edited = draw(numbers=(1, 2, 3, 4, 5, 7))
        self.assertEqual(self.store.add_draws(self.rule, [edited])["revised"], 1)
        self.assertEqual(self.store.list_draws(self.rule)[0].revision, 2)
        self.assertEqual(before["draws"][0]["payload"]["main"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(self.store.revisions("mega", "normal", "1")), 2)

    def test_invalid_batch_keeps_database_unchanged(self):
        with self.assertRaises(ValueError):
            self.store.add_draws(self.rule, [draw(identifier="1"), draw(numbers=(1, 1, 2, 3, 4, 5), identifier="2")])
        self.assertEqual(self.store.list_draws(self.rule), [])

    def test_saved_suggestions_and_reports_survive_reopen(self):
        from app.domain import Ticket
        ticket = Ticket("mega", "normal", self.rule.rule_version, {"main": [1, 2, 3, 4, 5, 6]})
        self.store.save_suggestions(self.rule, [ticket], "future-1", "uniform_v1", self.store.snapshot(self.rule))
        self.store.save_report({"status": "incomplete", "manifest": {"snapshot_hash": "a"}})
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(len(self.store.suggestions(self.rule)), 1)
        self.assertEqual(self.store.reports()[0]["status"], "incomplete")

    def test_cannot_save_future_suggestion_using_target_or_later_history(self):
        from app.domain import Ticket
        ticket = Ticket("mega", "normal", self.rule.rule_version, {"main": [1, 2, 3, 4, 5, 6]})
        self.store.add_draws(self.rule, [draw(identifier="10")])
        for identifier in ("10", "9", "00010"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.store.save_suggestions(self.rule, [ticket], identifier, "uniform_v1", self.store.snapshot(self.rule))

    def test_reusing_holdout_is_marked_exploratory(self):
        report = {"status": "completed", "assessment": "holdout_report_no_advantage_claim",
                  "manifest": {"game_id": "mega", "mode_id": "normal", "dataset_hash": "same-input", "holdout_count": 50}}
        self.store.save_report(report)
        self.store.save_report(report)
        self.assertEqual(self.store.reports()[0]["assessment"], "exploratory_reused_holdout")

    def test_suggestion_snapshot_can_be_recovered_and_marked_stale(self):
        from app.domain import Ticket
        ticket = Ticket("mega", "normal", self.rule.rule_version, {"main": [1, 2, 3, 4, 5, 6]})
        self.store.add_draws(self.rule, [draw(identifier="1")])
        snapshot = self.store.snapshot(self.rule)
        self.store.save_suggestions(self.rule, [ticket], "2", "uniform_v1", snapshot)
        self.store.add_draws(self.rule, [draw(identifier="1", numbers=(1, 2, 3, 4, 5, 7))])
        recovered = self.store.get_snapshot(snapshot["hash"])
        self.assertEqual(recovered["draws"][0]["payload"]["main"], [1, 2, 3, 4, 5, 6])
        self.assertTrue(self.store.suggestions(self.rule)[0]["stale"])

    def test_empty_snapshots_for_different_games_do_not_alias_rules(self):
        mega = self.store.snapshot(self.rule)
        lotto = self.store.snapshot(get_rule("lotto"))
        self.assertNotEqual(mega["hash"], lotto["hash"])
        self.assertEqual(self.store.get_snapshot(lotto["hash"])["rule"]["game_id"], "lotto")

    def test_v1_migration_preserves_data_and_releases_backup_handle(self):
        self.store.add_draws(self.rule, [draw()])
        self.store.close()
        connection = sqlite3.connect(self.path)
        connection.execute("DROP TABLE data_snapshots")
        connection.execute("PRAGMA user_version=1")
        connection.commit(); connection.close()
        self.store = Store(self.path)
        self.assertEqual(len(self.store.list_draws(self.rule)), 1)
        backup = self.path.with_suffix(".pre-v2.sqlite3")
        self.assertTrue(backup.is_file())
        backup.rename(self.path.with_suffix(".backup-check.sqlite3"))


if __name__ == "__main__":
    unittest.main()
