from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import boto3


LAB_DIR = Path(__file__).resolve().parent.parent
MLE_ROOT = LAB_DIR.parent
if str(MLE_ROOT) not in sys.path:
    sys.path.insert(0, str(MLE_ROOT))

from shared.datasets import DatasetManager


DEFAULT_KEY = "raw/fraud_data.csv"
DATASET_FILENAME = "01-data-pipeline/fraud_data.csv"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload raw fraud CSV to S3")
    parser.add_argument("--bucket", type=str, default=None, help="Target S3 bucket name")
    parser.add_argument("--region", type=str, default=None, help="AWS region override")
    parser.add_argument("--key", type=str, default=DEFAULT_KEY, help="S3 object key")
    return parser


def _resolve_bucket(cli_bucket: str | None) -> str:
    if cli_bucket is not None:
        return cli_bucket

    env_bucket = os.getenv("LAB01_BUCKET") or os.getenv("S3_BUCKET")
    if env_bucket is None:
        raise RuntimeError("Set --bucket or LAB01_BUCKET/S3_BUCKET environment variable")
    return env_bucket


def main() -> int:
    args = _build_parser().parse_args()
    bucket_name = _resolve_bucket(args.bucket)

    dataset_path = DatasetManager().cache_dir / DATASET_FILENAME
    if not dataset_path.exists():
        raise RuntimeError(
            f"Dataset not found at {dataset_path}. Run `uv run python aws/mle/01-data-pipeline/datasets.py --download` first."
        )

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    s3_client = session.client("s3")
    s3_client.upload_file(str(dataset_path), bucket_name, args.key)
    print(f"Uploaded {dataset_path} to s3://{bucket_name}/{args.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
