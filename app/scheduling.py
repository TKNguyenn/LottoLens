"""Opt-in Windows daily tasks scoped to this preferences profile."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from .rules import RULES

VIETNAM = timezone(timedelta(hours=7))
_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"


def _settings(preferences):
    values = preferences.get("auto_updates", {game: {"enabled": False, "time": "20:00"} for game in RULES})
    if not isinstance(values, dict) or set(values) != set(RULES):
        raise ValueError("Invalid automatic-update games.")
    for value in values.values():
        if (not isinstance(value, dict) or set(value) != {"enabled", "time"}
                or type(value["enabled"]) is not bool or not isinstance(value["time"], str)
                or re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value["time"]) is None):
            raise ValueError("Automatic-update time must be HH:MM and enabled must be boolean.")
    return values


def _run(arguments):
    return subprocess.run(arguments, capture_output=True, text=True, check=False,
                          creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)


def _task_name(preferences_path, game):
    identity = os.path.normcase(str(Path(preferences_path).resolve()))
    return "LottoLensDaily-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20] + "-" + game


def _task_xml(game, value, db_path, preferences_path, sid):
    script = Path(__file__).resolve().parents[1] / "scripts" / "scheduled_sync.py"
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        arguments = ["--scheduled"]
        working_directory = executable.parent
    else:
        executable = Path(sys.executable).resolve().with_name("pythonw.exe")
        if not executable.is_file():
            raise RuntimeError("Daily updates require pythonw.exe beside the current Python interpreter.")
        arguments = [str(script)]
        working_directory = script.parent.parent
    ET.register_namespace("", _NS)
    root = ET.Element("Task", {"xmlns": _NS, "version": "1.2"})

    def child(parent, name, value=None, **attributes):
        item = ET.SubElement(parent, name, attributes)
        if value is not None:
            item.text = value
        return item

    info = child(root, "RegistrationInfo")
    child(info, "Description", "LottoLens daily official-history update (Vietnam UTC+7).")
    trigger = child(child(root, "Triggers"), "CalendarTrigger")
    day = datetime.now(VIETNAM).date().isoformat()
    child(trigger, "StartBoundary", day + "T" + value["time"] + ":00+07:00")
    child(trigger, "Enabled", "true")
    child(child(trigger, "ScheduleByDay"), "DaysInterval", "1")
    principal = child(child(root, "Principals"), "Principal", id="CurrentUser")
    child(principal, "UserId", sid)
    child(principal, "LogonType", "InteractiveToken")
    child(principal, "RunLevel", "LeastPrivilege")
    settings = child(root, "Settings")
    for name, value in (("MultipleInstancesPolicy", "IgnoreNew"),
                        ("DisallowStartIfOnBatteries", "false"), ("StopIfGoingOnBatteries", "false"),
                        ("StartWhenAvailable", "false"), ("RunOnlyIfNetworkAvailable", "false"),
                        ("Enabled", "true"), ("Hidden", "true"), ("WakeToRun", "false"),
                        ("ExecutionTimeLimit", "PT2H")):
        child(settings, name, value)
    action = child(child(root, "Actions", Context="CurrentUser"), "Exec")
    child(action, "Command", str(executable))
    child(action, "Arguments", subprocess.list2cmdline(arguments + ["--game", game,
          "--db", str(Path(db_path).resolve()), "--preferences", str(Path(preferences_path).resolve())]))
    child(action, "WorkingDirectory", str(working_directory))
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _write_task(name, xml):
    if xml is None:
        result = _run(["schtasks", "/Delete", "/TN", name, "/F"])
        if result.returncode and _run(["schtasks", "/Query", "/TN", name, "/XML"]).returncode:
            return  # An absent task is already removed.
    else:
        with tempfile.TemporaryDirectory(prefix="lottolens-task-") as directory:
            path = Path(directory) / "task.xml"
            path.write_text('<?xml version="1.0" encoding="UTF-16"?>\n' + xml, encoding="utf-16")
            result = _run(["schtasks", "/Create", "/TN", name, "/XML", str(path), "/F"])
    if result.returncode:
        raise RuntimeError("Windows Task Scheduler rejected a daily schedule.")


def configure_schedules(preferences, db_path, preferences_path, previous_preferences):
    """Install enabled jobs on explicit Save; restore touched jobs after failure."""
    current, previous = _settings(preferences), _settings(previous_preferences)
    games = [game for game in RULES if current[game]["enabled"] or previous[game]["enabled"]]
    if not games:
        return lambda: None
    if os.name != "nt":
        raise RuntimeError("Daily automatic updates require Windows Task Scheduler.")
    result = _run(["whoami", "/user", "/fo", "csv", "/nh"])
    rows = list(csv.reader(result.stdout.splitlines()))
    if result.returncode or len(rows) != 1 or len(rows[0]) != 2 or not re.fullmatch(r"S-[0-9-]+", rows[0][1]):
        raise RuntimeError("Cannot identify the current Windows user for daily updates.")
    sid = rows[0][1]
    snapshots = {}
    for game in games:
        name = _task_name(preferences_path, game)
        result = _run(["schtasks", "/Query", "/TN", name, "/XML"])
        if result.returncode:
            snapshots[game] = None
        else:
            try:
                snapshots[game] = ET.tostring(ET.fromstring(result.stdout), encoding="unicode")
            except ET.ParseError as error:
                raise RuntimeError("Cannot read an existing daily schedule; no schedules changed.") from error
    touched = []

    def restore():
        failures = []
        for game in reversed(touched):
            try:
                _write_task(_task_name(preferences_path, game), snapshots[game])
            except Exception:
                failures.append(game)
        if failures:
            raise RuntimeError("Could not restore daily schedules for " + ", ".join(failures) + "; save settings again to repair them.")

    try:
        for game in games:
            touched.append(game)
            xml = _task_xml(game, current[game], db_path, preferences_path, sid) if current[game]["enabled"] else None
            _write_task(_task_name(preferences_path, game), xml)
    except Exception as error:
        try:
            restore()
            restored = True
        except Exception:
            restored = False
        detail = " Previous schedules were restored." if restored else " Some previous schedules could not be restored; save settings again to repair them."
        raise RuntimeError("Could not save Windows daily schedules." + detail) from error
    return restore
