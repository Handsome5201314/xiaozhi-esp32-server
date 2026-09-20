import hashlib
import tempfile
import unittest
from pathlib import Path

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from core.api.knowledge_sync import KnowledgeAccessPolicy, KnowledgeHandler, KnowledgeRepository, markdown_to_ebook
from core.security.session import DeviceSessionAuthenticator


class KnowledgeSyncTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.publish = self.root / "publish"
        self.source.joinpath("tenant-a", "user-a").mkdir(parents=True)
        self.source.joinpath("tenant-b", "user-b").mkdir(parents=True)
        self.markdown = """# 今日知识\n\n**重点**与 *说明*\n\n- 第一项\n- 第二项\n\n> 引用\n\n| 名称 | 值 |\n| --- | --- |\n| A | B |\n\n[[目标笔记|跳转]]\n\n```mermaid\ngraph TD\nA-->B\n```\n\n<script>alert(1)</script>\n"""
        self.source.joinpath("tenant-a", "user-a", "note.md").write_text(self.markdown, encoding="utf-8")
        self.source.joinpath("tenant-b", "user-b", "note.md").write_text("B tenant", encoding="utf-8")
        self.auth = DeviceSessionAuthenticator("k" * 32)
        self.token_a = self.auth.issue("tenant-a", "user-a", "AA:BB:CC:DD:EE:01", "device", ["knowledge:read", "knowledge:ack"])
        self.token_b = self.auth.issue("tenant-b", "user-b", "AA:BB:CC:DD:EE:02", "device", ["knowledge:read", "knowledge:ack"])
        repository = KnowledgeRepository(str(self.source), str(self.publish), max_file_bytes=1024)
        policy = KnowledgeAccessPolicy([{"tenant_id": "tenant-a", "user_id": "user-a", "device_ids": ["AA:BB:CC:DD:EE:01"]}])
        app = web.Application()
        app.add_routes(KnowledgeHandler(self.auth, repository, policy).routes())
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    def headers(self, token, device="AA:BB:CC:DD:EE:01"):
        return {"Authorization": "Bearer " + token, "Device-Id": device}

    async def test_deterministic_conversion_and_manifest_hashes(self):
        first = markdown_to_ebook(self.markdown)
        second = markdown_to_ebook(self.markdown)
        self.assertEqual(first, second)
        response = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a))
        self.assertEqual(response.status, 200)
        body = await response.json()
        record = body["data"]["files"][0]
        self.assertEqual(record["source_sha256"], hashlib.sha256((self.source / "tenant-a" / "user-a" / "note.md").read_bytes()).hexdigest())
        self.assertEqual(record["ebook_sha256"], hashlib.sha256(first).hexdigest())
        self.assertFalse(record["deleted"])
        self.assertNotIn("<script>", first.decode())

    async def test_range_resume_and_ack_hash(self):
        manifest = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a))
        record = (await manifest.json())["data"]["files"][0]
        response = await self.client.get(f"/v1/knowledge/files/{record['file_id']}", headers={**self.headers(self.token_a), "Range": "bytes=0-9"})
        self.assertEqual(response.status, 206)
        self.assertEqual(response.headers["Content-Range"], f"bytes 0-9/{record['ebook_size']}")
        self.assertEqual(response.headers["X-Knowledge-SHA256"], record["ebook_sha256"])
        ack = await self.client.post("/v1/knowledge/ack", headers=self.headers(self.token_a), json={"file_id": record["file_id"], "revision": record["revision"], "ebook_sha256": record["ebook_sha256"]})
        self.assertEqual(ack.status, 200)
        bad = await self.client.post("/v1/knowledge/ack", headers=self.headers(self.token_a), json={"file_id": record["file_id"], "revision": record["revision"], "ebook_sha256": "0" * 64})
        self.assertEqual(bad.status, 409)

    async def test_tenant_user_device_isolation(self):
        denied = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_b, "AA:BB:CC:DD:EE:02"))
        self.assertEqual(denied.status, 403)
        mismatch = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a, "AA:BB:CC:DD:EE:02"))
        self.assertEqual(mismatch.status, 403)

    async def test_failed_conversion_keeps_previous_revision(self):
        response = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a))
        original = await response.json()
        path = self.source / "tenant-a" / "user-a" / "broken.md"
        path.write_bytes(b"\xff\xfe")
        failed = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a))
        self.assertEqual(failed.status, 400)
        path.unlink()
        recovered = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a))
        self.assertEqual(recovered.status, 200)
        self.assertEqual((await recovered.json())["data"]["revision"], original["data"]["revision"])

    async def test_oversized_source_is_rejected(self):
        path = self.source / "tenant-a" / "user-a" / "large.md"
        path.write_text("x" * 1025, encoding="utf-8")
        response = await self.client.get("/v1/knowledge/manifest", headers=self.headers(self.token_a))
        self.assertEqual(response.status, 413)


if __name__ == "__main__":
    unittest.main()
