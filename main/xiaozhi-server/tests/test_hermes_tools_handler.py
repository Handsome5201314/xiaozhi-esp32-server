import sys
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from core.api.hermes_tools_handler import HermesToolsHandler
from core.security.session import DeviceSessionAuthenticator


class _Result:
    action = "response"
    response = "ok"
    content = None


class _Manager:
    def get_function_descriptions(self):
        return [{"type": "function", "function": {"name": "checklist.list"}}]

    async def execute_tool(self, name, arguments):
        assert name == "checklist.list"
        return _Result()


class HermesToolsHandlerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.auth = DeviceSessionAuthenticator("t" * 32)
        self.token = self.auth.issue("tenant-a", "user-a", "AA:BB:CC:DD:EE:01", "hermes", ["tools:call"])
        app = web.Application()
        app.add_routes(HermesToolsHandler(self.auth, lambda _context: _Manager()).routes())
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_list_and_call_require_device_session(self):
        headers = {"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"}
        response = await self.client.get("/v1/hermes/tools", headers=headers)
        self.assertEqual(response.status, 200)
        response = await self.client.post("/v1/hermes/tools/call", headers=headers,
                                          json={"name": "checklist.list", "arguments": {}})
        self.assertEqual(response.status, 200)
        response = await self.client.get("/v1/hermes/tools", headers={"Device-Id": headers["Device-Id"]})
        self.assertEqual(response.status, 401)

    async def test_gateway_rejects_tools_outside_first_batch(self):
        headers = {"Authorization": "Bearer " + self.token, "Device-Id": "AA:BB:CC:DD:EE:01"}
        response = await self.client.post("/v1/hermes/tools/call", headers=headers,
                                          json={"name": "reboot", "arguments": {}})
        self.assertEqual(response.status, 404)


if __name__ == "__main__":
    unittest.main()
