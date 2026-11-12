from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def snapshot_hash(rule_body, draw_bodies):
    return digest({"rule": rule_body, "draws": draw_bodies})


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def aware_time(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Thời điểm phải có định dạng ISO 8601.") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Thời điểm phải có múi giờ.")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class RuleSpec:
    game_id: str
    name: str
    kind: str
    population: int
    drawn: int
    selected: int
    result_path: str
    rules_url: str
    mode_id: str = "normal"
    rule_version: str = "observed-2026-11-09"
    price_vnd: int = 10_000
    special_max: int = 0
    bonus_from_remainder: bool = False
    math_ready: bool = False
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass
class Draw:
    game_id: str
    mode_id: str
    rule_version: str
    draw_id: str
    draw_at_utc: str
    payload: dict
    source_url: str
    fetched_at_utc: str
    raw_sha256: str
    published_at_utc: str | None = None
    revision: int = 1
    verification_status: str = "source_snapshot"


@dataclass
class Ticket:
    game_id: str
    mode_id: str
    rule_version: str
    selections: dict
    units: int = 1
    cost_vnd: int = 10_000


@dataclass
class EvalResult:
    matched_by_component: dict
    prize_tiers: list[str]
    payout_vnd: int | None
    payout_status: str
    details: str = ""


def _identity(rule, item):
    if (item.game_id, item.mode_id, item.rule_version) != (rule.game_id, rule.mode_id, rule.rule_version):
        raise ValueError("Trò chơi, biến thể hoặc phiên bản luật không khớp.")


def _numbers(values, count, maximum, *, unique=True):
    if not isinstance(values, (list, tuple)) or len(values) != count:
        raise ValueError(f"Cần đúng {count} số.")
    if any(type(x) is not int or not 1 <= x <= maximum for x in values):
        raise ValueError(f"Số phải là số nguyên từ 1 đến {maximum}.")
    if unique and len(set(values)) != len(values):
        raise ValueError("Không được lặp số trong thành phần này.")


def validate_draw(rule, draw):
    _identity(rule, draw)
    if not isinstance(draw.draw_id, str) or not draw.draw_id.strip():
        raise ValueError("Thiếu mã kỳ quay.")
    timestamp = aware_time(draw.draw_at_utc)
    aware_time(draw.fetched_at_utc)
    if draw.published_at_utc is not None:
        aware_time(draw.published_at_utc)
    if rule.effective_from and timestamp < aware_time(rule.effective_from):
        raise ValueError("Kỳ quay trước ngày hiệu lực luật.")
    if rule.effective_to and timestamp >= aware_time(rule.effective_to):
        raise ValueError("Kỳ quay sau thời hạn luật.")
    if not isinstance(draw.payload, dict):
        raise ValueError("Kết quả phải là object.")
    if rule.kind == "triples":
        groups = draw.payload.get("groups", {})
        if set(groups) != {"special", "first", "second", "third"}:
            raise ValueError("Thiếu nhóm giải Max 3D.")
        for key, size in (("special", 2), ("first", 4), ("second", 6), ("third", 8)):
            if len(groups[key]) != size or any(not isinstance(x, str) or len(x) != 3 or not x.isascii() or not x.isdigit() for x in groups[key]):
                raise ValueError("Nhóm giải phải giữ chuỗi ba chữ số, kể cả số 0 đầu.")
    else:
        _numbers(draw.payload.get("main"), rule.drawn, rule.population, unique=rule.kind != "dice")
        if rule.special_max:
            special = draw.payload.get("special")
            _numbers([special], 1, rule.special_max)
            if rule.bonus_from_remainder and special in draw.payload["main"]:
                raise ValueError("Số bonus phải khác các số chính.")


def validate_ticket(rule, ticket):
    _identity(rule, ticket)
    if type(ticket.units) is not int or ticket.units != 1 or ticket.cost_vnd != rule.price_vnd:
        raise ValueError("Bản hiện tại chỉ nhận một đơn vị vé cơ bản đúng mệnh giá.")
    if not isinstance(ticket.selections, dict):
        raise ValueError("Lựa chọn phải là object.")
    if rule.kind == "triples":
        values = ticket.selections.get("main", [])
        if set(ticket.selections) != {"main"} or not isinstance(values, (list, tuple)) or len(values) != rule.selected or any(not isinstance(x, str) or len(x) != 3 or not x.isascii() or not x.isdigit() for x in values):
            raise ValueError("Cần bộ ba chữ số đúng định dạng.")
    elif rule.kind == "dice":
        from .gameplay import validate_bingo
        validate_bingo(ticket.selections)
    else:
        _numbers(ticket.selections.get("main"), rule.selected, rule.population)
        if rule.game_id == "lotto":
            _numbers([ticket.selections.get("special")], 1, rule.special_max)
