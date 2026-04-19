"""Minimal entrypoint for loading downloaded files and computing stats."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default="data/raw",
        help="Directory containing downloaded game files.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory to write computed outputs.",
    )
    return parser.parse_args()


def load_data_files(input_dir: str) -> list[Path]:
    input_path = Path(input_dir)
    if not input_path.exists():
        return []
    return sorted(path for path in input_path.rglob("*") if path.is_file())


def run(input_dir: str, output_dir: str) -> Path:
    files = load_data_files(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_file = output_path / "summary.txt"
    summary_file.write_text(f"Loaded {len(files)} file(s) from {input_dir}\n", encoding="utf-8")
    return summary_file


def main() -> None:
    args = parse_args()
    summary_file = run(input_dir=args.input_dir, output_dir=args.output_dir)
    print(f"Wrote {summary_file}")


if __name__ == "__main__":
    main()
