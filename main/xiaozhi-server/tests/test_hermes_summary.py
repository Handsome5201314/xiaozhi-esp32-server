import unittest

from core.routing.hermes_router import HermesInstance, HermesResolver
from core.routing.hermes_summary import HermesSummaryClient
from core.routing.provider_resolver import ProviderResolutionError


class HermesSummaryClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_user_cannot_use_another_users_summary_instance(self):
        resolver = HermesResolver([
            HermesInstance("h1", "tenant-a", "user-a", None, "https://hermes.example.com", frozenset({"summary"}))
        ], allowed_hosts=["hermes.example.com"])
        client = HermesSummaryClient(resolver, lambda _id: "unused")
        with self.assertRaises(ProviderResolutionError):
            await client.generate("tenant-a", "user-b", "device-b", "今日事项")

    async def test_summary_capability_is_required(self):
        resolver = HermesResolver([
            HermesInstance("h1", "tenant-a", "user-a", None, "https://hermes.example.com", frozenset({"chat"}))
        ], allowed_hosts=["hermes.example.com"])
        client = HermesSummaryClient(resolver, lambda _id: "unused")
        with self.assertRaises(ProviderResolutionError):
            await client.generate("tenant-a", "user-a", "device-a", "今日事项")

    async def test_missing_secret_fails_before_network_call(self):
        resolver = HermesResolver([
            HermesInstance("h1", "tenant-a", "user-a", None, "https://hermes.example.com", frozenset({"summary"}))
        ], allowed_hosts=["hermes.example.com"])
        client = HermesSummaryClient(resolver, lambda _id: "")
        with self.assertRaisesRegex(RuntimeError, "凭据"):
            await client.generate("tenant-a", "user-a", "device-a", "今日事项")


if __name__ == "__main__":
    unittest.main()
