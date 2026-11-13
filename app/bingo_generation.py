"""Generate three-number Bingo18 reference results without creating game tickets."""
from collections import Counter
import json

from . import ai
from .ai_generation import INSTRUCTIONS
from .domain import aware_time, canonical
from .generation import generation_profile


def result_profile(rule, history, method, history_window):
    if rule.game_id != "bingo18":
        raise ValueError("Kiểu bộ ba kết quả chỉ dành cho Bingo18.")
    profile = generation_profile(rule, history, method, history_window, "single")
    ordered = sorted(history, key=lambda draw: (
        aware_time(draw.draw_at_utc), int(draw.draw_id) if draw.draw_id.isdigit() else 0, draw.draw_id
    ))[-history_window:]
    counts = [Counter(draw.payload["main"][position] for draw in ordered) for position in range(3)]
    return ordered, counts, profile


def generate_results(rule, history, count, method, rng, history_window):
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("Mỗi lần tạo từ 1 đến 100 bộ ba.")
    ordered, counts, profile = result_profile(rule, history, method, history_window)
    values = list(range(1, 7))
    weights = []
    for observed in counts:
        if method == "uniform_v1":
            weights.append([1] * 6)
        elif method == "bayes90_v1":
            weights.append([(observed[n] + 90/6) / (len(ordered) + 90) for n in values])
        else:
            weights.append([(observed[n] + 1) / (len(ordered) + 6) for n in values])
    results = [[rng.choices(values, weights=position, k=1)[0] for position in weights] for _ in range(count)]
    return {"results": results, "history_used": profile["history_used"]}


def build_result_request(config, rule, history, count, history_window):
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("Mỗi lần tạo từ 1 đến 100 bộ ba.")
    ordered, counts, profile = result_profile(rule, history, "bayes90_v1", history_window)
    context = {
        "game_id": rule.game_id, "output_kind": "three_number_reference_results", "count": count,
        "history_window": history_window, "cutoff_draw_id": profile["cutoff_draw_id"],
        "history": [[draw.draw_id, draw.payload["main"]] for draw in ordered],
        "position_counts": [{str(n): observed[n] for n in range(1, 7)} for observed in counts],
        "constraints": {"numbers_per_result": 3, "minimum": 1, "maximum": 6,
                        "integer_only": True, "keep_order": True, "repeated_numbers_allowed": True},
        "output_example": {"results": [[6, 3, 4], [5, 1, 5]], "explanation": "Giải thích ngắn."},
    }
    url, headers, body = ai.build_request(config, canonical(context), web_search=False)
    body["instructions"] = (
        INSTRUCTIONS.replace("90 kỳ", f"{history_window} kỳ")
        .replace("count bộ khác nhau", "count bộ ba")
        .replace("theo output_example", "gồm results và explanation theo output_example")
        + " Tạo bộ ba theo dạng kết quả quay Bingo18, giữ thứ tự và cho phép số lặp."
    )
    body["reasoning"] = {"effort": "high"}
    return url, headers, body


def generate_ai_results(request, count, cancel=lambda: False):
    url, headers, body = request
    response = ai.parse_response(ai._send(url, headers, body, cancel=cancel))
    text = response["text"].strip()
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].lower() in ("```", "```json") and lines[-1] == "```":
        text = "\n".join(lines[1:-1])
    try:
        result = json.loads(text)
    except (ValueError, TypeError):
        raise ValueError("AI trả bộ ba không hợp lệ.") from None
    if not isinstance(result, dict) or set(result) != {"results", "explanation"}:
        raise ValueError("AI trả bộ ba không hợp lệ.")
    rows = result["results"]
    if (not isinstance(rows, list) or len(rows) != count
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(n) is not int or not 1 <= n <= 6 for n in row) for row in rows)
            or not isinstance(result["explanation"], str) or not result["explanation"].strip()
            or len(result["explanation"]) > 12_000):
        raise ValueError("AI trả bộ ba không hợp lệ.")
    return result
