"""Offline checks for weighted and AI-generated Bingo18 result triples."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from random import Random
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai import AIConfig
from app.bingo_generation import build_result_request, generate_ai_results, generate_results
from app.rules import get_rule
from app.simulation import random_draw


def rejects(callback):
    try:
        callback()
    except ValueError:
        return
    raise AssertionError("Invalid input was accepted")


def main():
    rule = get_rule("bingo18")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history = [replace(random_draw(rule, Random(i), i + 1),
                       draw_at_utc=(start + timedelta(days=i)).isoformat(), payload={"main": [6, 6, 6]})
               for i in range(90)]
    totals = {}
    for method in ("uniform_v1", "frequency90_laplace1_v1", "bayes90_v1"):
        result = generate_results(rule, history, 100, method, Random(42), 90)
        assert result == generate_results(rule, list(reversed(history)), 100, method, Random(42), 90)
        assert len(result["results"]) == 100
        assert all(len(row) == 3 and all(type(n) is int and 1 <= n <= 6 for n in row) for row in result["results"])
        totals[method] = sum(row.count(6) for row in result["results"])
    assert totals["frequency90_laplace1_v1"] > 270
    assert totals["bayes90_v1"] > 150
    assert totals["uniform_v1"] < 80
    assert generate_results(rule, [], 1, "uniform_v1", Random(42), 90)["history_used"] == 0
    rejects(lambda: generate_results(rule, history[:2], 1, "bayes90_v1", Random(42), 90))
    for count in (True, 0, 101):
        rejects(lambda: generate_results(rule, history, count, "uniform_v1", Random(42), 90))
    request = build_result_request(AIConfig(api_key="offline-key"), rule, history, 2, 90)
    assert request[2]["reasoning"]["effort"] == "high" and "tools" not in request[2]
    good = {"results": [[6, 3, 4], [5, 1, 5]], "explanation": "fixture"}
    with patch("app.ai._send", return_value={"status": "completed", "output_text": json.dumps(good)}) as send:
        assert generate_ai_results(request, 2) == good
        send.assert_called_once()
        for rows in ([[1, 2]], [[1, 2, 7], [1, 2, 3]], [[True, 2, 3], [1, 2, 3]], [[1, 2, 3]]):
            send.return_value = {"status": "completed", "output_text": json.dumps({"results": rows, "explanation": "fixture"})}
            rejects(lambda: generate_ai_results(request, 2))
        send.return_value = {"status": "incomplete", "output_text": json.dumps(good)}
        rejects(lambda: generate_ai_results(request, 2))
    print("Bingo18 result generation passed: position weights, prior, order, bounds, AI validation and incomplete rejection.")


if __name__ == "__main__":
    main()
