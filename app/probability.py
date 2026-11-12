from fractions import Fraction
from math import comb
from .domain import validate_ticket


def overlap_probabilities(population, drawn, selected):
    if any(type(x) is not int for x in (population, drawn, selected)) or population <= 0 or not 0 <= drawn <= population or not 0 <= selected <= population:
        raise ValueError("Miền tổ hợp không hợp lệ.")
    denominator = comb(population, selected)
    return {k: Fraction(comb(drawn, k) * comb(population - drawn, selected - k), denominator)
            for k in range(max(0, selected - population + drawn), min(selected, drawn) + 1)}


def probabilities(rule, ticket):
    validate_ticket(rule, ticket)
    if not rule.math_ready:
        raise ValueError("Chưa xác minh đủ cơ chế quay để tính xác suất hạng giải của trò này.")
    if rule.kind in ("triples", "dice"):
        from .gameplay import game_probabilities
        return game_probabilities(rule, ticket.selections)
    distribution = overlap_probabilities(rule.population, rule.drawn, rule.selected)
    if rule.game_id == "mega":
        result = {name: distribution[k] for k, name in ((6, "Jackpot"), (5, "Giải Nhất"), (4, "Giải Nhì"), (3, "Giải Ba"))}
    elif rule.game_id == "power":
        jackpot2 = distribution[5] / 49
        result = {"Jackpot 1": distribution[6], "Jackpot 2": jackpot2,
                  "Giải Nhất": distribution[5] - jackpot2,
                  "Giải Nhì": distribution[4], "Giải Ba": distribution[3]}
    elif rule.game_id == "lotto":
        result = {}
        for k in range(6):
            for special, weight in ((True, Fraction(1, 12)), (False, Fraction(11, 12))):
                name = lotto_tier(k, special)
                result[name] = result.get(name, Fraction(0)) + distribution[k] * weight
        return result
    else:
        # shortcut: Keno exposes overlap odds only; enable named prize tiers after verifying its payout table.
        return {f"Trùng {k} số": p for k, p in distribution.items()}
    result["Không trúng"] = 1 - sum(result.values())
    return result


def lotto_tier(matches, special):
    if matches == 5:
        return "Độc Đắc" if special else "Giải Nhất"
    if matches == 4:
        return "Giải Nhì" if special else "Giải Ba"
    if matches == 3:
        return "Giải Tư" if special else "Giải Năm"
    return "Giải Khuyến Khích" if special else "Không trúng"
