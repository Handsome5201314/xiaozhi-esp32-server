import asyncio
import tempfile
import unittest
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer
from aiohttp import web

from core.api.daily_summary_handler import DailySummaryHandler, DailySummaryStore
from core.security.session import DeviceSessionAuthenticator


class DailySummaryHandlerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.auth = DeviceSessionAuthenticator("x" * 32)
        self.token = self.auth.issue("tenant-a", "user-a", "AA:BB:CC:DD:EE:01", "client", ["summary:read", "summary:write"])
        self.handler = DailySummaryHandler(self.auth, DailySummaryStore(str(Path(self.tmp.name) / "summary.json")))
        app = web.Application()
        app.add_routes(self.handler.routes())
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    async def test_missing_summary_is_observable(self):
        response = await self.client.get("/v1/daily-summary/today", headers={"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"})
        self.assertEqual(response.status, 404)

    async def test_generate_without_hermes_does_not_fabricate(self):
        response = await self.client.post("/v1/daily-summary/generate", headers={"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"})
        self.assertEqual(response.status, 503)

    async def test_hermes_can_submit_generated_content(self):
        response = await self.client.post(
            "/v1/daily-summary/generate?date=2026-09-16",
            headers={"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"},
            json={"title": "值班总结", "content": "完成查房与用药核对"},
        )
        self.assertEqual(response.status, 200)
        payload = await response.json()
        self.assertEqual(payload["data"]["title"], "值班总结")
        self.assertEqual(payload["data"]["content"], "完成查房与用药核对")

    async def test_summary_content_limit_is_enforced(self):
        response = await self.client.post(
            "/v1/daily-summary/generate?date=2026-09-16",
            headers={"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"},
            json={"content": "x" * 4001},
        )
        self.assertEqual(response.status, 400)

    async def test_cross_device_is_rejected(self):
        response = await self.client.get("/v1/daily-summary/today", headers={"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:02"})
        self.assertEqual(response.status, 403)

    async def test_generate_is_idempotent_per_user_and_date(self):
        calls = 0

        async def generator(_context, _date):
            nonlocal calls
            calls += 1
            return "完成事项：查房"

        handler = DailySummaryHandler(self.auth, self.handler.store, generator)
        status1, item1 = await handler.generate_once(self.auth.decode(self.token), "2026-09-16")
        status2, item2 = await handler.generate_once(self.auth.decode(self.token), "2026-09-16")
        self.assertEqual((status1, status2), (200, 200))
        self.assertEqual(calls, 1)
        self.assertEqual(item1["content"], item2["content"])

    async def test_concurrent_generation_calls_hermes_once(self):
        calls = 0

        async def generator(_context, _date):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.02)
            return "并发生成结果"

        self.handler.generator = generator
        context = self.auth.decode(self.token)
        results = await asyncio.gather(*(
            self.handler.generate_once(context, "2026-09-16") for _ in range(8)
        ))
        self.assertEqual(calls, 1)
        self.assertTrue(all(status == 200 for status, _ in results))

    async def test_same_user_id_in_other_tenant_cannot_read_or_ack(self):
        async def generator(_context, _date):
            return "仅租户 A 可读"

        self.handler.generator = generator
        await self.handler.generate_once(self.auth.decode(self.token), "2026-09-16")
        token_b = self.auth.issue("tenant-b", "user-a", "AA:BB:CC:DD:EE:01", "client", ["summary:read"])
        headers = {"Authorization": "Bearer " + token_b, "Device-Id": "AA:BB:CC:DD:EE:01"}
        response = await self.client.get("/v1/daily-summary/today?date=2026-09-16", headers=headers)
        self.assertEqual(response.status, 404)
        response = await self.client.post("/v1/daily-summary/ack?date=2026-09-16", headers=headers,
                                          json={"revision": "wrong-owner"})
        self.assertEqual(response.status, 404)

    async def test_corrupt_store_is_not_treated_as_empty(self):
        self.handler.store.path.write_text("{broken", encoding="utf-8")
        response = await self.client.get("/v1/daily-summary/today", headers={
            "Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"})
        self.assertEqual(response.status, 503)
        self.assertEqual(self.handler.store.path.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
