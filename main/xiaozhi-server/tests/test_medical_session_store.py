import tempfile
import unittest
from pathlib import Path

from core.medical.session_store import SessionCreate, SessionStore


class MedicalSessionStoreTest(unittest.TestCase):
    def test_finish_rejects_sequence_before_empty_session_sentinel(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SessionStore(Path(temporary))
            session = store.create(
                SessionCreate(device_id="box-01", mode="general", bed_id=None)
            )
            with self.assertRaisesRegex(ValueError, "last_sequence must be >= -1"):
                store.finish(session.session_id, -2)


if __name__ == "__main__":
    unittest.main()
