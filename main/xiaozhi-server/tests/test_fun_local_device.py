import tempfile
import unittest
from unittest.mock import patch

from core.providers.asr.fun_local import ASRProvider


class FunLocalDeviceTest(unittest.TestCase):
    def _config(self, output_dir, device):
        return {
            "model_dir": "models/SenseVoiceSmall",
            "output_dir": output_dir,
            "language": "zh",
            "device": device,
        }

    def test_passes_explicit_cuda_device_to_model(self):
        with tempfile.TemporaryDirectory() as output_dir:
            with (
                patch("core.providers.asr.fun_local.torch.cuda.is_available", return_value=True),
                patch("core.providers.asr.fun_local.torch.cuda.device_count", return_value=1),
                patch("core.providers.asr.fun_local.AutoModel") as auto_model,
            ):
                ASRProvider(self._config(output_dir, "cuda:0"), False)

        self.assertEqual(auto_model.call_args.kwargs["device"], "cuda:0")

    def test_rejects_cuda_when_runtime_is_unavailable(self):
        with tempfile.TemporaryDirectory() as output_dir:
            with (
                patch("core.providers.asr.fun_local.torch.cuda.is_available", return_value=False),
                patch("core.providers.asr.fun_local.AutoModel"),
                self.assertRaisesRegex(RuntimeError, "cuda:0"),
            ):
                ASRProvider(self._config(output_dir, "cuda:0"), False)

    def test_passes_explicit_cpu_device_to_model(self):
        with tempfile.TemporaryDirectory() as output_dir:
            with patch("core.providers.asr.fun_local.AutoModel") as auto_model:
                ASRProvider(self._config(output_dir, "cpu"), False)

        self.assertEqual(auto_model.call_args.kwargs["device"], "cpu")


if __name__ == "__main__":
    unittest.main()
