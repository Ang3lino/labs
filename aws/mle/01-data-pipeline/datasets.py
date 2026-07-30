from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from random import Random


LAB_DIR = Path(__file__).resolve().parent
MLE_ROOT = LAB_DIR.parent
if str(MLE_ROOT) not in sys.path:
    sys.path.insert(0, str(MLE_ROOT))

from shared.datasets import DatasetManager


OUTPUT_FILENAME = "01-data-pipeline/fraud_data.csv"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage synthetic fraud dataset for Lab 01")
    parser.add_argument("--download", action="store_true", help="Generate and cache synthetic CSV")
    parser.add_argument("--cleanup", action="store_true", help="Remove cached synthetic CSV")
    return parser


def _generate_synthetic_fraud_csv(destination: Path) -> Path:
    header_columns = [f"V{index}" for index in range(1, 31)] + ["Amount", "Class"]

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        from sklearn.datasets import make_classification

        features, labels = make_classification(
            n_samples=10000,
            n_features=30,
            n_informative=10,
            n_redundant=10,
            n_repeated=0,
            n_classes=2,
            weights=[0.99, 0.01],
            random_state=42,
        )

        with destination.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header_columns)
            for feature_row, label in zip(features, labels, strict=True):
                amount_value = abs(float(feature_row[0])) * 100.0
                writer.writerow([*feature_row, amount_value, int(label)])
    except ModuleNotFoundError:
        random = Random(42)
        with destination.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header_columns)
            for index in range(10000):
                feature_row = [random.gauss(0.0, 1.0) for _ in range(30)]
                amount_value = abs(feature_row[0]) * 100.0
                label = 1 if index < 100 else 0
                writer.writerow([*feature_row, amount_value, label])

    return destination


def _handle_download(manager: DatasetManager) -> int:
    output_path = manager.cache_dir / OUTPUT_FILENAME
    generated_path = _generate_synthetic_fraud_csv(output_path)
    # ponytail: synthetic fallback avoids Kaggle API key requirement
    # ponytail: if sklearn isn't installed locally, generate deterministic fallback rows
    print(generated_path)
    return 0


def _handle_cleanup(manager: DatasetManager) -> int:
    manager.cleanup(OUTPUT_FILENAME)
    print(f"Removed cache file: {manager.cache_dir / OUTPUT_FILENAME}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    manager = DatasetManager()

    if args.download:
        return _handle_download(manager)

    if args.cleanup:
        return _handle_cleanup(manager)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
