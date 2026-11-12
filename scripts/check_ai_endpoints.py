"""Offline endpoint negotiation and complete-output checks, no provider credentials."""
from io import BytesIO
import json
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import ai
from app.ai_protocols import completion_body, completion_result, completion_sse
from app.sources import CancelledError


def response(body, stream=False):
    value = BytesIO(body if isinstance(body, bytes) else json.dumps(body).encode())
    value.headers = {"Content-Type": "text/event-stream" if stream else "application/json"}
    return value


def missing(code=404, body=b'{"error":{"message":"Unknown endpoint","code":"endpoint_not_found"}}'):
    return HTTPError("https://provider.example/v1/responses", code, "error", {}, BytesIO(body))


def lines(events):
    return [line for item in events for line in [("data: " + (item if isinstance(item, str) else json.dumps(item)) + "\n").encode(), b"\n"]]


def main():
    config = ai.AIConfig(base_url="https://provider.example/custom/v1", model="router-model", api_key="local-secret")
    def run(effects, **kwargs):
        ai._ENDPOINT_CACHE.clear()
        with patch("app.ai.build_opener") as opener:
            opener.return_value.open.side_effect = effects
            result = ai.test_model(config, **kwargs)
            requests = [call.args[0] for call in opener.return_value.open.call_args_list]
            return result, requests
    chat = {"id": "chat-id", "model": "served-model", "choices": [{"index": 0, "message": {"content": "OK"}, "finish_reason": "stop"}], "usage": {"total_tokens": 3}}
    legacy = {"id": "cmpl-id", "model": "served-model", "choices": [{"index": 0, "text": "OK", "finish_reason": "stop"}]}
    good = {"status": "completed", "output_text": "OK", "model": "served-model"}
    result, requests = run([response(good)])
    assert result["api_endpoint"] == "responses" and len(requests) == 1
    result, requests = run([missing(), response(chat)])
    assert result["text"] == "OK" and result["api_endpoint"] == "chat/completions"
    assert [r.full_url for r in requests] == [config.base_url + "/responses", config.base_url + "/chat/completions"]
    assert json.loads(requests[1].data)["messages"][1] == {"role": "user", "content": "Chỉ trả lời OK."}
    assert "local-secret" not in result["notice"]
    result, requests = run([missing(405), missing(), response(legacy)])
    assert result["api_endpoint"] == "completions" and len(requests) == 3
    assert "prompt" in json.loads(requests[-1].data)

    for error in [missing(code) for code in (400, 401, 403, 408, 409, 422, 429, 500, 502, 503)] + [
        missing(404, b'{"error":{"code":"model_not_found","message":"No model router-model"}}'),
        missing(404, b'{"error":{"message":"Invalid key local-secret"}}'),
        missing(404, b'{"detail":"unexpected resource"}'), URLError("local-secret"), TimeoutError("local-secret"),
    ]:
        ai._ENDPOINT_CACHE.clear()
        with patch("app.ai.build_opener") as opener:
            opener.return_value.open.side_effect = error
            try:
                ai.test_model(config)
            except ValueError as failure:
                assert "local-secret" not in str(failure)
            else:
                raise AssertionError("Failed request accepted")
            assert opener.return_value.open.call_count == 1

    for error in (missing(404, b'{"detail":"Not Found"}'), missing(404, b'<html><title>404 Not Found</title></html>'),
                  missing(404, b'{"error":{"code":"unsupported_endpoint","message":"API unavailable"}}')):
        result, requests = run([error, response(chat)])
        assert result["api_endpoint"] == "chat/completions" and len(requests) == 2

    ai._ENDPOINT_CACHE.clear()
    with patch("app.ai.build_opener") as opener:
        opener.return_value.open.side_effect = [missing(), missing(), missing()]
        try:
            ai.test_model(config)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported endpoints accepted")
        assert opener.return_value.open.call_count == 3 and not ai._ENDPOINT_CACHE

    # Cache only successful endpoints and isolate it by credentials/model/base URL and feature needs.
    ai._ENDPOINT_CACHE.clear()
    with patch("app.ai.build_opener") as opener:
        opener.return_value.open.side_effect = [missing(), response(chat), response(chat)]
        ai.test_model(config); ai.test_model(config)
        assert [c.args[0].full_url for c in opener.return_value.open.call_args_list] == [
            config.base_url + "/responses", config.base_url + "/chat/completions", config.base_url + "/chat/completions"]
        opener.return_value.open.side_effect = [response(good)]
        ai.test_model(ai.AIConfig(base_url=config.base_url, model=config.model, api_key="different-key"))
        assert opener.return_value.open.call_args.args[0].full_url.endswith("/responses")
        for alternate in (ai.AIConfig(base_url="https://other.example/v1", model=config.model, api_key=config.api_key),
                          ai.AIConfig(base_url=config.base_url, model="other-model", api_key=config.api_key)):
            opener.return_value.open.side_effect = [response(good)]
            ai.test_model(alternate)
            assert opener.return_value.open.call_args.args[0].full_url.endswith("/responses")
        opener.return_value.open.side_effect = [response(good)]
        ai.search(config, "Find official sources")
        web_request = opener.return_value.open.call_args.args[0]
        assert web_request.full_url.endswith("/responses") and "tools" in json.loads(web_request.data)

    body = ai.build_request(config, "query", web_search=False)[2]
    body["reasoning"] = {"effort": "high"}
    assert completion_body(body, "chat/completions")["reasoning_effort"] == "high"
    web_body = ai.build_request(config, "query")[2]
    assert completion_body(web_body, "chat/completions")["web_search_options"] == {}
    for unsupported in (body, web_body):
        try:
            completion_body(unsupported, "completions")
        except ValueError:
            pass
        else:
            raise AssertionError("Legacy endpoint silently dropped requested features")
        ai._ENDPOINT_CACHE.clear()
        with patch("app.ai.build_opener") as opener:
            opener.return_value.open.side_effect = [missing(), missing()]
            url, headers, _ = ai.build_request(config, "query", web_search=False)
            try:
                ai._send(url, headers, unsupported)
            except ValueError:
                pass
            else:
                raise AssertionError("Unsupported legacy features were accepted")
            assert opener.return_value.open.call_count == 2

    for protocol, field in (("chat/completions", "delta"), ("completions", "text")):
        def event(text, finish=None):
            content = {"content": text} if field == "delta" else text
            return {"id": "id", "model": "served-model", "choices": [{"index": 0, field: content, "finish_reason": finish}]}
        deltas = []
        data = completion_sse(lines([event("O"), event("K", "stop"), {"choices": [], "usage": {"total_tokens": 3}}, "[DONE]"]), protocol, on_delta=deltas.append)
        assert ai.parse_response(data)["text"] == "OK" and deltas == ["O", "K"]
        assert data["id"] == "id" and data["model"] == "served-model" and data["usage"] == {"total_tokens": 3}
        for events in ([event("partial")], [event("partial"), "[DONE]"], [event("partial", "length"), "[DONE]"],
                       [event("partial", "stop")], [event("partial"), {"error": {"message": "bad"}}],
                       [event("partial", "stop"), event("extra"), "[DONE]"], ["not-json"]):
            try:
                completion_sse(lines(events), protocol)
            except ValueError:
                pass
            else:
                raise AssertionError("Incomplete/error stream accepted")

    for protocol, sample in (("chat/completions", chat), ("completions", legacy)):
        for finish in (None, "length", "content_filter", "tool_calls"):
            bad = {**sample, "choices": [{**sample["choices"][0], "finish_reason": finish}]}
            try:
                completion_result(bad, protocol)
            except ValueError:
                pass
            else:
                raise AssertionError("Incomplete JSON accepted")

    for broken in (response(b"not json"), response({"status": "incomplete", "output_text": "partial"}),
                   response(b'data: {"type":"response.output_text.delta","delta":"partial"}\n\n', True)):
        try:
            run([broken])
        except ValueError:
            assert not ai._ENDPOINT_CACHE
        else:
            raise AssertionError("Bad response was accepted")

    for failed in (response(b'data: {"choices":[{"delta":{"content":"partial"},"index":0}]}\n\n', True),
                   response({**chat, "choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]}),
                   response(b"not-json")):
        ai._ENDPOINT_CACHE.clear()
        with patch("app.ai.build_opener") as opener:
            opener.return_value.open.side_effect = [missing(), failed]
            try:
                ai.test_model(config)
            except ValueError:
                pass
            else:
                raise AssertionError("Partial completion accepted")
            assert opener.return_value.open.call_count == 2, "Must stop after receiving a completion response"
            assert not ai._ENDPOINT_CACHE

    # AI suggestions keep High reasoning and validation over Chat Completions.
    from app.ai_generation import generate_with_ai
    from app.domain import Draw
    from app.rules import BASE, get_rule
    rule = get_rule("mega")
    at = "2026-11-12T00:00:00+00:00"
    history = [Draw(rule.game_id, rule.mode_id, rule.rule_version, str(i), at,
                    {"main": [1, 2, 3, 4, 5, 6]}, BASE+rule.result_path, at, "a"*64) for i in range(90)]
    ticket_text = json.dumps({"tickets": [{"main": [1, 2, 3, 4, 5, 6]}], "explanation": "Reference only"})
    ai._ENDPOINT_CACHE.clear()
    with patch("app.ai.build_opener") as opener:
        opener.return_value.open.side_effect = [missing(), response({**chat, "choices": [{
            "message": {"content": ticket_text}, "finish_reason": "stop"}]})]
        generated = generate_with_ai(config, rule, history, 1)
        assert len(generated["tickets"]) == 1 and generated["metadata"]["reasoning_effort"] == "high"
        assert generated["metadata"]["response_model"] == "served-model"
        sent = json.loads(opener.return_value.open.call_args.args[0].data)
        assert sent["reasoning_effort"] == "high" and "tools" not in sent
        assert "history" in sent["messages"][1]["content"] and "local-secret" not in str(generated)

    cancelled = iter((False, True))
    try:
        run([missing()], cancel=lambda: next(cancelled))
    except CancelledError:
        pass
    else:
        raise AssertionError("Cancellation must stop endpoint negotiation")
    ai._ENDPOINT_CACHE.clear()
    # Exercise actual native worker, localized notices, and display through all three APIs.
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from tempfile import TemporaryDirectory
    from time import monotonic, sleep
    from PySide6.QtWidgets import QApplication
    from app.ui import Desktop
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as directory:
        folder = Path(directory)
        window = Desktop(folder / "db.sqlite3", folder / "config.json")
        window.history_poll.stop(); window.base.setText(config.base_url); window.key.setText(config.api_key)
        window.nav.setCurrentRow(6)
        try:
            for language in ("vi", "en"):
                window.apply_language(language)
                for theme in ("light", "dark"):
                    window.set_theme(theme)
                    for protocol in ("responses", "chat/completions", "completions"):
                        ai._ENDPOINT_CACHE.clear()
                        effects = [response(good)] if protocol == "responses" else [missing(), response(chat)] if protocol == "chat/completions" else [missing(), missing(), response(legacy)]
                        with patch("app.ai.build_opener") as opener:
                            opener.return_value.open.side_effect = effects
                            window.test_button.click()
                            assert window.worker is not None and not window.test_button.isEnabled()
                            end = monotonic() + 3
                            while window.worker is not None and monotonic() < end:
                                application.processEvents(); sleep(.005)
                            assert window.worker is None and window.test_button.isEnabled()
                            assert window.answer.toPlainText() == "OK"
                            assert protocol in window.notice.text()
                            assert ("completed" if language == "en" else "hoàn tất") in window.notice.text()
                            assert window.history_table.rowCount() == 0
        finally:
            window.close()
    ai._ENDPOINT_CACHE.clear()
    print("Automatic AI endpoints contract passed")


if __name__ == "__main__":
    main()
