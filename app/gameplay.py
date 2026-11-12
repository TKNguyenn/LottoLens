"""Basic Max tickets and all 38 Bingo18 choices; exact fair-draw event odds."""
from fractions import Fraction
from itertools import product

BINGO_PLAYS = ("single", "double", "triple", "any_triple", "sum", "size")
BINGO_LABELS = {"single": "Một số trùng", "double": "Hai số trùng", "triple": "Ba số trùng",
                "any_triple": "Ba số bất kỳ", "sum": "Cộng tổng", "size": "Lớn–Hòa–Nhỏ"}
SIZE_LABELS = {"small": "Nhỏ", "tie": "Hòa", "big": "Lớn"}


def bingo_choices(play_context=None):
    play = "single" if play_context is None else play_context
    if not isinstance(play, str) or play not in BINGO_PLAYS:
        raise ValueError("Cách chơi Bingo18 không hợp lệ.")
    values = range(3, 19) if play == "sum" else ("small", "tie", "big") if play == "size" else range(1, 7)
    if play == "any_triple":
        return [{"play": play, "main": []}]
    return [{"play": play, "main": [value]} for value in values]


def validate_bingo(selections, play_context=None):
    if not isinstance(selections, dict) or set(selections) != {"play", "main"}:
        raise ValueError("Vé Bingo18 cần đúng cách chơi và lựa chọn.")
    choices = bingo_choices(selections["play"])
    main = selections["main"]
    if (not isinstance(main, list) or any(type(x) is not int for x in main) and selections["play"] != "size"
            or selections not in choices or (play_context is not None and selections["play"] != play_context)):
        raise ValueError("Lựa chọn không đúng cách chơi Bingo18 đã chọn.")


def ticket_capacity(rule, play_context=None):
    if rule.kind == "dice":
        return len(bingo_choices(play_context))
    if play_context is not None:
        raise ValueError("Trò này không nhận cách chơi Bingo18.")
    if rule.kind == "triples":
        return 1000 ** rule.selected
    from math import comb
    return comb(rule.population, rule.selected) * (rule.special_max if rule.game_id == "lotto" else 1)


def sample_selections(rule, play_context=None):
    ticket_capacity(rule, play_context)
    if rule.kind == "dice":
        return bingo_choices(play_context)[0]
    if rule.kind == "triples":
        return {"main": ["007", "123"][:rule.selected]}
    result = {"main": list(range(1, rule.selected + 1))}
    if rule.game_id == "lotto":
        result["special"] = 1
    return result


def bingo_outcomes(selections, result):
    play, main = selections["play"], selections["main"]
    if play == "single":
        count = result.count(main[0])
        return {f"Xuất hiện {n} lần": count == n for n in (1, 2, 3)}
    if play == "double":
        hit = result.count(main[0]) >= 2
    elif play == "triple":
        hit = result.count(main[0]) == 3
    elif play == "any_triple":
        hit = len(set(result)) == 1
    elif play == "sum":
        hit = sum(result) == main[0]
    else:
        total = sum(result)
        hit = {"small": total <= 9, "tie": total in (10, 11), "big": total >= 12}[main[0]]
    return {"Trúng": hit}


def pair_probability(population, drawn, same=False):
    """At least two occurrences of A, or at least one each of distinct A/B."""
    q = Fraction(population - 1, population)
    if same:
        return 1 - q**drawn - drawn * Fraction(1, population) * q**(drawn - 1)
    return 1 - 2 * q**drawn + Fraction(population - 2, population)**drawn


def game_probabilities(rule, selections):
    if rule.kind == "dice":
        validate_bingo(selections)
        totals = {name: 0 for name in bingo_outcomes(selections, (1, 1, 1))}
        for result in product(range(1, 7), repeat=3):
            for name, hit in bingo_outcomes(selections, result).items():
                totals[name] += hit
        odds = {name: Fraction(count, 216) for name, count in totals.items()}
        odds["Không trúng"] = 1 - sum(odds.values())
        return odds
    q = Fraction(999, 1000)
    if rule.game_id == "max3d":
        odds = {name: 1-q**size for name, size in (("Giải Đặc biệt", 2), ("Giải Nhất", 4), ("Giải Nhì", 6), ("Giải Ba", 8))}
    else:
        same = selections["main"][0] == selections["main"][1]
        q = Fraction(999 if same else 998, 1000)
        odds = {"Giải Đặc biệt": Fraction(1, 1_000_000), "Giải phụ Đặc biệt": Fraction(1, 1_000_000)}
        odds.update({name: pair_probability(1000, size, same) for name, size in (("Giải Nhất", 4), ("Giải Nhì", 6), ("Giải Ba", 8), ("Giải Tư", 20))})
        odds.update({"Giải Năm": 1-q**2, "Giải Sáu": 1-q**18})
    odds["Trúng ít nhất một giải"] = 1-q**20
    odds["Không trúng"] = q**20
    return odds
