from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from random import Random


LAB_DIR = Path(__file__).resolve().parent
MLE_ROOT = LAB_DIR.parent
if str(MLE_ROOT) not in sys.path:
    sys.path.insert(0, str(MLE_ROOT))

from shared.datasets import DatasetManager


OUTPUT_FILENAME = "08-capstone/fraud_data.csv"
VERSION_FILENAME = "08-capstone/data_version.json"


@dataclass(frozen=True, slots=True)
class DataVersion:
    dataset_path: str
    generated_at_utc: str
    row_count: int
    feature_hash: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage synthetic fraud dataset for Lab 08 capstone")
    parser.add_argument("--download", action="store_true", help="Generate and cache synthetic CSV + version metadata")
    parser.add_argument("--cleanup", action="store_true", help="Remove cached synthetic CSV + version metadata")
    return parser


def _dataset_header_columns() -> list[str]:
    return [f"V{index}" for index in range(1, 31)] + ["Amount", "Class"]


def _generate_synthetic_fraud_csv(destination: Path) -> int:
    header_columns = _dataset_header_columns()
    destination.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
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
                rows_written += 1
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
                rows_written += 1

    return rows_written


def _compute_feature_hash(csv_path: Path) -> str:
    digest = hashlib.sha256()
    with csv_path.open("rb") as csv_file:
        for chunk in iter(lambda: csv_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_data_version(version_path: Path, version: DataVersion) -> None:
    payload = {
        "dataset_path": version.dataset_path,
        "generated_at_utc": version.generated_at_utc,
        "row_count": version.row_count,
        "feature_hash": version.feature_hash,
    }
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _handle_download(manager: DatasetManager) -> int:
    dataset_path = manager.cache_dir / OUTPUT_FILENAME
    version_path = manager.cache_dir / VERSION_FILENAME

    row_count = _generate_synthetic_fraud_csv(dataset_path)
    feature_hash = _compute_feature_hash(dataset_path)
    generated_at_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    version = DataVersion(
        dataset_path=str(dataset_path),
        generated_at_utc=generated_at_utc,
        row_count=row_count,
        feature_hash=feature_hash,
    )
    _write_data_version(version_path, version)

    # ponytail: synthetic fallback keeps capstone runnable without external dataset credentials
    print(dataset_path)
    print(version_path)
    return 0


def _handle_cleanup(manager: DatasetManager) -> int:
    manager.cleanup(OUTPUT_FILENAME)
    manager.cleanup(VERSION_FILENAME)
    print(f"Removed cache files: {manager.cache_dir / OUTPUT_FILENAME} and {manager.cache_dir / VERSION_FILENAME}")
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
