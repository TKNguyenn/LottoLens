from collections import Counter
from random import Random

from .domain import MAX_GROUP_SIZES, Draw, utc_now, validate_ticket
from .evaluation import EVENT_GAMES, FIXED, evaluate


def random_draw(rule, rng, identifier):
    if rule.kind == "triples":
        payload = {"groups": {group: [f"{rng.randrange(1000):03}" for _ in range(size)]
                              for group, size in MAX_GROUP_SIZES}}
    elif rule.kind == "dice":
        payload = {"main": [rng.randint(1, rule.population) for _ in range(rule.drawn)]}
    else:
        payload = {"main": sorted(rng.sample(range(1, rule.population+1), rule.drawn))}
    if rule.special_max:
        pool = [x for x in range(1, rule.special_max+1) if not rule.bonus_from_remainder or x not in payload["main"]]
        payload["special"] = pool[rng.randrange(len(pool))]
    now = utc_now()
    return Draw(rule.game_id, rule.mode_id, rule.rule_version, str(identifier), now, payload,
                "synthetic:simulation", now, "0"*64, verification_status="simulation")


def simulate(rule, ticket, trials, seed, cancel=lambda: False, progress=lambda done, total: None):
    validate_ticket(rule, ticket)
    if rule.game_id not in FIXED and rule.game_id not in EVENT_GAMES:
        raise ValueError("Trò chơi chưa hỗ trợ mô phỏng.")
    if type(trials) is not int or not 1 <= trials <= 100_000 or type(seed) is not int:
        raise ValueError("Mô phỏng cần 1–100.000 kỳ và seed nguyên.")
    rng, tiers, match_counts, completed, wins = Random(seed), Counter(), Counter(), 0, 0
    for index in range(trials):
        if index % 50 == 0:
            if cancel():
                break
            progress(index, trials)
        draw = random_draw(rule, rng, index+1)
        result = evaluate(rule, ticket, draw)
        tiers.update(result.prize_tiers or ["Không trúng"])
        wins += bool(result.prize_tiers)
        if rule.game_id == "keno":
            match_counts[f"Trùng {result.matched_by_component['main']} số"] += 1
        completed += 1
    progress(completed, trials)
    extra = {"winning_trials": wins} if rule.game_id in EVENT_GAMES else {}
    if rule.game_id == "keno":
        extra["prize_tiers"] = dict(tiers)
    if rule.kind == "triples":
        extra["tiers_overlap"] = True
    return {"status": "completed" if completed == trials else "incomplete", "seed": seed,
            "requested_trials": trials, "completed_trials": completed,
            "tiers": dict(match_counts if rule.game_id == "keno" else tiers), **extra,
            "cost_vnd": ticket.cost_vnd*completed,
            "note": "Dữ liệu mô phỏng, không phải lịch sử thật. Không quan sát thấy giải hiếm không có nghĩa xác suất bằng 0."}
