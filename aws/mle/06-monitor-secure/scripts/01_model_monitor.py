from __future__ import annotations

import argparse
import json
from datetime import datetime

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure SageMaker Model Monitor schedules")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--monitoring-schedule-name", default="mle-lab-06-data-quality-schedule")
    parser.add_argument("--monitoring-role-arn", required=True)
    parser.add_argument("--baseline-statistics-uri", required=True)
    parser.add_argument("--baseline-constraints-uri", required=True)
    parser.add_argument("--monitoring-image-uri", required=True)
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--ground-truth-s3-uri", required=True)
    parser.add_argument("--output-s3-uri", required=True)
    parser.add_argument("--instance-type", default="ml.m5.xlarge")
    return parser


def _create_data_quality_schedule(args: argparse.Namespace, client: "boto3.client") -> dict[str, object]:
    return client.create_monitoring_schedule(
        MonitoringScheduleName=args.monitoring_schedule_name,
        MonitoringScheduleConfig={
            "ScheduleConfig": {
                "ScheduleExpression": "cron(0 * ? * * *)",
            },
            "MonitoringJobDefinition": {
                "BaselineConfig": {
                    "StatisticsResource": {"S3Uri": args.baseline_statistics_uri},
                    "ConstraintsResource": {"S3Uri": args.baseline_constraints_uri},
                },
                "MonitoringAppSpecification": {
                    "ImageUri": args.monitoring_image_uri,
                },
                "MonitoringInputs": [
                    {
                        "EndpointInput": {
                            "EndpointName": args.endpoint_name,
                            "LocalPath": "/opt/ml/processing/input",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    }
                ],
                "MonitoringOutputConfig": {
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "S3Uri": args.output_s3_uri,
                                "LocalPath": "/opt/ml/processing/output",
                                "S3UploadMode": "EndOfJob",
                            }
                        }
                    ]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": args.instance_type,
                        "VolumeSizeInGB": 20,
                    }
                },
                "RoleArn": args.monitoring_role_arn,
            },
        },
    )


def _create_model_quality_schedule(args: argparse.Namespace, client: "boto3.client") -> dict[str, object]:
    schedule_name = f"{args.monitoring_schedule_name}-model-quality"
    return client.create_monitoring_schedule(
        MonitoringScheduleName=schedule_name,
        MonitoringScheduleConfig={
            "ScheduleConfig": {
                "ScheduleExpression": "cron(30 * ? * * *)",
            },
            "MonitoringJobDefinition": {
                "MonitoringAppSpecification": {
                    "ImageUri": args.monitoring_image_uri,
                },
                "MonitoringInputs": [
                    {
                        "EndpointInput": {
                            "EndpointName": args.endpoint_name,
                            "LocalPath": "/opt/ml/processing/input/endpoint",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                    {
                        "S3Input": {
                            "S3Uri": args.ground_truth_s3_uri,
                            "LocalPath": "/opt/ml/processing/input/groundtruth",
                            "S3DataType": "S3Prefix",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                ],
                "MonitoringOutputConfig": {
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "S3Uri": f"{args.output_s3_uri.rstrip('/')}/model-quality",
                                "LocalPath": "/opt/ml/processing/output",
                                "S3UploadMode": "EndOfJob",
                            }
                        }
                    ]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": args.instance_type,
                        "VolumeSizeInGB": 20,
                    }
                },
                "RoleArn": args.monitoring_role_arn,
            },
        },
    )


def _describe_schedule(client: "boto3.client", schedule_name: str) -> tuple[str, str]:
    schedule = client.describe_monitoring_schedule(MonitoringScheduleName=schedule_name)
    schedule_arn = str(schedule.get("MonitoringScheduleArn", ""))
    next_run = str(schedule.get("NextRunTime", "N/A"))
    return schedule_arn, next_run


def main() -> int:
    args = _build_parser().parse_args()
    sagemaker_client = boto3.client("sagemaker", region_name=args.region)

    data_quality_result = _create_data_quality_schedule(args, sagemaker_client)
    model_quality_result = _create_model_quality_schedule(args, sagemaker_client)

    data_quality_arn, data_quality_next = _describe_schedule(sagemaker_client, args.monitoring_schedule_name)
    model_quality_name = f"{args.monitoring_schedule_name}-model-quality"
    model_quality_arn, model_quality_next = _describe_schedule(sagemaker_client, model_quality_name)

    print("Created data quality monitoring schedule:")
    print(json.dumps(data_quality_result, indent=2, default=str))
    print("Created model quality monitoring schedule:")
    print(json.dumps(model_quality_result, indent=2, default=str))
    print(f"Data quality schedule ARN: {data_quality_arn}")
    print(f"Data quality next execution: {data_quality_next}")
    print(f"Model quality schedule ARN: {model_quality_arn}")
    print(f"Model quality next execution: {model_quality_next}")
    print(f"Schedule summary generated at: {datetime.utcnow().isoformat()}Z")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
