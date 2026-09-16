from __future__ import annotations

import json
import os
from pathlib import Path
from aiohttp import web
from core.security.session import DeviceSessionAuthenticator, SessionContext, SessionError


class QuizHandler:
    """Tenant-scoped quiz API backed by an explicitly configured JSON catalogue."""
    def __init__(self, auth: DeviceSessionAuthenticator, path: str):
        self.auth, self.path = auth, Path(path)

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise web.HTTPServiceUnavailable(text="题库不可用") from exc
        if not isinstance(data, dict) or not isinstance(data.get("subjects"), list) or not isinstance(data.get("questions"), list):
            raise web.HTTPServiceUnavailable(text="题库格式无效")
        return data

    def _ctx(self, request: web.Request) -> SessionContext:
        try:
            return self.auth.authenticate(request.headers.get("Authorization"), request.headers.get("Device-Id"), "quiz:read")
        except SessionError as exc:
            raise web.HTTPUnauthorized(text=str(exc)) if exc.status == 401 else web.HTTPForbidden(text=str(exc))

    def routes(self):
        return [web.get("/v1/quiz/subjects", self.subjects), web.get("/v1/quiz/questions/next", self.next_question),
                web.post("/v1/quiz/questions/{id}/answer", self.answer), web.get("/v1/quiz/wrong-answers", self.wrong_answers)]

    async def subjects(self, request):
        self._ctx(request); data = self._load()
        return web.json_response({"code": 0, "msg": "success", "data": data["subjects"]})

    async def next_question(self, request):
        self._ctx(request); data = self._load(); subject = request.query.get("subject")
        questions = [q for q in data["questions"] if not subject or q.get("subject") == subject]
        if not questions: return web.json_response({"code": 404, "msg": "暂无题目", "data": None}, status=404)
        q = questions[0]
        return web.json_response({"code": 0, "msg": "success", "data": {k: q[k] for k in ("id", "subject", "question", "options") if k in q}})

    async def answer(self, request):
        try:
            ctx = self.auth.authenticate(request.headers.get("Authorization"), request.headers.get("Device-Id"), "quiz:write")
        except SessionError as exc:
            raise web.HTTPUnauthorized(text=str(exc)) if exc.status == 401 else web.HTTPForbidden(text=str(exc))
        data = self._load(); q = next((x for x in data["questions"] if str(x.get("id")) == request.match_info["id"]), None)
        if q is None: return web.json_response({"code": 404, "msg": "题目不存在", "data": None}, status=404)
        try: body = await request.json(); answer = body.get("answer")
        except (ValueError, AttributeError): raise web.HTTPBadRequest(text="请求必须为 JSON")
        correct = answer == q.get("answer")
        path = self.path.with_suffix(self.path.suffix + ".answers")
        records = {}
        try: records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError): pass
        key = "|".join((ctx.tenant_id, ctx.user_id, ctx.device_id.lower()))
        wrong = records.setdefault(key, [])
        if correct and q["id"] in wrong: wrong.remove(q["id"])
        if not correct and q["id"] not in wrong: wrong.append(q["id"])
        path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        return web.json_response({"code": 0, "msg": "success", "data": {"correct": correct}})

    async def wrong_answers(self, request):
        ctx = self._ctx(request); path = self.path.with_suffix(self.path.suffix + ".answers")
        try: records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError): records = {}
        ids = records.get("|".join((ctx.tenant_id, ctx.user_id, ctx.device_id.lower())), [])
        questions = {str(q.get("id")): q for q in self._load()["questions"]}
        return web.json_response({"code": 0, "msg": "success", "data": [{k: questions[str(i)][k] for k in ("id", "subject", "question", "options") if k in questions[str(i)]} for i in ids if str(i) in questions]})


def from_environment():
    if os.environ.get("METALIO_QUIZ_ENABLED") != "1": return None
    secret = os.environ.get("METALIO_DEVICE_SESSION_SECRET")
    if not secret: raise ValueError("METALIO_DEVICE_SESSION_SECRET is required")
    path = os.environ.get("METALIO_QUIZ_CATALOG", "/data/quiz/catalog.json")
    return QuizHandler(DeviceSessionAuthenticator(secret), path)
