"""Entry point for the desktop app, analysis CLI and separate design preview."""
import argparse
from dataclasses import asdict
from fractions import Fraction
from getpass import getpass
import json
from pathlib import Path
from random import SystemRandom
import runpy
import sys

from app.ai import AIConfig, search
from app.backtest import run_backtest
from app.domain import Ticket
from app.generation import generate, METHODS, explain_ticket
from app.probability import probabilities, overlap_probabilities
from app.rules import RULES, get_rule
from app.settings import CONFIG_PATH, load_settings, save_settings
from app.simulation import simulate
from app.sources import CancelledError, OfficialSource, import_csv
from app.statistics import describe
from app.storage import Store

ROOT = Path(__file__).resolve().parent


def output(value):
    def serialize(item):
        if isinstance(item, Fraction):
            return {"numerator": item.numerator, "denominator": item.denominator, "decimal": float(item)}
        raise TypeError(type(item).__name__)
    print(json.dumps(value, ensure_ascii=False, indent=2, default=serialize))


def parser():
    root = argparse.ArgumentParser(description="Vietlott Desktop: ứng dụng máy tính và lõi phân tích.")
    root.add_argument("--db", type=Path, help="Database riêng; mặc định dùng LocalAppData/VietlottDesktop.")
    sub = root.add_subparsers(dest="command")
    preview = sub.add_parser("preview", help="Mở prototype độc lập, chưa nối dữ liệu thật.")
    preview.add_argument("--screenshot", type=Path)
    sub.add_parser("self-check", help="Kiểm tra nội bộ, không gọi API hoặc website.")
    for name in ("sync", "history", "stats", "odds", "generate", "backtest", "simulate", "import-csv"):
        command = sub.add_parser(name)
        command.add_argument("--game", choices=tuple(RULES), default="mega")
        command.add_argument("--mode", help="Ví dụ Keno pick1 đến pick10.")
        if name == "sync":
            command.add_argument("--limit", type=int, default=30)
        if name == "import-csv":
            command.add_argument("file", type=Path)
        if name in ("odds", "simulate"):
            command.add_argument("--numbers", help="Các số cách nhau bằng khoảng trắng; bỏ trống dùng vé minh họa 1..s.")
            command.add_argument("--special", type=int, default=1)
        if name == "generate":
            command.add_argument("--count", type=int, default=5)
            command.add_argument("--method", choices=METHODS, default="bayes90_v1")
            command.add_argument("--target-draw", help="Có mã kỳ đích thì lưu gợi ý, chưa có thì chỉ xuất.")
        if name in ("backtest", "simulate"):
            command.add_argument("--seed", type=int, default=42)
        if name == "simulate":
            command.add_argument("--trials", type=int, default=10_000)
    setup = sub.add_parser("configure-ai", help="Nhập key tại máy và lưu JSON, không gọi nhà cung cấp.")
    setup.add_argument("--config", type=Path, default=CONFIG_PATH)
    setup.add_argument("--base-url", default=AIConfig().base_url)
    setup.add_argument("--model", default="gpt-6.1-sol")
    ai = sub.add_parser("search", help="Gửi một yêu cầu Responses có web search và streaming.")
    ai.add_argument("query")
    ai.add_argument("--config", type=Path, default=CONFIG_PATH)
    return root


def run(args):
    if args.command is None:
        from app.ui import main as desktop_main
        return desktop_main(args.db)
    if args.command == "preview":
        sys.argv = [str(ROOT/"docs"/"prototype"/"desktop_preview.py")]
        if getattr(args, "screenshot", None):
            sys.argv.extend(["--screenshot", str(args.screenshot)])
        runpy.run_path(str(ROOT/"docs"/"prototype"/"desktop_preview.py"), run_name="__main__")
        return
    if args.command == "self-check":
        assert overlap_probabilities(45, 6, 6)[6] == Fraction(1, 8_145_060)
        assert sum(overlap_probabilities(55, 6, 6).values()) == 1
        output({"status": "passed", "scope": "math/import only", "provider_called": False})
        return
    if args.command == "configure-ai":
        config = AIConfig(base_url=args.base_url, model=args.model, api_key=getpass("API key (lưu trong JSON tại máy): "))
        if not config.api_key.strip():
            raise ValueError("Key trống; chưa ghi thay đổi.")
        save_settings(config, args.config)
        output({"saved": str(args.config), "endpoint": config.base_url.rstrip("/")+"/responses", "stream": True})
        return
    if args.command == "search":
        streamed = []
        def on_delta(chunk):
            streamed.append(chunk); print(chunk, end="", flush=True)
        result = search(load_settings(args.config), args.query, on_delta=on_delta)
        if streamed:
            print()
        else:
            print(result["text"])
        output({"sources": result["sources"], "notice": result["notice"]})
        return
    rule = get_rule(args.game, args.mode)
    if args.command in ("odds", "simulate"):
        selected = [int(x) for x in args.numbers.split()] if args.numbers else list(range(1, rule.selected+1))
        choices = {"main": selected}
        if rule.game_id == "lotto":
            choices["special"] = args.special
        ticket = Ticket(rule.game_id, rule.mode_id, rule.rule_version, choices, cost_vnd=rule.price_vnd)
        if args.command == "odds":
            output({"ticket": choices, "probabilities": probabilities(rule, ticket),
                    "assumption": "Quay công bằng, đúng mô hình luật hiện tại. Vé tự điền 1..s chỉ để minh họa."})
        else:
            output(simulate(rule, ticket, args.trials, args.seed))
        return
    store = Store(args.db)
    try:
        if args.command == "sync":
            receipt = OfficialSource(store.path.parent/"source-cache").fetch_history(rule, args.limit)
            stats = store.add_draws(rule, receipt.pop("draws"))
            output({**stats, **receipt, "stored_draws": len(store.list_draws(rule))})
        elif args.command == "import-csv":
            with args.file.open("rb") as stream:
                raw = stream.read(20*1024*1024+1)
            output(store.add_draws(rule, import_csv(raw, rule)))
        elif args.command == "history":
            output([asdict(draw) for draw in store.list_draws(rule)])
        elif args.command == "stats":
            output(describe(rule, store.list_draws(rule)))
        elif args.command == "generate":
            history = store.list_draws(rule)
            tickets = generate(rule, history, args.count, args.method, SystemRandom())
            if args.target_draw:
                store.save_suggestions(rule, tickets, args.target_draw, args.method, store.snapshot(rule, history))
            output({"tickets": [asdict(ticket) for ticket in tickets], "history_count": len(history),
                    "explanations": [explain_ticket(rule, history, ticket, args.method) for ticket in tickets],
                    "saved": bool(args.target_draw), "notice": "Bộ số tham khảo, chưa có bằng chứng tăng xác suất trúng."})
        elif args.command == "backtest":
            report = run_backtest(rule, store.list_draws(rule), {"seed": args.seed})
            report_id = store.save_report(report)
            report = store.reports()[0]
            output({"report_id": report_id, **{k: v for k, v in report.items() if k != "rows"}})
    finally:
        store.close()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        run(parser().parse_args())
        return 0
    except (ValueError, OSError, CancelledError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Đã hủy thao tác. Yêu cầu AI đã gửi có thể vẫn được tính phí.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
