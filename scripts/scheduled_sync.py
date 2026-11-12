"""Task Scheduler entry point. This helper deliberately does not load the GUI."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rules import RULES
from app.scheduled_sync import run_scheduled


def main():
    parser = argparse.ArgumentParser(description="One opt-in LottoLens daily history update.")
    parser.add_argument("--game", required=True, choices=tuple(RULES))
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--preferences", required=True, type=Path)
    args = parser.parse_args()
    result = run_scheduled(args.game, args.db, args.preferences)
    # pythonw has no standard output stream; Task Scheduler receives the exit code.
    if sys.stdout is not None:
        print("Daily history update finished." if result == 0 else "Daily history update failed; no automatic retry.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
