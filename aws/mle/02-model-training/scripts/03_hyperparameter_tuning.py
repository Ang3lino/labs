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
    parser = argparse.ArgumentParser(description="Run Bayesian AMT for Lab 02 PyTorch fraud model")
    parser.add_argument("--region", default=None)
    parser.add_argument("--instance-type", default="ml.m5.large")
    parser.add_argument("--max-jobs", type=int, default=10)
    parser.add_argument("--max-parallel-jobs", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=128)
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
    role_arn = get_sagemaker_role()
    bucket = get_default_bucket(boto_session)
    sagemaker_session = sagemaker.session.Session(boto_session=boto_session)

    try:
        from sagemaker.pytorch import PyTorch
        from sagemaker.tuner import CategoricalParameter, ContinuousParameter, HyperparameterTuner
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "This script expects SageMaker SDK v2-style `sagemaker.pytorch.PyTorch`. "
            "Install a compatible SDK version for estimator + tuner execution."
        ) from error

    train_uri = _upload_file_to_s3(bucket, TRAIN_FILENAME, boto_session.region_name)
    validation_uri = _upload_file_to_s3(bucket, VALIDATION_FILENAME, boto_session.region_name)

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
        },
        use_spot_instances=True,
        max_run=3600,
        max_wait=7200,
        sagemaker_session=sagemaker_session,
    )

    hyperparameter_ranges = {
        "learning_rate": ContinuousParameter(1e-4, 1e-1, scaling_type="Logarithmic"),
        "dropout": ContinuousParameter(0.1, 0.5),
        "hidden_dim": CategoricalParameter([64, 128, 256]),
    }

    tuner = HyperparameterTuner(
        estimator=estimator,
        objective_metric_name="validation:f1",
        hyperparameter_ranges=hyperparameter_ranges,
        max_jobs=args.max_jobs,
        max_parallel_jobs=args.max_parallel_jobs,
        strategy="Bayesian",
        objective_type="Maximize",
        metric_definitions=[{"Name": "validation:f1", "Regex": r"validation:f1=([0-9\.]+)"}],
    )

    tuner.fit({"train": train_uri, "validation": validation_uri})
    print(f"Started AMT tuning job: {tuner.latest_tuning_job.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
