"""Tenant-scoped daily summary endpoints for device clients.

The handler deliberately never fabricates an empty summary.  A deployment
provides a generator callback (Hermes integration) and a small JSON-backed
store for the bootstrap process; production can replace the store with the
existing database without changing the HTTP contract.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Awaitable, Callable, Optional

from aiohttp import web

from core.security.session import DeviceSessionAuthenticator, SessionError, SessionContext


class SummaryStoreError(Exception):
    """Safe public error; corrupt records must never become an empty store."""
    status = 503

    def __init__(self):
        super().__init__("总结存储不可用，请检查服务端存储状态")


class DailySummaryStore:
    """Experimental single-worker persistence, not the production MySQL store.

    Use exactly one store instance per file/process. Generation serialization
    covers that instance only; do not enable it in a multi-worker deployment.
    """
    def __init__(self, path: str):
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self._generation_locks = {}

    @staticmethod
    def key(context: SessionContext, date: str) -> str:
        # A tuple encoding avoids delimiter collisions and never trusts owner
        # identifiers supplied in the request body or URL.
        return json.dumps([context.tenant_id, context.user_id,
                           context.device_id.lower(), date], separators=(",", ":"))

    @asynccontextmanager
    async def generation(self, context: SessionContext, date: str):
        key = self.key(context, date)
        entry = self._generation_locks.setdefault(key, [asyncio.Lock(), 0])
        entry[1] += 1
        try:
            async with entry[0]:
                yield
        finally:
            entry[1] -= 1
            if entry[1] == 0:
                self._generation_locks.pop(key, None)

    async def _read(self) -> dict:
        try:
            text = await asyncio.to_thread(self.path.read_text, encoding="utf-8")
        except FileNotFoundError:
            return {"schema": 2, "records": {}}
        except OSError as exc:
            raise SummaryStoreError() from exc
        try:
            data = json.loads(text)
            if not isinstance(data, dict) or data.get("schema") != 2 or not isinstance(data.get("records"), dict):
                # Legacy user-only keys lack provable tenant ownership. Never
                # attach those records to a tenant implicitly or overwrite them.
                raise ValueError("unsupported summary schema")
            return data
        except (ValueError, TypeError) as exc:
            raise SummaryStoreError() from exc

    async def get(self, context: SessionContext, date: str) -> Optional[dict]:
        async with self._lock:
            return (await self._read())["records"].get(self.key(context, date))

    async def put(self, context: SessionContext, date: str, value: dict) -> dict:
        async with self._lock:
            data = await self._read()
            data["records"][self.key(context, date)] = value
            try:
                await asyncio.to_thread(self._write, data)
            except OSError as exc:
                raise SummaryStoreError() from exc
            return value

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as output:
            json.dump(data, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        tmp.replace(self.path)


class DailySummaryHandler:
    def __init__(self, authenticator: DeviceSessionAuthenticator, store: DailySummaryStore,
                 generator: Optional[Callable[[SessionContext, str], Awaitable[str]]] = None):
        self.authenticator, self.store, self.generator = authenticator, store, generator

    @staticmethod
    def _date(request: web.Request) -> str:
        value = request.query.get("date") or _dt.date.today().isoformat()
        try:
            _dt.date.fromisoformat(value)
        except ValueError as exc:
            raise web.HTTPBadRequest(text="date must be YYYY-MM-DD") from exc
        return value

    def routes(self):
        return [
            web.get("/v1/daily-summary/today", self.today),
            web.post("/v1/daily-summary/generate", self.generate),
            web.post("/v1/daily-summary/ack", self.ack),
        ]

    def _auth(self, request: web.Request, scope: str = "summary:read") -> SessionContext:
        return self.authenticator.authenticate(request.headers.get("Authorization"),
                                               request.headers.get("Device-Id"), scope)

    async def generate_once(self, context: SessionContext, date: str,
                            content: Optional[str] = None) -> tuple[int, dict]:
        """Serialize the entire read/generate/write operation for this owner."""
        async with self.store.generation(context, date):
            return await self._generate(context, date, content)

    async def _generate(self, context: SessionContext, date: str,
                        content: Optional[str] = None) -> tuple[int, dict]:
        existing = await self.store.get(context, date)
        if existing and existing.get("status") == "ready":
            return 200, existing
        if content is None:
            if self.generator is None:
                return 503, {"error": "Hermes 总结服务不可用"}
            try:
                content = await self.generator(context, date)
            except Exception:
                return 502, {"error": "Hermes 总结生成失败"}
        if not isinstance(content, str):
            return 502, {"error": "Hermes 总结格式无效"}
        content = content.strip()
        if not content:
            return 502, {"error": "Hermes 未返回总结"}
        if len(content) > 4000:
            return 400, {"error": "总结内容超过 4000 字符限制"}
        item = {"date": date, "title": "今日总结", "content": content,
                "status": "ready", "acknowledged": False,
                "updated_at": _dt.datetime.now(_dt.timezone.utc).isoformat()}
        return 200, await self.store.put(context, date, item)

    async def today(self, request: web.Request):
        try:
            context = self._auth(request)
            date = self._date(request)
            item = await self.store.get(context, date)
            if item is None:
                return web.json_response({"code": 404, "msg": "今日总结尚未生成", "data": None}, status=404)
            return web.json_response({"code": 0, "msg": "success", "data": item})
        except (SessionError, SummaryStoreError) as exc:
            return web.json_response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)

    async def generate(self, request: web.Request):
        try:
            context = self._auth(request, "summary:write")
            date = self._date(request)
            if request.content_length in (None, 0):
                body = {}
            else:
                try:
                    body = await request.json()
                except ValueError as exc:
                    raise web.HTTPBadRequest(text="请求必须为 JSON") from exc
            if not isinstance(body, dict):
                raise web.HTTPBadRequest(text="请求必须为对象")
            submitted_content = body.get("content")
            title = body.get("title")
            status, item = await self.generate_once(context, date, submitted_content)
            if status != 200:
                return web.json_response({"code": status, "msg": item["error"], "data": None}, status=status)
            if isinstance(title, str) and title.strip() and item.get("title") == "今日总结":
                item["title"] = title.strip()[:80]
                item = await self.store.put(context, date, item)
            return web.json_response({"code": 0, "msg": "success", "data": item})
        except (SessionError, SummaryStoreError) as exc:
            return web.json_response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)

    async def ack(self, request: web.Request):
        try:
            context = self._auth(request, "summary:read")
            date = self._date(request)
            async with self.store.generation(context, date):
                item = await self.store.get(context, date)
                if item is None:
                    return web.json_response({"code": 404, "msg": "总结不存在", "data": None}, status=404)
                item["acknowledged"] = True
                return web.json_response({"code": 0, "msg": "success", "data": await self.store.put(context, date, item)})
        except (SessionError, SummaryStoreError) as exc:
            return web.json_response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)


def from_environment() -> Optional[DailySummaryHandler]:
    if os.environ.get("METALIO_DAILY_SUMMARY_ENABLED") != "1":
        return None
    secret = os.environ.get("METALIO_DEVICE_SESSION_SECRET")
    if not secret:
        raise ValueError("METALIO_DEVICE_SESSION_SECRET is required")
    path = os.environ.get("METALIO_DAILY_SUMMARY_STORE", "/data/daily-summary.json")
    return DailySummaryHandler(
        DeviceSessionAuthenticator(secret),
        DailySummaryStore(path),
    )
