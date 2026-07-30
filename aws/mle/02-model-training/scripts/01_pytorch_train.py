from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description="Run Lab 02 PyTorch script-mode training on SageMaker")
    parser.add_argument("--region", default=None)
    parser.add_argument("--instance-type", default="ml.m5.large")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--max-run", type=int, default=3600)
    parser.add_argument("--max-wait", type=int, default=7200)
    return parser


def _s3_uri_for_cached_file(bucket: str, key: str, region: str | None) -> str:
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
        from sagemaker.pytorch import PyTorch
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "This script expects SageMaker SDK v2-style `sagemaker.pytorch.PyTorch`. "
            "Install a compatible SDK version for estimator script mode execution."
        ) from error

    sagemaker_session = sagemaker.session.Session(boto_session=boto_session)
    role_arn = get_sagemaker_role()
    bucket = get_default_bucket(boto_session)

    train_s3_uri = _s3_uri_for_cached_file(bucket, TRAIN_FILENAME, region_name)
    validation_s3_uri = _s3_uri_for_cached_file(bucket, VALIDATION_FILENAME, region_name)

    estimator = PyTorch(
        entry_point="train.py",
        source_dir=str((LAB_ROOT / "src").resolve()),
        role=role_arn,
        framework_version="2.2",
        py_version="py310",
        instance_count=1,
        instance_type=args.instance_type,
        hyperparameters={
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "dropout": args.dropout,
            "hidden_dim": args.hidden_dim,
        },
        use_spot_instances=True,
        max_run=args.max_run,
        max_wait=args.max_wait,
        sagemaker_session=sagemaker_session,
    )

    estimator.fit(
        {
            "train": train_s3_uri,
            "validation": validation_s3_uri,
        }
    )

    print(f"PyTorch training complete. Model artifacts: {estimator.model_data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
