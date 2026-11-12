import json
import unittest
from unittest.mock import patch

from app.ai import AIConfig
from app.ai_generation import build_generation_request, generate_with_ai, parse_tickets
from app.rules import get_rule
from app.sources import CancelledError
from test_core import draw


class AIGenerationTests(unittest.TestCase):
    def test_request_uses_only_last_ninety_real_draws_and_streams_without_web(self):
        history = [draw(identifier=f"{i:05}") for i in range(1, 101)]
        sent, deltas = [], []
        answer = {"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "Phân tích tần suất trong mẫu."}
        def transport(url, headers, body, **kwargs):
            sent.append((url, headers, body))
            kwargs["on_delta"]("Đang phân tích")
            return {"status": "completed", "output_text": json.dumps(answer), "model": "provider-model", "id": "response-local"}
        with patch("app.ai._send", side_effect=transport) as request:
            result = generate_with_ai(AIConfig(api_key="local-secret"), get_rule("mega"), history, 1, on_delta=deltas.append)
        request.assert_called_once()
        url, headers, body = sent[0]
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["model"], "gpt-6.1-sol")
        self.assertTrue(body["stream"])
        self.assertEqual(body.get("reasoning"), {"effort": "high"})
        self.assertNotIn("tools", body)
        self.assertNotIn("local-secret", json.dumps(body))
        context = json.loads(body["input"])
        self.assertEqual(len(context["history"]), 90)
        self.assertEqual(context["history"][0][0], "00011")
        self.assertEqual(context["cutoff_draw_id"], "00100")
        self.assertEqual(context["frequencies"]["1"], 90)
        self.assertEqual(result["tickets"][0].selections, answer["tickets"][0])
        self.assertEqual(result["metadata"]["requested_model"], "gpt-6.1-sol")
        self.assertEqual(result["metadata"]["reasoning_effort"], "high")
        self.assertEqual(result["metadata"]["response_model"], "provider-model")
        self.assertEqual(deltas, ["Đang phân tích"])

    def test_rejects_invalid_outputs_and_duplicate_bets(self):
        good = {"main": [1, 2, 3, 4, 5, 6]}
        cases = ["not json", "[]", json.dumps({"tickets": [good]}),
                 json.dumps({"tickets": [good], "explanation": ""}),
                 json.dumps({"tickets": [{"main": [1, 1, 2, 3, 4, 5]}], "explanation": "x"}),
                 json.dumps({"tickets": [{"main": [True, 2, 3, 4, 5, 6]}], "explanation": "x"}),
                 json.dumps({"tickets": [{"main": [1, 2, 3, 4, 5, 46]}], "explanation": "x"}),
                 json.dumps({"tickets": [{**good, "special": 7}], "explanation": "x"}),
                 json.dumps({"tickets": [good, {"main": [6, 5, 4, 3, 2, 1]}], "explanation": "x"})]
        for index, text in enumerate(cases):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_tickets(text, get_rule("mega"), 2 if index == len(cases)-1 else 1)

    def test_lotto_special_and_keno_request_size(self):
        text = '```json\n{"tickets":[{"main":[5,4,3,2,1],"special":12}],"explanation":"Tham khảo"}\n```'
        tickets, explanation = parse_tickets(text, get_rule("lotto"), 1)
        self.assertEqual(tickets[0].selections, {"main": [1, 2, 3, 4, 5], "special": 12})
        self.assertEqual(parse_tickets(text.replace("```json\n", "```\r\n"), get_rule("lotto"), 1)[0], tickets)
        with self.assertRaises(ValueError):
            parse_tickets(text.replace('"special":12', '"special":13'), get_rule("lotto"), 1)
        records = [draw("keno", tuple(range(61, 81)), identifier=f"{i:07}") for i in range(90)]
        _, _, body = build_generation_request(AIConfig(api_key="local"), get_rule("keno"), records, 100)
        self.assertLessEqual(len(body["input"]), 10_000)

    def test_insufficient_history_unsupported_rule_and_cancellation_do_not_retry(self):
        with patch("app.ai._send") as request:
            for rule, count in ((get_rule("mega"), 1), (get_rule("max3d"), 1), (get_rule("mega"), True)):
                with self.assertRaises(ValueError):
                    generate_with_ai(AIConfig(api_key="local"), rule, [], count)
            request.assert_not_called()
        history = [draw(identifier=str(i)) for i in range(90)]
        with patch("app.ai._send", side_effect=CancelledError("hủy")) as request:
            with self.assertRaises(CancelledError):
                generate_with_ai(AIConfig(api_key="local"), get_rule("mega"), history, 1)
            request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
