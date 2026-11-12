"""Native review images from a temporary database, without network or AI calls."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from PySide6.QtWidgets import QApplication
from app.ui import Desktop
from check_max_bingo_generation import history
from check_redesign import check_page


def main():
    app=QApplication([])
    output=Path(__file__).with_name("reviews");output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send",side_effect=AssertionError("No AI")), patch("app.ui.OfficialSource.fetch_history",side_effect=AssertionError("No source")):
        folder=Path(directory);w=Desktop(folder/"history.db",folder/"config.json")
        try:
            w.set_analysis_window(90);w.resize(1440,960);w.show()
            for game in ("max3d","max3dpro","bingo18"):
                w.game.setCurrentIndex(w.game.findData(game));w.store.add_draws(w.rule,history(w.rule));w.refresh()
                if game=="bingo18":w.change_play("sum");w.ticket_controls[0]["choice"].setCurrentIndex(7)
                w.method.setCurrentIndex(w.method.findData("bayes90_v1"));w.count.setValue(5);w.make_suggestions()
                for language in ("vi","en"):
                    w.apply_language(language)
                    for theme in ("light","dark"):
                        w.set_theme(theme)
                        for name,page in (("odds",3),("suggestions",4)):
                            w.nav.setCurrentRow(page);app.processEvents();check_page(w)
                            w.grab().save(str(output/f"{game}-{name}-{language}-{theme}.png"))
            w.game.setCurrentIndex(w.game.findData("bingo18"));w.change_play("any_triple")
            w.make_suggestions();w.resize(1000,700);w.nav.setCurrentRow(4);app.processEvents();check_page(w)
            w.grab().save(str(output/"bingo-any-triple-en-dark-small.png"))
            w.game.setCurrentIndex(w.game.findData("max3dpro"));w.change_max_sample("007","007");w.nav.setCurrentRow(3)
            app.processEvents();check_page(w);w.grab().save(str(output/"pro-identical-en-dark-small.png"))
        finally:w.close()
    print("Captured 26 Max/Bingo review images from temporary data; no HTTP/AI")


if __name__=="__main__":main()
