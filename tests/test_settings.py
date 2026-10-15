from pathlib import Path
import unittest
from unittest.mock import patch

from app.config import AppSettings, SettingsError
from app.config.settings import validate_local_endpoint


class SettingsTests(unittest.TestCase):
    def test_settings_use_project_local_paths(self) -> None:
        root = Path("/private/tmp/healthcare-settings-test")
        settings = AppSettings.from_environment(root)

        self.assertEqual(settings.paths.raw_data_dir, root / "data" / "raw")
        self.assertEqual(settings.paths.vector_store_dir, root / "vector_store")
        self.assertEqual(settings.ollama_base_url, "http://127.0.0.1:11434")

    def test_remote_ollama_endpoints_are_rejected(self) -> None:
        for endpoint in ("https://example.com", "http://192.168.1.10:11434", "http://ollama.local"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(SettingsError):
                    validate_local_endpoint(endpoint)

    def test_invalid_chunk_overlap_is_rejected(self) -> None:
        with patch.dict(
            "os.environ",
            {"HEALTHCARE_CHUNK_SIZE": "100", "HEALTHCARE_CHUNK_OVERLAP": "100"},
            clear=False,
        ):
            with self.assertRaisesRegex(SettingsError, "CHUNK_OVERLAP"):
                AppSettings.from_environment(Path("/private/tmp/healthcare-settings-test"))

