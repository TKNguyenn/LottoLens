"""Offline contract checks for the explicit model-list request."""
import json
from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai import AIConfig
from app.model_catalog import fetch_models
from app.sources import CancelledError


def main():
    config = AIConfig(base_url="https://provider.example/custom/v1/", model="", api_key="local-secret")
    response = BytesIO(json.dumps({"data": [{"id": "z-model"}, {"id": "a-model"}, {"id": "z-model"}]}).encode())
    with patch("app.model_catalog.build_opener") as opener:
        opener.return_value.open.return_value = response
        assert fetch_models(config) == {"models": ["a-model", "z-model"]}
        request = opener.return_value.open.call_args.args[0]
        assert request.full_url == "https://provider.example/custom/v1/models"
        assert request.get_method() == "GET" and request.data is None
        assert request.get_header("Authorization") == "Bearer local-secret"
        assert opener.return_value.open.call_count == 1

    with patch("app.model_catalog.build_opener") as opener:
        opener.return_value.open.return_value = BytesIO(b'{"data":[{"id":"default-model"}]}')
        assert fetch_models(AIConfig(api_key="local-secret"))["models"] == ["default-model"]
        assert opener.return_value.open.call_args.args[0].full_url == "https://api.openai.com/v1/models"

    # Router aliases confirmed by the user, including nested provider namespaces.
    router = "deepseek-v4.1-flash"
    aliases = ["deepseek-ai/deepseek-v4.1-flash-1017", "deepseek-v4.1-flash-1017",
               "deepseek-v4.1-flash-req", "creq/deepseek-v4.1-flash-req",
               "hada/deepseek-ai/deepseek-v4.1-flash-1017", "chib/deepseek-v4.1-flash",
               "opc/deepseek-v4.1-flash", "41/deepseek-v4.1-flash"]
    distinct = ["deepseek-v4.1-flash-thinking", "deepseek-v4.1-flash-lite", "deepseek-v4.1-flash-pro",
                "deepseek-v4.1-flash-9999", "deepseek-v4.2-flash", "gpt-6.1-sol",
                "gemini-3.8-flash", "gpt-6-astra", "gpt-6-astra-1017", "custom/only-model"]
    for names, expected in (
        ([router, *aliases, *distinct, "cx/gpt-6.1-sol"], [router, *distinct]),
        # Without the main router, dated/req bare IDs still hide their own prefixed copies.
        (aliases + distinct, [aliases[1], aliases[2], *aliases[5:], *distinct]),
        (["cx/gpt-6.1-sol", "gpt-6.1-sol"], ["gpt-6.1-sol"]),
        (["cx/gpt-6.1-sol"], ["cx/gpt-6.1-sol"]),
        (["gpt-6.1-sol", "cx/gpt-6.1-sol", "vendor/cx/gpt-6.1-sol", "other/gpt-6.1-sol",
          "gpt-6.1-sol-mini", "gpt-6.1-sol-pro", "gpt-6.1-sol-thinking", "gpt-6-sol"],
         ["gpt-6.1-sol", "gpt-6.1-sol-mini", "gpt-6.1-sol-pro", "gpt-6.1-sol-thinking", "gpt-6-sol"]),
        (["gemini-3.8-flash", "vendor/gemini-3.8-flash", "one/two/gemini-3.8-flash",
          "claude-model", "vendor/claude-model", "my-router", "vendor/my-router",
          "my-router-pro", "vendor/only-available"],
         ["gemini-3.8-flash", "claude-model", "my-router", "my-router-pro", "vendor/only-available"]),
        (["org/model", "provider/org/model", "other/provider/org/model"], ["org/model"]),
        (["model", "org/model", "provider/org/model"], ["model"]),
    ):
        for ordered in (names, list(reversed(names))):
            with patch("app.model_catalog.build_opener") as opener:
                opener.return_value.open.return_value = BytesIO(json.dumps({"data": [{"id": name} for name in ordered]}).encode())
                assert fetch_models(config)["models"] == sorted(set(expected)), names
                assert opener.return_value.open.call_count == 1
    with patch("app.model_catalog.build_opener") as opener:
        opener.return_value.open.return_value = BytesIO(b'{"data":[{"id":"late-model"}]}')
        cancelled = iter((False, True))
        try:
            fetch_models(config, cancel=lambda: next(cancelled))
        except CancelledError:
            pass
        else:
            raise AssertionError("Cancelled response used")
        assert opener.return_value.open.call_count == 1
    with patch("app.model_catalog.build_opener") as opener:
        try:
            fetch_models(AIConfig(api_key="local-secret\n"))
        except ValueError as error:
            assert "local-secret" not in str(error)
        else:
            raise AssertionError("Invalid header accepted")
        opener.assert_not_called()

    for body in (b"no json", b'{}', b'{"data":[]}', b'{"data":[{}]}', b'{"data":[{"id":1}]}',
                 b'{"data":[{"id":""}]}', b'x' * 2_000_001):
        with patch("app.model_catalog.build_opener") as opener:
            opener.return_value.open.return_value = BytesIO(body)
            try:
                fetch_models(config)
            except ValueError as error:
                assert "local-secret" not in str(error)
            else:
                raise AssertionError("Invalid response accepted")
            assert opener.return_value.open.call_count == 1

    for failure in (HTTPError(config.base_url, 401, "local-secret", {}, None),
                    HTTPError(config.base_url, 302, "redirect", {"Location": "https://elsewhere.example"}, None),
                    URLError("local-secret"), TimeoutError("local-secret")):
        with patch("app.model_catalog.build_opener") as opener:
            opener.return_value.open.side_effect = failure
            try:
                fetch_models(config)
            except ValueError as error:
                assert "local-secret" not in str(error)
            else:
                raise AssertionError("Network failure accepted")
            assert opener.return_value.open.call_count == 1

    with patch("app.model_catalog.build_opener") as opener:
        for url in ("http://provider.example/v1", "https://u:p@provider.example/v1", "https://provider.example/v1?q=key", "https://provider.example/v1#key"):
            try:
                fetch_models(AIConfig(base_url=url, api_key="local-secret"))
            except ValueError:
                pass
            else:
                raise AssertionError("Unsafe URL accepted")
        for cancelled in (True,):
            try:
                fetch_models(config, cancel=lambda: cancelled)
            except CancelledError:
                pass
            else:
                raise AssertionError("Cancelled request sent")
        opener.assert_not_called()
    # Exercise Qt's real worker wiring, without a provider or user files.
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from tempfile import TemporaryDirectory
    from time import monotonic, sleep
    from PySide6.QtWidgets import QApplication
    from app.ui import Desktop
    application = QApplication.instance() or QApplication([])
    def idle(window):
        end = monotonic() + 3
        while window.worker is not None and monotonic() < end:
            application.processEvents(); sleep(.005)
        assert window.worker is None
    with TemporaryDirectory() as directory:
        folder = Path(directory)
        with patch("app.ui.fetch_models") as fetch:
            window = Desktop(folder / "db.sqlite3", folder / "config.json")
            window.history_poll.stop()
            fetch.assert_not_called()
            window.key.setText("local-secret")
            window.model.setCurrentText("manual-model")
            window.nav.setCurrentRow(6)
            for language, button_text in (("vi", "Tải danh sách model"), ("en", "Fetch models")):
                window.apply_language(language)
                for theme in ("light", "dark"):
                    window.set_theme(theme)
                    assert window.fetch_models_button.text() == button_text
                    assert window.fetch_models_button.property("iconName") == "download"
                    fetch.return_value = {"models": ["a-model", "z-model"]}
                    previous = fetch.call_count
                    window.fetch_models_button.click()
                    assert not window.fetch_models_button.isEnabled() and not window.model.isEnabled()
                    assert not window.base.isEnabled() and not window.key.isEnabled()
                    idle(window)
                    assert fetch.call_count == previous + 1
                    assert window.model.currentText() == "manual-model"
                    assert [window.model.itemText(i) for i in range(window.model.count())] == ["a-model", "z-model"]
                    window.apply_language("en" if language == "vi" else "vi")
                    assert window.model.currentText() == "manual-model"
                    assert [window.model.itemText(i) for i in range(window.model.count())] == ["a-model", "z-model"]
                    window.apply_language(language)
                    window.model.setCurrentIndex(1)
                    assert window.current_config().model == "z-model"
                    window.save_config()
                    assert json.loads((folder / "config.json").read_text())["model"] == "z-model"
                    window.model.setCurrentText("manual-model")
                    window.key.setText(window.key.text() + "x")
                    assert window.model.count() == 0 and window.model.currentText() == "manual-model"
            # Run the actual catalog filter through the UI's asynchronous worker.
            fetch.side_effect = fetch_models
            for current in (router, aliases[0]):
                for language in ("vi", "en"):
                    window.apply_language(language)
                    window.model.setCurrentText(current)
                    with patch("app.model_catalog.build_opener") as opener:
                        opener.return_value.open.return_value = BytesIO(json.dumps({
                            "data": [{"id": name} for name in [router, *aliases, "gpt-6.1-sol", "cx/gpt-6.1-sol", "vendor/cx/gpt-6.1-sol"]]
                        }).encode())
                        window.fetch_models_button.click(); idle(window)
                        assert opener.return_value.open.call_count == 1
                        assert [window.model.itemText(i) for i in range(window.model.count())] == [router, "gpt-6.1-sol"]
                        assert window.current_config().model == current
                        assert window.model.isEnabled() and window.fetch_models_button.isEnabled()
                    window.model.setCurrentIndex(0)
                    assert window.current_config().model == router
            window.model.setCurrentText("manual-model")
            fetch.side_effect = ValueError("Nhà cung cấp trả danh sách model trống. Bạn vẫn có thể nhập tên model.")
            window.fetch_models_button.click(); idle(window)
            assert "empty model list" in window.notice.text()
            assert window.model.currentText() == "manual-model"
            assert window.fetch_models_button.isEnabled()
            window.base.setText("https://other.example/v1")
            assert window.model.count() == 0
            window.close()
    print("Model catalog contract passed")


if __name__ == "__main__":
    main()
