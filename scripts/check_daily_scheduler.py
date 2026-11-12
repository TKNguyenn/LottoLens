"""Offline scheduler checks; never registers tasks or contacts a provider."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def schedules():
    from app.rules import RULES
    return {"auto_updates": {game: {"enabled": False, "time": "20:00"} for game in RULES},
            "history_limits": {game: 2 for game in RULES}, "language": "vi", "analysis_window": 90}


def check_registration(folder):
    from app import scheduling
    old = schedules()
    new = deepcopy(old)
    new["auto_updates"]["mega"] = {"enabled": True, "time": "21:17"}
    db, prefs = folder / "history & data.sqlite3", folder / "prefs & settings.json"
    registered = []
    tasks = {}

    def run(args, **kwargs):
        assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
        assert kwargs.get("shell", False) is False
        if args[0] == "whoami":
            return subprocess.CompletedProcess(args, 0, '"COMPUTER\\user","S-1-5-21-123"\n', "")
        assert args[0] == "schtasks"
        name = args[args.index("/TN") + 1]
        if "/Query" in args:
            return subprocess.CompletedProcess(args, 0 if name in tasks else 1, tasks.get(name, ""), "")
        if "/Create" in args:
            xml = Path(args[args.index("/XML") + 1]).read_text(encoding="utf-16")
            registered.append((args, xml))
            tasks[name] = xml
        if "/Delete" in args:
            tasks.pop(name, None)
        return subprocess.CompletedProcess(args, 0, "", "")

    with patch.object(scheduling.subprocess, "run", side_effect=run) as process:
        scheduling.configure_schedules(old, db, prefs, old)
        process.assert_not_called()
        legacy = {key: value for key, value in old.items() if key != "auto_updates"}
        scheduling.configure_schedules(legacy, db, prefs, legacy)
        process.assert_not_called()
        invalid = deepcopy(new)
        invalid["auto_updates"]["mega"]["time"] = "24:00"
        try:
            scheduling.configure_schedules(invalid, db, prefs, old)
            raise AssertionError("Invalid times must fail before OS access")
        except ValueError:
            process.assert_not_called()
        scheduling.configure_schedules(new, db, prefs, old)
        assert len(registered) == 1
        args, xml = registered[0]
        ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
        root = ET.fromstring(xml)
        assert root.findtext("t:Triggers/t:CalendarTrigger/t:StartBoundary", namespaces=ns).endswith("T21:17:00+07:00")
        assert root.findtext("t:Principals/t:Principal/t:LogonType", namespaces=ns) == "InteractiveToken"
        assert root.findtext("t:Principals/t:Principal/t:UserId", namespaces=ns) == "S-1-5-21-123"
        assert root.findtext("t:Settings/t:StartWhenAvailable", namespaces=ns) == "false"
        assert root.findtext("t:Settings/t:MultipleInstancesPolicy", namespaces=ns) == "IgnoreNew"
        assert root.findtext("t:Settings/t:Hidden", namespaces=ns) == "true"
        assert root.find("t:Settings/t:RestartOnFailure", ns) is None
        command = root.findtext("t:Actions/t:Exec/t:Command", namespaces=ns)
        assert Path(command).is_absolute() and Path(command).name.lower() == "pythonw.exe"
        actual = root.findtext("t:Actions/t:Exec/t:Arguments", namespaces=ns)
        expected = subprocess.list2cmdline([str(Path(__file__).resolve().with_name("scheduled_sync.py")), "--game", "mega", "--db", str(db.resolve()), "--preferences", str(prefs.resolve())])
        assert actual == expected
        name = args[args.index("/TN") + 1]
        assert "mega" in name and "&" not in name and "/RU" not in args and "/RP" not in args
        scheduling.configure_schedules(new, db, prefs, new)
        assert len(registered) == 2, "Explicit Save must refresh enabled schedules"
        scheduling.configure_schedules(new, folder / "other.sqlite3", prefs, old)
        assert registered[-1][0][registered[-1][0].index("/TN") + 1] == name, "One task per game and preferences profile"

    newer = deepcopy(new)
    newer["auto_updates"]["mega"]["time"] = "22:00"
    newer["auto_updates"]["power"]["enabled"] = True
    ops = []
    snapshot = dict(tasks)

    def fail_second(args, **kwargs):
        if args[0] == "whoami":
            return run(args, **kwargs)
        if "/Query" not in args:
            ops.append(args)
            if len(ops) == 2:
                return subprocess.CompletedProcess(args, 1, "", "private diagnostic")
        return run(args, **kwargs)

    with patch.object(scheduling.subprocess, "run", side_effect=fail_second):
        try:
            scheduling.configure_schedules(newer, db, prefs, new)
            raise AssertionError("Partial registration must fail")
        except RuntimeError as error:
            assert "private diagnostic" not in str(error)
        assert len(ops) >= 4 and any("/Delete" in args for args in ops[2:]), "Restore old schedules after partial failure"
        assert set(tasks) == set(snapshot)
        assert all(ET.tostring(ET.fromstring(tasks[name])) == ET.tostring(ET.fromstring(xml)) for name, xml in snapshot.items())

    with patch.object(scheduling.subprocess, "run", side_effect=run):
        undo = scheduling.configure_schedules(newer, folder / "new target.sqlite3", prefs, new)
        undo()
        assert set(tasks) == set(snapshot), "Undo must restore actual OS snapshots, including the previous DB target"
        assert all(ET.tostring(ET.fromstring(tasks[name])) == ET.tostring(ET.fromstring(xml)) for name, xml in snapshot.items())

    def fail_install_and_restore(args, **kwargs):
        if "/Create" in args:
            return subprocess.CompletedProcess(args, 1, "", "")
        return run(args, **kwargs)

    with patch.object(scheduling.subprocess, "run", side_effect=fail_install_and_restore):
        try:
            scheduling.configure_schedules(newer, db, prefs, new)
            raise AssertionError("Rollback failures must be visible")
        except RuntimeError as error:
            assert "could not be restored" in str(error)


def check_background(folder):
    from app import scheduled_sync
    from app.domain import Draw
    from app.preferences import save_preferences
    from app.rules import BASE, get_rule
    from app.storage import Store
    prefs_path, db = folder / "preferences.json", folder / "scheduled.sqlite3"
    prefs = schedules()
    save_preferences(prefs_path, prefs)
    now = datetime(2026, 11, 11, 18, 0, tzinfo=timezone.utc)

    def receipt(rule, ids=(3, 2, 1)):
        draws = [Draw(rule.game_id, rule.mode_id, rule.rule_version, str(i),
                      f"2026-11-{i:02d}T11:00:00+00:00", {"main": list(range(1, rule.drawn + 1))},
                      BASE + rule.result_path, "2026-11-11T11:00:00+00:00", "a" * 64) for i in ids]
        return {"draws": draws[:2], "status": "requested_limit", "note": "fixture", "source_url": BASE + rule.result_path}

    with patch.object(scheduled_sync, "OfficialSource") as source:
        assert scheduled_sync.run_scheduled("mega", db, prefs_path, now) == 0
        source.assert_not_called()
        prefs["auto_updates"]["mega"]["enabled"] = True
        save_preferences(prefs_path, prefs)
        store = Store(db)
        try:
            store.add_draws(get_rule("mega"), receipt(get_rule("mega"), (2, 1))["draws"])
        finally:
            store.close()
        source.return_value.fetch_history.side_effect = lambda rule, limit, **kwargs: receipt(rule)
        assert scheduled_sync.run_scheduled("mega", db, prefs_path, now) == 0
        assert source.call_args.kwargs["max_attempts"] == 1
        assert scheduled_sync.run_scheduled("mega", db, prefs_path, now) == 0
        assert source.return_value.fetch_history.call_count == 1
        store = Store(db)
        try:
            assert len(store.list_draws(get_rule("mega"))) == 2
            assert store.auto_update_runs()[0]["day"] == "2026-11-12", "Daily claim must use Vietnam date"
        finally:
            store.close()
        later = datetime(2026, 11, 12, 18, 0, tzinfo=timezone.utc)
        source.return_value.fetch_history.side_effect = RuntimeError("secret-api-key must not be recorded")
        assert scheduled_sync.run_scheduled("mega", db, prefs_path, later) == 1
        assert scheduled_sync.run_scheduled("mega", db, prefs_path, later) == 0
        assert source.return_value.fetch_history.call_count == 2
        store = Store(db)
        try:
            runs = store.auto_update_runs()
            assert any(row["status"] == "failed" for row in runs)
            assert "secret-api-key" not in json.dumps(runs)
            assert len(store.list_draws(get_rule("mega"))) == 2
        finally:
            store.close()

        prefs["auto_updates"]["keno"]["enabled"] = True
        save_preferences(prefs_path, prefs)
        source.return_value.fetch_history.side_effect = lambda rule, limit, **kwargs: receipt(rule)
        before = source.return_value.fetch_history.call_count
        assert scheduled_sync.run_scheduled("keno", db, prefs_path, now) == 0
        assert source.return_value.fetch_history.call_count == before + 1
        store = Store(db)
        try:
            for pick in range(1, 11):
                rule = get_rule("keno", "pick" + str(pick))
                assert len(store.list_draws(rule)) == 2
                assert len(store.sync_window(rule, 2)) == 2
        finally:
            store.close()

        def incremental_keno(rule, limit, **kwargs):
            assert rule.mode_id == "pick6"
            assert {draw.draw_id for draw in kwargs["known_draws"]} == {"3", "2"}
            return {**receipt(rule, (4, 3)), "status": "known_boundary"}

        source.return_value.fetch_history.side_effect = incremental_keno
        assert scheduled_sync.run_scheduled("keno", db, prefs_path, later) == 0
        store = Store(db)
        try:
            for pick in range(1, 11):
                rule = get_rule("keno", "pick" + str(pick))
                assert {draw.draw_id for draw in store.list_draws(rule)} == {"4", "3"}
                assert len(store.sync_window(rule, 2)) == 2
            # Legacy/additive edits invalidate one mode's continuity proof.
            rule = get_rule("keno", "pick10")
            store.add_draws(rule, receipt(rule, (4, 3))["draws"])
        finally:
            store.close()

        def refill_keno(rule, limit, **kwargs):
            assert not kwargs["known_draws"], "One unproven mode requires one bounded full fill"
            return receipt(rule, (5, 4))

        source.return_value.fetch_history.side_effect = refill_keno
        assert scheduled_sync.run_scheduled("keno", db, prefs_path, datetime(2026, 11, 14, tzinfo=timezone.utc)) == 0
        store = Store(db)
        try:
            assert all(len(store.sync_window(get_rule("keno", "pick" + str(pick)), 2)) == 2 for pick in range(1, 11))
        finally:
            store.close()

        # Saving disabled while the request is in flight must prevent the commit.
        def disable(rule, limit, **kwargs):
            prefs["auto_updates"]["mega"]["enabled"] = False
            save_preferences(prefs_path, prefs)
            return receipt(rule, (5, 4))

        source.return_value.fetch_history.side_effect = disable
        assert scheduled_sync.run_scheduled("mega", db, prefs_path, datetime(2026, 11, 14, tzinfo=timezone.utc)) == 1
        store = Store(db)
        try:
            assert {draw.draw_id for draw in store.list_draws(get_rule("mega"))} == {"3", "2"}
        finally:
            store.close()

        prefs["auto_updates"]["mega"]["enabled"] = True
        save_preferences(prefs_path, prefs)
        source.return_value.fetch_history.side_effect = lambda rule, limit, **kwargs: receipt(rule, (5, 4))
        apply_sync_many = Store.apply_sync_many

        def disable_during_commit(store, batches, limit, check_cancel):
            checks = 0
            rule = batches[0][0]

            def checked():
                nonlocal checks
                checks += 1
                if checks == 5:
                    assert store.db.in_transaction
                    assert "5" in {draw.draw_id for draw in store.list_draws(rule)}
                    prefs["auto_updates"]["mega"]["enabled"] = False
                    save_preferences(prefs_path, prefs)
                check_cancel()

            return apply_sync_many(store, batches, limit, check_cancel=checked)

        with patch.object(Store, "apply_sync_many", new=disable_during_commit):
            assert scheduled_sync.run_scheduled("mega", db, prefs_path, datetime(2026, 11, 15, tzinfo=timezone.utc)) == 1
        store = Store(db)
        try:
            assert {draw.draw_id for draw in store.list_draws(get_rule("mega"))} == {"3", "2"}, "Disabling inside a transaction must roll back the first new draw too"
        finally:
            store.close()

        # A failure in mode 2 must also roll back mode 1's new retained window.
        source.return_value.fetch_history.side_effect = lambda rule, limit, **kwargs: receipt(rule, (7, 6))
        store = Store(db)
        try:
            store.db.executescript("""
                CREATE TRIGGER fail_second_keno_mode BEFORE INSERT ON draw_revisions
                WHEN NEW.game_id='keno' AND NEW.mode_id='pick2'
                BEGIN SELECT RAISE(ABORT,'fixture write failure'); END;
            """)
        finally:
            store.close()
        day = datetime(2026, 11, 16, tzinfo=timezone.utc)
        before = source.return_value.fetch_history.call_count
        assert scheduled_sync.run_scheduled("keno", db, prefs_path, day) == 1
        assert scheduled_sync.run_scheduled("keno", db, prefs_path, day) == 0
        assert source.return_value.fetch_history.call_count == before + 1
        store = Store(db)
        try:
            assert all({draw.draw_id for draw in store.list_draws(get_rule("keno", "pick" + str(pick)))} == {"5", "4"} for pick in range(1, 11)), "A second-mode SQL failure must roll back every Keno mode"
            assert any(row["game_id"] == "keno" and row["day"] == "2026-11-16" and row["status"] == "failed" for row in store.auto_update_runs())
            store.db.execute("DROP TRIGGER fail_second_keno_mode")
            store.db.commit()
        finally:
            store.close()

        disabled_during_second_mode = False

        def open_with_disable(path):
            store = Store(path)

            def observe(statement):
                nonlocal disabled_during_second_mode
                if statement.startswith("INSERT INTO draw_revisions") and "'keno','pick2'" in statement:
                    disabled_during_second_mode = True
                    prefs["auto_updates"]["keno"]["enabled"] = False
                    save_preferences(prefs_path, prefs)

            store.db.set_trace_callback(observe)
            return store

        day = datetime(2026, 11, 17, tzinfo=timezone.utc)
        before = source.return_value.fetch_history.call_count
        with patch.object(scheduled_sync, "Store", side_effect=open_with_disable):
            assert scheduled_sync.run_scheduled("keno", db, prefs_path, day) == 1
        assert disabled_during_second_mode
        prefs["auto_updates"]["keno"]["enabled"] = True
        save_preferences(prefs_path, prefs)
        assert scheduled_sync.run_scheduled("keno", db, prefs_path, day) == 0
        assert source.return_value.fetch_history.call_count == before + 1
        store = Store(db)
        try:
            assert all({draw.draw_id for draw in store.list_draws(get_rule("keno", "pick" + str(pick)))} == {"5", "4"} for pick in range(1, 11)), "Disabling during the second Keno mode must roll back every mode"
            assert any(row["game_id"] == "keno" and row["day"] == "2026-11-17" and row["status"] == "failed" for row in store.auto_update_runs())
        finally:
            store.close()
    assert "app.ai" not in sys.modules and "app.settings" not in sys.modules, "Background jobs must not import AI/config"


def main():
    with tempfile.TemporaryDirectory(prefix="lottolens schedule ") as directory:
        check_registration(Path(directory))
        check_background(Path(directory))
    print("Daily scheduler checks passed (mocked Windows tasks and provider; temporary SQLite).")


if __name__ == "__main__":
    main()
