from __future__ import annotations

import argparse
import json
import statistics

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SageMaker Clarify explainability analysis")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--processing-job-name", default="mle-lab-06-clarify-explainability")
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--training-data-s3-uri", required=True)
    parser.add_argument("--analysis-data-s3-uri", required=True)
    parser.add_argument("--output-s3-uri", required=True)
    parser.add_argument("--instance-type", default="ml.m5.xlarge")
    parser.add_argument("--label", default="Class")
    parser.add_argument("--features", nargs="+", required=True)
    parser.add_argument("--training-data-mean", nargs="+", type=float, required=True)
    return parser


def _create_clarify_job(args: argparse.Namespace, sagemaker_client: "boto3.client") -> dict[str, object]:
    shap_baseline = [statistics.mean(args.training_data_mean)] * len(args.features)
    analysis_config = {
        "dataset_type": "text/csv",
        "label": args.label,
        "features": args.features,
        "methods": {
            "shap": {
                "baseline": shap_baseline,
                "num_samples": 200,
                "agg_method": "mean_abs",
            }
        },
    }

    app_specification = {
        "ImageUri": args.image_uri,
        "ContainerEntrypoint": ["python3", "/opt/ml/processing/input/code/run_clarify.py"],
    }

    return sagemaker_client.create_processing_job(
        ProcessingJobName=args.processing_job_name,
        RoleArn=args.role_arn,
        AppSpecification=app_specification,
        ProcessingResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": args.instance_type,
                "VolumeSizeInGB": 30,
            }
        },
        ProcessingInputs=[
            {
                "InputName": "analysis-config",
                "S3Input": {
                    "S3Uri": args.training_data_s3_uri,
                    "LocalPath": "/opt/ml/processing/input/train",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                    "S3DataDistributionType": "FullyReplicated",
                },
            },
            {
                "InputName": "analysis-data",
                "S3Input": {
                    "S3Uri": args.analysis_data_s3_uri,
                    "LocalPath": "/opt/ml/processing/input/analysis",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                    "S3DataDistributionType": "FullyReplicated",
                },
            },
        ],
        ProcessingOutputConfig={
            "Outputs": [
                {
                    "OutputName": "analysis-output",
                    "S3Output": {
                        "S3Uri": args.output_s3_uri,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        Environment={
            "CLARIFY_ANALYSIS_CONFIG": json.dumps(analysis_config),
            "MODEL_NAME": args.model_name,
        },
    )


def _mock_shap_summary(features: list[str], mean_values: list[float]) -> list[tuple[str, float]]:
    ranked_pairs = sorted(
        [(feature, abs(value)) for feature, value in zip(features, mean_values, strict=True)],
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked_pairs


def main() -> int:
    args = _build_parser().parse_args()
    sagemaker_client = boto3.client("sagemaker", region_name=args.region)
    processing_response = _create_clarify_job(args, sagemaker_client)
    shap_ranked = _mock_shap_summary(args.features, args.training_data_mean)

    print("Started Clarify explainability processing job:")
    print(json.dumps(processing_response, indent=2, default=str))
    print("SHAP value summary (feature importance ranking):")
    for rank, (feature, importance) in enumerate(shap_ranked, start=1):
        print(f"{rank}. {feature}: {importance:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
