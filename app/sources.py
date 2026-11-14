import csv
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import hashlib
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .domain import Draw, aware_time, utc_now, validate_draw
from .rules import BASE


class CancelledError(Exception):
    pass


class RateLimitError(ValueError):
    def __init__(self, retry_after=""):
        now = datetime.now(timezone.utc)
        self.retry_at = now + timedelta(hours=1)
        try:
            requested = (now + timedelta(seconds=int(retry_after)) if re.fullmatch(r"[0-9]+", retry_after)
                         else parsedate_to_datetime(retry_after))
            if requested.tzinfo is None:
                requested = requested.replace(tzinfo=timezone.utc)
            self.retry_at = max(self.retry_at, requested)
        except (ValueError, TypeError, OverflowError):
            pass
        deadline = self.retry_at.astimezone(timezone(timedelta(hours=7))).isoformat(timespec="seconds")
        super().__init__("Nguồn Vietlott trả HTTP 429; không thay đổi dữ liệu cũ. Chờ đến " + deadline + ".")


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return " ".join(x if isinstance(x, str) else x.text() for x in self.children)

    def findall(self, tag=None, *, css=None, identity=None):
        result = []
        if (tag is None or self.tag == tag) and (css is None or css in self.attrs.get("class", "").split()) and (identity is None or self.attrs.get("id") == identity):
            result.append(self)
        for child in self.children:
            if isinstance(child, Node):
                result.extend(child.findall(tag, css=css, identity=identity))
        return result


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Node(); self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs); self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]; break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def _date_bucket(text):
    match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
    if not match:
        raise ValueError("Nguồn không có ngày quay hợp lệ.")
    # A date-only source supplies an ordering bucket, never an invented draw/publication time.
    value = datetime.strptime(match[1], "%d/%m/%Y").replace(tzinfo=timezone(timedelta(hours=7)))
    return value.astimezone(timezone.utc).isoformat()


def _make_draw(rule, container, source_url, raw_hash):
    text = container.text()
    identifier = re.search(r"#\s*(\d+)", text)
    if not identifier:
        raise ValueError("Nguồn không có mã kỳ quay.")
    spans = container.findall("span", css="bong_tron_bingo" if rule.kind == "dice" else "bong_tron")
    values = [s.text().strip() for s in spans]
    if any(not x.isascii() or not x.isdigit() for x in values):
        raise ValueError("Cấu trúc số kết quả đã thay đổi.")
    if rule.kind == "triples":
        if len(values) != 60:
            raise ValueError("Kết quả Max 3D phải có 20 bộ ba chữ số.")
        triples = ["".join(values[i:i+3]) for i in range(0, 60, 3)]
        payload = {"groups": {"special": triples[:2], "first": triples[2:6],
                              "second": triples[6:12], "third": triples[12:20]}}
    else:
        expected = rule.drawn + (1 if rule.special_max else 0)
        if len(values) != expected:
            raise ValueError(f"Nguồn trả {len(values)} số thay vì {expected}; không lưu kết quả thiếu.")
        payload = {"main": [int(x) for x in values[:rule.drawn]]}
        if rule.special_max:
            payload["special"] = int(values[-1])
    payload["time_precision"] = "date"
    item = Draw(rule.game_id, rule.mode_id, rule.rule_version, identifier[1],
                _date_bucket(text), payload, source_url, utc_now(), raw_hash,
                verification_status="historical_rule_unverified")
    validate_draw(rule, item)
    return item


def parse_results(raw, rule, source_url):
    if not raw or len(raw) > 2_000_000:
        raise ValueError("Trang kết quả rỗng hoặc vượt giới hạn 2 MB.")
    raw_hash = hashlib.sha256(raw).hexdigest()
    page = Page(raw.decode("utf-8-sig", errors="strict")).root
    if rule.game_id in ("keno", "bingo18"):
        panels = page.findall(identity="divRightContent")
        panel = panels[0] if panels else page
        rows = [r for r in panel.findall("tr") if re.search(r"#\s*\d+", r.text())]
        if not rows:
            raise ValueError("Trang không có hàng kết quả; có thể hết phạm vi hoặc nguồn thay đổi.")
        return [_make_draw(rule, row, source_url, raw_hash) for row in rows]
    panels = page.findall(identity="divLeftContent")
    if not panels:
        panels = [node for node in page.findall(css="porlet") if node.findall(css="chitietketqua_title")]
    if not panels:
        raise ValueError("Không tìm thấy vùng kết quả chính thức.")
    panel = panels[0]
    headings = " ".join(x.text() for x in panel.findall("h4")).lower().replace(" ", "").replace("/", "")
    marker = {"mega": "mega6/45", "power": "power6/55", "lotto": "lotto5/35",
              "max3d": "max3d", "max3dpro": "max3dpro"}[rule.game_id]
    if marker.replace("/", "") not in headings:
        raise ValueError("Trang kết quả không khớp trò chơi được chọn.")
    return [_make_draw(rule, panel, source_url, raw_hash)]


