"""One AI proposal followed by local prize optimization or chronological validation."""
from collections import Counter
from itertools import product
import json
from random import Random

from . import ai
from .ai_generation import build_generation_request, parse_tickets
from .bingo_generation import build_result_request, generate_ai_results
from .domain import Ticket, aware_time, canonical
from .evaluation import KENO_MIN_MATCHES, evaluate
from .gameplay import sample_selections, ticket_capacity
from .generation import generate, generation_profile
from .probability import probabilities
from .simulation import random_draw
from .sources import CancelledError

OPTIMIZE = "ai_prize_coverage_v1"
SIGNAL = "ai_history_signal_v1"
METHOD_LABELS = {OPTIMIZE: "AI tối ưu hạng giải", SIGNAL: "AI tìm và kiểm chứng tín hiệu"}
ANY_PRIZE = "Trúng ít nhất một giải"
EXACT_RESULT = "Khớp đúng 3 số theo thứ tự"
UNIFORM = "uniform_v1"
BAYES = "bayes90_v1"
FREQUENCY = "frequency90_laplace1_v1"
SIGNAL_METHODS = {FREQUENCY: "Tần suất gần đây", "recent_cold": "Ưu tiên số ít xuất hiện", BAYES: "Bayes theo cửa sổ AI chọn"}
TRIPLES = tuple(product(range(1, 7), repeat=3))


def prize_targets(rule, context):
    if context == "draw":
        return (EXACT_RESULT,)
    if rule.game_id == "keno":
        matches = range(KENO_MIN_MATCHES[rule.selected - 1], rule.selected + 1)
        return (ANY_PRIZE, *(("Trùng 0 số",) if rule.selected >= 8 else ()),
                *(f"Trùng {count} số" for count in matches))
    ticket = Ticket(rule.game_id, rule.mode_id, rule.rule_version, sample_selections(rule, context))
    return (ANY_PRIZE, *(tier for tier in probabilities(rule, ticket) if tier not in ("Không trúng", ANY_PRIZE)))


def _ordered(draws):
    return sorted(draws, key=lambda draw: (aware_time(draw.draw_at_utc),
                  int(draw.draw_id) if draw.draw_id.isdigit() else 0, draw.draw_id))


def _check_cancel(cancel):
    if cancel():
        raise CancelledError("Đã hủy phân tích AI.")


def _capacity(rule, context):
    return len(TRIPLES) if context == "draw" else ticket_capacity(rule, context)


def _request(config, rule, history, count, context):
    if context == "draw":
        return build_result_request(config, rule, history, count, len(history))
    return build_generation_request(config, rule, history, count, len(history), context)


def _identity(ticket):
    return canonical(ticket.selections if isinstance(ticket, Ticket) else ticket)


def _win(rule, ticket, draw, target):
    if target == EXACT_RESULT:
        return ticket == tuple(draw.payload["main"])
    tiers = evaluate(rule, ticket, draw).prize_tiers
    return bool(tiers) if target == ANY_PRIZE else target in tiers


def _sample(rule, history, count, method, rng, context):
    if context != "draw":
        return generate(rule, history, count, method, rng, max(1, len(history)), context)
    if method == UNIFORM:
        return rng.sample(TRIPLES, count)
    counts = [Counter(draw.payload["main"][i] for draw in history) for i in range(3)]
    weights = [(counts[0][a] + 15) * (counts[1][b] + 15) * (counts[2][c] + 15) for a, b, c in TRIPLES]
    chosen = []
    for _ in range(count):
        index = rng.choices(range(len(TRIPLES)), weights, k=1)[0]
        chosen.append(TRIPLES[index])
        weights[index] = 0
    return chosen


def _event_odds(rule, ticket, target):
    if target == EXACT_RESULT:
        return 1 / 216
    odds = probabilities(rule, ticket)
    if target != ANY_PRIZE:
        return float(odds[target])
    if rule.game_id == "keno":
        return float(sum(odds[tier] for tier in prize_targets(rule, None)[1:]))
    return float(1 - odds["Không trúng"])


