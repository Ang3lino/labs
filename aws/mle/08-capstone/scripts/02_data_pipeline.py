from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import boto3
from sagemaker.feature_store.feature_definition import FeatureDefinition, FeatureTypeEnum
from sagemaker.feature_store.feature_group import FeatureGroup
from sagemaker.session import Session


SCRIPT_DIR = Path(__file__).resolve().parent
CAPSTONE_DIR = SCRIPT_DIR.parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Lab 08 consolidated data pipeline")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--dataset-s3-key", default="raw/fraud_data.csv")
    parser.add_argument("--processed-s3-prefix", default="processed/")
    parser.add_argument("--feature-group-name", default="mle-lab-08-fraud-features")
    parser.add_argument("--record-id", default="record_id")
    parser.add_argument("--event-time", default="event_time")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _feature_type_for_name(column_name: str) -> FeatureTypeEnum:
    if column_name == "Class":
        return FeatureTypeEnum.INTEGRAL
    if column_name == "Amount" or column_name.startswith("V"):
        return FeatureTypeEnum.FRACTIONAL
    return FeatureTypeEnum.STRING


def _dataset_cache_path() -> Path:
    return Path("~/.cache/aws-mle-labs/08-capstone/fraud_data.csv").expanduser()


def _ensure_dataset_exists() -> Path:
    dataset_path = _dataset_cache_path()
    if dataset_path.exists():
        return dataset_path

    subprocess.run(["uv", "run", "python", str(CAPSTONE_DIR / "datasets.py"), "--download"], check=True)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset generation did not produce expected file: {dataset_path}")
    return dataset_path


def _upload_raw_data(s3_client: "boto3.client", bucket_name: str, key: str, source_path: Path) -> str:
    s3_client.upload_file(str(source_path), bucket_name, key)
    return f"s3://{bucket_name}/{key}"


def _run_glue_or_local_equivalent(bucket_name: str, raw_key: str, processed_prefix: str) -> str:
    processed_key = f"{processed_prefix.rstrip('/')}/fraud_data.parquet"
    return f"s3://{bucket_name}/{processed_key}"


def _create_feature_group(
    *,
    region: str,
    bucket_name: str,
    role_arn: str,
    feature_group_name: str,
    record_id: str,
    event_time: str,
) -> str:
    boto_session = boto3.Session(region_name=region)
    feature_store_session = Session(boto_session=boto_session)
    feature_group = FeatureGroup(name=feature_group_name, sagemaker_session=feature_store_session)

    feature_columns = [f"V{i}" for i in range(1, 31)] + ["Amount", "Class", record_id, event_time]
    feature_definitions = [
        FeatureDefinition(feature_name=column, feature_type=_feature_type_for_name(column))
        for column in feature_columns
    ]

    offline_store_uri = f"s3://{bucket_name}/feature-store/offline/"
    feature_group.create(
        s3_uri=offline_store_uri,
        record_identifier_name=record_id,
        event_time_feature_name=event_time,
        role_arn=role_arn,
        feature_definitions=feature_definitions,
        online_store_config={"EnableOnlineStore": True},
    )
    return feature_group_name


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()

    data_bucket_name = str(outputs["dataBucketName"])
    sagemaker_role_arn = str(outputs["sagemakerRoleArn"])

    session = boto3.Session(region_name=args.region)
    s3_client = session.client("s3")

    dataset_path = _ensure_dataset_exists()
    raw_s3_uri = _upload_raw_data(s3_client, data_bucket_name, args.dataset_s3_key, dataset_path)
    processed_s3_uri = _run_glue_or_local_equivalent(data_bucket_name, args.dataset_s3_key, args.processed_s3_prefix)
    feature_group_name = _create_feature_group(
        region=args.region,
        bucket_name=data_bucket_name,
        role_arn=sagemaker_role_arn,
        feature_group_name=args.feature_group_name,
        record_id=args.record_id,
        event_time=args.event_time,
    )

    print(f"Raw data uploaded: {raw_s3_uri}")
    print(f"Processed data target: {processed_s3_uri}")
    print(f"Feature group configured: {feature_group_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
