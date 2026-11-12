from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile

from .ai import AIConfig
from .paths import installed_data


CONFIG_PATH = (installed_data() or Path(__file__).resolve().parent.parent) / "config.json"


def save_settings(config, path=None):
    path = Path(path) if path else CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    body = asdict(config)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(body, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def load_settings(path=None):
    path = Path(path) if path else CONFIG_PATH
    if not path.exists():
        return AIConfig()
    body = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(body, dict) or set(body) != {"base_url", "api_key", "model"} or any(not isinstance(value, str) for value in body.values()):
        raise ValueError("config.json phải có ba chuỗi base_url, api_key, model.")
    return AIConfig(**body)
