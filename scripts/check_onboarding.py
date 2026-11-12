"""Offline native tutorial checks with isolated acceptance and completion files."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
from tempfile import TemporaryDirectory, gettempdir
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGraphicsBlurEffect
from app.onboarding import OnboardingDialog, show_onboarding
from app.ui import Desktop
from app import ui


def main():
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as directory, patch("app.ai._send", side_effect=AssertionError("Unexpected AI request")):
        folder = Path(directory)
        window = Desktop(folder / "db.sqlite3", folder / "config.json")
        window.history_poll.stop()
        window.resize(1000, 700); window.show()
        receipt = folder / "tour.txt"
        errors = []

        def inspect():
            try:
                dialog = application.activeModalWidget()
                assert isinstance(dialog, OnboardingDialog)
                assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
                assert isinstance(window.centralWidget().graphicsEffect(), QGraphicsBlurEffect)
                assert dialog.nav.count() == 8 and not dialog.previous.isEnabled()
                for index in range(8):
                    dialog.nav.setCurrentRow(index)
                    application.processEvents()
                    assert not dialog.picture.pixmap.isNull()
                    assert len(dialog.picture.marks) == len(dialog.steps[index][2])
                    assert dialog.picture.pixmap.width() >= dialog.picture.width() * dialog.devicePixelRatioF()
                    assert dialog.next.text()
                    if application.platformName() == "windows" and index in (0, 6, 7):
                        dialog.grab().save(str(Path(gettempdir()) / f"lottolens-onboarding-native-{window.language}-{window.theme_name}-{index}.png"))
                assert len(dialog.steps[6][2]) == 4
                dialog.previous.click(); assert dialog.nav.currentRow() == 6
                dialog.next.click(); assert dialog.nav.currentRow() == 7
                QTest.keyClick(dialog, Qt.Key.Key_Escape)
            except Exception as error:
                errors.append(error)
                application.activeModalWidget().reject()

        for language in ("vi", "en"):
            window.apply_language(language)
            for theme in ("light", "dark"):
                window.set_theme(theme)
                if receipt.exists():
                    receipt.unlink()
                QTimer.singleShot(0, inspect)
                show_onboarding(window, first_run=True, receipt_path=receipt)
                if errors:
                    raise errors.pop()
                assert receipt.read_text() == "1"
                assert window.centralWidget().graphicsEffect() is None
                with patch("app.onboarding.OnboardingDialog.exec", side_effect=AssertionError("Tour repeated")):
                    show_onboarding(window, first_run=True, receipt_path=receipt)
                QTimer.singleShot(0, inspect)
                show_onboarding(window, receipt_path=receipt)
                if errors:
                    raise errors.pop()
        window.nav.setCurrentRow(6)
        window.show()
        application.processEvents()
        if application.platformName() == "windows":
            window.grab().save(str(Path(gettempdir()) / "lottolens-fetch-models-native.png"))
        from app import onboarding
        failure = folder / "blocked"
        failure.mkdir()
        QTimer.singleShot(0, lambda: application.activeModalWidget().reject())
        with patch.object(onboarding.QMessageBox, "warning") as warning:
            show_onboarding(window, first_run=True, receipt_path=failure)
            warning.assert_called_once()
            assert failure.is_dir()
        missing = folder / "missing-receipt.txt"
        with patch.object(onboarding, "ASSETS", folder / "no-assets"), patch.object(onboarding.QMessageBox, "warning") as warning:
            show_onboarding(window, first_run=True, receipt_path=missing)
            warning.assert_called_once()
            assert not missing.exists()
        window.close()

    # Real entry point must present policy, then the tour, and neither on the next launch.
    from PySide6.QtWidgets import QCheckBox, QPushButton
    with TemporaryDirectory() as directory:
        folder = Path(directory)
        stages = []
        failures = []
        def tick():
            try:
                modal = application.activeModalWidget()
                if modal and modal.objectName() == "policyDialog":
                    stages.append("policy")
                    for checkbox in modal.findChildren(QCheckBox):
                        checkbox.setChecked(True)
                    next(b for b in modal.findChildren(QPushButton) if b.objectName() == "primary").click()
                    QTimer.singleShot(0, tick)
                elif isinstance(modal, OnboardingDialog):
                    stages.append("tour")
                    modal.skip.click()
                    QTimer.singleShot(0, tick)
                else:
                    stages.append("desktop")
                    next(w for w in application.topLevelWidgets() if isinstance(w, Desktop) and w.isVisible()).close()
            except Exception as error:
                failures.append(error)
                if application.activeModalWidget():
                    application.activeModalWidget().reject()
                QTimer.singleShot(0, application.quit)
        with (patch.dict(os.environ, {"LOCALAPPDATA": directory}), patch.object(ui, "CONFIG_PATH", folder / "config.json"),
              patch("app.ai._send", side_effect=AssertionError("Unexpected inference")),
              patch("app.ui.fetch_models", side_effect=AssertionError("Unexpected model fetch")),
              patch.object(ui.OfficialSource, "fetch_history", side_effect=AssertionError("Unexpected history fetch"))):
            QTimer.singleShot(0, tick)
            assert ui.main(folder / "db.sqlite3") == 0
            if failures:
                raise failures.pop()
            assert stages == ["policy", "tour", "desktop"], stages
            stages.clear()
            QTimer.singleShot(0, tick)
            assert ui.main(folder / "db.sqlite3") == 0
            if failures:
                raise failures.pop()
            assert stages == ["desktop"], stages
    print("Onboarding dialog contract passed")


if __name__ == "__main__":
    main()
