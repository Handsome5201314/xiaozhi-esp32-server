import time
from typing import TYPE_CHECKING

import requests

from config.logger import setup_logging
from plugins_func.register import Action, ActionResponse, ToolType, register_function

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

AI_SCALE_ASSESSMENT_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "ai_scale_assessment",
        "description": (
            "连接儿童和家庭量表服务。当用户想做情绪、焦虑、注意力、发育、睡眠、行为相关筛查时调用。"
            "不要自行编造量表题目、分数或医学诊断；必须通过本工具初始化身份、获取量表、创建会话、提交答案和查询结果。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型：init/list_scales/start_session/submit_answer/get_session/get_result",
                },
                "scaleId": {
                    "type": "string",
                    "description": "量表ID，例如 PHQ-9、GAD-7、SSS、M_CHAT_R、SNAP-IV",
                },
                "sessionId": {
                    "type": "string",
                    "description": "量表会话ID，用于继续提交答案或恢复进度",
                },
                "questionId": {
                    "type": "integer",
                    "description": "当前题目编号",
                },
                "score": {
                    "type": "number",
                    "description": "根据用户语音回答解析出的题目分数",
                },
                "language": {
                    "type": "string",
                    "description": "语言代码，默认 zh",
                },
                "nickname": {
                    "type": "string",
                    "description": "默认成员昵称，首次初始化时可选",
                },
            },
            "required": ["action"],
        },
    },
}


def _plugin_config(conn: "ConnectionHandler"):
    return conn.config.get("plugins", {}).get("ai_scale_service", {})


def _base_url(conn: "ConnectionHandler"):
    return _plugin_config(conn).get("base_url", "https://tongyimohe.cloud").rstrip("/")


def _partner_token(conn: "ConnectionHandler"):
    return _plugin_config(conn).get("partner_token", "")


def _device_id(conn: "ConnectionHandler"):
    prefix = _plugin_config(conn).get("device_id_prefix", "xiaozhi")
    raw_device_id = getattr(conn, "device_id", None) or getattr(conn, "session_id", None) or "unknown-device"
    raw_device_id = str(raw_device_id).strip() or "unknown-device"
    return raw_device_id if raw_device_id.startswith(f"{prefix}-") else f"{prefix}-{raw_device_id}"


def _cache(conn: "ConnectionHandler"):
    if not hasattr(conn, "ai_scale_state"):
        conn.ai_scale_state = {}
    return conn.ai_scale_state


def _headers(token: str):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _request(method: str, url: str, *, token: str, payload=None, timeout=15):
    response = requests.request(
        method,
        url,
        headers=_headers(token),
        json=payload,
        timeout=timeout,
    )
    response.encoding = "utf-8"
    try:
        data = response.json()
    except Exception:
        data = {"text": response.text}

    if not response.ok:
        raise RuntimeError(f"量表服务请求失败({response.status_code}): {data}")

    return data


def _ensure_agent_session(conn: "ConnectionHandler", nickname=None):
    state = _cache(conn)
    now = int(time.time())
    if state.get("agent_token") and int(state.get("token_expires_at", 0)) - now > 60:
        return state["agent_token"]

    partner_token = _partner_token(conn)
    if not partner_token:
        raise RuntimeError("小智服务端未配置 ai_scale_service.partner_token")

    payload = {
        "deviceId": _device_id(conn),
        "entrypoint": "agent",
        "clientKind": "ai_toy",
        "autoCreateBinding": True,
        "memberSnapshot": {
            "nickname": nickname or _plugin_config(conn).get("default_nickname", "本人"),
            "relation": "SELF",
            "languagePreference": "ZH",
        },
    }
    data = _request(
        "POST",
        f"{_base_url(conn)}/api/agent/session",
        token=partner_token,
        payload=payload,
    )

    session = data.get("session", {})
    member = data.get("member", {})
    state["agent_token"] = data["token"]
    state["token_expires_at"] = session.get("exp", now + 3600)
    state["member_id"] = member.get("id") or session.get("member_id")
    state["device_id"] = payload["deviceId"]
    return state["agent_token"]


