import json
import os
import tempfile
import unittest

import httpx

from core.providers.llm.hermes import HermesChatClient, HermesChatError


class HermesClientTest(unittest.TestCase):
    def transport(self, handler):
        return httpx.MockTransport(handler)

    def test_non_stream_response_uses_model_and_returns_text(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(body["model"], "301-pediatrics")
            self.assertEqual(request.headers["authorization"], "Bearer secret")
            return httpx.Response(200, json={"choices": [{"message": {"content": "答复"}}]})

        client = HermesChatClient("https://hermes.example", "secret", "301-pediatrics",
                                  stream=False, transport=self.transport(handler))
        self.assertEqual("答复", "".join(client.response("s", [{"role": "user", "content": "你好"}])))

    def test_sse_concatenates_content_and_tool_deltas(self):
        body = "data: {\"choices\":[{\"delta\":{\"content\":\"你\"}}]}\n\n" \
               "data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"c1\",\"function\":{\"name\":\"quiz\",\"arguments\":\"{\\\"x\\\":1\"}}]}}]}\n\n" \
               "data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"function\":{\"arguments\":\"}\"}}]}}]}\n\n" \
               "data: [DONE]\n\n"

        def handler(request):
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)

        client = HermesChatClient("https://hermes.example", "secret", stream=True,
                                  transport=self.transport(handler))
        parts = list(client.response_with_functions("s", [{"role": "user", "content": "题"}], []))
        self.assertEqual("你", parts[0][0])
        self.assertEqual("quiz", parts[1][1][0].function.name)
        self.assertEqual("{\"x\":1", parts[1][1][0].function.arguments)
        self.assertEqual("}", parts[2][1][0].function.arguments)

    def test_status_and_invalid_payload_are_explicit_errors(self):
        def unauthorized(_request):
            return httpx.Response(401, json={"error": "bad"})

        client = HermesChatClient("https://hermes.example", "secret", stream=False,
                                  transport=self.transport(unauthorized))
        with self.assertRaisesRegex(HermesChatError, "鉴权"):
            list(client.response("s", []))

        def malformed(_request):
            return httpx.Response(200, json={"choices": []})

        client = HermesChatClient("https://hermes.example", "secret", stream=False,
                                  transport=self.transport(malformed))
        with self.assertRaises(HermesChatError):
            list(client.response("s", []))

    def test_invalid_configured_ca_is_rejected_before_request(self):
        with self.assertRaisesRegex(ValueError, "CA"):
            HermesChatClient("https://hermes.example", "secret", ca_cert=os.path.join(
                tempfile.gettempdir(), "missing-hermes-ca.crt"))


if __name__ == "__main__":
    unittest.main()
