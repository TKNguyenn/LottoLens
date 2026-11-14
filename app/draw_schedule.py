"""Normal Vietnam draw schedules with a publication buffer for history checks."""
from datetime import timedelta

# Weekday indices follow datetime.weekday().
WEEKLY = {"mega": (2, 4, 6), "power": (1, 3, 5), "max3d": (0, 2, 4), "max3dpro": (1, 3, 5)}
# First draw minute after midnight, interval, and number of draws per day.
FAST = {"keno": (6 * 60 + 8, 8, 119), "bingo18": (6 * 60 + 5, 6, 159)}
FAST_PUBLICATION_BUFFER = {"keno": 4, "bingo18": 8}
DRAW_MODE = "draw"
CUSTOM_MODE = "custom"


def _clock(minute):
    return f"{minute // 60:02}:{minute % 60:02}"


PRESET_LABELS = {
    "mega": "Thứ Tư, Sáu và Chủ nhật · 18:45",
    "power": "Thứ Ba, Năm và Bảy · 18:45",
    "max3d": "Thứ Hai, Tư và Sáu · 18:45",
    "max3dpro": "Thứ Ba, Năm và Bảy · 18:45",
    "lotto": "Hằng ngày · 13:15 và 21:15",
    **{game: f"Hằng ngày · mỗi {interval} phút, {_clock(first + FAST_PUBLICATION_BUFFER[game])}–"
              f"{_clock(first + FAST_PUBLICATION_BUFFER[game] + interval * (count - 1))}"
       for game, (first, interval, count) in FAST.items()},
}


def triggers(game, value):
    """Return (start time, weekdays, repetition minutes, duration minutes)."""
    if value.get("mode", CUSTOM_MODE) == CUSTOM_MODE:
        return ((value["time"], (), 0, 0),)
    if game in WEEKLY:
        return (("18:45", WEEKLY[game], 0, 0),)
    if game == "lotto":
        return (("13:15", (), 0, 0), ("21:15", (), 0, 0))
    first, interval, count = FAST[game]
    return ((_clock(first + FAST_PUBLICATION_BUFFER[game]), (), interval, (count - 1) * interval + 1),)


def active_slot(game, value, instant):
    """Find the due slot, allowing a short scheduler startup delay."""
    for start, weekdays, interval, duration in triggers(game, value):
        if weekdays and instant.weekday() not in weekdays:
            continue
        hour, minute = map(int, start.split(":"))
        boundary = instant.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elapsed = (instant - boundary) // timedelta(minutes=1)
        if elapsed < 0:
            continue
        offset = elapsed // interval * interval if interval else 0
        if elapsed - offset < 5 and offset < max(1, duration):
            return boundary + timedelta(minutes=offset)
    return None
