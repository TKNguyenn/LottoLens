"""Offline checks for fast-game source selection, pacing and HTTP 429 cooldown."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.preferences import default_preferences, save_preferences
from app.rules import BASE, get_rule
from app.scheduled_sync import run_scheduled
from app.scheduling import VIETNAM
from app.sources import CancelledError, OfficialSource, parse_results
from app.storage import Store


def source_checks():
    fixtures = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    for game, fixture in (("keno", "keno_results.html"), ("bingo18", "bingo_results.html")):
        rule = get_rule(game)
        raw = (fixtures / fixture).read_bytes()
        url = BASE + rule.result_path
        known = parse_results(raw, rule, url)
        source = OfficialSource(max_attempts=1)
        clock, starts = [100.0], []
        response = MagicMock()
        response.__enter__.return_value = response
        response.url, response.read.return_value = url, raw

        def request(req, **kwargs):
            starts.append(clock[0])
            assert req.full_url == url
            return response

        def sleep(seconds):
            clock[0] += seconds

        with patch("app.sources.urlopen", side_effect=request), patch("app.sources.time.monotonic", side_effect=lambda: clock[0]), patch("app.sources.time.sleep", side_effect=sleep):
            receipt = source.fetch_history(rule, 1, known_draws=known)
            assert receipt["status"] == "known_boundary" and len(starts) == 1
            assert receipt["source_url"] == url
            source._request(url)
            assert len(starts) == 2 and starts[1] - starts[0] >= 2
            before = len(starts)
            try:
                source._request(url, cancel=lambda: clock[0] >= starts[-1] + .5)
            except CancelledError:
                pass
            else:
                raise AssertionError("Pacing must remain cancellable")
            assert len(starts) == before

        for attempts in (1, 3):
            source = OfficialSource(max_attempts=attempts)
            with patch("app.sources.urlopen", side_effect=HTTPError(url, 429, "rate limited", {"Retry-After": "7200"}, None)) as request:
                try:
                    source.fetch_history(rule, 1)
                except ValueError as error:
                    assert "HTTP 429" in str(error)
                    assert error.retry_at >= datetime.now(timezone.utc) + timedelta(seconds=7190)
                else:
                    raise AssertionError("429 must stop the fetch")
                assert request.call_count == 1

    source = OfficialSource(max_attempts=1)
    rule = get_rule("mega")
    raw = (fixtures / "mega_results.html").read_bytes()
    with patch.object(source, "_request", return_value=raw) as request:
        source.fetch_history(rule, 1)
        assert request.call_args.args[0] == BASE + rule.result_path


def cooldown_checks():
    with TemporaryDirectory() as directory:
        prefs, database = Path(directory) / "prefs.json", Path(directory) / "history.sqlite3"
        body = default_preferences()
        for game in ("keno", "bingo18"):
            body["auto_updates"][game]["enabled"] = True
        save_preferences(prefs, body)
        now = datetime(2026, 11, 13, 13, 24, tzinfo=VIETNAM)
        with patch("app.scheduled_sync.OfficialSource") as source:
            fetch = source.return_value.fetch_history
            fetch.side_effect = ValueError("Nguồn Vietlott trả HTTP 429; không thay đổi dữ liệu cũ.")
            assert run_scheduled("keno", database, prefs, now) == 1
            assert run_scheduled("keno", database, prefs, now) == 0
            for minute in (25, 31, 37, 43, 49, 55):
                assert run_scheduled("bingo18", database, prefs, now.replace(minute=minute)) == 0
            assert run_scheduled("keno", database, prefs, now.replace(minute=32)) == 0
            assert run_scheduled("bingo18", database, prefs, now.replace(hour=14, minute=19)) == 0
            assert fetch.call_count == 1, "429 cooldown must cover both fast games and survive new worker processes"
            with closing(Store(database)) as store:
                assert len(store.auto_update_runs()) == 1
                assert not store.list_draws(get_rule("keno"))
            fetch.side_effect = None
            fetch.return_value = {"status": "requested_limit", "draws": []}
            assert run_scheduled("bingo18", database, prefs, now.replace(hour=14, minute=25)) == 0
            assert fetch.call_count == 2


def retry_after_checks():
    from app.sources import RateLimitError
    from app.scheduled_sync import _failure_message
    now = datetime(2026, 11, 13, 6, 24, tzinfo=timezone.utc)
    for header, seconds in (("", 3600), ("120", 3600), ("7200", 7200),
                            ("invalid", 3600), ("9" * 100, 3600),
                            (format_datetime(now + timedelta(hours=3), usegmt=True), 10800)):
        with patch("app.sources.datetime") as clock:
            clock.now.return_value = now
            error = RateLimitError(header)
        assert error.retry_at == now + timedelta(seconds=seconds)
        assert _failure_message(error) == str(error) and "HTTP 429" in str(error)
    with TemporaryDirectory() as directory:
        prefs, database = Path(directory) / "prefs.json", Path(directory) / "history.sqlite3"
        body = default_preferences()
        for game in ("keno", "bingo18"):
            body["auto_updates"][game]["enabled"] = True
        save_preferences(prefs, body)
        with patch("app.sources.datetime") as clock:
            clock.now.return_value = now
            error = RateLimitError("7200")
        with patch("app.scheduled_sync.OfficialSource") as source:
            fetch = source.return_value.fetch_history
            fetch.side_effect = error
            assert run_scheduled("keno", database, prefs, now) == 1
            assert run_scheduled("bingo18", database, prefs, now.replace(hour=7, minute=55)) == 0
            assert fetch.call_count == 1, "Server Retry-After must survive a new scheduler process"
            fetch.side_effect = None
            fetch.return_value = {"status": "requested_limit", "draws": []}
            assert run_scheduled("bingo18", database, prefs, now.replace(hour=8, minute=25)) == 0
            assert fetch.call_count == 2


def translation_checks():
    from app.i18n import set_language, tr
    from app.ui import Desktop
    row = {"game_id": "keno", "day": "2026-11-13 13:24", "message": "HTTP 429"}
    hint = Desktop.schedule_failure_hint(None, row)
    try:
        set_language("en")
        assert "one hour" in tr(hint) and "Retry-After" in tr(hint)
        message = "Nguồn Vietlott trả HTTP 429; không thay đổi dữ liệu cũ. Chờ đến 2026-11-13T15:24:00+07:00."
        assert "Wait until 2026-11-13T15:24:00+07:00" in tr(message)
    finally:
        set_language("vi")


if __name__ == "__main__":
    source_checks()
    cooldown_checks()
    retry_after_checks()
    translation_checks()
    print("Fast sync passed: default URL, incremental head, cancellable pacing, single HTTP attempt, one-hour cooldown and persisted Retry-After.")
