from .domain import EvalResult, validate_draw, validate_ticket
from .gameplay import bingo_outcomes
from .probability import lotto_tier

FIXED = {
    "mega": {"Giải Nhất": 10_000_000, "Giải Nhì": 300_000, "Giải Ba": 30_000},
    "power": {"Giải Nhất": 40_000_000, "Giải Nhì": 500_000, "Giải Ba": 50_000},
    "lotto": {"Giải Nhất": 10_000_000, "Giải Nhì": 5_000_000, "Giải Ba": 500_000,
              "Giải Tư": 100_000, "Giải Năm": 30_000, "Giải Khuyến Khích": 10_000},
}
EVENT_GAMES = {"keno", "max3d", "max3dpro", "bingo18"}
KENO_MIN_MATCHES = (1, 2, 2, 2, 3, 3, 3, 4, 4, 5)
MAX_TIER_NAMES = {"special": "Giải Đặc biệt", "first": "Giải Nhất", "second": "Giải Nhì", "third": "Giải Ba"}


def _max_tiers(game, selections, groups):
    first = selections[0]
    if game == "max3d":
        return [name for group, name in MAX_TIER_NAMES.items() if first in groups[group]]
    pair = tuple(selections)
    special = tuple(groups["special"])
    tiers = []
    if pair == special:
        tiers.append("Giải Đặc biệt")
    if pair == special[::-1]:
        tiers.append("Giải phụ Đặc biệt")
    rest = [number for group in ("first", "second", "third") for number in groups[group]]
    second = pair[1]
    pair_groups = [(groups[group], MAX_TIER_NAMES[group]) for group in ("first", "second", "third")]
    pair_groups.append((special + tuple(rest), "Giải Tư"))
    for numbers, name in pair_groups:
        pair_matches = numbers.count(first) >= 2 if first == second else first in numbers and second in numbers
        if pair_matches:
            tiers.append(name)
    if first in special or second in special:
        tiers.append("Giải Năm")
    if first in rest or second in rest:
        tiers.append("Giải Sáu")
    return tiers


def evaluate(rule, ticket, draw):
    validate_ticket(rule, ticket)
    validate_draw(rule, draw)
    if rule.game_id in EVENT_GAMES:
        matched = {}
        if rule.game_id == "keno":
            count = len(set(ticket.selections["main"]) & set(draw.payload["main"]))
            matched["main"] = count
            wins = count >= KENO_MIN_MATCHES[rule.selected-1] or (rule.selected >= 8 and count == 0)
            tiers = [f"Trùng {count} số"] if wins else []
        elif rule.kind == "dice":
            outcomes = bingo_outcomes(ticket.selections, draw.payload["main"])
            tiers = [name for name, hit in outcomes.items() if hit]
        else:
            tiers = _max_tiers(rule.game_id, ticket.selections["main"], draw.payload["groups"])
        return EvalResult(matched, tiers, None if tiers else 0, "unknown" if tiers else "known")
    if rule.game_id not in FIXED:
        raise ValueError("Chưa bật đối chiếu hạng giải: cần xác minh đầy đủ bảng trả thưởng.")
    matches = len(set(ticket.selections["main"]) & set(draw.payload["main"]))
    bonus = draw.payload.get("special") in ticket.selections["main"] if rule.game_id == "power" else None
    if rule.game_id == "mega":
        tier = {6: "Jackpot", 5: "Giải Nhất", 4: "Giải Nhì", 3: "Giải Ba"}.get(matches, "Không trúng")
    elif rule.game_id == "power":
        tier = "Jackpot 2" if matches == 5 and bonus else {6: "Jackpot 1", 5: "Giải Nhất", 4: "Giải Nhì", 3: "Giải Ba"}.get(matches, "Không trúng")
    else:
        bonus = ticket.selections["special"] == draw.payload["special"]
        tier = lotto_tier(matches, bonus)
    if tier == "Không trúng":
        return EvalResult({"main": matches, "special": bonus}, [], 0, "known")
    payout = FIXED[rule.game_id].get(tier)
    if draw.payload.get("roll_down") or draw.verification_status not in {"rule_verified", "simulation"}:
        payout = None
    return EvalResult({"main": matches, "special": bonus}, [tier], payout,
                      "fixed_gross" if payout is not None else "unknown",
                      "Chưa trừ thuế; jackpot/chia giải cần dữ liệu riêng của kỳ.")
