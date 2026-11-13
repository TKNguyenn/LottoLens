"""Read public LottoLens releases and verify the Windows setup before launch."""
from dataclasses import dataclass
from hashlib import sha256
from http.client import HTTPException
import json
import re
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__
from .sources import CancelledError

RELEASE_PAGE = "https://github.com/TKNguyenn/LottoLens/releases"
RELEASE_API = "https://api.github.com/repos/TKNguyenn/LottoLens/releases/latest"
MAX_SETUP_BYTES = 250 * 1024 * 1024


@dataclass(frozen=True)
class Release:
    version: str
    url: str = ""
    size: int = 0
    digest: str = ""


class ReleaseRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if req.full_url == RELEASE_API or target.scheme != "https" or target.netloc not in {
            "release-assets.githubusercontent.com", "objects.githubusercontent.com",
            "github-releases.githubusercontent.com",
        }:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_release():
    request = Request(RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "LottoLens/" + __version__})
    try:
        with build_opener(ReleaseRedirect()).open(request, timeout=12) as response:
            raw = response.read(1_000_001)
    except HTTPError as error:
        if error.code == 404:
            return {"status": "unpublished"}
        raise ValueError(f"Kiểm tra bản cập nhật thất bại (HTTP {error.code}).") from None
    except (URLError, OSError, HTTPException):
        raise ValueError("Không kết nối được với GitHub để kiểm tra cập nhật.") from None

    try:
        body = json.loads(raw) if len(raw) <= 1_000_000 else None
    except (ValueError, UnicodeError):
        body = None
    tag = body.get("tag_name") if isinstance(body, dict) else None
    match = re.fullmatch(r"[vV]?([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})", tag) if isinstance(tag, str) else None
    if not match:
        raise ValueError("GitHub trả thông tin bản phát hành không hợp lệ.")
    version = match[1]
    if body.get("draft") or body.get("prerelease") or tuple(map(int, version.split("."))) <= tuple(map(int, __version__.split("."))):
        return {"status": "current"}
    name = f"LottoLens-Setup-{version}.exe"
    url = f"{RELEASE_PAGE}/download/{tag}/{name}"
    assets = body.get("assets")
    for asset in assets if isinstance(assets, list) else ():
        if not isinstance(asset, dict):
            continue
        size, digest = asset.get("size"), asset.get("digest")
        if (asset.get("name") == name and asset.get("state") == "uploaded" and asset.get("browser_download_url") == url
                and type(size) is int and 0 < size <= MAX_SETUP_BYTES
                and isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", digest)):
            return {"status": "available", "release": Release(version, url, size, digest[7:])}
    return {"status": "available", "release": Release(version)}


def download_setup(release, path, cancel, progress):
    checksum, count = sha256(), 0
    deadline = monotonic() + 300
    partial = path.with_suffix(".part")
    try:
        request = Request(release.url, headers={"User-Agent": "LottoLens/" + __version__})
        with build_opener(ReleaseRedirect()).open(request, timeout=15) as response, partial.open("xb") as file:
            while True:
                if cancel():
                    raise CancelledError("Đã hủy tải bản cập nhật.")
                if monotonic() > deadline:
                    raise ValueError("Hết thời gian tải bản cập nhật.")
                chunk = response.read1(256 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > release.size:
                    raise ValueError("Kích thước bộ cài tải về không khớp với GitHub.")
                checksum.update(chunk)
                file.write(chunk)
                progress(count, release.size)
        if count != release.size or checksum.hexdigest() != release.digest:
            raise ValueError("Bộ cài tải về không khớp mã SHA-256 hoặc kích thước trên GitHub.")
        partial.replace(path)
    except (URLError, TimeoutError, HTTPException):
        raise ValueError("Không kết nối được với GitHub để tải bộ cài.") from None
    finally:
        partial.unlink(missing_ok=True)
