"""Offline UI checks; existing tests/ stays immutable. Run from the project root."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from random import Random
from threading import Event
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtGui import QFontDatabase
from app.theme import LIGHT, DARK, build_qss
from app.components import BallDelegate, BallLabel, NumberHeatmap, SourceDelegate
from app.domain import Draw
from app.rules import BASE, get_rule


def check_page(window):
    for _ in range(3):
        QApplication.processEvents()
    scroll = window.pages.currentWidget()
    assert scroll.horizontalScrollBar().maximum() == 0
    for label in scroll.widget().findChildren(QLabel):
        if label.isVisibleTo(window) and label.wordWrap():
            assert label.height() + 1 >= label.heightForWidth(label.width()), (window.game.currentData(), window.pages.currentIndex(), label.text()[:60], label.size(), label.heightForWidth(label.width()))
    for button in scroll.widget().findChildren(QPushButton):
        if button.isVisibleTo(window):
            assert button.x() >= 0 and button.geometry().right() < button.parentWidget().width(), (window.pages.currentIndex(), button.text())


def main():
    app = QApplication.instance() or QApplication([])
    # Windows' offscreen Qt plugin has no system font database.
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "CascadiaMono.ttf"):
            font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name
            if font.exists():
                QFontDatabase.addApplicationFont(str(font))
    for tokens in (LIGHT, DARK):
        assert tokens["red"] in build_qss(tokens)
        for size in (22, 26, 42, 52):
            for variant in ("normal", "hit", "gold"):
                ball = BallLabel(7, size=size, variant=variant)
                assert ball.size().width() == size
                assert not ball.grab().isNull()
        heat = NumberHeatmap()
        heat.set_data({n: n % 9 for n in range(1, 46)})
        heat.resize(450, heat.heightForWidth(450))
        assert not heat.grab().isNull()
    from app.ui import Desktop
    assert SourceDelegate.source_text("manual:csv") == "Nhập CSV"
    assert SourceDelegate.source_text("https://vietlott.vn/example") == "Xem nguồn ↗"
    groups = {key: [f"{i:03}" for i in range(count)] for key, count in (("special", 2), ("first", 4), ("second", 6), ("third", 8))}
    assert len(BallDelegate.groups(json.dumps(groups))) == 4
    assert BallDelegate.row_height(json.dumps(groups), 300) >= 210
    with tempfile.TemporaryDirectory() as directory, ExitStack() as cleanup:
        folder = Path(directory)
        with patch("app.ui.OfficialSource.fetch_history", side_effect=AssertionError("startup network")), patch("app.ai._send", side_effect=AssertionError("startup AI")):
            window = Desktop(folder / "history.sqlite3", folder / "config.json")
            cleanup.callback(window.close)
            window.show()
            for theme in ("dark", "light", "dark", "light"):
                window.set_theme(theme, persist=True)
                assert window.theme_name == theme
                assert json.loads((folder / "theme.json").read_text())["theme"] == theme
                assert not (folder / "config.json").exists()
                for size in ((1000, 700), (1920, 1080)):
                    window.resize(*size)
                    for game in range(window.game.count()):
                        window.game.setCurrentIndex(game)
                        for page in range(window.pages.count()):
                            window.nav.setCurrentRow(page)
                            app.processEvents()
                            assert window.pages.currentIndex() == page
                            scroll = window.pages.currentWidget()
                            assert scroll.horizontalScrollBar().maximum() == 0, (theme, size, game, page)
                            check_page(window)
            rng = Random(42)
            for game in ("mega", "power", "lotto", "keno", "max3d", "max3dpro", "bingo18"):
                rule = get_rule(game)
                draws = []
                for i in range(95 if rule.kind == "set" else 3):
                    payload = {"groups": groups} if rule.kind == "triples" else {"main": sorted(rng.sample(range(1, rule.population + 1), rule.drawn)) if rule.kind == "set" else [1, 2, 3]}
                    if rule.special_max:
                        payload["special"] = next(n for n in range(1, rule.special_max + 1) if n not in payload["main"]) if rule.bonus_from_remainder else 1
                    at = (datetime(2026, 11, 7, 17, tzinfo=timezone.utc) - timedelta(days=95-i)).isoformat()
                    draws.append(Draw(game, rule.mode_id, rule.rule_version, str(i+1), at, payload, BASE + rule.result_path, at, "a" * 64))
                window.store.add_draws(rule, draws)
            for language in ("en", "vi"):
                window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                for size in ((1000, 700), (1920, 1080)):
                    window.resize(*size)
                    for game in range(window.game.count()):
                        window.game.setCurrentIndex(game)
                        for page in range(window.pages.count()):
                            window.nav.setCurrentRow(page); app.processEvents()
                            scroll = window.pages.currentWidget()
                            assert scroll.horizontalScrollBar().maximum() == 0, ("populated", language, size, game, page)
                            check_page(window)
                        if window.rule.kind == "triples":
                            assert window.history_table.rowHeight(0) >= 210
            window.game.setCurrentIndex(0)
            window.method.setCurrentIndex(window.method.findData("bayes90_v1"))
            window.target.setText("96"); window.make_suggestions()
            assert window.suggestion_table.rowCount() == 5
            assert window.save_button.isEnabled()
            original = (window.generated, window.explanation.toPlainText(), window.target.text())
            for theme in ("dark", "light"):
                window.set_theme(theme)
                assert (window.generated, window.explanation.toPlainText(), window.target.text()) == original
            window.window_size.setCurrentIndex(1)
            assert window.stats_metrics[0].value.text() == "30"
            window.history_search.setText("no-such-draw")
            assert all(window.history_table.isRowHidden(i) for i in range(95))
            window.history_search.clear()
            assert not any(window.history_table.isRowHidden(i) for i in range(95))
            window.key.setText("temporary-qa-key")
            window.toggle_key(); assert window.key.echoMode() == window.key.EchoMode.Normal
            window.toggle_key(); assert window.key.echoMode() == window.key.EchoMode.Password
            started, release = Event(), Event()
            def offline(*args, **kwargs):
                started.set(); release.wait(2); raise OSError("Offline QA")
            with patch("app.ui.OfficialSource.fetch_history", side_effect=offline) as request:
                window.sync(); assert started.wait(2)
                for widget in (window.game, window.count, window.target, window.query, window.verify_method, window.stats_segments):
                    assert not widget.isEnabled()
                release.set()
                deadline = time.monotonic() + 5
                while window.worker and time.monotonic() < deadline:
                    app.processEvents(); time.sleep(.01)
                assert window.worker is None
                assert "Offline QA" in window.notice.text()
                assert request.call_count == 1
                assert window.count.isEnabled() and window.query.isEnabled()
            incomplete = {"status": "incomplete", "draws": [replace(window.draws[-1], draw_id="96")], "note": "incomplete fixture"}
            with patch("app.ui.OfficialSource.fetch_history", return_value=incomplete):
                window.sync()
                deadline = time.monotonic() + 5
                while window.worker and time.monotonic() < deadline:
                    app.processEvents(); time.sleep(.01)
                assert window.worker is None
                assert len(window.store.list_draws(get_rule("mega"))) == 95, "Incomplete history must not be stored"
            from app.ui import draw_date
            assert draw_date(Draw("mega", "normal", "v1", "1", "2026-11-07T17:00:00+00:00", {}, "", "", "")) == "08/11/2026"
            window.close()
    print("Redesign OK: painted components; empty/populated 7 games x 8 pages at 1000x700/1920x1080, populated VI/EN; themes preserve state; sources/dates/groups; offline failure restores inputs; incomplete history not stored; no retry/startup requests.")


if __name__ == "__main__":
    main()
