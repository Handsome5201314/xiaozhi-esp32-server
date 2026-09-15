"""Native Metalio HTTP routes. Disabled unless complete deployment config is present."""
import json
import os
import re

from aiohttp import web
from aiohttp.web_log import AccessLogger
from core.providers.tasks.feishu_checklist import ChecklistError, FeishuChecklist, authorize_device
from core.security.session import DeviceSessionAuthenticator, SessionError, SessionContext


def compact_json(value):
    """Keep native checklist responses below the firmware's small-body limit."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class ChecklistAccessLogger(AccessLogger):
    def log(self, request, response, time):
        if request.path.startswith("/b/"):
            self.logger.info("native_checklist method=%s status=%s duration=%.3f", request.method, response.status, time)
        else:
            super().log(request, response, time)


class ChecklistHandler:
    def __init__(self, token, device_id, source):
        if not re.fullmatch(r"[a-f0-9]{32}", token):
            raise ValueError("Checklist token must contain 128 random bits")
        if not re.fullmatch(r"(?:[a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2}", device_id):
            raise ValueError("Checklist device ID is invalid")
        self.token, self.device_id, self.source = token, device_id, source

    @classmethod
    def from_environment(cls):
        if os.environ.get("METALIO_CHECKLIST_ENABLED") != "1":
            return None
        return cls(os.environ["METALIO_CHECKLIST_TOKEN"], os.environ["METALIO_CHECKLIST_DEVICE_ID"],
                   FeishuChecklist(os.environ["METALIO_FEISHU_APP_ID"], os.environ["METALIO_FEISHU_APP_SECRET"],
                                   os.environ["METALIO_FEISHU_TASKLIST"], os.environ["METALIO_FEISHU_ASSIGNEE"]))

    def routes(self):
        path = "/b/{token}/xiaozhi/api/checklist/items"
        return [web.get(path + "/all", self.handle), web.post(path + "/{guid}/complete", self.handle),
                web.post(path, self.handle), web.delete(path + "/{guid}", self.handle)]

    @staticmethod
    def _response(payload, status=200):
        return web.json_response(payload, status=status, dumps=compact_json)

    async def handle(self, request):
        if not authorize_device(request.match_info["token"], request.headers.get("Device-Id"), self.token, self.device_id):
            return self._response({"code": 401, "msg": "设备认证失败", "data": None}, status=401)
        try:
            if request.method == "GET":
                result = await self.source.items()
            elif request.method == "POST" and "guid" in request.match_info:
                result = await self.source.complete(request.match_info["guid"])
            elif request.method == "POST":
                try:
                    body = await request.json()
                except ValueError as exc:
                    raise ChecklistError(400, "请求必须为 JSON") from exc
                if not isinstance(body, dict):
                    raise ChecklistError(400, "请求必须为对象")
                result = await self.source.create(body.get("title"), body.get("request_id"))
            else:
                raise ChecklistError(405, "请在飞书管理删除；胸卡支持标记完成")
            return self._response({"code": 0, "msg": "success", "data": result})
        except ChecklistError as exc:
            return self._response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)


class UnifiedChecklistHandler:
    """Tenant/user scoped checklist entry point.

    ``sources`` is keyed by user id and is populated by the manager service.
    A source owns the external system state (currently Feishu); this handler
    only applies session authorization and selects the user's source.
    """

    def __init__(self, authenticator: DeviceSessionAuthenticator, sources: dict[str, object]):
        self.authenticator = authenticator
        self.sources = sources

    @staticmethod
    def _response(payload, status=200):
        return web.json_response(payload, status=status, dumps=compact_json)

    def routes(self):
        path = "/v1/checklist/items"
        return [web.get(path, self.handle), web.post(path, self.handle), web.post(path + "/{guid}/complete", self.handle)]

    def _source(self, context: SessionContext):
        source = self.sources.get(context.user_id)
        if source is None:
            raise ChecklistError(403, "当前用户未绑定待办数据源")
        return source

    async def handle(self, request):
        try:
            required_scope = "checklist:read"
            if request.method == "POST":
                required_scope = "checklist:write"
            context = self.authenticator.authenticate(
                request.headers.get("Authorization"), request.headers.get("Device-Id"), required_scope
            )
            source = self._source(context)
            if request.method == "GET":
                result = await source.items()
            elif "guid" in request.match_info:
                result = await source.complete(request.match_info["guid"])
            else:
                try:
                    body = await request.json()
                except ValueError as exc:
                    raise ChecklistError(400, "请求必须为 JSON") from exc
                if not isinstance(body, dict):
                    raise ChecklistError(400, "请求必须为对象")
                result = await source.create(body.get("title"), body.get("request_id"))
            return self._response({"code": 0, "msg": "success", "data": result})
        except SessionError as exc:
            return self._response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)
        except ChecklistError as exc:
            return self._response({"code": exc.status, "msg": str(exc), "data": None}, status=exc.status)

    @classmethod
    def from_environment(cls):
        """Build the migration endpoint from a manager-provided JSON mapping.

        The mapping contains only connection references and is intended for a
        bootstrap/single-process deployment. Production deployments should load
        the same records from manager-api and a server-side secret store.
        """
        if os.environ.get("METALIO_UNIFIED_CHECKLIST_ENABLED") != "1":
            return None
        secret = os.environ.get("METALIO_DEVICE_SESSION_SECRET")
        if not secret:
            raise ValueError("METALIO_DEVICE_SESSION_SECRET is required")
        try:
            bindings = json.loads(os.environ.get("METALIO_CHECKLIST_BINDINGS_JSON", "{}"))
        except json.JSONDecodeError as exc:
            raise ValueError("METALIO_CHECKLIST_BINDINGS_JSON must be valid JSON") from exc
        if not isinstance(bindings, dict):
            raise ValueError("METALIO_CHECKLIST_BINDINGS_JSON must be an object")
        sources = {}
        for user_id, binding in bindings.items():
            if not isinstance(binding, dict):
                raise ValueError("checklist binding must be an object")
            sources[str(user_id)] = FeishuChecklist(
                binding.get("app_id"), binding.get("app_secret"), binding.get("tasklist_guid"), binding.get("assignee_id")
            )
        return cls(DeviceSessionAuthenticator(secret), sources)
