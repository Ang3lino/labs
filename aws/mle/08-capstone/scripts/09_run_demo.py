from __future__ import annotations

import argparse
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Lab 08 end-to-end demo")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-name", default="mle-lab-08-fraud-endpoint")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _print_dry_run_flow(region: str, endpoint_name: str) -> None:
    print("Lab 08 Capstone Demo (dry-run)")
    print("1) Validate infrastructure outputs and resolved AWS resources")
    print("2) Upload latest fraud dataset to S3 raw/ prefix")
    print("3) Run ETL and feature ingestion into SageMaker Feature Store")
    print("4) Start PyTorch training with AMT Bayesian HPO (5 jobs)")
    print("5) Register best model in SageMaker Model Registry")
    print("6) Deploy model to SageMaker real-time endpoint")
    print("7) Configure endpoint auto-scaling target tracking at InvocationsPerInstance=70")
    print("8) Configure Model Monitor schedule and Clarify explainability report")
    print("9) Trigger retraining rule via EventBridge for new S3 raw data")
    print("10) Review CloudWatch dashboard and security/cost reports")
    print(
        "Dashboard URL: "
        f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name=mle-lab-08-capstone-dashboard"
    )
    print(f"Inference endpoint (planned): {endpoint_name}")


def _invoke_endpoint(region: str, endpoint_name: str) -> dict[str, object]:
    import boto3

    runtime_client = boto3.client("sagemaker-runtime", region_name=region)
    sample_row = ",".join(["0.0"] * 30 + ["150.0"])
    response = runtime_client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="text/csv",
        Body=sample_row.encode("utf-8"),
    )
    body = response["Body"].read().decode("utf-8")
    return {
        "status_code": response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0),
        "body": body,
    }


def _monitoring_status(region: str, endpoint_name: str) -> str:
    import boto3

    cloudwatch = boto3.client("cloudwatch", region_name=region)
    metric_response = cloudwatch.list_metrics(
        Namespace="AWS/SageMaker",
        MetricName="Invocations",
        Dimensions=[{"Name": "EndpointName", "Value": endpoint_name}],
    )
    metric_count = len(metric_response.get("Metrics", []))
    return f"Found {metric_count} CloudWatch invocation metric definitions"


def main() -> int:
    args = _build_parser().parse_args()

    if args.dry_run:
        _print_dry_run_flow(args.region, args.endpoint_name)
        return 0

    outputs = _load_infra_outputs()
    prediction = _invoke_endpoint(args.region, args.endpoint_name)
    monitor_status = _monitoring_status(args.region, args.endpoint_name)
    dashboard_name = str(outputs.get("cloudwatchDashboardName", "mle-lab-08-capstone-dashboard"))
    dashboard_url = (
        f"https://{args.region}.console.aws.amazon.com/cloudwatch/home?region={args.region}"
        f"#dashboards:name={dashboard_name}"
    )

    print("Live demo results")
    print("Prediction response:")
    print(json.dumps(prediction, indent=2))
    print(f"Monitoring check: {monitor_status}")
    print(f"Dashboard URL: {dashboard_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
