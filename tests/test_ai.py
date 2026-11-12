from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.ai import AIConfig, build_request, parse_response, parse_sse, search, test_model as run_model_test
from app.settings import save_settings, load_settings


class AIAdapterTests(unittest.TestCase):
    def test_model_probe_uses_responses_stream_without_web_tool_and_returns_status(self):
        deltas = []
        sent = []
        def transport(url, headers, body, **kwargs):
            sent.append((url, body))
            kwargs["on_delta"]("OK")
            return {"status": "completed", "model": "gpt-6.1-sol", "output_text": "OK"}
        with patch("app.ai._send", side_effect=transport):
            result = run_model_test(AIConfig(api_key="local-test"), on_delta=deltas.append)
        self.assertTrue(result["ok"])
        self.assertEqual(deltas, ["OK"])
        self.assertEqual(sent[0][0], "https://api.openai.com/v1/responses")
        self.assertTrue(sent[0][1]["stream"])
        self.assertNotIn("tools", sent[0][1])
        self.assertNotIn("include", sent[0][1])
        self.assertFalse(result["web_search_tested"])

    def test_default_uses_openai_and_exact_model(self):
        config = AIConfig(api_key="test-secret")
        url, headers, body = build_request(config, "Tìm nguồn kết quả Mega")
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["model"], "gpt-6.1-sol")
        self.assertEqual(body["tools"], [{"type": "web_search"}])
        self.assertTrue(body["stream"])
        self.assertNotIn("test-secret", str(body))
        self.assertIn("Authorization", headers)

    def test_responses_style_uses_actual_search_tool(self):
        _, _, body = build_request(AIConfig(api_key="secret"), "Nguồn Lotto")
        self.assertEqual(body["tools"], [{"type": "web_search"}])
        self.assertNotIn("messages", body)

    def test_citations_are_preserved_and_bad_urls_filtered(self):
        response = {"choices": [{"message": {"content": "Kết quả có tại nguồn.", "annotations": [
            {"type": "url_citation", "url_citation": {"url": "https://vietlott.vn/vi/home", "title": "Vietlott"}},
            {"type": "url_citation", "url_citation": {"url": "javascript:alert(1)", "title": "bad"}}
        ]}}]}
        result = parse_response(response)
        self.assertEqual(result["text"], "Kết quả có tại nguồn.")
        self.assertEqual(result["sources"], [{"url": "https://vietlott.vn/vi/home", "title": "Vietlott"}])
        self.assertFalse(result["verified_draws"])

    def test_no_automatic_retry_or_live_provider_probe(self):
        response = {"choices": [{"message": {"content": "Không tìm thấy nguồn đủ tin cậy."}}]}
        with patch("app.ai._send", return_value=response) as transport:
            result = search(AIConfig(api_key="local-test-only"), "Nguồn lịch sử")
        self.assertEqual(result["sources"], [])
        self.assertEqual(transport.call_count, 1)
        self.assertFalse(result["verified_draws"])

    def test_reject_embedded_credentials_and_missing_key(self):
        for config in (AIConfig(), AIConfig(base_url="https://user:pass@example.com/v1", api_key="x"),
                       AIConfig(base_url="http://api.openai.com/v1", api_key="x")):
            with self.assertRaises(ValueError):
                build_request(config, "query")

    def test_json_settings_preserve_the_three_user_requested_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"settings.json"
            save_settings(AIConfig(api_key="local-secret-unique"), path)
            import json
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(stored), {"base_url", "api_key", "model"})
            self.assertEqual(stored["api_key"], "local-secret-unique")
            config = load_settings(path)
            self.assertEqual(config.api_key, "local-secret-unique")
            self.assertEqual(config.model, "gpt-6.1-sol")

    def test_streaming_deltas_completed_response_and_citations(self):
        import json
        events = [
            {"type": "response.output_text.delta", "delta": "Xin "},
            {"type": "response.output_text.delta", "delta": "chào"},
            {"type": "response.completed", "response": {"status": "completed", "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "Xin chào", "annotations": [
                    {"type": "url_citation", "url": "https://vietlott.vn/", "title": "Vietlott"}
                ]}]}]}}
        ]
        lines = []
        for event in events:
            lines.extend([(f"data: {json.dumps(event,ensure_ascii=False)}\n").encode(), b"\n"])
        chunks = []
        data = parse_sse(lines, lambda: False, chunks.append)
        self.assertEqual(chunks, ["Xin ", "chào"])
        self.assertEqual(parse_response(data)["text"], "Xin chào")
        self.assertEqual(len(parse_response(data)["sources"]), 1)

    def test_stream_without_completion_or_cancel_is_not_success(self):
        from app.sources import CancelledError
        with self.assertRaises(ValueError):
            parse_sse([b'data: {"type":"response.output_text.delta","delta":"partial"}\n', b'\n'], lambda: False, lambda _: None)
        with self.assertRaises(CancelledError):
            parse_sse([b'data: {}\n', b'\n'], lambda: True, lambda _: None)

    def test_json_fallback_incomplete_or_failed_is_not_success(self):
        for status in ("incomplete", "failed", "cancelled", "in_progress", "queued"):
            with self.subTest(status=status), self.assertRaises(ValueError):
                parse_response({"status": status, "output_text": "partial"})


if __name__ == "__main__":
    unittest.main()
