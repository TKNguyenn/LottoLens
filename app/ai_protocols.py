"""Translate text-only requests and completed outputs for compatible legacy APIs."""
import json

from .sources import CancelledError


def endpoint_missing(error):
    if error.code not in (404, 405):
        return False
    raw = error.read(16_385)
    if len(raw) > 16_384:
        return False
    text = raw.decode("utf-8", errors="replace").strip().lower()
    # A 404 may describe a missing model/key rather than a missing route.
    if any(word in text for word in ("model", "key", "auth", "quota", "credit", "permission", "rate_limit")):
        return False
    if error.code == 405 or not text:
        return True
    try:
        body = json.loads(text)
        value = body.get("error", body) if isinstance(body, dict) else body
        if isinstance(value, dict):
            if value.get("code") in ("endpoint_not_found", "route_not_found", "unsupported_endpoint"):
                return True
            text = str(value.get("message") or value.get("detail") or value.get("code") or "")
        elif isinstance(value, str):
            text = value
    except ValueError:
        pass
    return text in ("not found", "404 not found", "404 page not found", "endpoint_not_found", "route_not_found") or (
        text.startswith("<") and "<title>404 not found</title>" in text) or (
        any(word in text for word in ("endpoint", "route"))
        and any(word in text for word in ("unknown", "not found", "unsupported", "not supported", "does not exist")))


def completion_body(body, protocol):
    if protocol == "responses":
        return body
    converted = {"model": body["model"], "stream": True}
    if protocol == "chat/completions":
        converted["messages"] = [{"role": "system", "content": body["instructions"]},
                                 {"role": "user", "content": body["input"]}]
        if body.get("reasoning"):
            converted["reasoning_effort"] = body["reasoning"]["effort"]
        if body.get("tools"):
            converted["web_search_options"] = {}
    else:
        if body.get("reasoning") or body.get("tools"):
            raise ValueError("Completions không hỗ trợ web search hoặc mức suy luận High. Hãy dùng model hỗ trợ Responses hoặc Chat Completions.")
        converted["prompt"] = body["instructions"] + "\n\n" + body["input"] + "\n\n"
    return converted


def completion_result(data, protocol):
    if not isinstance(data, dict) or data.get("error") or data.get("status") not in (None, "completed"):
        raise ValueError("API trả lỗi hoặc phản hồi chưa hoàn tất; nội dung đang thấy chỉ là một phần.")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("Phản hồi completion không đúng định dạng hoặc chưa hoàn tất.")
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        raise ValueError("Phản hồi completion chưa hoàn tất hoặc bị giới hạn; không tự gửi lại.")
    message = choice.get("message", {}) if protocol == "chat/completions" else {"content": choice.get("text")}
    if not isinstance(message, dict) or message.get("tool_calls") or message.get("function_call"):
        raise ValueError("Phản hồi completion không đúng định dạng hoặc chưa hoàn tất.")
    text = message.get("content")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("API không trả nội dung văn bản có thể đọc.")
    return {"status": "completed", "id": data.get("id"), "model": data.get("model"),
            "usage": data.get("usage", {}), "choices": [{"message": message}],
            "citations": data.get("citations", [])}


def completion_sse(lines, protocol, cancel=lambda: False, on_delta=lambda delta: None):
    pending, fragments, annotations, citations = [], [], [], []
    received, stopped = 0, False
    result = {"id": None, "model": None, "usage": {}}

    def consume():
        nonlocal stopped
        payload = "\n".join(pending); pending.clear()
        if not payload:
            return None
        if payload.strip() == "[DONE]":
            if not stopped:
                raise ValueError("Phản hồi completion chưa hoàn tất hoặc bị giới hạn; không tự gửi lại.")
            return completion_result({**result, "citations": citations, "choices": [{"finish_reason": "stop",
                "message": {"content": "".join(fragments), "annotations": annotations}}]}, "chat/completions")
        try:
            event = json.loads(payload)
        except ValueError:
            raise ValueError("Luồng AI có sự kiện không đúng JSON; kết quả chưa hoàn tất.") from None
        if not isinstance(event, dict) or event.get("error"):
            raise ValueError("API báo lỗi hoặc phản hồi chưa hoàn tất; không tự gửi lại.")
        for key in ("id", "model", "usage"):
            if event.get(key) is not None:
                result[key] = event[key]
        if isinstance(event.get("citations"), list):
            citations.extend(event["citations"])
        choices = event.get("choices", [])
        if not isinstance(choices, list) or len(choices) > 1:
            raise ValueError("Phản hồi completion không đúng định dạng hoặc chưa hoàn tất.")
        for choice in choices:
            if not isinstance(choice, dict) or choice.get("index", 0) != 0:
                raise ValueError("Phản hồi completion không đúng định dạng hoặc chưa hoàn tất.")
            delta = choice.get("delta", {}) if protocol == "chat/completions" else {"content": choice.get("text", "")}
            if not isinstance(delta, dict) or delta.get("tool_calls") or delta.get("function_call"):
                raise ValueError("Phản hồi completion không đúng định dạng hoặc chưa hoàn tất.")
            text = delta.get("content") or ""
            if not isinstance(text, str) or (stopped and (text or choice.get("finish_reason"))):
                raise ValueError("Phản hồi completion không đúng định dạng hoặc chưa hoàn tất.")
            if isinstance(delta.get("annotations"), list):
                annotations.extend(delta["annotations"])
            if text:
                fragments.append(text); on_delta(text)
            if choice.get("finish_reason") is not None:
                if choice["finish_reason"] != "stop":
                    raise ValueError("Phản hồi completion chưa hoàn tất hoặc bị giới hạn; không tự gửi lại.")
                stopped = True
        return None

    for raw in lines:
        if cancel():
            raise CancelledError("Đã hủy nhận AI. Yêu cầu có thể vẫn được nhà cung cấp tính phí.")
        received += len(raw)
        if received > 4_000_000:
            raise ValueError("Luồng AI vượt giới hạn 4 MB; kết quả chưa hoàn tất.")
        try:
            line = raw.decode("utf-8-sig").rstrip("\r\n")
        except UnicodeError:
            raise ValueError("Luồng AI không dùng UTF-8 hợp lệ.") from None
        if not line:
            data = consume()
            if data is not None:
                return data
        elif line.startswith("data:"):
            pending.append(line[5:].lstrip(" "))
    data = consume()
    if data is not None:
        return data
    raise ValueError("Luồng completion kết thúc trước [DONE]; kết quả chưa hoàn tất.")
