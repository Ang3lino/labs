from __future__ import annotations

import argparse
import os
import time

import boto3
import pandas as pd
from sagemaker.feature_store.feature_definition import FeatureDefinition, FeatureTypeEnum
from sagemaker.feature_store.feature_group import FeatureGroup
from sagemaker.session import Session


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and ingest SageMaker Feature Store group")
    parser.add_argument("--bucket", required=True, help="S3 bucket containing processed data")
    parser.add_argument("--prefix", default="processed/", help="S3 prefix for processed parquet")
    parser.add_argument("--group-name", default="fraud-features-lab01", help="Feature group name")
    parser.add_argument("--record-id", default="record_id", help="Record identifier feature")
    parser.add_argument("--event-time", default="event_time", help="Event time feature")
    parser.add_argument("--role-arn", default=os.getenv("SAGEMAKER_ROLE_ARN"), help="SageMaker role ARN")
    parser.add_argument("--region", default=None, help="AWS region override")
    return parser


def _feature_type_for_dtype(dtype: str) -> FeatureTypeEnum:
    lowered = dtype.lower()
    if "int" in lowered or "float" in lowered:
        return FeatureTypeEnum.FRACTIONAL
    return FeatureTypeEnum.STRING


def main() -> int:
    args = _build_parser().parse_args()
    if args.role_arn is None:
        raise RuntimeError("Provide --role-arn or set SAGEMAKER_ROLE_ARN")

    boto_session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    sm_session = Session(boto_session=boto_session)
    s3_uri = f"s3://{args.bucket}/{args.prefix}"

    sample_df = pd.read_parquet(s3_uri)
    if args.record_id not in sample_df.columns:
        sample_df[args.record_id] = sample_df.index.astype(str)
    if args.event_time not in sample_df.columns:
        sample_df[args.event_time] = pd.Timestamp.utcnow().isoformat()

    feature_definitions = [
        FeatureDefinition(feature_name=column, feature_type=_feature_type_for_dtype(str(dtype)))
        for column, dtype in sample_df.dtypes.items()
    ]

    feature_group = FeatureGroup(name=args.group_name, sagemaker_session=sm_session)
    feature_group.create(
        s3_uri=f"s3://{args.bucket}/feature-store/offline/",
        record_identifier_name=args.record_id,
        event_time_feature_name=args.event_time,
        role_arn=args.role_arn,
        feature_definitions=feature_definitions,
        online_store_config={"EnableOnlineStore": True},
        offline_store_config={
            "S3StorageConfig": {"S3Uri": f"s3://{args.bucket}/feature-store/offline/"},
            "DisableGlueTableCreation": False,
            "DataCatalogConfig": {
                "TableName": f"{args.group_name}_table",
                "Database": "sagemaker_featurestore",
                "Catalog": str(boto_session.client("sts").get_caller_identity()["Account"]),
            },
        },
    )

    waiter = boto_session.client("sagemaker").get_waiter("feature_group_created_or_deleted")
    waiter.wait(FeatureGroupName=args.group_name)

    feature_group.ingest(data_frame=sample_df, max_workers=2, wait=True)
    print(f"Created and ingested feature group: {args.group_name}")
    print("Online store enabled: True")
    print(f"Offline store path: s3://{args.bucket}/feature-store/offline/")
    time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
