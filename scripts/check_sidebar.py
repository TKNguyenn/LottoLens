"""Offline regression checks for the approved collapsible sidebar."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication
from app.ui import Desktop
from check_redesign import check_page


def sidebar_copy_geometry(window):
    header = window.brand_text.layout()
    labels = [header.itemAt(index).widget() for index in range(header.count())] + window.sidebar_notes
    for note in window.sidebar_notes:
        assert note.isVisible() and note.height() >= note.heightForWidth(note.width()), note.text()
    return window.sidebar_footer.height(), [(label.geometry().getRect(), label.minimumHeight()) for label in labels]


def settle_sidebar(window):
    animation = window.sidebar_animation
    if animation.state() == QAbstractAnimation.State.Running:
        assert QSignalSpy(animation.finished).wait(2000), "Sidebar animation did not finish"
    QApplication.processEvents()


def main():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        with patch("app.ai._send", side_effect=AssertionError("Sidebar triggered AI")) as ai_request, patch("app.ui.OfficialSource.fetch_history", side_effect=AssertionError("Sidebar triggered network")) as history_request:
            window = Desktop(folder / "history.sqlite3", folder / "config.json")
            try:
                window.show(); window.activateWindow()
                assert QTest.qWaitForWindowActive(window, 1500)
                assert window.sidebar.width() == 236
                expanded_copy = sidebar_copy_geometry(window)
                window.sidebar_toggle.click(); settle_sidebar(window)
                assert window.sidebar_collapsed and window.sidebar.width() == 68
                assert window.sidebar_toggle.isChecked()
                assert "Mở rộng" in window.sidebar_toggle.accessibleName()
                assert not window.brand_text.isVisible()
                assert window.theme_button.isVisible()
                window.sidebar_toggle.click(); settle_sidebar(window)
                assert sidebar_copy_geometry(window) == expanded_copy, (
                    "Expanding must restore the header and footer geometry", expanded_copy, sidebar_copy_geometry(window)
                )
                window.set_sidebar_collapsed(True, animate=False)
                window.nav.set_count(123)
                assert "123" in window.nav.item(1).toolTip()
                assert window.nav.item(1).text() == "Lịch sử"
                for theme in ("dark", "light"):
                    window.set_theme(theme)
                    for collapsed in (False, True):
                        window.set_sidebar_collapsed(collapsed, animate=False)
                        window.nav.setFocus()
                        QTest.mouseClick(window.sidebar_toggle, Qt.MouseButton.LeftButton); settle_sidebar(window)
                        assert not window.sidebar_toggle.hasFocus(), "Mouse click must not leave toggle focus border"
                        image = window.sidebar_toggle.grab().toImage()
                        assert image.pixelColor(image.width() // 2, 0) != QColor(window.tokens["red"])
                        window.nav.setFocus()
                        QTest.keyClick(window.nav, Qt.Key.Key_Backtab)
                        assert window.sidebar_toggle.hasFocus(), (
                            "Toggle must remain reachable using keyboard", theme, collapsed, window.isActiveWindow(),
                            type(app.focusWidget()).__name__,
                        )
                        image = window.sidebar_toggle.grab().toImage()
                        assert image.pixelColor(image.width() // 2, 0) == QColor(window.tokens["red"]), "Keyboard focus must remain visible"
                        QTest.keyClick(window.sidebar_toggle, Qt.Key.Key_Space); settle_sidebar(window)
                        assert window.sidebar_collapsed == collapsed
                        QTest.mouseClick(window.sidebar_toggle, Qt.MouseButton.LeftButton); settle_sidebar(window)
                        assert not window.sidebar_toggle.hasFocus(), "Mouse click must also clear previous keyboard focus"
                        window.set_sidebar_collapsed(collapsed, animate=False)
                    for size in ((1000, 700), (1920, 1080)):
                        window.resize(*size)
                        window.set_sidebar_collapsed(False, animate=False)
                        for language in ("vi", "en"):
                            window.apply_language(language); app.processEvents()
                            expanded_copy = sidebar_copy_geometry(window)
                            window.sidebar_toggle.click(); settle_sidebar(window)
                            assert all(not note.isVisible() for note in window.sidebar_notes)
                            window.sidebar_toggle.click(); settle_sidebar(window)
                            assert sidebar_copy_geometry(window) == expanded_copy, (theme, size, language)
                            window.set_sidebar_collapsed(True, animate=False)
                            window.set_sidebar_collapsed(False, animate=False)
                            app.processEvents()
                            assert sidebar_copy_geometry(window) == expanded_copy, (
                                theme, size, language, "instant", expanded_copy, sidebar_copy_geometry(window)
                            )
                        window.apply_language("vi")
                        window.set_sidebar_collapsed(True, animate=False)
                        for page in range(7):
                            window.nav.setCurrentRow(page); app.processEvents()
                            assert window.pages.currentIndex() == page
                            assert window.sidebar_collapsed and window.sidebar.width() == 68
                            check_page(window)
                window.nav.setCurrentRow(4)
                window.method.setCurrentIndex(window.method.findData("uniform_v1"))
                window.make_suggestions(); window.target.setText("99")
                state = (window.generated, window.explanation.toPlainText(), window.target.text(), window.nav.currentRow(), window.game.currentData())
                window.sidebar_toggle.click(); settle_sidebar(window)
                assert window.sidebar.width() == 236 and window.brand_text.isVisible()
                expanded_copy = sidebar_copy_geometry(window)
                window.sidebar_toggle.click(); QTest.qWait(50)
                assert 68 < window.sidebar.width() < 236, "Expected a real width animation"
                window.sidebar_toggle.click(); settle_sidebar(window)
                assert window.sidebar.width() == 236 and not window.sidebar_collapsed
                assert sidebar_copy_geometry(window) == expanded_copy
                assert state == (window.generated, window.explanation.toPlainText(), window.target.text(), window.nav.currentRow(), window.game.currentData())
                assert window.nav.item(1).toolTip() == ""
                window.sidebar_toggle.setFocus()
                QTest.keyClick(window.sidebar_toggle, Qt.Key.Key_Space); settle_sidebar(window)
                assert window.sidebar_collapsed
                window.theme_button.click()
                assert window.sidebar_collapsed and window.sidebar.width() == 68
                assert not (folder / "config.json").exists()
                assert set(json.loads((folder / "theme.json").read_text())) == {"theme"}
                ai_request.assert_not_called(); history_request.assert_not_called()
            finally:
                window.close()
    print("Sidebar OK: 236/68px, header/footer restored across 2 themes/languages/sizes, animation and rapid reversal, mouse and keyboard, retained generated state, offline.")


if __name__ == "__main__":
    main()
