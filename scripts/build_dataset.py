from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rappi_availability.load_data import load_all_availability_data, save_processed_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized Rappi availability dataset.")
    parser.add_argument("--input", default="Archivo (1)", help="Folder containing exported CSV files.")
    parser.add_argument(
        "--output",
        default="data/processed/availability_long.csv",
        help="Destination normalized CSV path.",
    )
    args = parser.parse_args()

    frame = load_all_availability_data(args.input)
    output_path = save_processed_dataset(frame, args.output)
    print(f"Wrote {len(frame):,} rows to {output_path}")


if __name__ == "__main__":
    main()