def _summarize_scales(data):
    scales = data.get("scales", [])
    if not scales:
        return "当前没有可用量表。"
    lines = ["当前可用语音量表："]
    for item in scales:
        lines.append(f"- {item.get('id')}: {item.get('name') or item.get('title') or '量表'}")
    return "\n".join(lines)


@register_function("ai_scale_assessment", AI_SCALE_ASSESSMENT_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def ai_scale_assessment(
    conn: "ConnectionHandler",
    action: str,
    scaleId: str = None,
    sessionId: str = None,
    questionId: int = None,
    score: float = None,
    language: str = "zh",
    nickname: str = None,
):
    try:
        action = str(action or "").strip()
        token = _ensure_agent_session(conn, nickname=nickname)
        state = _cache(conn)
        base_url = _base_url(conn)

        if action == "init":
            return ActionResponse(
                Action.REQLLM,
                f"量表服务已连接，deviceId={state.get('device_id')}，memberId={state.get('member_id')}",
                None,
            )

        if action == "list_scales":
            data = _request("GET", f"{base_url}/api/skill/v1/scales?aiToy=voiceFriendly", token=token)
            return ActionResponse(Action.REQLLM, _summarize_scales(data), None)

        if action == "start_session":
            if not scaleId:
                return ActionResponse(Action.RESPONSE, None, "请先选择要开始的量表。")
            payload = {"memberId": state.get("member_id"), "language": language or "zh"}
            data = _request(
                "POST",
                f"{base_url}/api/skill/v1/scales/{scaleId}/sessions",
                token=token,
                payload=payload,
            )
            session = data.get("session", {})
            state["active_scale_id"] = scaleId
            state["active_session_id"] = session.get("id")
            return ActionResponse(Action.REQLLM, f"已开始量表会话：{session}", None)

        active_scale_id = scaleId or state.get("active_scale_id")
        active_session_id = sessionId or state.get("active_session_id")

        if action == "submit_answer":
            if not active_scale_id or not active_session_id:
                return ActionResponse(Action.RESPONSE, None, "当前没有正在进行的量表会话。")
            if questionId is None or score is None:
                return ActionResponse(Action.RESPONSE, None, "请提供题目编号和分数。")
            data = _request(
                "POST",
                f"{base_url}/api/skill/v1/scales/{active_scale_id}/sessions/{active_session_id}/answer",
                token=token,
                payload={"questionId": int(questionId), "score": score},
            )
            return ActionResponse(Action.REQLLM, f"答案已提交：{data.get('session')}", None)

        if action == "get_session":
            if not active_scale_id or not active_session_id:
                return ActionResponse(Action.RESPONSE, None, "当前没有可恢复的量表会话。")
            data = _request(
                "GET",
                f"{base_url}/api/skill/v1/scales/{active_scale_id}/sessions/{active_session_id}",
                token=token,
            )
            return ActionResponse(Action.REQLLM, f"当前量表进度：{data.get('session')}", None)

        if action == "get_result":
            if not active_scale_id or not active_session_id:
                return ActionResponse(Action.RESPONSE, None, "当前没有可查询的量表结果。")
            data = _request(
                "GET",
                f"{base_url}/api/skill/v1/scales/{active_scale_id}/sessions/{active_session_id}/result",
                token=token,
            )
            return ActionResponse(Action.REQLLM, f"量表结果：{data.get('session')}", None)

        return ActionResponse(Action.RESPONSE, None, f"未知量表操作：{action}")

    except Exception as error:
        logger.bind(tag=TAG).error(f"量表服务调用失败: {error}")
        return ActionResponse(Action.RESPONSE, None, f"量表服务暂时不可用：{error}")
