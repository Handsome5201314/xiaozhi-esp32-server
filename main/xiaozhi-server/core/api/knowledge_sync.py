"""Tenant-scoped Markdown to safe, deterministic ebook synchronization."""
from __future__ import annotations

import hashlib
import base64
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aiohttp import web

from core.security.session import DeviceSessionAuthenticator, SessionContext, SessionError


class KnowledgeError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_component(value: str) -> str:
    if not isinstance(value, str) or not value or value in {".", ".."} or len(value) > 128:
        raise KnowledgeError(403, "知识库主体无效")
    if any(char in value for char in ("/", "\\", "\x00")):
        raise KnowledgeError(403, "知识库主体无效")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        return value
    # Device-derived user IDs may contain ':' (for example a MAC address).
    # Encode non-path-safe but otherwise valid identifiers instead of rejecting
    # them or ever placing raw input into a filesystem path.
    return "~" + base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", lambda m: f"[图片: {m.group(1)}]" if m.group(1) else "[图片]", text)
    # Every Markdown destination becomes plain text, including unsupported
    # schemes. The device never receives a clickable or executable URL.
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]+)?\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]+)?\]\]", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)", lambda m: m.group(1) or m.group(2), text)
    # HTML is rendered as plain text; no markup reaches the device.
    text = re.sub(r"<[^>]*>", "", text)
    return "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)


def markdown_to_ebook(markdown: str) -> bytes:
    """Convert supported Markdown to deterministic UTF-8 plain text."""
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    in_fence = False
    fence_language = ""
    table_separator = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
    for raw in lines:
        line = raw.rstrip()
        fence = re.match(r"^\s*(```+|~~~+)\s*([^ ]*)\s*$", line)
        if fence:
            if not in_fence:
                in_fence, fence_language = True, fence.group(2).lower()
                output.append(f"[代码块{(': ' + fence_language) if fence_language else ''}]")
            else:
                in_fence, fence_language = False, ""
            continue
        if in_fence:
            output.append(_inline(line))
            continue
        if table_separator.match(line):
            continue
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        if heading:
            output.append(_inline(heading.group(1)).strip())
            continue
        quote = re.match(r"^\s*>\s?(.*)$", line)
        if quote:
            output.append("| " + _inline(quote.group(1)))
            continue
        item = re.match(r"^\s*(?:[-+*]|\d+[.)])\s+(.*)$", line)
        if item:
            output.append("- " + _inline(item.group(1)))
            continue
        if "|" in line and line.strip().startswith("|"):
            cells = [re.sub(r"^\s+|\s+$", "", cell) for cell in line.strip().strip("|").split("|")]
            output.append(" | ".join(_inline(cell) for cell in cells))
            continue
        output.append(_inline(line))
    while output and not output[-1]:
        output.pop()
    return ("\n".join(output) + "\n").encode("utf-8")


class KnowledgeAccessPolicy:
    """Optional allow-list in addition to signed session identity and scopes."""
    def __init__(self, bindings: Optional[list[dict]] = None):
        self.bindings = bindings

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("METALIO_KNOWLEDGE_PERMISSIONS_JSON")
        if not raw:
            return cls(None)
        try:
            bindings = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("METALIO_KNOWLEDGE_PERMISSIONS_JSON must be valid JSON") from exc
        if not isinstance(bindings, list):
            raise ValueError("METALIO_KNOWLEDGE_PERMISSIONS_JSON must be a list")
        return cls(bindings)

    def allows(self, context: SessionContext) -> bool:
        if self.bindings is None:
            return True
        for binding in self.bindings:
            if not isinstance(binding, dict):
                continue
            if str(binding.get("tenant_id")) != context.tenant_id or str(binding.get("user_id")) != context.user_id:
                continue
            devices = binding.get("device_ids", ["*"])
            if isinstance(devices, list) and ("*" in devices or context.device_id.lower() in {str(x).lower() for x in devices}):
                return bool(binding.get("enabled", True))
        return False


