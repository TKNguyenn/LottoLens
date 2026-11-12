from .domain import EvalResult, validate_draw, validate_ticket
from .probability import lotto_tier

FIXED = {
    "mega": {"Giải Nhất": 10_000_000, "Giải Nhì": 300_000, "Giải Ba": 30_000},
    "power": {"Giải Nhất": 40_000_000, "Giải Nhì": 500_000, "Giải Ba": 50_000},
    "lotto": {"Giải Nhất": 10_000_000, "Giải Nhì": 5_000_000, "Giải Ba": 500_000,
              "Giải Tư": 100_000, "Giải Năm": 30_000, "Giải Khuyến Khích": 10_000},
}


def evaluate(rule, ticket, draw):
    validate_ticket(rule, ticket)
    validate_draw(rule, draw)
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
