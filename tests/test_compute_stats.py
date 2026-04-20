import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from moneydisc.analysis.compute_stats import load_data_files, run


class ComputeStatsTests(unittest.TestCase):
    def test_load_data_files_recurses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "sub").mkdir()
            (base / "a.csv").write_text("a", encoding="utf-8")
            (base / "sub" / "b.csv").write_text("b", encoding="utf-8")
            files = load_data_files(str(base))
            self.assertEqual([f.name for f in files], ["a.csv", "b.csv"])

    def test_run_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            in_dir = base / "in"
            out_dir = base / "out"
            in_dir.mkdir()
            (in_dir / "game1.csv").write_text("contents", encoding="utf-8")
            summary_file = run(str(in_dir), str(out_dir))
            self.assertTrue(summary_file.exists())
            self.assertIn("Loaded 1 file(s)", summary_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
