"""Offline checks for GitHub release discovery and installer integrity."""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import __version__
from app.updates import RELEASE_API, RELEASE_PAGE, check_release, download_setup
from app.preferences import default_preferences, validate_preferences
from app.sources import CancelledError


def check_ui(directory, release):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QFontDatabase
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.ui import Desktop

    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")

    def wait_for_idle(worker="update_check_worker"):
        for _ in range(100):
            if getattr(window, worker) is None:
                app.processEvents()
                return
            QTest.qWait(10)
        raise AssertionError("Update check did not finish")

    window = Desktop(directory / "history.db", directory / "config.json")
    try:
        window.show()
        window.activateWindow()
        assert QTest.qWaitForWindowActive(window, 1500)
        app.processEvents()
        button, toggle = window.check_updates_button, window.theme_button
        assert button.text() == "Kiểm tra cập nhật" and not toggle.text()
        assert button.geometry().right() < toggle.geometry().left()
        window.apply_language("en")
        assert button.text() == "Check for updates"
        window.set_sidebar_collapsed(True, animate=False)
        app.processEvents()
        assert not button.text() and not button.icon().isNull()
        assert button.geometry().bottom() < toggle.geometry().top()
        assert button.accessibleName() == "Check for updates"
        window.set_sidebar_collapsed(False, animate=False)
        app.processEvents()
        assert button.text() == "Check for updates"
        with (patch("app.ui.check_release", return_value={"status": "available", "release": release}) as check,
              patch.object(window, "offer_app_update") as offer):
            check.assert_not_called()
            window.start_app_update_checks()
            QTest.qWait(20)
            wait_for_idle()
            assert window.app_update_timer.interval() == 3_600_000 and window.app_update_timer.isActive()
            offer.assert_called_once_with(release)
            window.app_update_timer.timeout.emit()
            wait_for_idle()
            assert check.call_count == 2
            offer.assert_called_once()
            window.app_update_input.setChecked(False)
            window.save_interface_preferences()
            assert not window.app_update_timer.isActive()
            assert not json.loads(window.preferences_path.read_text(encoding="utf-8"))["auto_app_updates"]
            window.check_app_updates()
            assert check.call_count == 2
            check.return_value = {"status": "unpublished"}
            button.click()
            wait_for_idle()
            assert check.call_count == 3 and "No LottoLens release" in window.notice.text()

        for theme in ("light", "dark"):
            window.set_theme(theme)
            for compact in (False, True):
                window.set_sidebar_collapsed(compact, animate=False)
                app.processEvents()
                window.nav.setFocus()
                ready = Event()

                def check_when_ready():
                    ready.wait(2)
                    return {"status": "unpublished"}

                with patch("app.ui.check_release", side_effect=check_when_ready) as check:
                    try:
                        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                        assert window.update_check_worker is not None
                        assert not toggle.hasFocus(), (theme, compact, "mouse click moved focus to day/night")
                        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                    finally:
                        ready.set()
                        wait_for_idle()
                    check.assert_called_once()
                    assert not toggle.hasFocus()
                    assert button.hasFocus()
                QTest.keyClick(button, Qt.Key.Key_Tab)
                assert toggle.hasFocus() and toggle.property("keyboardFocus")
                image = toggle.grab().toImage()
                assert image.pixelColor(image.width() // 2, 0) == QColor(window.tokens["red"])

        def select(caption):
            dialog = app.activeModalWidget()
            assert isinstance(dialog, QMessageBox)
            next(button for button in dialog.buttons() if button.text() == caption).click()

        with (patch("app.ui.installed_data", return_value=directory / "data"),
              patch("app.ui.download_setup", side_effect=lambda _release, path, *_: path.write_bytes(b"checked")) as download,
              patch("app.ui.subprocess.Popen") as launch, patch.object(window, "close") as close):
            QTimer.singleShot(0, lambda: select("Later"))
            window.offer_app_update(release)
            download.assert_not_called()
            QTimer.singleShot(0, lambda: select("Update now"))
            window.offer_app_update(release)
            wait_for_idle("worker")
            download.assert_called_once()
            args = launch.call_args.args[0]
            assert f"/DIR={directory}" in args and f"/UPDATEPID={os.getpid()}" in args and "/LANG=english" in args
            close.assert_called_once()
            Path(args[0]).unlink()
    finally:
        window.close()


def main():
    setup = b"test installer"
    major, minor, patch_version = map(int, __version__.split("."))
    newer = f"{major}.{minor}.{patch_version + 1}"
    name = f"LottoLens-Setup-{newer}.exe"
    url = f"{RELEASE_PAGE}/download/v{newer}/{name}"
    body = {"tag_name": "v" + newer, "draft": False, "prerelease": False, "assets": [{
        "name": name, "browser_download_url": url, "state": "uploaded",
        "size": len(setup), "digest": "sha256:" + sha256(setup).hexdigest(),
    }]}

    with patch("app.updates.build_opener") as opener:
        request = opener.return_value.open
        request.side_effect = HTTPError(RELEASE_API, 404, "Not Found", {}, None)
        assert check_release()["status"] == "unpublished"
        request.side_effect = None
        for tag, status in (("V" + __version__, "current"), ("0.2.0", "current"), ("v" + newer, "available")):
            request.return_value = BytesIO(json.dumps({**body, "tag_name": tag}).encode())
            result = check_release()
            assert result["status"] == status
        release = result["release"]
        assert release.url == url
        assert request.call_args.args[0].full_url == RELEASE_API
        assert request.call_args.args[0].get_header("Authorization") is None
        for change in ({"browser_download_url": "https://example.invalid/file.exe"}, {"digest": None}):
            invalid = {**body, "assets": [{**body["assets"][0], **change}]}
            request.return_value = BytesIO(json.dumps(invalid).encode())
            assert not check_release()["release"].url
        with TemporaryDirectory() as directory:
            path = Path(directory) / name
            request.return_value = BytesIO(setup)
            download_setup(release, path, lambda: False, lambda *_: None)
            assert path.read_bytes() == setup
            path.unlink()
            request.return_value = BytesIO(b"!" * len(setup))
            try:
                download_setup(release, path, lambda: False, lambda *_: None)
            except ValueError:
                assert not path.exists()
            else:
                raise AssertionError("Accepted a mismatched SHA-256")
            request.return_value = BytesIO(setup)
            try:
                download_setup(release, path, lambda: True, lambda *_: None)
            except CancelledError:
                assert not path.exists() and not path.with_suffix(".part").exists()
            else:
                raise AssertionError("Accepted a canceled download")
    legacy = default_preferences()
    del legacy["auto_app_updates"]
    assert validate_preferences(legacy)["auto_app_updates"] is True
    assert validate_preferences({**legacy, "auto_app_updates": False})["auto_app_updates"] is False
    with TemporaryDirectory() as directory:
        check_ui(Path(directory), release)
    print("Release detection, verified download, sidebar, timer, manual check and settings passed.")


if __name__ == "__main__":
    main()
