"""Project a scoped Feishu task list into the Metalio native checklist contract."""
import asyncio
import hmac
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

import aiohttp


class ChecklistError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def authorize_device(token, device, expected_token, expected_device):
    return hmac.compare_digest(token or "", expected_token) and hmac.compare_digest(
        (device or "").lower(), expected_device.lower()
    )


def task_to_item(task):
    guid, title = task.get("guid"), task.get("summary")
    if not isinstance(guid, str) or not 1 <= len(guid.encode()) <= 47:
        raise ChecklistError(502, "飞书返回的任务标识无效")
    if not isinstance(title, str) or not title.strip():
        raise ChecklistError(502, "飞书返回的任务标题无效")
    raw = title.encode("utf-8")
    if len(raw) > 95:
        title = raw[:92].decode("utf-8", errors="ignore") + "…"
    day = clock = ""
    try:
        completed = int(task.get("completed_at") or "0") > 0
        due = task.get("due")
        if due:
            stamp = int(due["timestamp"])
            dt = datetime.fromtimestamp(stamp / 1000, timezone(timedelta(hours=8)))
            day = dt.strftime("%Y-%m-%d")
            if not due.get("is_all_day", False):
                clock = dt.strftime("%H:%M")
    except (ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
        raise ChecklistError(502, "飞书返回的任务时间无效") from exc
    return {"id": guid, "title": title, "planDate": day, "planTime": clock,
            "status": "done" if completed else "pending"}


class FeishuChecklist:
    """Feishu owns task state; only the short-lived API credential is cached."""
    API = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id, app_secret, tasklist_guid, assignee_id):
        if not all([app_id, app_secret, tasklist_guid, assignee_id]):
            raise ValueError("Feishu checklist configuration is incomplete")
        UUID(tasklist_guid)
        self.app_id, self.app_secret = app_id, app_secret
        self.tasklist_guid, self.assignee_id = tasklist_guid, assignee_id
        self._token = ""
        self._expires = 0
        self._token_lock = asyncio.Lock()

    async def _http(self, method, path, **kwargs):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client:
                async with client.request(method, self.API + path, **kwargs) as response:
                    if response.status >= 400:
                        raise ChecklistError(502, f"飞书 HTTP 请求失败（{response.status}）")
                    data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise ChecklistError(502, "飞书服务暂不可用或响应无效") from exc
        if not isinstance(data, dict) or data.get("code") != 0:
            code = data.get("code") if isinstance(data, dict) else "invalid"
            raise ChecklistError(502, f"飞书接口未成功（{code}），请检查应用权限")
        return data

    async def _access_token(self):
        async with self._token_lock:
            if time.monotonic() >= self._expires:
                data = await self._http("POST", "/auth/v3/tenant_access_token/internal",
                                        json={"app_id": self.app_id, "app_secret": self.app_secret})
                token, expiry = data.get("tenant_access_token"), data.get("expire")
                if not isinstance(token, str) or not isinstance(expiry, int) or expiry <= 60:
                    raise ChecklistError(502, "飞书认证响应无效")
                self._token, self._expires = token, time.monotonic() + expiry - 60
            return self._token

    async def _request(self, method, path, **kwargs):
        token = await self._access_token()
        data = await self._http(method, path, headers={"Authorization": "Bearer " + token}, **kwargs)
        return data.get("data", {})

    async def list_tasks(self):
        tasks, cursor, seen = [], "", set()
        while True:
            params = {"page_size": "100", "user_id_type": "open_id"}
            if cursor:
                params["page_token"] = cursor
            data = await self._request("GET", f"/task/v2/tasklists/{self.tasklist_guid}/tasks", params=params)
            items = data.get("items")
            if not isinstance(items, list):
                raise ChecklistError(502, "飞书任务清单响应格式无效")
            tasks.extend(items)
            # Firmware vector is bounded at 64 entries; never silently omit tasks.
            if len(tasks) > 64:
                raise ChecklistError(409, "清单超过胸卡 64 项上限，请先整理清单")
            if not data.get("has_more", False):
                return tasks
            cursor = data.get("page_token")
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise ChecklistError(502, "飞书任务分页响应无效")
            seen.add(cursor)

    async def items(self):
        return [task_to_item(task) for task in await self.list_tasks()]

    async def complete(self, guid):
        try:
            UUID(guid)
        except ValueError as exc:
            raise ChecklistError(400, "任务标识无效") from exc
        tasks = await self.list_tasks()
        task = next((t for t in tasks if t.get("guid") == guid), None)
        if task is None:
            raise ChecklistError(404, "任务不属于胸卡清单")
        if int(task.get("completed_at") or "0") > 0:
            return task_to_item(task)
        await self._request("PATCH", f"/task/v2/tasks/{guid}",
                            json={"task": {"completed_at": str(int(time.time() * 1000))},
                                  "update_fields": ["completed_at"]})
        data = await self._request("GET", f"/task/v2/tasks/{guid}")
        result = task_to_item(data.get("task", {}))
        if result["status"] != "done":
            raise ChecklistError(502, "飞书任务完成状态尚未确认")
        return result

    async def create(self, title, request_id):
        if not isinstance(title, str) or not title.strip() or len(title) > 500:
            raise ChecklistError(400, "任务标题不能为空且不得超过 500 字")
        try:
            UUID(request_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ChecklistError(400, "创建任务需要 UUID request_id，避免重复创建") from exc
        data = await self._request("POST", "/task/v2/tasks", json={
            "summary": title.strip(), "client_token": request_id,
            "members": [{"id": self.assignee_id, "type": "user", "role": "assignee"}],
            "tasklists": [{"tasklist_guid": self.tasklist_guid}],
        })
        return task_to_item(data.get("task", {}))
