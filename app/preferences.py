"""Presentation preferences, separate from AI configuration and stored draw data."""
import json
from pathlib import Path
import re

from .rules import RULES


def default_preferences():
    return {"language": "vi", "history_limits": {game: 100 for game in RULES}, "analysis_window": 90,
            "auto_updates": {game: {"enabled": False, "time": "20:00"} for game in RULES},
            "auto_app_updates": True}


def validate_preferences(body):
    if (not isinstance(body, dict) or not {"language", "history_limits"} <= set(body)
            or set(body) - {"language", "history_limits", "analysis_window", "auto_updates", "auto_app_updates"}):
        raise ValueError("Cài đặt giao diện không hợp lệ.")
    limits = body["history_limits"]
    if body["language"] not in ("vi", "en") or not isinstance(limits, dict) or set(limits) != set(RULES):
        raise ValueError("Ngôn ngữ hoặc danh sách trò chơi không hợp lệ.")
    if any(type(value) is not int or not 1 <= value <= 2000 for value in limits.values()):
        raise ValueError("Số kỳ tải phải là số nguyên từ 1 đến 2000.")
    window = body.get("analysis_window", 90)
    if type(window) is not int or not 1 <= window <= 2000:
        raise ValueError("Số kỳ phân tích phải là số nguyên từ 1 đến 2000.")
    automatic = body.get("auto_updates", default_preferences()["auto_updates"])
    if not isinstance(automatic, dict) or set(automatic) != set(RULES):
        raise ValueError("Danh sách lịch tự cập nhật không hợp lệ.")
    for value in automatic.values():
        if (not isinstance(value, dict) or set(value) != {"enabled", "time"}
                or type(value["enabled"]) is not bool or not isinstance(value["time"], str)
                or re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value["time"]) is None):
            raise ValueError("Lịch tự cập nhật cần công tắc bật/tắt và giờ HH:MM hợp lệ.")
    app_updates = body.get("auto_app_updates", True)
    if type(app_updates) is not bool:
        raise ValueError("Cài đặt giao diện không hợp lệ.")
    return {"language": body["language"], "history_limits": dict(limits), "analysis_window": window,
            "auto_updates": {game: dict(value) for game, value in automatic.items()}, "auto_app_updates": app_updates}


def load_preferences(path):
    path = Path(path)
    if not path.exists():
        return default_preferences()
    return validate_preferences(json.loads(path.read_text(encoding="utf-8")))


def save_preferences(path, body):
    body = validate_preferences(body)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
