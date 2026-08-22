import unittest

from core.http_server import SimpleHttpServer


class HttpServerRoutesTest(unittest.TestCase):
    def test_manager_api_mode_still_exposes_device_ota_routes(self):
        server = SimpleHttpServer(
            {
                "read_config_from_api": True,
                "server": {
                    "ip": "0.0.0.0",
                    "port": 8000,
                    "http_port": 8003,
                    "auth_key": "test-auth-key",
                    "auth": {"enabled": False},
                },
            }
        )

        app = server.create_application()
        routes = {
            (route.method, route.resource.canonical) for route in app.router.routes()
        }

        self.assertIn(("GET", "/xiaozhi/ota/"), routes)
        self.assertIn(("POST", "/xiaozhi/ota/"), routes)
        self.assertIn(("OPTIONS", "/xiaozhi/ota/"), routes)


if __name__ == "__main__":
    unittest.main()