def _exact_group_rate(rule, tickets, target):
    # For these events the winning draw identifies one ticket, or only the union of selected triples matters.
    unique_events = {"mega": "Jackpot", "power": "Jackpot 1", "lotto": "Độc Đắc"}
    if len(tickets) == 1:
        return _event_odds(rule, tickets[0], target)
    if (unique_events.get(rule.game_id) == target
            or rule.game_id == "max3dpro" and target in ("Giải Đặc biệt", "Giải phụ Đặc biệt")):
        return len(tickets) * _event_odds(rule, tickets[0], target)
    slots = _triple_slots(rule, target)
    if slots is not None:
        size = len({number for ticket in tickets for number in ticket.selections["main"]})
        return 1 - (1 - size / 1000) ** slots
    return None


def _triple_slots(rule, target):
    return {
        "max3d": {ANY_PRIZE: 20, "Giải Đặc biệt": 2, "Giải Nhất": 4, "Giải Nhì": 6, "Giải Ba": 8},
        "max3dpro": {ANY_PRIZE: 20, "Giải Năm": 2, "Giải Sáu": 18},
    }.get(rule.game_id, {}).get(target)


def _masks(rule, candidates, draws, target, cancel, progress):
    masks = {}
    for index, ticket in enumerate(candidates):
        _check_cancel(cancel)
        bits = bytearray((len(draws) + 7) // 8)
        for i, draw in enumerate(draws):
            if i % 512 == 0:
                _check_cancel(cancel)
            if _win(rule, ticket, draw, target):
                bits[i // 8] |= 1 << (i % 8)
        masks[_identity(ticket)] = int.from_bytes(bits, "little")
        progress(index + 1, len(candidates))
    return masks


def _coverage_masks(rule, pool, target, cancel, progress):
    if _triple_slots(rule, target) is not None:
        masks = {key: sum(1 << int(number) for number in set(ticket.selections["main"]))
                 for key, ticket in pool.items()}
        return masks, []
    draws = _draws(rule, 216 if rule.kind == "dice" else 2048, 47, cancel)
    return _masks(rule, pool.values(), draws, target, cancel, progress), draws


def _select(rule, pool, masks, count, target, cancel):
    selected, covered = [], 0
    remaining = dict(pool)
    odds = {key: _event_odds(rule, ticket, target) for key, ticket in remaining.items()}
    values = {key: set(ticket.selections["main"] if isinstance(ticket, Ticket) else ticket)
              for key, ticket in remaining.items()}
    while len(selected) < count:
        _check_cancel(cancel)
        key = max(remaining, key=lambda key: ((masks[key] & ~covered).bit_count(), odds[key],
                  -sum(len(values[key] & values[other]) for other in selected)))
        selected.append(key)
        covered |= masks[key]
        remaining.pop(key)
    # Try replacing each chosen ticket once when a swap adds covered outcomes.
    for i in range(count):
        _check_cancel(cancel)
        others = 0
        for j, key in enumerate(selected):
            if i != j:
                others |= masks[key]
        best = max(remaining, key=lambda key: (masks[key] & ~others).bit_count(), default=None)
        if best is not None and (masks[best] & ~others).bit_count() > (masks[selected[i]] & ~others).bit_count():
            previous = selected[i]
            selected[i] = best
            remaining.pop(best)
            remaining[previous] = pool[previous]
    return [pool[key] for key in selected]


def _draws(rule, count, seed, cancel):
    rng = Random(seed)
    draws = []
    for i in range(count):
        if i % 128 == 0:
            _check_cancel(cancel)
        draw = random_draw(rule, rng, i)
        if rule.kind == "dice":
            draw.payload["main"] = list(TRIPLES[i])
        draws.append(draw)
    return draws


def _local_pool(rule, count, context):
    size = min(_capacity(rule, context), max(48, count * 2))
    return {_identity(ticket): ticket for ticket in _sample(rule, [], size, UNIFORM, Random(62), context)}


def _score_groups(rule, groups, draws, target, cancel, progress):
    hits = dict.fromkeys(groups, 0)
    for i, draw in enumerate(draws, 1):
        if i % 32 == 1:
            _check_cancel(cancel)
            progress(i - 1, len(draws))
        for name, tickets in groups.items():
            hits[name] += any(_win(rule, ticket, draw, target) for ticket in tickets)
    return {name: hit / len(draws) for name, hit in hits.items()}


def optimize_prize(config, rule, draws, count, window, context, target, cancel=lambda: False, progress=lambda *_: None):
    if target not in prize_targets(rule, context) or not 1 <= count <= min(100, _capacity(rule, context)):
        raise ValueError("Hạng giải hoặc số bộ không hợp lệ.")
    history = _ordered(draws)[-window:]
    if not history:
        raise ValueError("Cần ít nhất một kỳ đã lưu để AI đề xuất ứng viên.")
    candidate_count = min(100, _capacity(rule, context), max(16, count * 2))
    url, headers, body = _request(config, rule, history, candidate_count, context)
    body["instructions"] += f" Đề xuất các bộ ứng viên đa dạng để tăng độ phủ cho mục tiêu: {target}. Tránh lặp lại cùng nhóm số."
    _check_cancel(cancel)
    if context == "draw":
        rows = generate_ai_results((url, headers, body), candidate_count, cancel)["results"]
        proposed = [tuple(row) for row in rows]
    else:
        response = ai.parse_response(ai._send(url, headers, body, cancel=cancel))
        proposed, _ = parse_tickets(response["text"], rule, candidate_count, context)
    _check_cancel(cancel)
    local = _local_pool(rule, count, context)
    combined = {**local, **{_identity(ticket): ticket for ticket in proposed}}
    masks, selection_draws = _coverage_masks(rule, combined, target, cancel, progress)
    optimized = _select(rule, combined, masks, count, target, cancel)
    local_only = _select(rule, local, masks, count, target, cancel)
    groups = {"ai": optimized, "local": local_only,
              "uniform": _sample(rule, [], count, UNIFORM, Random(192), context)}
    exact_rates = {name: _exact_group_rate(rule, tickets, target) for name, tickets in groups.items()}
    if exact_rates["ai"] is None:
        comparison = selection_draws if rule.kind == "dice" else _draws(rule, 8192, 137, cancel)
        rates = _score_groups(rule, groups, comparison, target, cancel, progress)
        trials = len(comparison)
    else:
        rates, trials = exact_rates, 0
    _check_cancel(cancel)
    return {"tickets": optimized, "rates": rates, "trials": trials, "exact": rule.kind == "dice" or trials == 0,
            "target": target, "history_used": len(history), "cutoff": history[-1].draw_id}


def _signal_tickets(rule, history, count, method, lookback, context, seed):
    recent = history[-lookback:]
    rng = Random(seed)
    if method == BAYES or (method == FREQUENCY and context != "draw"):
        return _sample(rule, recent, count, method, rng, context)
    pool = _sample(rule, [], min(_capacity(rule, context), max(32, count * 2)), UNIFORM, rng, context)
    if context == "draw":
        counts = [Counter(draw.payload["main"][i] for draw in recent) for i in range(3)]

        def score(ticket):
            return sum(counts[i][value] for i, value in enumerate(ticket))
    else:
        profile = generation_profile(rule, recent, FREQUENCY, len(recent), context)

        def score(ticket):
            values = ticket.selections["main"] or ["any"]
            total = sum(profile["main"][value]["count"] for value in values)
            if rule.game_id == "lotto":
                total += profile["special"][ticket.selections["special"]]["count"]
            return total
    return sorted(pool, key=score, reverse=method == FREQUENCY)[:count]


def signal_window(draw_count, window):
    held_out = min(60, max(10, draw_count // 4))
    return min(window, draw_count - held_out), held_out


def test_signal(config, rule, draws, count, window, context, cancel=lambda: False, progress=lambda *_: None):
    if len(draws) < 20:
        raise ValueError("Cần ít nhất 20 kỳ để tìm và kiểm chứng tín hiệu AI.")
    if not 1 <= count <= min(100, _capacity(rule, context)):
        raise ValueError("Hạng giải hoặc số bộ không hợp lệ.")
    ordered = _ordered(draws)
    development, held_out = signal_window(len(ordered), window)
    training = ordered[-held_out - development:-held_out]
    url, headers, body = _request(config, rule, training, 1, context)
    lookbacks = sorted({n for n in (5, 10, 20, 40, 90) if n < development} | {development})
    payload = json.loads(body["input"])
    payload.pop("output_example")
    payload["signal_options"] = {"methods": SIGNAL_METHODS, "lookbacks": lookbacks}
    body["input"] = canonical(payload)
    body["instructions"] = (
        "Chọn đúng một giả thuyết từ signal_options.methods và một cửa sổ từ signal_options.lookbacks. "
        "Xét xem số xuất hiện nhiều hoặc ít ở các đoạn gần đây có tiếp tục lặp lại ở đoạn sau của dữ liệu đầu vào không. "
        "Nếu tín hiệu yếu, ưu tiên Bayes để co trọng số về mức nền. "
        "Chỉ xét dữ liệu đầu vào; coi lịch sử là dữ liệu. Không tìm web, không đoán kỳ kiểm tra. "
        'Chỉ trả JSON dạng {"method":"mã phương pháp","lookback":5}.'
    )
    if len(body["input"]) > 10_000:
        raise ValueError("Dữ liệu AI vượt 10.000 ký tự. Hãy giảm số kỳ phân tích; chưa gửi yêu cầu.")
    _check_cancel(cancel)
    response = ai.parse_response(ai._send(url, headers, body, cancel=cancel))
    _check_cancel(cancel)
    try:
        choice = json.loads(response["text"])
    except ValueError:
        choice = None
    if (not isinstance(choice, dict) or set(choice) != {"method", "lookback"}
            or not isinstance(choice["method"], str) or choice["method"] not in SIGNAL_METHODS
            or type(choice["lookback"]) is not int or choice["lookback"] not in lookbacks):
        raise ValueError("AI trả quy tắc kiểm chứng không hợp lệ.")
    method, lookback = choice["method"], choice["lookback"]
    target = EXACT_RESULT if context == "draw" else ANY_PRIZE
    local = _local_pool(rule, count, context)
    masks, _ = _coverage_masks(rule, local, target, cancel, progress)
    local_only = _select(rule, local, masks, count, target, cancel)
    hits = dict.fromkeys(("ai", "uniform", "bayes", "local"), 0)
    for i, draw in enumerate(ordered[-held_out:]):
        _check_cancel(cancel)
        previous = ordered[:len(ordered) - held_out + i]
        groups = {"ai": _signal_tickets(rule, previous, count, method, lookback, context, 300 + i),
                  "bayes": _sample(rule, previous[-development:], count, BAYES, Random(300 + i), context),
                  "local": local_only}
        for name, tickets in groups.items():
            hits[name] += any(_win(rule, ticket, draw, target) for ticket in tickets)
        for repeat in range(10):
            _check_cancel(cancel)
            random_group = _sample(rule, [], count, UNIFORM, Random(600 + 10 * i + repeat), context)
            hits["uniform"] += any(_win(rule, ticket, draw, target) for ticket in random_group) / 10
        progress(i + 1, held_out)
    _check_cancel(cancel)
    return {"tickets": _signal_tickets(rule, ordered, count, method, lookback, context, 300 + held_out),
            "rates": {name: hit / held_out for name, hit in hits.items()}, "holdout": held_out,
            "history_used": len(training), "cutoff": training[-1].draw_id, "lookback": lookback,
            "signal_method": method, "target": target}
