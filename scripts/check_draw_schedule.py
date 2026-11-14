"""Check draw-based Windows triggers and background updates without live draws."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain import Draw
from app.draw_schedule import DRAW_MODE, active_slot
from app.preferences import default_preferences, save_preferences
from app.rules import BASE, get_rule
from app.scheduled_sync import run_scheduled
from app.scheduling import VIETNAM, _task_xml
from app.storage import Store


def main():
    body = default_preferences()
    schedule = {"mode": DRAW_MODE, "enabled": True, "time": "20:00"}
    expected = {
        "mega": ("18:45", ("Wednesday", "Friday", "Sunday")),
        "power": ("18:45", ("Tuesday", "Thursday", "Saturday")),
        "max3d": ("18:45", ("Monday", "Wednesday", "Friday")),
        "max3dpro": ("18:45", ("Tuesday", "Thursday", "Saturday")),
    }
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}

    with TemporaryDirectory() as directory:
        folder = Path(directory)
        prefs, database = folder / "preferences.json", folder / "history.sqlite3"
        for game, value in body["auto_updates"].items():
            root = ET.fromstring(_task_xml(game, value, database, prefs, "S-1-5-21-1"))
            jobs = root.findall("t:Triggers/t:CalendarTrigger", ns)
            times = [job.findtext("t:StartBoundary", namespaces=ns)[11:16] for job in jobs]
            if game in expected:
                start, days = expected[game]
                assert times == [start]
                assert tuple(day.tag.split("}")[1] for day in jobs[0].find("t:ScheduleByWeek/t:DaysOfWeek", ns)) == days
            elif game == "lotto":
                assert times == ["13:15", "21:15"]
            else:
                start, interval, duration = {"keno": ("06:12", 8, 945), "bingo18": ("06:13", 6, 949)}[game]
                assert times == [start]
                assert jobs[0].findtext("t:Repetition/t:Interval", namespaces=ns) == f"PT{interval}M"
                assert jobs[0].findtext("t:Repetition/t:Duration", namespaces=ns) == f"PT{duration}M"

        body["auto_updates"]["lotto"] = schedule
        body["history_limits"]["lotto"] = 1
        save_preferences(prefs, body)
        rule = get_rule("lotto")
        url = BASE + rule.result_path
        draws = [Draw(rule.game_id, rule.mode_id, rule.rule_version, str(i), date,
                      {"main": [1, 2, 3, 4, 5], "special": i}, url, date, "a" * 64)
                 for i, date in enumerate(("2026-11-11T17:00:00+00:00", "2026-11-12T17:00:00+00:00",
                                           "2026-11-12T17:00:00+00:00"), 1)]
        morning = datetime(2026, 11, 13, 6, 15, tzinfo=timezone.utc)
        evening = datetime(2026, 11, 13, 14, 15, tzinfo=timezone.utc)
        with patch("app.scheduled_sync.OfficialSource") as source:
            fetch = source.return_value.fetch_history
            assert run_scheduled("lotto", database, prefs, morning.replace(minute=0)) == 0
            fetch.assert_not_called()
            fetch.return_value = {"status": "requested_limit", "draws": [draws[1]]}
            assert run_scheduled("lotto", database, prefs, morning) == 0
            assert run_scheduled("lotto", database, prefs, morning.replace(minute=16)) == 0
            assert fetch.call_count == 1
            fetch.return_value = {"status": "requested_limit", "draws": [draws[0], draws[1]]}
            assert run_scheduled("lotto", database, prefs, evening) == 0
            assert fetch.call_count == 2 and fetch.call_args.args[1] == 2
            with closing(Store(database)) as store:
                assert [row["status"] for row in store.auto_update_runs()] == ["waiting", "success"]
                assert [draw.draw_id for draw in store.list_draws(rule)] == ["2"]

            fetch.return_value = {"status": "requested_limit", "draws": draws[1:]}
            other_database = folder / "evening.sqlite3"
            assert run_scheduled("lotto", other_database, prefs, evening) == 0
            with closing(Store(other_database)) as store:
                assert store.auto_update_runs()[0]["status"] == "success"
                assert [draw.draw_id for draw in store.list_draws(rule)] == ["3"]

        friday = datetime(2026, 11, 13, 18, 45, tzinfo=VIETNAM)
        assert active_slot("mega", schedule, friday) == friday
        assert active_slot("power", schedule, friday) is None
        for game, first, last in (("keno", "06:12", "21:56"), ("bingo18", "06:13", "22:01")):
            start = datetime.fromisoformat("2026-11-13T" + first).replace(tzinfo=VIETNAM)
            end = datetime.fromisoformat("2026-11-13T" + last).replace(tzinfo=VIETNAM)
            assert active_slot(game, schedule, start - timedelta(minutes=1)) is None
            assert active_slot(game, schedule, start) == start
            assert active_slot(game, schedule, end) == end
            assert active_slot(game, schedule, end + timedelta(minutes=5)) is None
        body["auto_updates"]["bingo18"] = schedule
        body["history_limits"]["bingo18"] = 1
        save_preferences(prefs, body)
        rule = get_rule("bingo18")
        draw = Draw(rule.game_id, rule.mode_id, rule.rule_version, "4", "2026-11-12T17:00:00+00:00",
                    {"main": [1, 2, 3]}, BASE + rule.result_path, "2026-11-13T04:00:00+00:00", "a" * 64)
        with patch("app.scheduled_sync.OfficialSource") as source:
            fetch = source.return_value.fetch_history
            fetch.return_value = {"status": "requested_limit", "draws": [draw]}
            assert run_scheduled("bingo18", database, prefs, friday.replace(minute=43)) == 0
            assert run_scheduled("bingo18", database, prefs, friday.replace(minute=44)) == 0
            assert run_scheduled("bingo18", database, prefs, friday.replace(minute=49)) == 0
            assert fetch.call_count == 2
        with closing(Store(database)) as store:
            assert len(store.list_draws(rule)) == 1
            assert next(row for row in store.auto_update_runs(latest_only=True) if row["game_id"] == "bingo18")["status"] == "waiting"
    print("Draw schedules passed: seven Windows trigger plans, Vietnam slots, duplicate protection and Lotto evening publication.")


if __name__ == "__main__":
    main()
