"""Run the full StatsBank pipeline: load data, compute stats, write outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from moneydisc.analysis.config import GAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default="data/raw",
        help="Directory containing downloaded game CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory to write computed outputs.",
    )
    parser.add_argument(
        "--model-dir",
        default="models",
        help="Directory containing GPA model pickle files.",
    )
    return parser.parse_args()


def run(
    input_dir: str,
    output_dir: str,
    model_dir: str = "models",
    games: dict[str, str] | None = None,
) -> Path:
    from moneydisc.analysis.stats_bank import StatsBank

    sb = StatsBank(
        data_dir=input_dir,
        output_dir=output_dir,
        model_dir=model_dir,
        games=games if games is not None else GAMES,
    )
    sb.prepare_data()
    sb.compute_all_stats()
    sb.export_stats()
    return Path(output_dir) / "aggregated_player_stats.csv"


def main() -> None:
    args = parse_args()
    output_file = run(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        model_dir=args.model_dir,
    )
    print(f"Wrote {output_file}")


if __name__ == "__main__":
    main()
