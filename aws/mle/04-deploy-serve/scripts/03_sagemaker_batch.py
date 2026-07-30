from __future__ import annotations

import argparse
import os

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SageMaker batch transform")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--model-name", default=os.getenv("SAGEMAKER_MODEL_NAME", "mle-lab-04-batch-model"), help="Existing SageMaker model name")
    parser.add_argument("--transform-job-name", default="mle-lab-04-batch-transform", help="Transform job name")
    parser.add_argument("--input-s3", required=True, help="S3 input path (s3://bucket/prefix)")
    parser.add_argument("--output-s3", required=True, help="S3 output path (s3://bucket/prefix)")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    sagemaker = session.client("sagemaker")

    sagemaker.create_transform_job(
        TransformJobName=args.transform_job_name,
        ModelName=args.model_name,
        TransformInput={
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": args.input_s3,
                }
            },
            "ContentType": "application/json",
            "SplitType": "Line",
        },
        TransformOutput={
            "S3OutputPath": args.output_s3,
        },
        TransformResources={
            "InstanceType": "ml.m5.large",
            "InstanceCount": 1,
        },
        MaxConcurrentTransforms=4,
    )

    status = sagemaker.describe_transform_job(TransformJobName=args.transform_job_name)["TransformJobStatus"]
    print(f"Batch transform job status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
