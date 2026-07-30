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


TRAIN_FILENAME = "02-model-training/train.csv"
VALIDATION_FILENAME = "02-model-training/validation.csv"
TEST_FILENAME = "02-model-training/test.csv"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage synthetic fraud dataset splits for Lab 02")
    parser.add_argument("--download", action="store_true", help="Generate and cache train/validation/test CSV files")
    parser.add_argument("--cleanup", action="store_true", help="Remove cached Lab 02 split CSV files")
    return parser


def _generate_features_and_labels() -> tuple[list[list[float]], list[int]]:
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
        feature_rows = features.tolist()
        label_rows = labels.tolist()
        return feature_rows, label_rows
    except ModuleNotFoundError:
        random = Random(42)
        feature_rows: list[list[float]] = []
        label_rows: list[int] = []
        for index in range(10000):
            feature_row = [random.gauss(0.0, 1.0) for _ in range(30)]
            label = 1 if index < 100 else 0
            feature_rows.append(feature_row)
            label_rows.append(label)
        return feature_rows, label_rows


def _rows_from_features_labels(features: list[list[float]], labels: list[int]) -> list[list[float]]:
    rows: list[list[float]] = []
    for feature_row, label in zip(features, labels, strict=True):
        amount_value = abs(float(feature_row[0])) * 100.0
        rows.append([*feature_row, amount_value, int(label)])
    return rows


def _stratified_indices(labels: list[int]) -> tuple[list[int], list[int], list[int]]:
    positive_indices = [idx for idx, label in enumerate(labels) if label == 1]
    negative_indices = [idx for idx, label in enumerate(labels) if label == 0]

    random = Random(42)
    random.shuffle(positive_indices)
    random.shuffle(negative_indices)

    def split_group(indices: list[int]) -> tuple[list[int], list[int], list[int]]:
        total = len(indices)
        train_end = int(total * 0.7)
        validation_end = train_end + int(total * 0.15)
        train_part = indices[:train_end]
        validation_part = indices[train_end:validation_end]
        test_part = indices[validation_end:]
        return train_part, validation_part, test_part

    pos_train, pos_validation, pos_test = split_group(positive_indices)
    neg_train, neg_validation, neg_test = split_group(negative_indices)

    train_indices = [*pos_train, *neg_train]
    validation_indices = [*pos_validation, *neg_validation]
    test_indices = [*pos_test, *neg_test]
    random.shuffle(train_indices)
    random.shuffle(validation_indices)
    random.shuffle(test_indices)
    return train_indices, validation_indices, test_indices


def _write_split_csv(destination: Path, rows: list[list[float]], indices: list[int]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    header_columns = [f"V{index}" for index in range(1, 31)] + ["Amount", "Class"]

    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header_columns)
        for row_index in indices:
            writer.writerow(rows[row_index])
    return destination


def _handle_download(manager: DatasetManager) -> int:
    features, labels = _generate_features_and_labels()
    rows = _rows_from_features_labels(features, labels)
    train_indices, validation_indices, test_indices = _stratified_indices(labels)

    train_path = _write_split_csv(manager.cache_dir / TRAIN_FILENAME, rows, train_indices)
    validation_path = _write_split_csv(manager.cache_dir / VALIDATION_FILENAME, rows, validation_indices)
    test_path = _write_split_csv(manager.cache_dir / TEST_FILENAME, rows, test_indices)

    # ponytail: keep CSV for readability in study labs; parquet conversion is covered in Lab 01
    print(f"train: {train_path}")
    print(f"validation: {validation_path}")
    print(f"test: {test_path}")
    return 0


def _handle_cleanup(manager: DatasetManager) -> int:
    manager.cleanup(TRAIN_FILENAME)
    manager.cleanup(VALIDATION_FILENAME)
    manager.cleanup(TEST_FILENAME)
    print(f"Removed cache files under: {manager.cache_dir / '02-model-training'}")
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
