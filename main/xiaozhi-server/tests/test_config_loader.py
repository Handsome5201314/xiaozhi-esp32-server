import unittest
from unittest.mock import AsyncMock, patch

from config.config_loader import get_config_from_api_async


class ConfigLoaderTest(unittest.IsolatedAsyncioTestCase):
    async def test_manager_api_keeps_local_medical_config(self):
        local_config = {
            "manager-api": {"url": "http://manager", "secret": "manager-secret"},
            "server": {
                "ip": "0.0.0.0",
                "port": 8000,
                "http_port": 8003,
                "websocket": "wss://tongyimoheai.top/xiaozhi/v1/",
            },
            "medical": {
                "api_key": "medical-secret",
                "beds_file": "data/medical/beds.json",
                "data_dir": "data/medical/sessions",
            },
        }
        remote_config = {
            "server": {"auth": {"enabled": False}},
            "prompt_template": "agent-base-prompt.txt",
        }

        with (
            patch("config.config_loader.init_service"),
            patch(
                "config.config_loader.get_server_config",
                new=AsyncMock(return_value=remote_config),
            ),
        ):
            loaded = await get_config_from_api_async(local_config)

        self.assertEqual(loaded.get("medical"), local_config["medical"])
        self.assertEqual(
            loaded["server"]["websocket"], local_config["server"]["websocket"]
        )


if __name__ == "__main__":
    unittest.main()
