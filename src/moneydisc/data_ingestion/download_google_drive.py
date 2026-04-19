"""Download files from a Google Drive folder."""

from __future__ import annotations

import argparse
from pathlib import Path

import gdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder-url", required=True, help="Google Drive folder URL.")
    parser.add_argument(
        "--output-dir",
        default="data/raw",
        help="Directory where files should be downloaded.",
    )
    return parser.parse_args()


def download_folder(folder_url: str, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    gdown.download_folder(url=folder_url, output=str(output_path), quiet=False)


def main() -> None:
    args = parse_args()
    download_folder(folder_url=args.folder_url, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
