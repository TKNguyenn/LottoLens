"""Window persistence checks use only temporary config and database files."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication
from app.ui import Desktop


def main():
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as directory:
        folder = Path(directory)
        geometry = folder / "window_geometry.bin"
        def open_window():
            window = Desktop(folder / "db.sqlite3", folder / "config.json")
            window.history_poll.stop()
            return window
        window = open_window()
        assert not geometry.exists()
        window.show(); app.processEvents()
        area = window.screen().availableGeometry()
        window.resize(max(1000, min(1120, area.width()-80)), max(700, min(720, area.height()-80)))
        app.processEvents()
        expected = window.size()
        window.close()
        assert geometry.is_file(), "Closing a visible idle window must save its geometry"
        saved = geometry.read_bytes()
        window = open_window()
        window.show(); app.processEvents()
        assert window.size() == expected, (window.size(), expected)
        assert window.minimumWidth() == 1000 and window.minimumHeight() == 700
        assert not (folder / "config.json").exists(), "Geometry must not create or modify AI configuration"
        window.close()

        # Qt should recover windows previously saved beyond the current screen.
        window = open_window(); window.move(50000, 50000)
        geometry.write_bytes(bytes(window.saveGeometry()))
        window.close()
        window = open_window(); window.show(); app.processEvents()
        frame, area = window.frameGeometry(), window.screen().availableGeometry()
        assert frame.intersects(area), (frame, area)
        window.close()

        if app.platformName() == "windows":
            window = open_window(); window.showMaximized(); app.processEvents()
            assert window.isMaximized()
            window.close()
            window = open_window(); window.show(); app.processEvents()
            assert window.isMaximized(), "Maximized state must survive reopening"
            window.showNormal(); app.processEvents(); window.close()

        for invalid in (b"", b"not a Qt geometry", b"x" * 10000):
            geometry.write_bytes(invalid)
            window = open_window()
            assert window.width() >= 1000 and window.height() >= 700
            window.close()

        geometry.write_bytes(saved)
        window = open_window(); window.show(); app.processEvents()
        window.worker = SimpleNamespace(cancelled=Event())
        event = QCloseEvent()
        with patch.object(window.store, "close", wraps=window.store.close) as close:
            window.closeEvent(event)
            assert not event.isAccepted() and window.closing and window.worker.cancelled.is_set()
            assert geometry.read_bytes() == saved, "Ignored close must not persist geometry"
            close.assert_not_called()
        window.worker = None
        window.close()

        # A failed atomic write must preserve the previous file and allow idle close.
        previous = geometry.read_bytes()
        window = open_window(); window.show(); app.processEvents()
        with patch("app.ui.QSaveFile.open", return_value=False):
            window.close()
        assert not window.isVisible() and geometry.read_bytes() == previous
    print("Window geometry contract passed")


if __name__ == "__main__":
    main()
