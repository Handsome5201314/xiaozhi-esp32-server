import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from core.api.checklist_handler import UnifiedChecklistHandler
from core.routing.provider_resolver import ProviderInstance, ProviderResolver, ProviderResolutionError
from core.routing.hermes_router import HermesInstance, HermesResolver
from core.security.session import DeviceSessionAuthenticator, SessionError


class FakeSource:
    def __init__(self, title):
        self.title = title

    async def items(self):
        return [{"id": self.title, "title": self.title, "status": "pending"}]

    async def complete(self, guid):
        return {"id": guid, "status": "done"}

    async def create(self, title, request_id):
        return {"id": request_id, "title": title, "status": "pending"}


class DeviceSessionTests(unittest.TestCase):
    def setUp(self):
        self.auth = DeviceSessionAuthenticator("s" * 32)
        self.token = self.auth.issue("tenant-a", "user-a", "AA:BB:CC:DD:EE:01", "client-a", ["checklist:read", "checklist:write"])

    def test_context_contains_identity_and_revocation_is_immediate(self):
        context = self.auth.authenticate("Bearer " + self.token, "aa:bb:cc:dd:ee:01", "checklist:read")
        self.assertEqual((context.tenant_id, context.user_id), ("tenant-a", "user-a"))
        self.auth.revoke(context)
        with self.assertRaises(SessionError):
            self.auth.authenticate("Bearer " + self.token, "AA:BB:CC:DD:EE:01")

    def test_device_header_cannot_be_swapped(self):
        with self.assertRaises(SessionError) as error:
            self.auth.authenticate("Bearer " + self.token, "AA:BB:CC:DD:EE:02")
        self.assertEqual(error.exception.status, 403)


class UnifiedChecklistTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.auth = DeviceSessionAuthenticator("t" * 32)
        self.a = self.auth.issue("tenant-a", "user-a", "AA:BB:CC:DD:EE:01", "client-a", ["checklist:read"])
        self.b = self.auth.issue("tenant-a", "user-b", "AA:BB:CC:DD:EE:02", "client-b", ["checklist:read"])
        app = web.Application()
        app.add_routes(UnifiedChecklistHandler(self.auth, {"user-a": FakeSource("a"), "user-b": FakeSource("b")}).routes())
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_users_only_see_their_own_source(self):
        response = await self.client.get("/v1/checklist/items", headers={"Authorization": "Bearer " + self.a, "Device-Id": "AA:BB:CC:DD:EE:01"})
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["data"][0]["id"], "a")

    async def test_swapping_bearer_and_device_is_denied(self):
        response = await self.client.get("/v1/checklist/items", headers={"Authorization": "Bearer " + self.a, "Device-Id": "AA:BB:CC:DD:EE:02"})
        self.assertEqual(response.status, 403)


class ProviderResolverTests(unittest.TestCase):
    def test_device_binding_wins_over_user_and_tenant(self):
        resolver = ProviderResolver([
            ProviderInstance("tenant", "t", None, None, "llm", "https://example.com", priority=1),
            ProviderInstance("user", "t", "u", None, "llm", "https://example.com", priority=100),
            ProviderInstance("device", "t", "u", "d", "llm", "https://example.com", priority=100),
        ], allowed_hosts=["example.com"])
        self.assertEqual(resolver.resolve("t", "u", "d", "llm").id, "device")

    def test_private_provider_address_is_rejected(self):
        resolver = ProviderResolver([ProviderInstance("x", "t", "u", None, "tts", "https://127.0.0.1")])
        with self.assertRaises(ProviderResolutionError):
            resolver.resolve("t", "u", "d", "tts")

    def test_hermes_device_binding_and_health_failover(self):
        resolver = HermesResolver([
            HermesInstance("unhealthy", "t", "u", "d", "https://example.com", frozenset({"chat"}), healthy=False),
            HermesInstance("user", "t", "u", None, "https://example.com", frozenset({"chat"}), priority=10),
        ], allowed_hosts=["example.com"])
        self.assertEqual(resolver.resolve("t", "u", "d").id, "user")


if __name__ == "__main__":
    unittest.main()
