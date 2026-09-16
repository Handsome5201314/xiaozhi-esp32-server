"""Authenticated tool gateway for Hermes integrations.

Hermes calls this server with a device session and receives only tools that
belong to that tenant/user/device. Device credentials and provider secrets are
never exposed in the tool description or result.
"""
from __future__ import annotations

from aiohttp import web

from core.security.session import DeviceSessionAuthenticator, SessionError, SessionContext


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

    async def list_tools(self, request: web.Request):
        try:
            context = self._auth(request)
            manager = self.tool_manager_factory(context)
            tools = manager.get_function_descriptions()
            return web.json_response({"code": 0, "data": tools})
        except SessionError as exc:
            return web.json_response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)

    async def call_tool(self, request: web.Request):
        try:
            context = self._auth(request)
            body = await request.json()
            if not isinstance(body, dict) or not isinstance(body.get("name"), str):
                return web.json_response({"code": 400, "msg": "name is required", "data": None}, status=400)
            manager = self.tool_manager_factory(context)
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
