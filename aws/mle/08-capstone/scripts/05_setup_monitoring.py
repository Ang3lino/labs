from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure monitoring for Lab 08 endpoint")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-name", default="mle-lab-08-fraud-endpoint")
    parser.add_argument("--monitoring-schedule-name", default="mle-lab-08-monitor")
    parser.add_argument("--monitoring-image-uri", default="156813124566.dkr.ecr.us-east-1.amazonaws.com/sagemaker-model-monitor-analyzer")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _create_model_monitor(
    *,
    sm_client: "boto3.client",
    role_arn: str,
    endpoint_name: str,
    schedule_name: str,
    monitoring_image_uri: str,
    output_s3_uri: str,
) -> dict[str, object]:
    return sm_client.create_monitoring_schedule(
        MonitoringScheduleName=schedule_name,
        MonitoringScheduleConfig={
            "ScheduleConfig": {"ScheduleExpression": "cron(0 * ? * * *)"},
            "MonitoringJobDefinition": {
                "MonitoringAppSpecification": {"ImageUri": monitoring_image_uri},
                "MonitoringInputs": [
                    {
                        "EndpointInput": {
                            "EndpointName": endpoint_name,
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
                                "S3Uri": output_s3_uri,
                                "LocalPath": "/opt/ml/processing/output",
                                "S3UploadMode": "EndOfJob",
                            }
                        }
                    ]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.m5.xlarge",
                        "VolumeSizeInGB": 20,
                    }
                },
                "RoleArn": role_arn,
            },
        },
    )


def _run_clarify_report(endpoint_name: str, data_bucket_name: str) -> str:
    explainability_report_uri = f"s3://{data_bucket_name}/clarify/{endpoint_name}/"
    return explainability_report_uri


def _put_cloudwatch_dashboard(region: str, endpoint_name: str, dashboard_name: str) -> str:
    cloudwatch = boto3.client("cloudwatch", region_name=region)
    body = json.dumps(
        {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "Endpoint Invocations",
                        "region": region,
                        "view": "timeSeries",
                        "metrics": [["AWS/SageMaker", "Invocations", "EndpointName", endpoint_name]],
                    },
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "ModelLatency p95",
                        "region": region,
                        "view": "timeSeries",
                        "metrics": [
                            ["AWS/SageMaker", "ModelLatency", "EndpointName", endpoint_name, {"stat": "p95"}]
                        ],
                    },
                },
            ]
        }
    )
    cloudwatch.put_dashboard(DashboardName=dashboard_name, DashboardBody=body)
    return (
        f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}"
        f"#dashboards:name={dashboard_name}"
    )


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()
    data_bucket_name = str(outputs["dataBucketName"])
    sagemaker_role_arn = str(outputs["sagemakerRoleArn"])
    dashboard_name = str(outputs.get("cloudwatchDashboardName", "mle-lab-08-dashboard"))

    sm_client = boto3.client("sagemaker", region_name=args.region)
    monitor_response = _create_model_monitor(
        sm_client=sm_client,
        role_arn=sagemaker_role_arn,
        endpoint_name=args.endpoint_name,
        schedule_name=args.monitoring_schedule_name,
        monitoring_image_uri=args.monitoring_image_uri,
        output_s3_uri=f"s3://{data_bucket_name}/monitoring/",
    )

    explainability_report_uri = _run_clarify_report(args.endpoint_name, data_bucket_name)
    dashboard_url = _put_cloudwatch_dashboard(args.region, args.endpoint_name, dashboard_name)

    print("Model Monitor schedule response:")
    print(json.dumps(monitor_response, indent=2, default=str))
    print(f"Clarify report target: {explainability_report_uri}")
    print(f"CloudWatch dashboard: {dashboard_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
