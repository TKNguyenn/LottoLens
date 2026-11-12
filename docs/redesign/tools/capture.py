import os
import sys
if "--native" not in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import sqlite3
import json
import re
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from app.storage import data_directory
from app.ui import Desktop
from app.domain import Draw
from app.rules import get_rule, BASE

application = QApplication([])
for name in ("SegUIVar.ttf", "segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "CascadiaMono.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
output = Path(__file__).resolve().parents[1]
if "--gradient" in sys.argv:
    output = output / "gradient" / ("native-compact" if "--collapsed" in sys.argv else "native-expanded")
else:
    output = output / "reviews" / ("native-sidebar" if "--collapsed" in sys.argv else "native-ui")
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    source = data_directory() / "history.sqlite3"
    if source.exists():
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original, sqlite3.connect(folder / "history.sqlite3") as backup:
            original.backup(backup)
        original.close(); backup.close()
    window = Desktop(folder / "history.sqlite3", folder / "config.json")
    try:
        if not window.draws:
            html = (Path(__file__).resolve().parents[1] / "vietlott-redesign.html").read_text(encoding="utf-8")
            fixture = json.loads(re.search(r"const DB = (.*);", html).group(1))
            for game in ("mega", "power"):
                rule = get_rule(game)
                draws = []
                for row in fixture[game]["latest"]:
                    payload = {"main": row["main"]}
                    if row.get("special"):
                        payload["special"] = row["special"]
                    draws.append(Draw(game, rule.mode_id, rule.rule_version, row["id"], row["at"], payload, BASE + rule.result_path, row["at"], "a" * 64))
                window.store.add_draws(rule, draws)
            window.refresh()
        window.method.setCurrentIndex(window.method.findData("uniform_v1"))
        window.make_suggestions()
        window.notice.setText("Dữ liệu xem thử từ 12 kỳ trong HTML · bộ số do app tạo tại máy, chưa lưu.")
        window.resize(1440, 960); window.show()
        if "--collapsed" in sys.argv:
            window.set_sidebar_collapsed(True, animate=False)
        for theme in ("light", "dark"):
            window.set_theme(theme)
            for i, name in enumerate(("overview", "history", "stats", "odds", "suggest", "verify", "ai")):
                window.nav.setCurrentRow(i)
                for _ in range(3):
                    application.processEvents()
                window.grab().save(str(output / (name + "-" + theme + ".png")))
        window.resize(1000, 700)
        for i in range(7):
            window.nav.setCurrentRow(i); application.processEvents()
            window.grab().save(str(output / ("small-" + str(i) + ".png")))
        print("Captured 14 themed pages and 7 small-window pages; draws:", len(window.draws))
    finally:
        window.close()
