"""Explicit offline build diagnostic, never called during normal startup."""
import json
from pathlib import Path
import socket


def check_install(output):
    from PySide6.QtWidgets import QApplication
    from . import __version__
    from .paths import installed_data
    from .settings import CONFIG_PATH
    from .storage import data_directory
    from .policy import POLICY_PATH
    from .onboarding import ASSETS, SCREENS, OnboardingDialog
    from .ui import Desktop

    def offline(*args, **kwargs):
        raise AssertionError("Build diagnostic attempted a network connection")

    socket.create_connection = offline
    socket.socket.connect = offline
    assert data_directory() == installed_data() == CONFIG_PATH.parent
    assert "LottoLens" in POLICY_PATH.read_text(encoding="utf-8")
    guide = json.loads((ASSETS / "guide.json").read_text(encoding="utf-8"))
    application = QApplication([])
    window = Desktop()
    window.show()
    application.processEvents()
    assert window.store.path == data_directory()/"history.sqlite3"
    assert not window.windowIcon().isNull()
    for theme in ("dark", "light"):
        window.set_theme(theme)
        for language in ("en", "vi"):
            window.apply_language(language)
            for index in range(window.pages.count()):
                window.nav.setCurrentRow(index)
                application.processEvents()
            dialog = OnboardingDialog(window)
            for index in range(len(SCREENS)):
                dialog.show_step(index)
                application.processEvents()
            dialog.close()
    result = {"version": __version__, "pages": window.pages.count(), "data_directory": str(data_directory()),
              "config_path": str(CONFIG_PATH), "assets": str(ASSETS), "themes": ["dark", "light"],
              "languages": ["vi", "en"], "network": "blocked", "guide_loaded": bool(guide)}
    window.close()
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0
