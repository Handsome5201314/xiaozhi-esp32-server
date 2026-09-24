"""OpenAI-compatible Hermes adapter used only by routed device sessions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

import httpx

class HermesChatError(RuntimeError):
    """An upstream Hermes failure that must be visible to the current session."""


@dataclass
class _Function:
    name: str = ""
    arguments: str = ""


@dataclass
class _ToolCall:
    id: str = ""
    function: _Function = None
    index: int = 0

    def __post_init__(self):
        if self.function is None:
            self.function = _Function()


class HermesChatClient:
    def __init__(self, base_url: str, api_key: str, model: str = "",
                 timeout: float = 60.0, stream: bool = True, transport=None,
                 capability_context=None):
        if not base_url.lower().startswith("https://"):
            raise ValueError("Hermes 地址必须使用 HTTPS")
        if not api_key or not api_key.strip():
            raise ValueError("Hermes API Key 不可用")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model or "hermes"
        self.timeout = httpx.Timeout(timeout)
        self.stream = stream
        self.transport = transport
        self.capability_context = capability_context or {}

    def _messages(self, messages):
        if not self.capability_context:
            return messages
        context = {"role": "system", "content": "设备能力声明（仅作能力约束上下文）：" +
                   json.dumps(self.capability_context, ensure_ascii=False, sort_keys=True)}
        return [context, *messages]

    @staticmethod
    def _content(message: dict) -> str:
        value = message.get("content", "")
        if value is None:
            return ""
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

    def _request(self, messages, tools=None, stream=False):
        payload = {"model": self.model_name, "messages": messages, "stream": stream}
        if tools:
            payload["tools"] = tools
        try:
            return httpx.Client(timeout=self.timeout, follow_redirects=False, trust_env=False, transport=self.transport)
        except TypeError:
            return httpx.Client(timeout=self.timeout, follow_redirects=False, transport=self.transport)

    def _headers(self):
        return {"Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json", "Accept": "text/event-stream, application/json"}

    @staticmethod
    def _raise_status(response):
        if response.status_code in (401, 403):
            raise HermesChatError("Hermes 鉴权失败")
        if response.status_code == 429:
            raise HermesChatError("Hermes 请求过于频繁")
        if response.status_code >= 500:
            raise HermesChatError("Hermes 服务暂时不可用")
        if response.status_code >= 400:
            raise HermesChatError("Hermes 请求被拒绝")

    def _non_stream(self, messages, tools=None):
        messages = self._messages(messages)
        with self._request(messages, tools, stream=False) as client:
            try:
                response = client.post(self.base_url + "/v1/chat/completions",
                                       json={"model": self.model_name, "messages": messages,
                                             "stream": False, **({"tools": tools} if tools else {})},
                                       headers=self._headers())
            except httpx.TimeoutException as exc:
                raise HermesChatError("Hermes 请求超时") from exc
            except httpx.HTTPError as exc:
                raise HermesChatError("Hermes 网络请求失败") from exc
        self._raise_status(response)
        try:
            data = response.json()
            message = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise HermesChatError("Hermes 返回格式无效") from exc
        content = self._content(message)
        calls = []
        for index, call in enumerate(message.get("tool_calls") or []):
            fn = call.get("function") or {}
            calls.append(_ToolCall(call.get("id", ""), _Function(fn.get("name", ""), fn.get("arguments", "")), index))
        return content, calls

    def _stream(self, messages, tools=None):
        messages = self._messages(messages)
        payload = {"model": self.model_name, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools
        try:
            with self._request(messages, tools, stream=True) as client:
                with client.stream("POST", self.base_url + "/v1/chat/completions",
                                   json=payload, headers=self._headers()) as response:
                    self._raise_status(response)
                    for line in response.iter_lines():
                        if not line:
                            continue
                        if isinstance(line, bytes):
                            line = line.decode("utf-8", errors="replace")
                        if not line.startswith("data:"):
                            continue
                        line = line[5:].strip()
                        if line == "[DONE]":
                            return
                        try:
                            data = json.loads(line)
                            delta = data["choices"][0].get("delta") or {}
                        except (ValueError, KeyError, IndexError, TypeError) as exc:
                            raise HermesChatError("Hermes SSE 返回格式无效") from exc
                        calls = []
                        for index, call in enumerate(delta.get("tool_calls") or []):
                            fn = call.get("function") or {}
                            calls.append(_ToolCall(call.get("id", ""), _Function(fn.get("name", ""), fn.get("arguments", "")), call.get("index", index)))
                        yield delta.get("content") or "", calls
        except HermesChatError:
            raise
        except httpx.TimeoutException as exc:
            raise HermesChatError("Hermes 流式请求超时") from exc
        except httpx.HTTPError as exc:
            raise HermesChatError("Hermes 流式请求失败") from exc

    def response(self, session_id, dialogue, **kwargs):
        if self.stream:
            for content, _ in self._stream(dialogue):
                if content:
                    yield content
            return
        content, _ = self._non_stream(dialogue)
        if content:
            yield content

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        if self.stream:
            yield from self._stream(dialogue, functions)
            return
        content, calls = self._non_stream(dialogue, functions)
        if calls:
            yield content, calls
        else:
            yield content, None


class HermesUnavailableLLM:
    def response(self, session_id, dialogue, **kwargs):
        raise HermesChatError("当前 Metalio 设备没有可用的 Hermes 实例")

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        raise HermesChatError("当前 Metalio 设备没有可用的 Hermes 实例")
