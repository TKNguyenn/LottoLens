from collections import defaultdict
from dataclasses import asdict
from datetime import timedelta, timezone
from math import ceil
from random import Random

from . import __version__
from .domain import aware_time, digest, snapshot_hash, validate_draw
from .evaluation import evaluate, FIXED
from .generation import generate, METHODS


def _seed(master, label):
    return int(digest([master, label])[:16], 16)


def _interval(rows, count, draws_per_target, seed):
    days = defaultdict(lambda: [0., 0])
    for row in rows:
        day = aware_time(row["draw_at_utc"]).astimezone(timezone(timedelta(hours=7))).date().isoformat()
        days[day][0] += row["strategy_wins"] - row["baseline_mean_wins"]
        days[day][1] += draws_per_target
    if len(days) < 30:
        return {"value": None, "reason": "Chưa đủ 30 block ngày cho khoảng bootstrap ổn định.", "days": len(days)}
    values = list(days.values())
    rng, samples = Random(seed), []
    for _ in range(count):
        chosen = [values[rng.randrange(len(values))] for _ in values]
        samples.append(sum(x[0] for x in chosen)/sum(x[1] for x in chosen))
    samples.sort()
    return {"value": [samples[int(.025*(count-1))], samples[int(.975*(count-1))]],
            "days": len(days), "resamples": count, "method": "paired_day_block_bootstrap"}


def run_backtest(rule, draws, config, cancel=lambda: False, progress=lambda done, total: None):
    if rule.game_id not in FIXED:
        raise ValueError("Backtest theo hạng giải hiện chỉ bật Mega, Power, Lotto cơ bản.")
    config = {"tickets_per_draw": 5, "baseline_runs": 200, "seed": 42,
              "bootstrap_runs": 2000, "method": "frequency90_laplace1_v1", "history_window": 90, **config}
    for name, maximum in (("tickets_per_draw", 100), ("baseline_runs", 2000), ("bootstrap_runs", 10_000), ("history_window", 2000)):
        if type(config[name]) is not int or not 1 <= config[name] <= maximum:
            raise ValueError(f"Tham số {name} nằm ngoài giới hạn.")
    if type(config["seed"]) is not int or config["method"] not in METHODS:
        raise ValueError("Seed hoặc phương pháp không hợp lệ.")
    ordered = sorted(draws, key=lambda d: (aware_time(d.draw_at_utc), int(d.draw_id) if d.draw_id.isdigit() else 0, d.draw_id))
    for draw in ordered:
        validate_draw(rule, draw)
    if len({d.draw_id for d in ordered}) != len(ordered):
        raise ValueError("Backtest chứa kỳ trùng; chỉ dùng một revision mỗi kỳ.")
    history_window = config["history_window"]
    targets = len(ordered)-history_window
    if targets < 1:
        raise ValueError(f"Cần ít nhất {history_window+1} kỳ cùng luật để kiểm chứng sau warm-up {history_window} kỳ.")
    holdout_count = max(50, ceil(.2*targets)) if targets >= 100 else 0
    count, baseline_runs, seed = config["tickets_per_draw"], config["baseline_runs"], config["seed"]
    manifest = {"game_id": rule.game_id, "mode_id": rule.mode_id, "rule_version": rule.rule_version,
                "dataset_hash": digest([asdict(d) for d in ordered]), "config": config,
                "input_snapshot": {"hash": snapshot_hash(asdict(rule), [asdict(d) for d in ordered]),
                                   "draws": [asdict(d) for d in ordered], "rule": asdict(rule)},
                "app_version": __version__, "warmup": history_window, "holdout_count": holdout_count,
                "holdout_ids": [d.draw_id for d in ordered[-holdout_count:]] if holdout_count else [],
                "history_provenance": "reconstructed_from_current_snapshots", "seed_algorithm": "Python random.Random + SHA256 substreams",
                "historical_rule_effectivity_verified": bool(rule.effective_from)}
    rows = []
    generation_options = {"history_window": history_window} if history_window != 90 else {}
    for offset, target in enumerate(ordered[history_window:]):
        if cancel():
            break
        previous = ordered[:history_window+offset]
        tickets = generate(rule, previous, count, config["method"], Random(_seed(seed, ["strategy", target.draw_id])), **generation_options)
        strategy = [evaluate(rule, ticket, target) for ticket in tickets]
        baseline = []
        aborted = False
        for repeat in range(baseline_runs):
            if cancel():
                aborted = True; break
            random_tickets = generate(rule, previous, count, "uniform_v1", Random(_seed(seed, ["baseline", repeat, target.draw_id])), **generation_options)
            baseline.append(sum(bool(evaluate(rule, ticket, target).prize_tiers) for ticket in random_tickets))
        if aborted:
            break
        rows.append({"target_draw_id": target.draw_id, "draw_at_utc": target.draw_at_utc,
                     "phase": "holdout" if holdout_count and offset >= targets-holdout_count else "development",
                     "history_cutoff": previous[-1].draw_id, "history_count": len(previous),
                     "tickets": [ticket.selections for ticket in tickets], "cost_vnd": count*rule.price_vnd,
                     "strategy_wins": sum(bool(result.prize_tiers) for result in strategy),
                     "baseline_mean_wins": sum(baseline)/len(baseline), "baseline_wins": baseline,
                     "payout_vnd": sum(result.payout_vnd for result in strategy) if all(result.payout_vnd is not None for result in strategy) else None})
        progress(offset+1, targets)
    complete = len(rows) == targets
    summary = {}
    for phase in ("development", "holdout"):
        phase_rows = [row for row in rows if row["phase"] == phase]
        if not phase_rows:
            continue
        total = len(phase_rows)*count
        strategy_rate = sum(row["strategy_wins"] for row in phase_rows)/total
        baseline_rates = sorted(sum(row["baseline_wins"][i] for row in phase_rows)/total for i in range(baseline_runs))
        baseline_mean = sum(baseline_rates)/baseline_runs
        summary[phase] = {"draws": len(phase_rows), "tickets": total, "strategy_win_rate": strategy_rate,
                          "baseline_mean_win_rate": baseline_mean, "difference": strategy_rate-baseline_mean,
                          "baseline_95_range": [baseline_rates[int(.025*(baseline_runs-1))], baseline_rates[int(.975*(baseline_runs-1))]],
                          "difference_interval": _interval(phase_rows, config["bootstrap_runs"], count, _seed(seed, phase))}
    return {"status": "completed" if complete else "incomplete", "manifest": manifest, "rows": rows,
            "summary": summary, "assessment": "holdout_report_no_advantage_claim" if holdout_count and complete else "exploratory_only",
            "conclusion": "Chưa có bằng chứng phương pháp làm tăng xác suất trúng. Báo cáo này không tự xác nhận lợi thế.",
            "limitations": ["Lịch sử hiện tại có thể đã sửa; mốc công bố và ngày hiệu lực luật chưa xác minh đầy đủ.",
                            "Lợi nhuận/EV không được suy từ jackpot hiện tại; payout thiếu giữ unknown.",
                            "Chạy lại holdout sau khi chỉnh phương pháp là thăm dò, không phải xác nhận độc lập."]}
