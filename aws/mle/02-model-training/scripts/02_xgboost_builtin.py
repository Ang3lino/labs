from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import boto3


LAB_ROOT = Path(__file__).resolve().parents[1]
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))
if str(LAB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT.parent))

from shared.aws_helpers import get_default_bucket, get_sagemaker_role, get_session
from shared.datasets import DatasetManager


TRAIN_FILENAME = "02-model-training/train.csv"
VALIDATION_FILENAME = "02-model-training/validation.csv"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train SageMaker XGBoost built-in baseline for Lab 02")
    parser.add_argument("--region", default=None)
    parser.add_argument("--instance-type", default="ml.m5.large")
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--eta", type=float, default=0.2)
    parser.add_argument("--num-round", type=int, default=150)
    parser.add_argument("--scale-pos-weight", type=float, default=99.0)
    parser.add_argument("--pytorch-metrics-json", default=None)
    return parser


def _upload_file_to_s3(bucket: str, key: str, region: str | None) -> str:
    local_path = DatasetManager().cache_dir / key
    if not local_path.exists():
        raise FileNotFoundError(
            f"Missing dataset file at {local_path}. Run: uv run python aws/mle/02-model-training/datasets.py --download"
        )

    session = boto3.Session(region_name=region) if region else boto3.Session()
    s3_client = session.client("s3")
    s3_key = f"lab-02/model-training/{key}"
    s3_client.upload_file(str(local_path), bucket, s3_key)
    return f"s3://{bucket}/{s3_key}"


def main() -> int:
    import sagemaker

    args = _build_parser().parse_args()
    boto_session = get_session(region=args.region)
    region_name = boto_session.region_name or "us-east-1"

    try:
        from sagemaker import image_uris
        from sagemaker.estimator import Estimator
    except (ImportError, ModuleNotFoundError) as error:
        raise RuntimeError(
            "This script expects SageMaker SDK v2 estimator APIs (`sagemaker.estimator` and `image_uris`). "
            "Install a compatible SDK version for built-in algorithm training."
        ) from error

    role_arn = get_sagemaker_role()
    sagemaker_session = sagemaker.session.Session(boto_session=boto_session)
    bucket = get_default_bucket(boto_session)

    train_uri = _upload_file_to_s3(bucket, TRAIN_FILENAME, region_name)
    validation_uri = _upload_file_to_s3(bucket, VALIDATION_FILENAME, region_name)

    xgboost_image = image_uris.retrieve(
        framework="xgboost",
        region=region_name,
        version="1.7-1",
        image_scope="training",
        instance_type=args.instance_type,
    )

    estimator = Estimator(
        image_uri=xgboost_image,
        role=role_arn,
        instance_count=1,
        instance_type=args.instance_type,
        output_path=f"s3://{bucket}/lab-02/model-training/xgboost-output",
        sagemaker_session=sagemaker_session,
    )
    estimator.set_hyperparameters(
        max_depth=args.max_depth,
        eta=args.eta,
        objective="binary:logistic",
        num_round=args.num_round,
        scale_pos_weight=args.scale_pos_weight,
        eval_metric="auc",
    )

    estimator.fit({"train": train_uri, "validation": validation_uri})

    print("XGBoost baseline complete.")
    print(f"XGBoost model artifacts: {estimator.model_data}")

    if args.pytorch_metrics_json:
        metrics_path = Path(args.pytorch_metrics_json)
        if metrics_path.exists():
            pytorch_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            print("PyTorch validation metrics (for manual comparison):")
            print(json.dumps(pytorch_metrics, indent=2))
        else:
            print(f"PyTorch metrics file not found: {metrics_path}")
    else:
        print("Provide --pytorch-metrics-json to print side-by-side metric context.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
