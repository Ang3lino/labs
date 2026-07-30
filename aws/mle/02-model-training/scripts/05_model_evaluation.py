from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import boto3
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, roc_curve


LAB_ROOT = Path(__file__).resolve().parents[1]
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))
if str(LAB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT.parent))

from shared.datasets import DatasetManager


TEST_FILENAME = "02-model-training/test.csv"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate registered Lab 02 model on cached test split")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--model-package-arn", required=True)
    parser.add_argument("--output-json", default=str(LAB_ROOT / "evaluation_metrics.json"))
    parser.add_argument(
        "--score-column",
        default="Amount",
        help="Fallback score feature for offline demo when endpoint invocation is not wired",
    )
    return parser


def _format_confusion_table(matrix: np.ndarray) -> str:
    lines = [
        "+-----------------+-----------+-----------+",
        "|                 | Predicted0| Predicted1|",
        "+-----------------+-----------+-----------+",
        f"| Actual0         | {matrix[0, 0]:9d} | {matrix[0, 1]:9d} |",
        f"| Actual1         | {matrix[1, 0]:9d} | {matrix[1, 1]:9d} |",
        "+-----------------+-----------+-----------+",
    ]
    return "\n".join(lines)


def main() -> int:
    args = _build_parser().parse_args()
    sm_client = boto3.client("sagemaker", region_name=args.region)
    package_description = sm_client.describe_model_package(ModelPackageName=args.model_package_arn)

    test_path = DatasetManager().cache_dir / TEST_FILENAME
    if not test_path.exists():
        raise FileNotFoundError(
            f"Missing test split at {test_path}. Run: uv run python aws/mle/02-model-training/datasets.py --download"
        )

    dataframe = pd.read_csv(test_path)
    labels = dataframe["Class"].to_numpy(dtype="int32")

    if args.score_column not in dataframe.columns:
        raise ValueError(f"Score column '{args.score_column}' not found in test CSV")

    # ponytail: offline evaluation stub uses normalized feature as proxy score when endpoint is not deployed yet
    raw_scores = dataframe[args.score_column].to_numpy(dtype="float64")
    score_min = float(raw_scores.min())
    score_max = float(raw_scores.max())
    probabilities = (raw_scores - score_min) / max(score_max - score_min, 1e-9)
    predictions = (probabilities >= 0.5).astype("int32")

    matrix = confusion_matrix(labels, predictions)
    report = classification_report(labels, predictions, target_names=["non_fraud", "fraud"], output_dict=True)
    fpr, tpr, thresholds = roc_curve(labels, probabilities)

    confusion_table = _format_confusion_table(matrix)
    print("Confusion matrix:")
    print(confusion_table)
    print("Classification report:")
    print(json.dumps(report, indent=2))

    metrics = {
        "model_package_arn": args.model_package_arn,
        "model_approval_status": package_description.get("ModelApprovalStatus"),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "roc_curve": {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thresholds.tolist(),
        },
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved evaluation metrics JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
