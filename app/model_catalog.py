"""One explicit OpenAI-compatible GET /models, separate from inference."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener

from .ai import _NoRedirect
from .sources import CancelledError


def fetch_models(config, cancel=lambda: False):
    parsed = urlparse(config.base_url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError("Base URL phải là HTTPS, không chứa tài khoản, query hoặc fragment.")
    if not config.api_key.strip():
        raise ValueError("Chưa có API key. Nhập tại máy trong phần cấu hình AI.")
    if any(not 32 <= ord(char) <= 126 for char in config.api_key):
        raise ValueError("API key chứa ký tự không hợp lệ.")
    if cancel():
        raise CancelledError("Đã hủy tải danh sách model.")
    request = Request(config.base_url.rstrip("/") + "/models", headers={
        "Authorization": "Bearer " + config.api_key.strip(), "Accept": "application/json",
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(2_000_001)
        if cancel():
            raise CancelledError("Đã hủy tải danh sách model.")
        if len(raw) > 2_000_000:
            raise ValueError("Danh sách model vượt giới hạn 2 MB.")
        body = json.loads(raw.decode("utf-8"))
    except HTTPError as error:
        raise ValueError(f"Tải danh sách model thất bại (HTTP {error.code}). Kiểm tra Base URL và API key; không tự thử lại.") from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("Không kết nối được để tải model. Không tự thử lại; bạn vẫn có thể nhập tên model.") from None
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError("Danh sách model không đúng định dạng OpenAI-compatible.") from None
    entries = body.get("data") if isinstance(body, dict) else None
    if not isinstance(entries, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("id"), str)
        or not item["id"].strip() or len(item["id"]) > 256 for item in entries
    ):
        raise ValueError("Danh sách model không đúng định dạng OpenAI-compatible.")
    ids = {item["id"] for item in entries}
    # Only these suffix aliases were confirmed by the router owner; other versions stay separate.
    aliases = {"deepseek-v4.1-flash-1017": "deepseek-v4.1-flash",
               "deepseek-v4.1-flash-req": "deepseek-v4.1-flash"}
    models = []
    for name in sorted(ids):
        parts = name.split("/")
        router = aliases.get(parts[-1], parts[-1])
        if router != name and router in ids:
            continue
        if any("/".join(parts[index:]) in ids for index in range(1, len(parts))):
            continue
        models.append(name)
    if not models:
        raise ValueError("Nhà cung cấp trả danh sách model trống. Bạn vẫn có thể nhập tên model.")
    return {"models": models}