def import_csv(raw, rule):
    if len(raw) > 20*1024*1024:
        raise ValueError("CSV vượt giới hạn 20 MB.")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"draw_id", "draw_date", "main"}.issubset(reader.fieldnames or ()):
        raise ValueError("CSV cần cột draw_id, draw_date, main; thêm special nếu trò có số đặc biệt.")
    if rule.kind != "set":
        raise ValueError("CSV bản này chỉ nhập trò tập số; Max/Bingo dùng nguồn chính thức.")
    items, ids = [], set()
    for line, row in enumerate(reader, 2):
        try:
            date = datetime.strptime(row["draw_date"], "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=7)))
            payload = {"main": [int(x) for x in row["main"].replace(",", " ").split()], "time_precision": "date"}
            if rule.special_max:
                payload["special"] = int(row.get("special", ""))
            item = Draw(rule.game_id, rule.mode_id, rule.rule_version, row["draw_id"].strip(),
                        date.astimezone(timezone.utc).isoformat(), payload,
                        "manual:csv", utc_now(), hashlib.sha256(raw).hexdigest(),
                        verification_status="manual_unverified")
            validate_draw(rule, item)
            if item.draw_id in ids:
                raise ValueError("Mã kỳ trùng trong file.")
            ids.add(item.draw_id); items.append(item)
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f"CSV dòng {line}: {error}") from None
    if not items:
        raise ValueError("CSV không có dữ liệu.")
    return items


