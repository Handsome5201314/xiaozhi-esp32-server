import json
import hmac
import logging
from pathlib import Path
from uuid import uuid4

from aiohttp import WSMsgType, web

from config.config_loader import get_project_dir
from core.medical.config import load_bed_config
from core.medical.frame import FrameDecodeError, decode_frame
from core.medical.session_store import SessionCreate, SessionStore


TAG = __name__


class MedicalGatewayError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class MedicalHandler:
    """HTTP/WebSocket adapter for the ESP32 medical recorder."""

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(TAG)
        medical = config.get("medical", {})
        beds_file = medical.get("beds_file", "data/medical/beds.json")
        data_dir = medical.get("data_dir", "data/medical/sessions")
        self.api_key = medical.get("api_key", "")
        self.beds_file = self._resolve_path(beds_file)
        self.store = SessionStore(self._resolve_path(data_dir))

    @staticmethod
    def _resolve_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else Path(get_project_dir()) / path

    def routes(self) -> list[web.RouteDef]:
        routes: list[web.RouteDef] = [web.get("/health", self.health)]
        for prefix in ("/v1", "/medical/v1"):
            routes.extend(
                [
                    web.get(f"{prefix}/devices/{{device_id}}/beds", self.beds),
                    web.post(f"{prefix}/sessions", self.create_session),
                    web.get(f"{prefix}/sessions/{{session_id}}/audio", self.audio),
                    web.post(f"{prefix}/sessions/{{session_id}}/finish", self.finish),
                ]
            )
        return routes

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def beds(self, request: web.Request) -> web.Response:
        device_id = self._authenticate(request)
        path_device_id = request.match_info["device_id"].strip()
        if not path_device_id:
            raise MedicalGatewayError(400, "INVALID_DEVICE", "device_id is required")
        self._require_device(device_id, path_device_id)
        config = load_bed_config(self.beds_file)
        return web.json_response(
            {
                "revision": config.revision,
                "updated_at": config.updated_at,
                "beds": [
                    {"id": bed.id, "label": bed.label, "enabled": bed.enabled}
                    for bed in config.beds
                ],
            }
        )

    async def create_session(self, request: web.Request) -> web.Response:
        authenticated_device_id = self._authenticate(request)
        body = await self._json_body(request)
        device_id = body.get("device_id")
        mode = body.get("mode")
        bed_id = body.get("bed_id")
        if not isinstance(device_id, str) or not device_id.strip():
            raise MedicalGatewayError(422, "INVALID_REQUEST", "device_id is required")
        self._require_device(authenticated_device_id, device_id)
        if mode not in {"bed", "general"}:
            raise MedicalGatewayError(422, "INVALID_REQUEST", "mode must be bed or general")

        bed_config = load_bed_config(self.beds_file)
        if mode == "bed" and bed_id not in bed_config.enabled_bed_ids():
            raise MedicalGatewayError(409, "BED_DISABLED", "该床位当前不可用")
        if mode == "general" and bed_id is not None:
            raise MedicalGatewayError(422, "INVALID_REQUEST", "通用录音不能绑定床位")

        try:
            session = self.store.create(
                SessionCreate(
                    session_id=body.get("session_id"),
                    device_id=device_id,
                    mode=mode,
                    bed_id=bed_id,
                )
            )
        except (TypeError, ValueError) as exc:
            raise MedicalGatewayError(422, "INVALID_REQUEST", str(exc)) from exc

        return web.json_response(
            {
                "session_id": session.session_id,
                "audio_path": f"/v1/sessions/{session.session_id}/audio",
            },
            status=201,
        )

    async def audio(self, request: web.Request) -> web.WebSocketResponse:
        session_id = request.match_info["session_id"]
        device_id = self._authenticate(request)
        self._require_session_owner(session_id, device_id)
        websocket = web.WebSocketResponse(heartbeat=30)
        await websocket.prepare(request)
        try:
            async for message in websocket:
                if message.type == WSMsgType.BINARY:
                    try:
                        ack = self.store.append_frame(session_id, decode_frame(message.data))
                    except (FrameDecodeError, KeyError, ValueError) as exc:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "INVALID_AUDIO_FRAME",
                                "message": str(exc),
                            }
                        )
                        await websocket.close(code=1003)
                        break
                    await websocket.send_json({"type": "ack", "sequence": ack})
                elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                    break
                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "INVALID_AUDIO_FRAME",
                            "message": "audio websocket accepts binary frames only",
                        }
                    )
        except (ConnectionResetError, RuntimeError) as exc:
            self.logger.bind(tag=TAG).debug(f"medical audio websocket closed: {exc}")
        return websocket

    async def finish(self, request: web.Request) -> web.Response:
        device_id = self._authenticate(request)
        self._require_session_owner(request.match_info["session_id"], device_id)
        body = await self._json_body(request)
        last_sequence = body.get("last_sequence")
        if not isinstance(last_sequence, int) or isinstance(last_sequence, bool) or last_sequence < -1:
            raise MedicalGatewayError(422, "INVALID_REQUEST", "last_sequence must be an integer >= -1")
        try:
            result = self.store.finish(request.match_info["session_id"], last_sequence)
        except KeyError as exc:
            raise MedicalGatewayError(404, "SESSION_NOT_FOUND", str(exc)) from exc
        except ValueError as exc:
            raise MedicalGatewayError(422, "INVALID_REQUEST", str(exc)) from exc
        return web.json_response({"status": result.status, "missing": result.missing})

    def _authenticate(self, request: web.Request) -> str:
        authorization = request.headers.get("Authorization", "")
        device_id = request.headers.get("Device-Id", "").strip()
        prefix = "Bearer "
        token = authorization[len(prefix) :] if authorization.startswith(prefix) else ""
        if not self.api_key or not token or not hmac.compare_digest(token, self.api_key):
            raise MedicalGatewayError(401, "AUTH_REQUIRED", "medical API authentication failed")
        if not device_id:
            raise MedicalGatewayError(401, "AUTH_REQUIRED", "Device-Id header is required")
        return device_id

    @staticmethod
    def _require_device(authenticated_device_id: str, requested_device_id: str) -> None:
        if not hmac.compare_digest(authenticated_device_id, requested_device_id.strip()):
            raise MedicalGatewayError(403, "DEVICE_MISMATCH", "device identity does not match")

    def _require_session_owner(self, session_id: str, device_id: str) -> None:
        try:
            owner = self.store.get(session_id).device_id
        except (KeyError, ValueError) as exc:
            raise MedicalGatewayError(404, "SESSION_NOT_FOUND", "session does not exist") from exc
        self._require_device(device_id, owner)

    @staticmethod
    async def _json_body(request: web.Request) -> dict:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise MedicalGatewayError(422, "INVALID_REQUEST", "request body must be JSON") from exc
        if not isinstance(body, dict):
            raise MedicalGatewayError(422, "INVALID_REQUEST", "request body must be an object")
        return body


@web.middleware
async def medical_error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except MedicalGatewayError as exc:
        return web.json_response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": f"req_{uuid4().hex}",
                }
            },
            status=exc.status,
        )
