import asyncio
import queue
import unittest
from unittest.mock import patch

from loguru import logger

from core.connection import ConnectionHandler


class ConnectionBindWaitTests(unittest.TestCase):
    def test_first_message_waits_for_manager_binding_state(self):
        routed_messages = []
        false_bind_prompts = []

        async def record_message(_connection, message):
            routed_messages.append(message)

        async def record_false_bind_prompt():
            false_bind_prompts.append(True)

        async def exercise():
            connection = ConnectionHandler.__new__(ConnectionHandler)
            connection.bind_completed_event = asyncio.Event()
            connection.need_bind = False
            connection.config = {}
            connection.vad = object()
            connection.asr = object()
            connection._discard_message_with_bind_prompt = record_false_bind_prompt

            async def finish_manager_lookup():
                await asyncio.sleep(1.1)
                connection.bind_completed_event.set()

            lookup = asyncio.create_task(finish_manager_lookup())
            await connection._route_message("hello")
            await lookup

        with patch("core.connection.handleTextMessage", record_message):
            asyncio.run(exercise())

        self.assertEqual(routed_messages, ["hello"])
        self.assertEqual(false_bind_prompts, [])


class ConnectionBindTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_keeps_binding_unknown_and_later_audio_recovers(self):
        connection = ConnectionHandler.__new__(ConnectionHandler)
        connection.bind_completed_event = asyncio.Event()
        connection.need_bind = False
        connection.logger = logger
        connection.last_bind_prompt_time = 0
        connection.bind_prompt_interval = 60
        connection.vad = object()
        connection.asr = object()
        connection.conn_from_mqtt_gateway = False
        connection.asr_audio_queue = queue.Queue()

        await asyncio.wait_for(connection._route_message(b"early-audio"), timeout=12)

        self.assertFalse(connection.bind_completed_event.is_set())
        self.assertFalse(connection.need_bind)
        self.assertEqual(connection.last_bind_prompt_time, 0)
        self.assertTrue(connection.asr_audio_queue.empty())

        connection.bind_completed_event.set()
        await connection._route_message(b"ready-audio")
        self.assertEqual(connection.asr_audio_queue.get_nowait(), b"ready-audio")
        self.assertTrue(connection.asr_audio_queue.empty())


if __name__ == "__main__":
    unittest.main()
