"""Opt-in official-history updates, with one attempt per configured slot."""
from dataclasses import replace
from datetime import datetime, timedelta
import re

from .domain import aware_time, validate_draw
from .draw_schedule import DRAW_MODE, FAST, active_slot
from .preferences import load_preferences
from .rules import get_rule
from .scheduling import VIETNAM
from .sources import CancelledError, OfficialSource, RateLimitError
from .storage import Store


def _failure_message(error):
    if isinstance(error, RateLimitError):
        return str(error)
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
    """Return 0 for success/no-op, 1 for failure."""
    store = None
    day = None
    claimed = False
    try:
        rule = get_rule(game_id)
        preferences = load_preferences(preferences_path)
        schedule = preferences["auto_updates"][game_id]
        if not schedule["enabled"]:
            return 0
        instant = now if now is not None else datetime.now(VIETNAM)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("Scheduled update time must include a timezone.")
        local = instant.astimezone(VIETNAM)
        local_date = local.date()
        day = local_date.isoformat()
        by_draw = schedule.get("mode") == DRAW_MODE
        slot = active_slot(game_id, schedule, local) if by_draw else None
        if by_draw and slot is None:
            return 0
        if slot is not None:
            day = slot.strftime("%Y-%m-%d %H:%M")
        store = Store(db_path)
        if game_id in FAST:
            for previous in store.auto_update_runs(latest_only=True):
                if (previous["game_id"] in FAST and previous["status"] == "failed"
                        and "HTTP 429" in previous["message"] and len(previous["day"]) == 16):
                    failed_slot = datetime.fromisoformat(previous["day"]).replace(tzinfo=VIETNAM)
                    pause_until = failed_slot + timedelta(hours=1)
                    deadline = re.search(r"Chờ đến ([0-9T:+-]+)\.$", previous["message"])
                    if deadline:
                        try:
                            pause_until = max(pause_until, aware_time(deadline[1]))
                        except ValueError:
                            pass
                    if failed_slot <= local < pause_until:
                        return 0
        if not store.claim_auto_update(game_id, day):
            return 0
        claimed = True
        limit = preferences["history_limits"][game_id]

        def cancelled():
            return load_preferences(preferences_path)["auto_updates"][game_id] != schedule

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
        # A date-only Lotto page needs two draws to identify the evening session.
        required_today = 2 if by_draw and game_id == "lotto" and slot.hour == 21 else 1
        fetch_limit = max(limit, required_today)
        receipt = OfficialSource(max_attempts=1).fetch_history(rule, fetch_limit, cancel=cancelled, known_draws=known)
        if receipt.get("status") not in {"requested_limit", "source_boundary", "known_boundary"}:
            raise ValueError("The official source did not complete a retained-history window.")
        if by_draw:
            today = {draw.draw_id for draw in receipt["draws"]
                     if aware_time(draw.draw_at_utc).astimezone(VIETNAM).date() == local_date}
            if len(today) < required_today:
                check_enabled()
                store.finish_auto_update(game_id, day, "waiting", "Chưa thấy kỳ dự kiến trên nguồn Vietlott.")
                return 0
        batches = []
        for item in rules:
            draws = [replace(draw, mode_id=item.mode_id) for draw in receipt["draws"]]
            for draw in draws:
                validate_draw(item, draw)
            batches.append((item, {**receipt, "draws": draws}))
        check_enabled()
        counts = store.apply_sync_many(batches, limit, check_cancel=check_enabled)
        if by_draw and game_id in FAST and not any(row["added"] or row["revised"] for row in counts):
            store.finish_auto_update(game_id, day, "waiting", "Chưa có kỳ mới trên nguồn Vietlott.")
        else:
            store.finish_auto_update(game_id, day, "success", "Official history updated.")
        return 0
    except Exception as error:
        if claimed:
            try:
                store.finish_auto_update(game_id, day, "failed", _failure_message(error))
            except Exception:
                pass  # The persisted claim still prevents a second attempt for this slot.
        return 1
    finally:
        if store is not None:
            store.close()
