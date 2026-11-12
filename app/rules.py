from dataclasses import replace
from .domain import RuleSpec

BASE = "https://vietlott.vn"
RULES = {
    "mega": RuleSpec("mega", "Mega 6/45", "set", 45, 6, 6,
        "/vi/trung-thuong/ket-qua-trung-thuong/645",
        BASE + "/vi/choi/mega-6-45/cach-choi", math_ready=True),
    "power": RuleSpec("power", "Power 6/55", "set", 55, 6, 6,
        "/vi/trung-thuong/ket-qua-trung-thuong/655",
        BASE + "/vi/choi/power-6-55/cach-choi", special_max=55,
        bonus_from_remainder=True, math_ready=True),
    "lotto": RuleSpec("lotto", "Lotto 5/35", "set", 35, 5, 5,
        "/vi/trung-thuong/ket-qua-trung-thuong/535",
        BASE + "/vi/choi/lotto535/cach-choi", special_max=12, math_ready=True),
    "keno": RuleSpec("keno", "Keno", "set", 80, 20, 6,
        "/vi/trung-thuong/ket-qua-trung-thuong/winning-number-keno",
        BASE + "/vi/choi/keno/cach-choi", mode_id="pick6", math_ready=True),
    "max3d": RuleSpec("max3d", "Max 3D", "triples", 1000, 20, 1,
        "/vi/trung-thuong/ket-qua-trung-thuong/max-3d",
        BASE + "/vi/choi/max3d/cach-choi", math_ready=True),
    "max3dpro": RuleSpec("max3dpro", "Max 3D Pro", "triples", 1000, 20, 2,
        "/vi/trung-thuong/ket-qua-trung-thuong/max-3dpro",
        BASE + "/vi/choi/max3dpro/cach-choi", math_ready=True),
    "bingo18": RuleSpec("bingo18", "Bingo18", "dice", 6, 3, 3,
        "/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18",
        BASE + "/vi/choi/bingo/cach-choi", math_ready=True),
}


def get_rule(game_id, mode_id=None):
    if game_id not in RULES:
        raise ValueError("Trò chơi chưa có trong danh mục.")
    rule = RULES[game_id]
    if game_id == "keno" and mode_id is not None:
        if not mode_id.startswith("pick") or not mode_id[4:].isdigit() or not 1 <= int(mode_id[4:]) <= 10:
            raise ValueError("Keno hỗ trợ chọn từ 1 đến 10 số.")
        return replace(rule, mode_id=mode_id, selected=int(mode_id[4:]))
    if mode_id is not None and mode_id != rule.mode_id:
        raise ValueError("Biến thể chưa hỗ trợ; không dùng luật biến thể khác thay thế.")
    return rule