class OfficialSource:
    def __init__(self, cache_dir=None, max_attempts=3):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise ValueError("Số lần kết nối phải từ 1 đến 3.")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.max_attempts = max_attempts
        self._request_interval = 0
        self._next_request_at = 0

    def _cache(self, raw):
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / (hashlib.sha256(raw).hexdigest()+".bin")).write_bytes(raw)

    def _request(self, url, *, method=None, payload=None, cancel=lambda: False):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"vietlott.vn", "www.vietlott.vn"} or parsed.username or parsed.password:
            raise ValueError("Bộ tải chính thức chỉ truy cập HTTPS của Vietlott.")
        headers = {"User-Agent": "VietlottDesktop/0.1 (personal history reader)", "Referer": BASE + "/"}
        data = None
        if method:
            headers.update({"X-AjaxPro-Method": method, "Content-Type": "text/plain; charset=utf-8"})
            data = json.dumps(payload).encode("utf-8")
        for attempt in range(self.max_attempts):
            while self._request_interval and time.monotonic() < self._next_request_at:
                if cancel():
                    raise CancelledError("Đã hủy tải; dữ liệu đang lưu không bị thay đổi.")
                time.sleep(min(.1, max(0, self._next_request_at - time.monotonic())))
            if cancel():
                raise CancelledError("Đã hủy tải; dữ liệu đang lưu không bị thay đổi.")
            self._next_request_at = time.monotonic() + self._request_interval
            try:
                with urlopen(Request(url, data=data, headers=headers), timeout=15) as response:
                    if urlparse(response.url).hostname not in {"vietlott.vn", "www.vietlott.vn"}:
                        raise ValueError("Nguồn chuyển hướng ngoài host chính thức.")
                    raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError("Nguồn trả dữ liệu quá giới hạn 2 MB.")
                self._cache(raw)
                return raw
            except HTTPError as error:
                if error.code == 429:
                    raise RateLimitError(error.headers.get("Retry-After", "") if error.headers else "") from None
                if error.code not in (500, 502, 503, 504) or attempt == self.max_attempts - 1:
                    raise ValueError(f"Nguồn Vietlott trả HTTP {error.code}; không thay đổi dữ liệu cũ.") from None
                retry_after = error.headers.get("Retry-After", "")
                if retry_after and (not retry_after.isdigit() or int(retry_after) > 30):
                    raise ValueError("Nguồn yêu cầu chờ lâu; hãy cập nhật lại sau.") from None
                delay = int(retry_after) if retry_after else attempt+1
            except (URLError, TimeoutError, OSError):
                if attempt == self.max_attempts - 1:
                    raise ValueError(f"Không kết nối được Vietlott sau {self.max_attempts} lần; vẫn giữ lịch sử cũ.") from None
                delay = attempt+1
            for _ in range(delay*10):
                if cancel():
                    raise CancelledError("Đã hủy tải.")
                time.sleep(.1)

    def _ajax(self, path, method, payload, cancel):
        raw = self._request(BASE+path, method=method, payload=payload, cancel=cancel)
        envelope = json.loads(raw.decode("utf-8-sig"))
        value = envelope.get("value")
        if not isinstance(value, dict) or value.get("Error"):
            raise ValueError("Vietlott không trả kết quả hợp lệ cho yêu cầu này.")
        return value

    def fetch_history(self, rule, limit=30, cancel=lambda: False, progress=lambda done, total: None, known_draws=()):
        if type(limit) is not int or not 1 <= limit <= 2000:
            raise ValueError("Mỗi lần tải từ 1 đến 2000 kỳ; có thể tiếp tục ở lần sau.")
        known_draws = list(known_draws)
        for draw in known_draws:
            validate_draw(rule, draw)
        known_ids = {draw.draw_id for draw in known_draws}
        if len(known_ids) < limit:
            known_ids = set()

        def overlap_index(records):
            return next((i for i, draw in enumerate(records[:limit]) if draw.draw_id in known_ids), None)

        fast = rule.game_id in ("keno", "bingo18")
        self._request_interval = 2 if fast else 0
        url = BASE+rule.result_path
        raw = self._request(url, cancel=cancel)
        self._cache(raw)
        items = parse_results(raw, rule, url)
        items.sort(key=lambda item: (aware_time(item.draw_at_utc), int(item.draw_id), item.draw_id), reverse=True)
        render = None
        seen = {x.draw_id for x in items}
        page_index = -1 if rule.game_id in ("keno", "bingo18") else 0
        total_rows = 0
        reached_end = False
        source_day = aware_time(items[0].draw_at_utc).astimezone(timezone(timedelta(hours=7)))
        empty_days = 0
        detail_class = key = None
        boundary = overlap_index(items)
        while len(items) < limit and boundary is None:
            if cancel():
                raise CancelledError("Đã hủy tải; chưa ghi batch vào dữ liệu chính.")
            if render is None:
                render = self._ajax("/ajaxpro/Vietlott.Utility.WebEnvironments,Vietlott.Utility.ashx",
                                    "ServerSideFrontEndCreateRenderInfo", {"SiteId": "main.frontend.vi"}, cancel)
                render["SiteLang"] = "vi"
            if rule.game_id in ("keno", "bingo18"):
                page_index += 1
                kind = "Keno" if rule.game_id == "keno" else "Bingo"
                data = {"ORenderInfo": render, "GameId": "6" if kind == "Keno" else "8",
                        "GameDrawNo": "", "number": "",
                        "DrawDate": source_day.strftime("%d/%m/%Y") if kind == "Keno" else "",
                        "PageIndex": page_index, "TotalRow": total_rows}
                if kind == "Keno":
                    data.update({"ProcessType": 0, "OddEven": 2, "UpperLower": 2})
                result = self._ajax(f"/ajaxpro/Vietlott.PlugIn.WebParts.Game{kind}CompareWebPart,Vietlott.PlugIn.WebParts.ashx",
                                    "ServerSideDrawResult", data, cancel)
                raw = result.get("HtmlContent", "").encode("utf-8")
                total_rows = result.get("RetNumber", 0)
                if "#" not in Page(raw.decode()).root.text():
                    if kind == "Keno" and empty_days < 7:
                        source_day -= timedelta(days=1)
                        page_index = -1
                        total_rows = 0
                        empty_days += 1
                        continue
                    reached_end = True; break
            else:
                text = raw.decode("utf-8")
                previous = re.search(r"btn_chuyendulieu_left[^>]*href=\"javascript:ClientDrawResult\('([^']+)'", text)
                if not previous:
                    reached_end = True; break
                if previous[1] in seen:
                    raise ValueError("Nguồn trả lại kỳ đã tải; dừng để tránh vòng lặp.")
                proxy = re.search(r"(Game\w+ResultDetailWebPart)\.ServerSideDrawResult\(ORenderInfo,'([^']+)'", text)
                if proxy:
                    detail_class, key = proxy[1], proxy[2]
                elif detail_class is None:
                    raise ValueError("Không đọc được cơ chế tải kỳ trước từ nguồn chính thức.")
                result = self._ajax(f"/ajaxpro/Vietlott.PlugIn.WebParts.{detail_class},Vietlott.PlugIn.WebParts.ashx",
                                    "ServerSideDrawResult", {"ORenderInfo": render, "Key": key, "DrawId": previous[1]}, cancel)
                raw = ("<div id='divLeftContent'>" + result.get("RetExtraParam1", "") + "</div>" + result.get("RetExtraParam2", "")).encode("utf-8")
            self._cache(raw)
            incoming = parse_results(raw, rule, url)
            fresh = [item for item in incoming if item.draw_id not in seen]
            if not fresh:
                if rule.game_id in ("keno", "bingo18") and page_index == 0:
                    continue
                raise ValueError("Phân trang không cung cấp thêm kỳ mới; không thể khẳng định hết lịch sử.")
            items.extend(fresh); seen.update(x.draw_id for x in fresh)
            items.sort(key=lambda item: (aware_time(item.draw_at_utc), int(item.draw_id), item.draw_id), reverse=True)
            boundary = overlap_index(items)
            empty_days = 0
            progress(min(limit, len(items)), limit)
            time.sleep(.15)
        items.sort(key=lambda item: (aware_time(item.draw_at_utc), int(item.draw_id), item.draw_id), reverse=True)
        if cancel():
            raise CancelledError("Đã hủy tải; chưa ghi batch vào dữ liệu chính.")
        return {"draws": items[:boundary+1] if boundary is not None else items[:limit],
                "status": "known_boundary" if boundary is not None else "source_boundary" if reached_end else "requested_limit",
                "note": "Chỉ là phạm vi tải được, chưa chứng minh toàn bộ lịch sử. Keno có giới hạn tìm kiếm 6 tháng theo trang nguồn.",
                "source_url": url}
