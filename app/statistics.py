from collections import Counter
from itertools import combinations
from math import sqrt
from .domain import aware_time, validate_draw


def wilson95(successes, trials):
    if type(successes) is not int or type(trials) is not int or trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("Cỡ mẫu hoặc số lần xuất hiện không hợp lệ.")
    z = 1.959963984540054
    p = successes / trials
    denominator = 1 + z*z/trials
    center = (p + z*z/(2*trials)) / denominator
    margin = z * sqrt(p*(1-p)/trials + z*z/(4*trials*trials)) / denominator
    return max(0., center - margin), min(1., center + margin)


def holm_adjust(p_values):
    if any(type(p) not in (int, float) or not 0 <= p <= 1 for p in p_values):
        raise ValueError("p-value phải thuộc [0,1].")
    adjusted = [0.] * len(p_values)
    running = 0.
    for rank, index in enumerate(sorted(range(len(p_values)), key=p_values.__getitem__)):
        running = max(running, min(1., (len(p_values) - rank)*p_values[index]))
        adjusted[index] = running
    return adjusted


def describe(rule, draws):
    ordered = sorted(draws, key=lambda d: (aware_time(d.draw_at_utc), d.draw_id))
    seen = set()
    frequencies, specials, pairs = Counter(), Counter(), Counter()
    last, gaps, sums, evens = {}, {}, [], []
    for index, draw in enumerate(ordered):
        validate_draw(rule, draw)
        if draw.draw_id in seen:
            raise ValueError("Dữ liệu thống kê chứa hai phiên bản của cùng kỳ.")
        seen.add(draw.draw_id)
        if rule.kind == "triples":
            values = [x for group in draw.payload["groups"].values() for x in group]
        else:
            values = draw.payload["main"]
            sums.append(sum(values)); evens.append(sum(x % 2 == 0 for x in values))
        frequencies.update(values)
        for value in set(values):
            if value in last:
                gaps.setdefault(value, []).append(index-last[value])
            last[value] = index
        if rule.kind == "set":
            pairs.update(combinations(sorted(values), 2))
        if "special" in draw.payload:
            specials[draw.payload["special"]] += 1
    if rule.kind != "triples":
        frequencies = Counter({x: frequencies[x] for x in range(1, rule.population+1)})
    result = {"count": len(ordered), "frequencies": dict(frequencies),
              "special_frequencies": dict(specials),
              "pairs": [{"numbers": list(k), "count": v} for k, v in pairs.most_common(30)],
              "completed_gaps": gaps, "current_gaps": {k: len(ordered)-1-v for k, v in last.items()},
              "sums": sums, "even_counts": evens,
              "note": "Thống kê lịch sử không phải xác suất trúng kỳ tới. Khoảng cách hiện tại còn bị cắt tại cuối mẫu."}
    if ordered and rule.kind == "set":
        result["wilson95"] = {x: wilson95(c, len(ordered)) for x, c in frequencies.items()}
        result["expected_per_number"] = len(ordered)*rule.drawn/rule.population
    return result
