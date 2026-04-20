import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from moneydisc.data_ingestion.download_google_drive import download_folder


class DownloadGoogleDriveTests(unittest.TestCase):
    @patch("moneydisc.data_ingestion.download_google_drive.gdown.download_folder")
    def test_download_folder_creates_output_dir(self, mock_download_folder) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "raw"
            download_folder("https://drive.google.com/drive/folders/example", str(output_dir))
            self.assertTrue(output_dir.exists())
            mock_download_folder.assert_called_once_with(
                url="https://drive.google.com/drive/folders/example",
                output=str(output_dir),
                quiet=False,
            )


if __name__ == "__main__":
    unittest.main()
