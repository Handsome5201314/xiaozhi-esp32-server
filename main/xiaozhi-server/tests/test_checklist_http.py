import unittest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from core.api.checklist_handler import ChecklistHandler, ChecklistError
from core.providers.tasks.feishu_checklist import FeishuChecklist


class FakeChecklist:
    async def items(self):
        return [{"id": "task-1", "title": "中文待办", "planDate": "", "planTime": "", "status": "pending"}]

    async def complete(self, guid):
        raise ChecklistError(404, "任务不属于胸卡清单")

    async def create(self, title, request_id):
        raise ChecklistError(400, "任务标题不能为空且不得超过 500 字")


class ChecklistHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # A real provider object: denied requests must never reach its network boundary.
        source = FeishuChecklist("unused", "unused", "00000000-0000-0000-0000-000000000001", "unused")
        handler = ChecklistHandler("a"*32, "10:20:ba:6e:0b:90", source)
        app = web.Application()
        app.add_routes(handler.routes())
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.path = "/b/" + "a"*32 + "/xiaozhi/api/checklist/items"

    async def asyncTearDown(self):
        await self.client.close()

    async def test_missing_mac_and_wrong_secret_are_denied(self):
        for path, headers in [(self.path+"/all", {}), (self.path.replace("a"*32, "b"*32)+"/all", {"Device-Id":"10:20:ba:6e:0b:90"})]:
            response = await self.client.get(path, headers=headers)
            self.assertEqual(response.status, 401)
            self.assertIsNone((await response.json())["data"])

    async def test_deletion_is_explicitly_disabled(self):
        response = await self.client.delete(self.path+"/anything", headers={"Device-Id":"10:20:ba:6e:0b:90"})
        self.assertEqual(response.status, 405)
        self.assertEqual((await response.json())["code"], 405)

    async def test_native_completion_post_accepts_empty_body_and_validates_id(self):
        response = await self.client.post(self.path+"/invalid-id/complete",
                                          headers={"Device-Id":"10:20:ba:6e:0b:90"}, data=b"")
        self.assertEqual(response.status, 400)
        body = await response.json()
        self.assertEqual(body["code"], 400)
        self.assertIsNone(body["data"])

    async def test_native_completion_requires_device_authentication(self):
        response = await self.client.post(self.path+"/invalid-id/complete", data=b"")
        self.assertEqual(response.status, 401)

    async def test_invalid_create_body_rejected_before_network(self):
        for body in [[], {"title":"test"}, {"title":"", "request_id":"bad"}]:
            response = await self.client.post(self.path, headers={"Device-Id":"10:20:ba:6e:0b:90"}, json=body)
            self.assertEqual(response.status, 400)

    async def test_success_response_uses_compact_utf8_json(self):
        handler = ChecklistHandler("a"*32, "10:20:ba:6e:0b:90", FakeChecklist())
        app = web.Application()
        app.add_routes(handler.routes())
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get(self.path + "/all", headers={"Device-Id": "10:20:ba:6e:0b:90"})
            self.assertEqual(response.status, 200)
            body = await response.read()
            expected = '{"code":0,"msg":"success","data":[{"id":"task-1","title":"中文待办","planDate":"","planTime":"","status":"pending"}]}'.encode("utf-8")
            self.assertEqual(body, expected)
            self.assertNotIn(b": ", body)
            self.assertNotIn(b"\\u", body)
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
