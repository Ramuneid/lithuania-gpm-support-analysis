import hashlib
import importlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
verification = importlib.import_module("08_verify_reproducibility")


class OutputHashTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.html_dir = self.root / "outputs/heatmaps"
        self.html_dir.mkdir(parents=True)
        for name in verification.EXPECTED_HTML_REPORTS:
            (self.html_dir / name).write_text("<html>Report</html>", encoding="utf-8")

    def test_hashes_csv_and_html_and_detects_changed_bytes(self):
        csv = self.root / "data/processed/recipients.csv"
        csv.parent.mkdir(parents=True)
        csv.write_text("recipient_code\n00123\n", encoding="utf-8")
        nested = self.html_dir / "extra/report.html"
        nested.parent.mkdir()
        nested.write_text("<html>Additional report</html>", encoding="utf-8")
        archive = self.root / "outputs/reproducibility/old/report.html"
        archive.parent.mkdir(parents=True)
        archive.write_text("Old report", encoding="utf-8")
        before = verification.collect_output_hashes(self.root)
        for path in [csv, nested, *(self.html_dir / n for n in verification.EXPECTED_HTML_REPORTS)]:
            self.assertEqual(before[str(path.relative_to(self.root))], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertNotIn(str(archive.relative_to(self.root)), before)
        self.assertEqual(len(before), len(verification.EXPECTED_HTML_REPORTS) + 2)
        nested.write_text("<html>Changed report</html>", encoding="utf-8")
        after = verification.collect_output_hashes(self.root)
        self.assertNotEqual(before[str(nested.relative_to(self.root))], after[str(nested.relative_to(self.root))])

    def test_missing_expected_export_fails(self):
        (self.html_dir / verification.EXPECTED_HTML_REPORTS[0]).unlink()
        with self.assertRaisesRegex(RuntimeError, "Missing or empty expected HTML report"):
            verification.collect_output_hashes(self.root)

    def test_empty_expected_export_fails(self):
        (self.html_dir / verification.EXPECTED_HTML_REPORTS[0]).write_bytes(b"")
        with self.assertRaisesRegex(RuntimeError, "Missing or empty expected HTML report"):
            verification.collect_output_hashes(self.root)
