"""Rendered checks for the approved native gradient and sidebar header."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPoint, qInstallMessageHandler
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.components import NumberHeatmap, SectionCard
from app.theme import LIGHT, DARK
from app.ui import Desktop


def main():
    def luminance(value):
        rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        return sum(weight * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) for weight, v in zip((.2126, .7152, .0722), rgb))
    style_errors = []
    qInstallMessageHandler(lambda kind, context, message: style_errors.append(message) if any(s in message.lower() for s in ("stylesheet", "unknown property", "qpainter::")) else None)
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send") as ai, patch("app.ui.OfficialSource.fetch_history") as history:
        folder = Path(directory)
        window = Desktop(folder / "history.sqlite3", folder / "config.json")
        try:
            window.show()
            for theme in ("light", "dark"):
                window.set_theme(theme)
                for _ in range(3):
                    app.processEvents()
                card = SectionCard(parent=window); card.resize(400, 180); card.show()
                image = card.grab().toImage()
                assert image.pixelColor(22, 80) != image.pixelColor(375, 150), "Card surface must render a gradient"
                card.close()
                if theme == "light":
                    heat = NumberHeatmap(parent=window); heat.set_data({1: 5, 2: 0, 3: 6}); heat.resize(400, 100)
                    image = heat.grab().toImage()
                    ink = min(luminance(image.pixelColor(x, y).name()) for x in range(5, 35) for y in range(5, 30))
                    assert (luminance("#D34A61") + .05) / (ink + .05) >= 4.5, "Rendered light heatmap level5 text contrast"
                    heat.close()
                button = next(b for b in window.actions if b.objectName() == "primary" and b.isVisibleTo(window))
                image = button.grab().toImage()
                assert image.pixelColor(8, 8) != image.pixelColor(button.width() - 9, 8), "CTA must render a gradient"
                canvas = window.pages.currentWidget().widget()
                image = canvas.grab().toImage()
                assert image.pixelColor(canvas.width() - 3, 3) != image.pixelColor(3, canvas.height() - 3), "Canvas glow must render"
                for collapsed in (True, False, True, False):
                    window.set_sidebar_collapsed(collapsed, animate=False)
                    for _ in range(3):
                        app.processEvents()
                    toggle = window.sidebar_toggle
                    assert window.sidebar.isAncestorOf(toggle), "Toggle belongs inside sidebar header"
                    assert window.brand_logo.isVisible() is not collapsed
                    center = toggle.mapTo(window.sidebar, toggle.rect().center())
                    assert center.y() < window.nav.mapTo(window.sidebar, QPoint()).y()
                    if collapsed:
                        assert abs(center.x() - window.sidebar.width() / 2) <= 2
                    else:
                        assert center.x() > window.brand_text.mapTo(window.sidebar, window.brand_text.rect().topRight()).x()
                    assert window.sidebar.width() == (68 if collapsed else 236)
            ai.assert_not_called(); history.assert_not_called()
            assert not style_errors, style_errors
        finally:
            window.close()
    for tokens in (LIGHT, DARK):
        ink = luminance(tokens["on_red"])
        for token in ("cta_top", "cta_mid", "cta_end", "cta_hover_top", "cta_hover_mid", "cta_hover_end"):
            bg = luminance(tokens[token])
            assert (max(ink, bg) + .05) / (min(ink, bg) + .05) >= 4.5, (token, tokens[token])
    print("Gradient OK: rendered card/CTA/canvas, CTA contrast >=4.5:1, light/dark, sidebar-owned panel toggle, centered compact header, no QSS/painter errors or startup/network calls.")


if __name__ == "__main__":
    main()
