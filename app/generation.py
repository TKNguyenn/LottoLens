from collections import Counter
from .domain import Ticket, aware_time, canonical, validate_draw, validate_ticket
from .probability import probabilities
from .gameplay import bingo_choices, bingo_outcomes, game_probabilities, ticket_capacity

METHODS = ("uniform_v1", "frequency90_laplace1_v1", "bayes90_v1")
METHOD_LABELS = {"bayes90_v1": "Xác suất–thống kê 90 kỳ (Bayes)",
                 "frequency90_laplace1_v1": "Tần suất 90 kỳ", "uniform_v1": "Chọn ngẫu nhiên đồng đều"}


def generation_profile(rule, history, method, history_window=90, play_context=None):
    if type(history_window) is not int or not 1 <= history_window <= 2000:
        raise ValueError("Số kỳ phân tích phải là số nguyên từ 1 đến 2000.")
    if method not in METHODS or rule.kind not in ("set", "triples", "dice"):
        raise ValueError("Phương pháp/trò chưa hỗ trợ sinh số.")
    ticket_capacity(rule, play_context)
    ordered = sorted(history, key=lambda d: (aware_time(d.draw_at_utc), int(d.draw_id) if d.draw_id.isdigit() else 0, d.draw_id))
    for draw in ordered:
        validate_draw(rule, draw)
    if len({d.draw_id for d in ordered}) != len(ordered):
        raise ValueError("History chứa kỳ trùng; hãy chọn một revision mỗi kỳ.")
    if method != "uniform_v1" and len(ordered) < history_window:
        raise ValueError(f"Phương pháp thống kê cần ít nhất {history_window} kỳ trước kỳ đích.")
    sample = ordered[-history_window:]
    if rule.kind != "set":
        if rule.kind == "triples":
            counts = Counter(n for d in sample for group in d.payload["groups"].values() for n in group)
            fair = {f"{n:03}": 20/1000 for n in range(1000)}
        else:
            choices = bingo_choices(play_context)
            fair = {}; counts = Counter()
            for choice in choices:
                key = choice["main"][0] if choice["main"] else "any"
                odds = game_probabilities(rule, choice)
                fair[key] = float(1-odds["Không trúng"])
                counts[key] = sum(any(bingo_outcomes(choice, d.payload["main"]).values()) for d in sample)
        rows = {}
        for key, prior in fair.items():
            if method == "bayes90_v1":
                weight = (counts[key]+90*prior)/(len(sample)+90)
            elif method == "frequency90_laplace1_v1":
                weight = (counts[key]+1)/(len(sample)*(20 if rule.kind == "triples" else 1)+(1000 if rule.kind == "triples" else 2))
            else:
                weight = 1
            rows[key] = {"count": counts[key], "historical_rate": counts[key]/len(sample) if sample else None,
                         "fair_rate": prior, "model_rate": weight}
        return {"method": method, "play_context": play_context, "history_window": history_window,
                "history_used": len(sample), "cutoff_draw_id": sample[-1].draw_id if sample else None,
                "main": rows, "special": {}, "prior_equivalent_draws": 90 if method == "bayes90_v1" else 0,
                "observation_unit": "occurrences_per_draw" if rule.kind == "triples" else "winning_draws",
                "note": "Trọng số dùng để chọn vé tham khảo; không phải xác suất trúng. Tần suất đếm theo kỳ, Max đếm số lần chuỗi xuất hiện trong 20 kết quả/kỳ."}
    counts = Counter(n for d in sample for n in d.payload["main"])
    special_counts = Counter(d.payload.get("special") for d in sample)
    prior_rate = rule.drawn/rule.population

    def rows(maximum, observed, prior):
        result = {}
        for number in range(1, maximum+1):
            if method == "bayes90_v1":
                model_rate = (observed[number] + 90*prior)/(len(sample)+90)
            elif method == "frequency90_laplace1_v1":
                model_rate = (observed[number]+1)/(len(sample)+maximum)
            else:
                model_rate = prior
            result[number] = {"count": observed[number], "historical_rate": observed[number]/len(sample) if sample else None,
                              "fair_rate": prior, "model_rate": model_rate}
        return result
    return {"method": method, "history_window": history_window, "history_used": len(sample), "cutoff_draw_id": sample[-1].draw_id if sample else None,
            "main": rows(rule.population, counts, prior_rate),
            "special": rows(rule.special_max, special_counts, 1/rule.special_max) if rule.game_id == "lotto" else {},
            "prior_equivalent_draws": 90 if method == "bayes90_v1" else 0,
            "note": "model_rate là trọng số mô hình chọn số, không phải xác suất trúng thực tế của số hay bộ số."}


