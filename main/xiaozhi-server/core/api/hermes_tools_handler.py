"""Authenticated tool gateway for Hermes integrations.

Hermes calls this server with a device session and receives only tools that
belong to that tenant/user/device. Device credentials and provider secrets are
never exposed in the tool description or result.
"""
from __future__ import annotations

from aiohttp import web

from core.security.session import DeviceSessionAuthenticator, SessionError, SessionContext

HERMES_TOOL_ALLOWLIST = frozenset({
    "checklist.list", "checklist.complete", "daily_summary.read", "medical.record.create",
})

def _tool_name(description):
    return description.get("function", {}).get("name") if isinstance(description, dict) else None


class OnlineDeviceRegistry:
    """Process-local registry of authenticated device connections."""
    def __init__(self):
        self._connections = {}

    def register(self, context: SessionContext, connection):
        self._connections[(context.tenant_id, context.user_id, context.device_id.lower())] = connection

    def remove(self, context: SessionContext, connection=None):
        key = (context.tenant_id, context.user_id, context.device_id.lower())
        if connection is None or self._connections.get(key) is connection:
            self._connections.pop(key, None)

    def get(self, context: SessionContext):
        return self._connections.get((context.tenant_id, context.user_id, context.device_id.lower()))


class HermesToolsHandler:
    def __init__(self, authenticator: DeviceSessionAuthenticator, tool_manager_factory):
        self.authenticator = authenticator
        self.tool_manager_factory = tool_manager_factory

    def routes(self):
        return [
            web.get("/v1/hermes/tools", self.list_tools),
            web.post("/v1/hermes/tools/call", self.call_tool),
        ]

    def _auth(self, request: web.Request) -> SessionContext:
        return self.authenticator.authenticate(
            request.headers.get("Authorization"), request.headers.get("Device-Id"), "tools:call"
        )

    def _manager(self, context: SessionContext):
        connection = self.tool_manager_factory(context)
        if connection is None:
            raise SessionError(503, "设备当前不在线")
        manager = getattr(connection, "func_handler", connection)
        if manager is None:
            raise SessionError(503, "设备工具尚未初始化")
        return getattr(manager, "tool_manager", manager)

    async def list_tools(self, request: web.Request):
        try:
            context = self._auth(request)
            manager = self._manager(context)
            tools = [item for item in manager.get_function_descriptions()
                     if _tool_name(item) in HERMES_TOOL_ALLOWLIST]
            return web.json_response({"code": 0, "data": tools})
        except SessionError as exc:
            return web.json_response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)

    async def call_tool(self, request: web.Request):
        try:
            context = self._auth(request)
            body = await request.json()
            if not isinstance(body, dict) or not isinstance(body.get("name"), str):
                return web.json_response({"code": 400, "msg": "name is required", "data": None}, status=400)
            if body["name"] not in HERMES_TOOL_ALLOWLIST:
                return web.json_response({"code": 404, "msg": "工具不可用", "data": None}, status=404)
            manager = self._manager(context)
            result = await manager.execute_tool(body["name"], body.get("arguments", {}))
            return web.json_response({"code": 0, "data": {
                "action": getattr(result.action, "value", str(result.action)),
                "response": result.response,
                "content": result.content,
            }})
        except SessionError as exc:
            return web.json_response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)
        except ValueError:
            return web.json_response({"code": 400, "msg": "请求必须为 JSON", "data": None}, status=400)
        except Exception:
            # Do not return provider/device internals or credentials to Hermes.
            return web.json_response({"code": 502, "msg": "工具执行失败", "data": None}, status=502)
