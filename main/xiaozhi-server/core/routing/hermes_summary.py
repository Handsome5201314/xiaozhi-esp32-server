"""Server-side Hermes adapter for daily summaries.

Only the server holds the bearer token.  The adapter accepts a secret
provider callback so routing metadata and credentials stay separate.
"""
from __future__ import annotations

from typing import Awaitable, Callable

import aiohttp

from .hermes_router import HermesResolver


class HermesSummaryClient:
    def __init__(self, resolver: HermesResolver,
                 secret_provider: Callable[[str], Awaitable[str] | str],
                 timeout_seconds: float = 30):
        self.resolver = resolver
        self.secret_provider = secret_provider
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def generate(self, tenant_id: str, user_id: str, device_id: str, prompt: str) -> str:
        instance = self.resolver.resolve(tenant_id, user_id, device_id, "summary")
        secret = self.secret_provider(instance.id)
        if hasattr(secret, "__await__"):
            secret = await secret
        if not isinstance(secret, str) or not secret.strip():
            raise RuntimeError("Hermes 凭据不可用")
        url = instance.base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": "hermes",
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "请将输入整理成简洁、可执行的中文临床工作日报。"},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": "Bearer " + str(secret), "Content-Type": "application/json"}
        async with aiohttp.ClientSession(timeout=self.timeout) as client:
            async with client.post(url, json=payload, headers=headers) as response:
                if response.status >= 500:
                    raise RuntimeError("Hermes 服务暂时不可用")
                if response.status >= 400:
                    raise RuntimeError("Hermes 请求被拒绝")
                data = await response.json(content_type=None)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Hermes 返回格式无效") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Hermes 未返回总结")
        return content.strip()