def explain_ticket(rule, history, ticket, method, history_window=90, play_context=None):
    validate_ticket(rule, ticket)
    profile = generation_profile(rule, history, method, history_window, play_context)
    if rule.kind != "set":
        if rule.kind == "dice" and ticket.selections not in bingo_choices(play_context):
            raise ValueError("Lựa chọn không đúng cách chơi Bingo18 đã chọn.")
        keys = ticket.selections["main"] or ["any"]
        odds = probabilities(rule, ticket)
        p = odds.get("Trúng ít nhất một giải", 1-odds["Không trúng"])
        return {"method": method, "play_context": play_context, "history_window": history_window,
                "history_used": profile["history_used"], "prior_equivalent_draws": profile["prior_equivalent_draws"],
                "cutoff_draw_id": profile["cutoff_draw_id"], "observation_unit": profile["observation_unit"],
                "formula": f"Bayes: (quan sát + 90 × mức nền) / ({len(history[-history_window:])} + 90)." if method == "bayes90_v1" else METHOD_LABELS[method].replace("90 kỳ", f"{history_window} kỳ"),
                "selected_number_stats": [{"number": x, **profile["main"][x]} for x in keys],
                "win_probability": {"numerator": p.numerator, "denominator": p.denominator}, "note": profile["note"]}
    result = {"method": method, "history_window": history_window, "history_used": profile["history_used"],
              "prior_equivalent_draws": profile["prior_equivalent_draws"], "cutoff_draw_id": profile["cutoff_draw_id"],
              "formula": f"Trọng số = (số lần xuất hiện + 90 × xác suất nền) / ({history_window} + 90); lấy mẫu không hoàn lại." if method == "bayes90_v1" else METHOD_LABELS[method].replace("90 kỳ", f"{history_window} kỳ"),
              "selected_number_stats": [{"number": x, **profile["main"][x]} for x in ticket.selections["main"]],
              "note": profile["note"]}
    if rule.game_id == "lotto":
        result["special_stats"] = {"number": ticket.selections["special"], **profile["special"][ticket.selections["special"]]}
    if rule.game_id in ("mega", "power", "lotto"):
        key = {"mega": "Jackpot", "power": "Jackpot 1", "lotto": "Độc Đắc"}[rule.game_id]
        probability = probabilities(rule, ticket)[key]
        result["jackpot_probability"] = {"numerator": probability.numerator, "denominator": probability.denominator}
    return result


def _pick(values, weights, rng):
    threshold = rng.random() * sum(weights)
    for index, weight in enumerate(weights):
        threshold -= weight
        if threshold < 0:
            return values[index]
    return values[-1]


def generate(rule, history, count, method, rng, history_window=90, play_context=None):
    if type(count) is not int or not 1 <= count <= 1000:
        raise ValueError("Mỗi lần tạo từ 1 đến 1000 bộ số.")
    if method not in METHODS:
        raise ValueError("Phương pháp chưa hỗ trợ.")
    profile = generation_profile(rule, history, method, history_window, play_context)
    capacity = ticket_capacity(rule, play_context)
    if count > capacity:
        raise ValueError("Số vé vượt không gian lựa chọn hợp lệ.")
    output, seen = [], set()
    if rule.kind != "set":
        candidates = bingo_choices(play_context) if rule.kind == "dice" else [{"main": [f"{n:03}"]} for n in range(1000)]
        values = [c["main"][0] if c["main"] else "any" for c in candidates]
        weights = [profile["main"][value]["model_rate"] for value in values]
        for _ in range(count*100):
            first = _pick(list(range(len(candidates))), weights, rng)
            selections = {**candidates[first], "main": list(candidates[first]["main"])}
            if rule.game_id == "max3dpro":
                selections["main"].append(_pick(values, weights, rng))
            key = canonical(selections)
            if key in seen:
                continue
            ticket = Ticket(rule.game_id, rule.mode_id, rule.rule_version, selections, cost_vnd=rule.price_vnd)
            validate_ticket(rule, ticket)
            output.append(ticket); seen.add(key)
            if len(output) == count:
                return output
            if rule.game_id != "max3dpro":
                candidates.pop(first); values.pop(first); weights.pop(first)
        raise ValueError(f"Chỉ tạo được {len(output)}/{count} vé khác nhau; hãy giảm số vé yêu cầu.")
    for _ in range(count*100):
        values = list(range(1, rule.population+1))
        weights = [profile["main"][x]["model_rate"] for x in values]
        selected = []
        for _ in range(rule.selected):
            value = _pick(values, weights, rng)
            index = values.index(value)
            selected.append(values.pop(index)); weights.pop(index)
        selections = {"main": sorted(selected)}
        if rule.game_id == "lotto":
            values = list(range(1, rule.special_max+1))
            weights = [profile["special"][x]["model_rate"] for x in values]
            selections["special"] = _pick(values, weights, rng)
        key = canonical(selections)
        if key in seen:
            continue
        ticket = Ticket(rule.game_id, rule.mode_id, rule.rule_version, selections, cost_vnd=rule.price_vnd)
        validate_ticket(rule, ticket)
        output.append(ticket); seen.add(key)
        if len(output) == count:
            return output
    raise ValueError(f"Chỉ tạo được {len(output)}/{count} vé khác nhau; hãy giảm số vé yêu cầu.")
