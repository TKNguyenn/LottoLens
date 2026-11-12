"""One opt-in, once-per-Vietnam-day official-history update; no AI imports."""
from dataclasses import replace
from datetime import datetime
import re

from .domain import validate_draw
from .preferences import load_preferences
from .rules import get_rule
from .scheduling import VIETNAM
from .sources import CancelledError, OfficialSource
from .storage import Store


def _failure_message(error):
    # Only known downloader copy is safe to persist; arbitrary errors can contain credentials.
    text = str(error)
    fixed = {"Trang kết quả rỗng hoặc vượt giới hạn 2 MB.", "Nguồn trả dữ liệu quá giới hạn 2 MB.",
             "Nguồn chuyển hướng ngoài host chính thức.", "Bộ tải chính thức chỉ truy cập HTTPS của Vietlott.",
             "Không tìm thấy vùng kết quả chính thức.", "Trang kết quả không khớp trò chơi được chọn.",
             "Trang không có hàng kết quả; có thể hết phạm vi hoặc nguồn thay đổi.",
             "Vietlott không trả kết quả hợp lệ cho yêu cầu này.",
             "Không đọc được cơ chế tải kỳ trước từ nguồn chính thức.",
             "Nguồn trả lại kỳ đã tải; dừng để tránh vòng lặp.",
             "Phân trang không cung cấp thêm kỳ mới; không thể khẳng định hết lịch sử.",
             "Nguồn yêu cầu chờ lâu; hãy cập nhật lại sau.",
             "Kết quả Max 3D phải có 20 bộ ba chữ số.", "Nguồn không có ngày quay hợp lệ.",
             "Nguồn không có mã kỳ quay.", "Cấu trúc số kết quả đã thay đổi."}
    patterns = (r"Nguồn Vietlott trả HTTP [1-5][0-9]{2}; không thay đổi dữ liệu cũ\.",
                r"Không kết nối được Vietlott sau [1-3] lần; vẫn giữ lịch sử cũ\.",
                r"Nguồn trả [0-9]{1,3} số thay vì [0-9]{1,3}; không lưu kết quả thiếu\.")
    if isinstance(error, ValueError) and (text in fixed or any(re.fullmatch(pattern, text) for pattern in patterns)):
        return text
    return "Tự cập nhật gặp lỗi " + type(error).__name__ + "."


def run_scheduled(game_id, db_path, preferences_path, now=None):
    """Return 0 for success/no-op, 1 for failure; never retry a claimed day."""
    store = None
    day = None
    claimed = False
    try:
        rule = get_rule(game_id)
        preferences = load_preferences(preferences_path)
        if not preferences["auto_updates"][game_id]["enabled"]:
            return 0
        instant = now if now is not None else datetime.now(VIETNAM)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("Scheduled update time must include a timezone.")
        day = instant.astimezone(VIETNAM).date().isoformat()
        store = Store(db_path)
        if not store.claim_auto_update(game_id, day):
            return 0
        claimed = True
        limit = preferences["history_limits"][game_id]

        def cancelled():
            return not load_preferences(preferences_path)["auto_updates"][game_id]["enabled"]

        def check_enabled():
            if cancelled():
                raise CancelledError("Automatic updates were disabled before saving.")

        rules = [get_rule("keno", "pick" + str(pick)) for pick in range(1, 11)] if game_id == "keno" else [rule]
        windows = [store.sync_window(item, limit) for item in rules]
        known = store.sync_window(rule, limit)
        # Every Keno mode must share the proven boundary before one fetch can serve them all.
        identities = lambda draws: [(item.draw_id, item.draw_at_utc, item.payload) for item in draws]
        if any(not window or identities(window) != identities(known) for window in windows):
            known = []
        receipt = OfficialSource(max_attempts=1).fetch_history(rule, limit, cancel=cancelled, known_draws=known)
        if receipt.get("status") not in {"requested_limit", "source_boundary", "known_boundary"}:
            raise ValueError("The official source did not complete a retained-history window.")
        batches = []
        for item in rules:
            draws = [replace(draw, mode_id=item.mode_id) for draw in receipt["draws"]]
            for draw in draws:
                validate_draw(item, draw)
            batches.append((item, {**receipt, "draws": draws}))
        check_enabled()
        store.apply_sync_many(batches, limit, check_cancel=check_enabled)
        store.finish_auto_update(game_id, day, "success", "Official history updated.")
        return 0
    except Exception as error:
        if claimed:
            try:
                store.finish_auto_update(game_id, day, "failed", _failure_message(error))
            except Exception:
                pass  # The persisted claim still prevents a second attempt today.
        return 1
    finally:
        if store is not None:
            store.close()
