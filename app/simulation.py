from collections import Counter
from random import Random

from .domain import Draw, utc_now, validate_ticket
from .evaluation import evaluate, FIXED


def random_draw(rule, rng, identifier):
    payload = {"main": sorted(rng.sample(range(1, rule.population+1), rule.drawn))}
    if rule.special_max:
        pool = [x for x in range(1, rule.special_max+1) if not rule.bonus_from_remainder or x not in payload["main"]]
        payload["special"] = pool[rng.randrange(len(pool))]
    now = utc_now()
    return Draw(rule.game_id, rule.mode_id, rule.rule_version, str(identifier), now, payload,
                "synthetic:simulation", now, "0"*64, verification_status="simulation")


def simulate(rule, ticket, trials, seed, cancel=lambda: False, progress=lambda done, total: None):
    validate_ticket(rule, ticket)
    if rule.kind != "set" or type(trials) is not int or not 1 <= trials <= 100_000 or type(seed) is not int:
        raise ValueError("Mô phỏng nhận trò tập số, 1–100.000 kỳ và seed nguyên.")
    rng, tiers, completed = Random(seed), Counter(), 0
    for index in range(trials):
        if index % 50 == 0:
            if cancel():
                break
            progress(index, trials)
        draw = random_draw(rule, rng, index+1)
        if rule.game_id in FIXED:
            result = evaluate(rule, ticket, draw)
            tier = result.prize_tiers[0] if result.prize_tiers else "Không trúng"
        else:
            matches = len(set(ticket.selections["main"]) & set(draw.payload["main"]))
            tier = f"Trùng {matches} số"
        tiers[tier] += 1; completed += 1
    progress(completed, trials)
    return {"status": "completed" if completed == trials else "incomplete", "seed": seed,
            "requested_trials": trials, "completed_trials": completed, "tiers": dict(tiers),
            "cost_vnd": ticket.cost_vnd*completed,
            "note": "Dữ liệu mô phỏng, không phải lịch sử thật. Không quan sát thấy giải hiếm không có nghĩa xác suất bằng 0."}