class KnowledgeRepository:
    def __init__(self, source_root: str, publish_root: str, max_file_bytes: int = 2 * 1024 * 1024,
                 max_files: int = 1000, max_total_bytes: int = 50 * 1024 * 1024,
                 chunk_size: int = 64 * 1024):
        if max_file_bytes <= 0 or max_file_bytes > 50 * 1024 * 1024:
            raise ValueError("max_file_bytes is out of range")
        self.source_root = Path(source_root).resolve()
        self.publish_root = Path(publish_root).resolve()
        if self.source_root == self.publish_root or self.source_root in self.publish_root.parents or self.publish_root in self.source_root.parents:
            raise ValueError("source_root and publish_root must be separate")
        if max_total_bytes <= 0 or max_total_bytes > 500 * 1024 * 1024:
            raise ValueError("max_total_bytes is out of range")
        self.max_file_bytes, self.max_files = max_file_bytes, max_files
        self.max_total_bytes, self.chunk_size = max_total_bytes, chunk_size

    def _scope(self, context: SessionContext) -> tuple[Path, Path]:
        tenant, user = _safe_component(context.tenant_id), _safe_component(context.user_id)
        source = (self.source_root / tenant / user).resolve()
        if self.source_root not in source.parents:
            raise KnowledgeError(403, "知识库路径无效")
        key = _sha256(f"{context.tenant_id}\0{context.user_id}".encode())
        publish = self.publish_root / key
        publish.mkdir(parents=True, exist_ok=True)
        return source, publish

    @staticmethod
    def _read_state(path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"schema": 1, "revision": 0, "records": {}, "acks": {}}
        except (OSError, ValueError) as exc:
            raise KnowledgeError(503, "知识库状态不可用") from exc
        if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("records"), dict):
            raise KnowledgeError(503, "知识库状态无效")
        data.setdefault("acks", {})
        return data

    @staticmethod
    def _atomic_write(path: Path, content: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def sync(self, context: SessionContext) -> dict:
        source_dir, publish_dir = self._scope(context)
        state_path = publish_dir / "state.json"
        state = self._read_state(state_path)
        files = []
        if source_dir.exists():
            for candidate in source_dir.rglob("*.md"):
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                if source_dir not in resolved.parents:
                    raise KnowledgeError(400, "知识库包含越界路径")
                files.append(candidate)
        if len(files) > self.max_files:
            raise KnowledgeError(413, "知识库文件数量超过限制")
        current: dict[str, dict] = {}
        total_bytes = 0
        for candidate in sorted(files, key=lambda item: item.relative_to(source_dir).as_posix()):
            relative = candidate.relative_to(source_dir).as_posix()
            try:
                raw = candidate.read_bytes()
            except OSError as exc:
                raise KnowledgeError(503, "知识库源文件不可读") from exc
            if len(raw) > self.max_file_bytes:
                raise KnowledgeError(413, "知识库文件超过大小限制")
            total_bytes += len(raw)
            if total_bytes > self.max_total_bytes:
                raise KnowledgeError(413, "知识库总大小超过限制")
            try:
                markdown = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise KnowledgeError(400, "知识库必须使用 UTF-8 Markdown") from exc
            file_id = _sha256(relative.encode("utf-8"))[:32]
            ebook = markdown_to_ebook(markdown)
            record = {
                "revision": state["revision"] + 1,
                "file_id": file_id,
                "path": relative,
                "source_sha256": _sha256(raw),
                "ebook_sha256": _sha256(ebook),
                "source_size": len(raw),
                "ebook_size": len(ebook),
                "updated_at": _utc_now(),
                "deleted": False,
            }
            previous = state["records"].get(file_id)
            if previous and all(previous.get(key) == record.get(key) for key in ("path", "source_sha256", "ebook_sha256", "source_size", "ebook_size", "deleted")):
                record = previous
            else:
                self._atomic_write(publish_dir / f"{file_id}.md", raw)
                self._atomic_write(publish_dir / f"{file_id}.ebook", ebook)
            current[file_id] = record
        for file_id, previous in state["records"].items():
            if file_id not in current and not previous.get("deleted"):
                tombstone = dict(previous)
                tombstone.update({"revision": state["revision"] + 1, "updated_at": _utc_now(), "deleted": True})
                current[file_id] = tombstone
        changed = current != state["records"]
        if changed:
            revision = state["revision"] + 1
            for record in current.values():
                if record not in state["records"].values():
                    record["revision"] = revision
            state["revision"] = revision
            state["records"] = current
            self._atomic_write(state_path, json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return state

    def manifest(self, context: SessionContext) -> dict:
        state = self.sync(context)
        records = sorted(state["records"].values(), key=lambda item: (item["path"], item["file_id"]))
        return {"revision": state["revision"], "chunk_size": self.chunk_size, "files": records}

    def file_path(self, context: SessionContext, file_id: str, source: bool = False) -> tuple[dict, Path]:
        state = self.sync(context)
        record = state["records"].get(file_id)
        if not record or record.get("deleted"):
            raise KnowledgeError(404, "知识库文件不存在")
        path = self._scope(context)[1] / f"{file_id}.{'md' if source else 'ebook'}"
        if not path.is_file():
            raise KnowledgeError(503, "知识库文件不可用")
        return record, path

    def ack(self, context: SessionContext, file_id: str, revision: int, ebook_sha256: str) -> dict:
        state = self.sync(context)
        record = state["records"].get(file_id)
        if not record or record.get("deleted"):
            raise KnowledgeError(404, "知识库文件不存在")
        if revision != record["revision"] or ebook_sha256 != record["ebook_sha256"]:
            raise KnowledgeError(409, "知识库版本或哈希不匹配")
        state["acks"][context.device_id.lower()] = {"revision": revision, "file_id": file_id, "ebook_sha256": ebook_sha256, "updated_at": _utc_now()}
        self._atomic_write(self._scope(context)[1] / "state.json", json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return state["acks"][context.device_id.lower()]


class KnowledgeHandler:
    def __init__(self, authenticator: DeviceSessionAuthenticator, repository: KnowledgeRepository, policy: KnowledgeAccessPolicy):
        self.authenticator, self.repository, self.policy = authenticator, repository, policy

    def routes(self):
        return [web.get("/v1/knowledge/manifest", self.manifest), web.get("/v1/knowledge/files/{file_id}", self.file), web.post("/v1/knowledge/ack", self.ack)]

    def _auth(self, request: web.Request, scope: str) -> SessionContext:
        try:
            context = self.authenticator.authenticate(request.headers.get("Authorization"), request.headers.get("Device-Id"), scope)
        except SessionError as exc:
            raise KnowledgeError(exc.status, str(exc)) from exc
        if not self.policy.allows(context):
            raise KnowledgeError(403, "当前设备无权访问知识库")
        return context

    @staticmethod
    def _json(payload, status=200):
        return web.json_response({"code": 0 if status < 300 else status, "msg": "success" if status < 300 else payload, "data": payload if status < 300 else None}, status=status)

    async def manifest(self, request):
        try:
            context = self._auth(request, "knowledge:read")
            return self._json(self.repository.manifest(context))
        except KnowledgeError as exc:
            return self._json(str(exc), exc.status)

    async def file(self, request):
        try:
            context = self._auth(request, "knowledge:read")
            # Device sessions receive only the generated ebook. The original
            # Markdown remains server-side migration/source material.
            source = False
            record, path = self.repository.file_path(context, request.match_info["file_id"], source)
            total = path.stat().st_size
            start, end = 0, total - 1
            range_header = request.headers.get("Range")
            if range_header:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
                if not match or (not match.group(1) and not match.group(2)):
                    raise KnowledgeError(416, "Range 无效")
                try:
                    if match.group(1):
                        start = int(match.group(1))
                        end = int(match.group(2) or total - 1)
                    else:
                        length = int(match.group(2))
                        start, end = max(0, total - length), total - 1
                except ValueError as exc:
                    raise KnowledgeError(416, "Range 无效") from exc
                if start < 0 or start > end or start >= total:
                    raise KnowledgeError(416, "Range 超出文件范围")
                end = min(end, total - 1)
            with path.open("rb") as handle:
                handle.seek(start)
                body = handle.read(end - start + 1)
            response = web.Response(body=body, status=206 if range_header else 200, content_type="text/plain", charset="utf-8")
            response.headers["Accept-Ranges"] = "bytes"
            response.headers["Content-Length"] = str(len(body))
            response.headers["X-Knowledge-SHA256"] = record["source_sha256" if source else "ebook_sha256"]
            response.headers["ETag"] = record["source_sha256" if source else "ebook_sha256"]
            if range_header:
                response.headers["Content-Range"] = f"bytes {start}-{end}/{total}"
            return response
        except KnowledgeError as exc:
            return self._json(str(exc), exc.status)

    async def ack(self, request):
        try:
            context = self._auth(request, "knowledge:ack")
            try:
                body = await request.json()
            except ValueError as exc:
                raise KnowledgeError(400, "请求必须为 JSON") from exc
            if not isinstance(body, dict) or not isinstance(body.get("file_id"), str) or not isinstance(body.get("revision"), int) or not isinstance(body.get("ebook_sha256"), str):
                raise KnowledgeError(400, "file_id、revision、ebook_sha256 为必填字段")
            return self._json(self.repository.ack(context, body["file_id"], body["revision"], body["ebook_sha256"]))
        except KnowledgeError as exc:
            return self._json(str(exc), exc.status)


def from_environment(secret: str | None = None) -> Optional[KnowledgeHandler]:
    if os.environ.get("METALIO_KNOWLEDGE_ENABLED") != "1":
        return None
    secret = secret or os.environ.get("METALIO_DEVICE_SESSION_SECRET", "")
    if len(secret) < 32:
        raise ValueError("METALIO_DEVICE_SESSION_SECRET is required")
    source_root = os.environ.get("METALIO_KNOWLEDGE_SOURCE_ROOT", "/data/knowledge/source")
    publish_root = os.environ.get("METALIO_KNOWLEDGE_PUBLISH_ROOT", "/data/knowledge/published")
    max_file_bytes = int(os.environ.get("METALIO_KNOWLEDGE_MAX_FILE_BYTES", str(2 * 1024 * 1024)))
    max_total_bytes = int(os.environ.get("METALIO_KNOWLEDGE_MAX_TOTAL_BYTES", str(50 * 1024 * 1024)))
    return KnowledgeHandler(DeviceSessionAuthenticator(secret), KnowledgeRepository(source_root, publish_root, max_file_bytes, max_total_bytes=max_total_bytes), KnowledgeAccessPolicy.from_environment())
