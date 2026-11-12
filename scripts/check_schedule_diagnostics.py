"""Regression for silent daily failures; all requests/tasks mocked, DB temporary."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import scheduled_sync
from app.preferences import default_preferences,save_preferences
from app.scheduling import VIETNAM
from app.storage import Store


def main():
    for message in ("Trang kết quả rỗng hoặc vượt giới hạn 2 MB.", "Nguồn trả dữ liệu quá giới hạn 2 MB.",
                    "Nguồn chuyển hướng ngoài host chính thức.", "Bộ tải chính thức chỉ truy cập HTTPS của Vietlott."):
        assert scheduled_sync._failure_message(ValueError(message))==message
    with tempfile.TemporaryDirectory() as directory:
        folder=Path(directory);db=folder/"history.db";path=folder/"ui_preferences.json"
        prefs=default_preferences();prefs["auto_updates"]["max3d"]["enabled"]=True
        save_preferences(path,prefs)
        today=datetime.now(VIETNAM)
        with patch.object(scheduled_sync,"OfficialSource") as source:
            source.return_value.fetch_history.side_effect=ValueError("Nguồn Vietlott trả HTTP 503; không thay đổi dữ liệu cũ.")
            assert scheduled_sync.run_scheduled("max3d",db,path,today)==1
            with _store(db) as store:
                row=store.auto_update_runs()[0]
                assert "HTTP 503" in row["message"],row
            assert scheduled_sync.run_scheduled("max3d",db,path,today)==0
            source.return_value.fetch_history.assert_called_once()
            prefs["auto_updates"]["bingo18"]["enabled"]=True;save_preferences(path,prefs)
            source.return_value.fetch_history.side_effect=ValueError("secret-api-key https://user:password@example.test/?token=private")
            assert scheduled_sync.run_scheduled("bingo18",db,path,today)==1
            with _store(db) as store:
                assert "secret-api-key" not in json.dumps(store.auto_update_runs())
                assert "password" not in json.dumps(store.auto_update_runs())
        from PySide6.QtWidgets import QApplication
        from app.ui import Desktop
        app=QApplication.instance() or QApplication([])
        with patch("app.ai._send") as send,patch("app.ui.OfficialSource.fetch_history") as fetch:
            w=Desktop(db,folder/"config.json")
            try:
                w.game.setCurrentIndex(w.game.findData("max3d"))
                assert "thất bại" in w.auto_status_labels["max3d"].text()
                assert "HTTP 503" in w.auto_status_labels["max3d"].text()
                # Another game's result must not hide the active game's failure.
                with _store(db) as store:
                    store.claim_auto_update("mega",today.date().isoformat())
                    store.finish_auto_update("mega",today.date().isoformat(),"success","Official history updated.")
                w.poll_background_updates()
                assert "Max 3D" in w.notice.text() and "HTTP 503" in w.notice.text(),w.notice.text()
                w.apply_language("en")
                assert "failed" in w.auto_status_labels["max3d"].text()
                assert "thất bại" not in w.auto_status_labels["max3d"].text()
                send.assert_not_called();fetch.assert_not_called()
            finally:w.close()
    print("Schedule diagnostics OK: safe cause, active-game notice, persistent VI/EN per-game status, no retry/network")


from contextlib import contextmanager
@contextmanager
def _store(path):
    store=Store(path)
    try:yield store
    finally:store.close()


if __name__=="__main__":main()
