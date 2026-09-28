import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

spec = importlib.util.spec_from_file_location('download_sources', Path(__file__).resolve().parents[1] / 'src/01_download_sources.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceConfigTests(unittest.TestCase):
    def test_optional_local_override_preserves_registry_fields(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sources.yaml'
            path.write_text('metadata:\n  raw_file: "metadata.csv"\n  local_path: "placeholder"\n', encoding='utf-8')
            self.assertEqual(module.load_sources(path)['metadata']['local_path'], 'placeholder')
            path.with_name('sources.local.yaml').write_text('metadata:\n  local_path: "D:/private/metadata.csv"\n', encoding='utf-8')
            result = module.load_sources(path)['metadata']
            self.assertEqual(result['local_path'], 'D:/private/metadata.csv')
            self.assertEqual(result['raw_file'], 'metadata.csv')

    def test_unknown_override_fails(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sources.yaml'
            path.write_text('metadata:\n  raw_file: "metadata.csv"\n  local_path: "placeholder"\n', encoding='utf-8')
            path.with_name('sources.local.yaml').write_text('typo:\n  local_path: "file.csv"\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unknown local source'):
                module.load_sources(path)
