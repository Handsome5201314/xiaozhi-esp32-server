import json
import unittest
from pathlib import Path

from aiohttp import web
from aiohttp.client_exceptions import WSServerHandshakeError
from aiohttp.test_utils import AioHTTPTestCase

from core.api.medical_handler import MedicalHandler, medical_error_middleware
from core.medical.frame import AudioFrame, encode_frame


class MedicalGatewayTest(AioHTTPTestCase):
    api_key = "test-medical-api-key"

    async def get_application(self):
        root = self.root
        self.root = root
        beds = root / "beds.json"
        beds.write_text(
            json.dumps(
                {
                    "revision": 1,
                    "updated_at": "2026-08-21T12:00:00+08:00",
                    "beds": [
                        {"id": "1", "label": "1床", "enabled": True},
                        {"id": "9", "label": "9床", "enabled": False},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        handler = MedicalHandler(
            {
                "medical": {
                    "beds_file": str(beds),
                    "data_dir": str(root / "sessions"),
                    "api_key": self.api_key,
                }
            }
        )
        app = web.Application(middlewares=[medical_error_middleware])
        app.add_routes(handler.routes())
        return app

    async def asyncSetUp(self):
        import tempfile

        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        await super().asyncSetUp()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self._temp.cleanup()

    def auth_headers(self, device_id="box-01"):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Device-Id": device_id,
        }

    async def test_requires_bearer_key(self):
        response = await self.client.get("/v1/devices/box-01/beds")
        self.assertEqual(response.status, 401)
        self.assertEqual((await response.json())["error"]["code"], "AUTH_REQUIRED")

        response = await self.client.get(
            "/v1/devices/box-01/beds",
            headers={"Authorization": "Bearer wrong-key", "Device-Id": "box-01"},
        )
        self.assertEqual(response.status, 401)
        self.assertEqual((await response.json())["error"]["code"], "AUTH_REQUIRED")

    async def test_rejects_device_identity_mismatch(self):
        response = await self.client.get(
            "/v1/devices/box-02/beds", headers=self.auth_headers("box-01")
        )
        self.assertEqual(response.status, 403)
        self.assertEqual((await response.json())["error"]["code"], "DEVICE_MISMATCH")

        response = await self.client.post(
            "/v1/sessions",
            headers=self.auth_headers("box-01"),
            json={"device_id": "box-02", "mode": "general", "bed_id": None},
        )
        self.assertEqual(response.status, 403)
        self.assertEqual((await response.json())["error"]["code"], "DEVICE_MISMATCH")

    async def test_beds_and_disabled_bed(self):
        response = await self.client.get(
            "/medical/v1/devices/box-01/beds", headers=self.auth_headers()
        )
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["beds"][0]["id"], "1")

        response = await self.client.post(
            "/v1/sessions",
            headers=self.auth_headers(),
            json={"device_id": "box-01", "mode": "bed", "bed_id": "9"},
        )
        self.assertEqual(response.status, 409)
        self.assertEqual((await response.json())["error"]["code"], "BED_DISABLED")

    async def test_audio_ack_and_finish(self):
        response = await self.client.post(
            "/medical/v1/sessions",
            headers=self.auth_headers(),
            json={"device_id": "box-01", "mode": "general", "bed_id": None},
        )
        self.assertEqual(response.status, 201)
        session_id = (await response.json())["session_id"]

        with self.assertRaises(WSServerHandshakeError) as mismatch:
            await self.client.ws_connect(
                f"/v1/sessions/{session_id}/audio", headers=self.auth_headers("box-02")
            )
        self.assertEqual(mismatch.exception.status, 403)

        websocket = await self.client.ws_connect(
            f"/v1/sessions/{session_id}/audio", headers=self.auth_headers()
        )
        await websocket.send_bytes(encode_frame(AudioFrame(0, 0, 0, b"opus")))
        message = await websocket.receive_json()
        self.assertEqual(message, {"type": "ack", "sequence": 0})
        await websocket.close()

        response = await self.client.post(
            f"/medical/v1/sessions/{session_id}/finish",
            headers=self.auth_headers("box-02"),
            json={"last_sequence": 0},
        )
        self.assertEqual(response.status, 403)
        self.assertEqual((await response.json())["error"]["code"], "DEVICE_MISMATCH")

        response = await self.client.post(
            f"/medical/v1/sessions/{session_id}/finish",
            headers=self.auth_headers(),
            json={"last_sequence": 0},
        )
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["status"], "completed")
        self.assertTrue((self.root / "sessions" / session_id / "recording.ogg").exists())

    async def test_finish_rejects_invalid_sequence_values(self):
        response = await self.client.post(
            "/v1/sessions",
            headers=self.auth_headers(),
            json={"device_id": "box-01", "mode": "general", "bed_id": None},
        )
        self.assertEqual(response.status, 201)
        session_id = (await response.json())["session_id"]

        for last_sequence in (-2, True, 1.5, "0", None):
            with self.subTest(last_sequence=last_sequence):
                response = await self.client.post(
                    f"/v1/sessions/{session_id}/finish",
                    headers=self.auth_headers(),
                    json={"last_sequence": last_sequence},
                )
                self.assertEqual(response.status, 422)
                self.assertEqual((await response.json())["error"]["code"], "INVALID_REQUEST")
                self.assertFalse((self.root / "sessions" / session_id / "finish.json").exists())

    async def test_empty_session_can_finish_without_audio_frames(self):
        response = await self.client.post(
            "/v1/sessions",
            headers=self.auth_headers(),
            json={"device_id": "box-01", "mode": "general", "bed_id": None},
        )
        self.assertEqual(response.status, 201)
        session_id = (await response.json())["session_id"]

        response = await self.client.post(
            f"/v1/sessions/{session_id}/finish",
            headers=self.auth_headers(),
            json={"last_sequence": -1},
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.json(), {"status": "completed", "missing": []})
        self.assertTrue((self.root / "sessions" / session_id / "recording.ogg").exists())


if __name__ == "__main__":
    unittest.main()
