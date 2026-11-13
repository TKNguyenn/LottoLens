"""Versioned native title stays stable across live language switches."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app import __version__, ui


def main():
    application = QApplication.instance() or QApplication([])
    failures = []
    expected = f"LottoLens — V{__version__}"
    def inspect():
        window = next(w for w in application.topLevelWidgets() if isinstance(w, ui.Desktop) and w.isVisible())
        try:
            assert application.applicationVersion() == __version__
            for language in ("en", "vi", "en"):
                window.apply_language(language)
                assert window.windowTitle() == expected, window.windowTitle()
                if application.platformName() == "windows":
                    import ctypes
                    buffer = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetWindowTextW(ctypes.c_void_p(int(window.winId())), buffer, len(buffer))
                    assert buffer.value == expected, buffer.value
        except Exception as error:
            failures.append(error)
        finally:
            window.close()
    with TemporaryDirectory() as directory:
        folder = Path(directory)
        with (patch.object(ui, "CONFIG_PATH", folder / "config.json"),
              patch.object(ui, "show_policy", return_value=True), patch.object(ui, "show_onboarding")):
            QTimer.singleShot(0, inspect)
            assert ui.main(folder / "db.sqlite3") == 0
    if failures:
        raise failures[0]
    print("Versioned window title passed")


if __name__ == "__main__":
    main()
