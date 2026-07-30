from __future__ import annotations

import argparse
import os
from pathlib import Path

from sagemaker import Session
from sagemaker.clarify import BiasConfig, DataConfig, ModelConfig, SageMakerClarifyProcessor


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SageMaker Clarify pre-training bias checks")
    parser.add_argument("--role-arn", default=os.getenv("SAGEMAKER_ROLE_ARN"), help="SageMaker execution role")
    parser.add_argument("--bucket", required=True, help="S3 bucket for Clarify outputs")
    parser.add_argument("--dataset-s3-uri", required=True, help="Input dataset S3 URI")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--instance-type", default="ml.m5.xlarge", help="Clarify processing instance type")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.role_arn is None:
        raise RuntimeError("Provide --role-arn or set SAGEMAKER_ROLE_ARN")

    sagemaker_session = Session()
    output_uri = f"s3://{args.bucket}/clarify/bias/"

    data_config = DataConfig(
        s3_data_input_path=args.dataset_s3_uri,
        s3_output_path=output_uri,
        label="Class",
        dataset_type="text/csv",
    )

    bias_config = BiasConfig(
        label_values_or_threshold=["1"],
        facet_name="Class",
        facet_values_or_threshold=["1"],
        label="Class",
    )

    clarify_processor = SageMakerClarifyProcessor(
        role=args.role_arn,
        instance_count=1,
        instance_type=args.instance_type,
        sagemaker_session=sagemaker_session,
    )

    clarify_processor.run_pre_training_bias(
        data_config=data_config,
        data_bias_config=bias_config,
        methods={"CI": {"threshold": 0.0}, "DPL": {"threshold": 0.0}},
    )

    report_path = Path("clarify_pretraining_report.json")
    print("Clarify pre-training bias run submitted.")
    print("Requested metrics: CI (Class Imbalance), DPL (Difference in Proportions of Labels)")
    print(f"Output location: {output_uri}")
    print(f"Local report placeholder: {report_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
