import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import tempfile
import time
from threading import Event
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from app.rules import get_rule, BASE
from app.storage import Store
from app.ui import Desktop
from test_core import draw


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.window = Desktop(self.folder/"history.sqlite3", self.folder/"config.json")

    def tearDown(self):
        self.wait_idle()
        self.window.close()
        self.application.processEvents()
        self.temp.cleanup()

    def wait_idle(self):
        deadline = time.monotonic()+5
        while self.window.worker is not None and time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(.01)
        self.assertIsNone(self.window.worker)

    def test_sources_follow_game_and_all_pages_open(self):
        for index, game in enumerate(("mega", "power", "lotto", "keno", "max3d", "max3dpro", "bingo18")):
            self.window.game.setCurrentIndex(index)
            self.assertIn(BASE+get_rule(game).result_path, self.window.source_links.text())
            self.assertIn(get_rule(game).rules_url, self.window.source_links.text())
            self.window.nav.setCurrentRow(index)
            self.assertEqual(self.window.pages.currentIndex(), index)
        self.assertEqual(self.window.history_table.rowCount(), 0)

    def test_generate_uses_history_and_saves_selected_method(self):
        rule = get_rule("mega")
        self.window.store.add_draws(rule, [draw(identifier=str(i+1)) for i in range(90)])
        self.window.refresh()
        self.window.target.setText("91")
        self.window.make_suggestions()
        self.assertEqual(self.window.suggestion_table.rowCount(), 5)
        self.assertIn("90", self.window.explanation.toPlainText())
        self.assertIn("8,145,060", self.window.explanation.toPlainText())
        self.window.save_generated()
        self.assertEqual(len(self.window.store.suggestions(rule)), 5)
        self.assertEqual(self.window.store.suggestions(rule)[0]["method"], "bayes90_v1")

    def test_missing_history_has_actionable_message(self):
        self.window.make_suggestions()
        self.assertEqual(self.window.suggestion_table.rowCount(), 0)
        self.assertIn("90", self.window.notice.text())

    def test_test_button_streams_without_web_search_and_config_saves(self):
        self.window.key.setText("local-test-key")
        self.window.save_config()
        body = json.loads((self.folder/"config.json").read_text(encoding="utf-8"))
        self.assertEqual(set(body), {"base_url", "api_key", "model"})
        self.assertEqual(body["model"], "gpt-6.1-sol")
        seen = []
        started, release = Event(), Event()
        def transport(url, headers, payload, cancel, on_delta):
            seen.append((url, payload))
            on_delta("O"); started.set(); release.wait(2); on_delta("K")
            return {"status": "completed", "output_text": "OK"}
        with patch("app.ai._send", side_effect=transport):
            self.window.test_button.click()
            self.assertTrue(started.wait(2))
            self.application.processEvents()
            self.assertEqual(self.window.answer.toPlainText(), "O")
            release.set()
            self.wait_idle()
        self.assertTrue(seen[0][0].endswith("/responses"))
        self.assertTrue(seen[0][1]["stream"])
        self.assertNotIn("tools", seen[0][1])
        self.assertIn("OK", self.window.answer.toPlainText())
        self.assertIn("không kiểm tra web search", self.window.notice.text())
        self.assertTrue(self.window.test_button.isEnabled())

    def test_provider_failure_returns_to_idle(self):
        self.window.key.setText("local-test-key")
        with patch("app.ai._send", side_effect=ValueError("HTTP 401")):
            self.window.test_button.click()
            self.wait_idle()
        self.assertIn("401", self.window.notice.text())
        self.assertTrue(self.window.test_button.isEnabled())

    def test_sync_imports_validated_results_and_refreshes_ui(self):
        receipt = {"draws": [draw()], "note": "Một kỳ từ fixture nguồn", "status": "partial"}
        with patch("app.ui.OfficialSource.fetch_history", return_value=receipt):
            self.window.sync()
            self.wait_idle()
        self.assertEqual(len(self.window.store.list_draws(get_rule("mega"))), 1)
        self.assertEqual(self.window.history_table.rowCount(), 1)
        self.assertIn("fixture", self.window.notice.text())

    def test_invalid_source_results_show_error_without_writing(self):
        invalid = draw(numbers=(1, 1, 2, 3, 4, 5))
        with patch("app.ui.OfficialSource.fetch_history", return_value={"draws": [invalid], "note": ""}):
            self.window.sync()
            self.wait_idle()
        self.assertEqual(self.window.store.list_draws(get_rule("mega")), [])
        self.assertNotIn("Đang tải", self.window.notice.text())

    def test_cancelled_sync_does_not_commit_and_close_waits(self):
        started, release = Event(), Event()
        def fetch(*args, **kwargs):
            started.set()
            release.wait(2)
            return {"draws": [draw()], "note": ""}
        with patch("app.ui.OfficialSource.fetch_history", side_effect=fetch):
            self.window.sync()
            self.assertTrue(started.wait(2))
            self.window.close()
            self.assertTrue(self.window.closing)
            release.set()
            self.wait_idle()
        with_store = Store(self.folder/"history.sqlite3")
        try:
            self.assertEqual(with_store.list_draws(get_rule("mega")), [])
        finally:
            with_store.close()

    def test_search_receives_selected_official_sources(self):
        self.window.game.setCurrentIndex(1)
        self.window.key.setText("local-test-key")
        sent = []
        def transport(url, headers, payload, cancel, on_delta):
            sent.append(payload)
            return {"status": "completed", "output_text": "Nguồn Power", "citations": ["https://vietlott.vn/vi/home"]}
        with patch("app.ai._send", side_effect=transport):
            self.window.run_ai()
            self.wait_idle()
        self.assertIn(BASE+get_rule("power").result_path, sent[0]["input"])
        self.assertEqual(sent[0]["tools"], [{"type": "web_search"}])
        self.assertIn("https://vietlott.vn/vi/home", self.window.answer.toHtml())

    def test_cancelled_experiments_show_partial_counts_and_save_incomplete(self):
        for experiment in ("simulation", "backtest"):
            started, release = Event(), Event()
            def run(*args, **kwargs):
                started.set(); release.wait(2)
                return {"status": "incomplete", "completed_trials": 50, "manifest": {},
                        "conclusion": "Chưa có bằng chứng tăng xác suất.", "note": "Đã chạy 50 kỳ."}
            function = "app.ui.simulate" if experiment == "simulation" else "app.ui.run_backtest"
            with patch(function, side_effect=run):
                self.window.run_simulation() if experiment == "simulation" else self.window.backtest()
                self.assertTrue(started.wait(2))
                self.window.cancel_task(); release.set(); self.wait_idle()
            self.assertIn('"completed_trials": 50', self.window.report.toPlainText())
            self.assertIn('"status": "incomplete"', self.window.report.toPlainText())
            self.assertIn("chưa hoàn tất", self.window.notice.text())
        self.assertEqual(self.window.store.reports()[0]["status"], "incomplete")

    def test_ai_method_streams_on_its_page_then_saves_model_provenance(self):
        index = self.window.method.findData("ai_history90_v1")
        self.assertGreaterEqual(index, 0)
        self.window.store.add_draws(get_rule("mega"), [draw(identifier=str(i+1)) for i in range(90)])
        self.window.refresh(); self.window.method.setCurrentIndex(index)
        self.window.count.setValue(1); self.window.key.setText("local-secret")
        self.window.target.setText("91")
        started, release = Event(), Event()
        text = json.dumps({"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "Lý do AI chọn số."})
        def transport(url, headers, body, **kwargs):
            kwargs["on_delta"]("Phân tích đang chạy"); started.set(); release.wait(2)
            return {"status": "completed", "output_text": text}
        with patch("app.ai._send", side_effect=transport):
            self.window.make_suggestions()
            self.assertTrue(started.wait(2)); self.application.processEvents()
            self.assertIn("Phân tích đang chạy", self.window.explanation.toPlainText())
            self.assertIsNone(self.window.generated)
            release.set(); self.wait_idle()
        self.assertEqual(self.window.suggestion_table.rowCount(), 1)
        self.assertIn("Lý do AI", self.window.explanation.toPlainText())
        self.assertIn("8,145,060", self.window.explanation.toPlainText())
        self.window.save_generated()
        saved = self.window.store.suggestions(get_rule("mega"))[0]
        self.assertEqual(saved["method"], "ai_history90_v1")
        self.assertEqual(saved["metadata"]["requested_model"], "gpt-6.1-sol")
        self.assertEqual(saved["metadata"]["history_used"], 90)
        self.assertNotIn("local-secret", json.dumps(saved))

    def test_ai_bad_response_clears_previous_bets_and_is_not_saved(self):
        self.window.store.add_draws(get_rule("mega"), [draw(identifier=str(i)) for i in range(90)])
        self.window.refresh(); self.window.make_suggestions()
        self.assertIsNotNone(self.window.generated)
        self.window.method.setCurrentIndex(self.window.method.findData("ai_history90_v1"))
        self.window.key.setText("local-secret")
        with patch("app.ai._send", return_value={"status": "completed", "output_text": "không phải JSON"}):
            self.window.make_suggestions(); self.wait_idle()
        self.assertIsNone(self.window.generated)
        self.assertEqual(self.window.suggestion_table.rowCount(), 0)
        self.assertEqual(self.window.store.suggestions(get_rule("mega")), [])

    def test_ai_generation_does_not_become_a_paid_backtest(self):
        index = self.window.method.findData("ai_history90_v1")
        self.assertGreaterEqual(index, 0)
        self.window.method.setCurrentIndex(index)
        with patch("app.ai._send") as request, self.assertRaisesRegex(ValueError, "AI"):
            self.window.backtest()
        request.assert_not_called()

    def test_cancelled_ai_proposal_does_not_enable_saving(self):
        self.window.store.add_draws(get_rule("mega"), [draw(identifier=str(i)) for i in range(90)])
        self.window.refresh(); self.window.count.setValue(1); self.window.key.setText("local")
        self.window.method.setCurrentIndex(self.window.method.findData("ai_history90_v1"))
        started, release = Event(), Event()
        def transport(*args, **kwargs):
            started.set(); release.wait(2)
            return {"status": "completed", "output_text": json.dumps({"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "x"})}
        with patch("app.ai._send", side_effect=transport):
            self.window.make_suggestions(); self.assertTrue(started.wait(2))
            self.window.cancel_task(); release.set(); self.wait_idle()
        self.assertIsNone(self.window.generated)
        self.assertEqual(self.window.suggestion_table.rowCount(), 0)
        with self.assertRaises(ValueError):
            self.window.save_generated()

    def test_generation_snapshot_matches_input_after_external_history_revision(self):
        rule = get_rule("mega")
        self.window.store.add_draws(rule, [draw(identifier=str(i+1)) for i in range(90)])
        self.window.count.setValue(1); self.window.key.setText("local"); self.window.target.setText("91")
        for method, replacement in (("bayes90_v1", 7), ("ai_history90_v1", 8)):
            self.window.refresh()
            captured = self.window.draws[-1].payload["main"][:]
            external = Store(self.folder/"history.sqlite3")
            try:
                external.add_draws(rule, [draw(numbers=(1, 2, 3, 4, 5, replacement), identifier="90")])
            finally:
                external.close()
            self.window.method.setCurrentIndex(self.window.method.findData(method))
            response = {"status": "completed", "output_text": json.dumps({"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "x"})}
            with patch("app.ai._send", return_value=response):
                self.window.make_suggestions(); self.wait_idle()
            self.window.save_generated()
            record = self.window.store.suggestions(rule)[0]
            snapshot = self.window.store.get_snapshot(record["snapshot_hash"])
            self.assertEqual(snapshot["draws"][-1]["payload"]["main"], captured)
            self.assertTrue(record["stale"])


if __name__ == "__main__":
    unittest.main()
