from __future__ import annotations

import argparse
import json

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create CloudWatch dashboard for ML monitoring")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--dashboard-name", default="mle-lab-06-monitoring-dashboard")
    parser.add_argument("--endpoint-name", required=True)
    return parser


def _dashboard_body(region: str, endpoint_name: str) -> str:
    payload = {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Endpoint Invocations",
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
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
                    "title": "Model Latency p50/p99",
                    "view": "timeSeries",
                    "region": region,
                    "metrics": [
                        ["AWS/SageMaker", "ModelLatency", "EndpointName", endpoint_name, {"stat": "p50"}],
                        ["AWS/SageMaker", "ModelLatency", "EndpointName", endpoint_name, {"stat": "p99"}],
                    ],
                },
            },
            {
                "type": "metric",
                "x": 0,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "4xx / 5xx Error Rate",
                    "view": "timeSeries",
                    "region": region,
                    "metrics": [
                        ["AWS/SageMaker", "Invocation4XXErrors", "EndpointName", endpoint_name],
                        ["AWS/SageMaker", "Invocation5XXErrors", "EndpointName", endpoint_name],
                    ],
                },
            },
            {
                "type": "metric",
                "x": 12,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "CPU / Memory Utilization",
                    "view": "timeSeries",
                    "region": region,
                    "metrics": [
                        ["AWS/SageMaker", "CPUUtilization", "EndpointName", endpoint_name],
                        ["AWS/SageMaker", "MemoryUtilization", "EndpointName", endpoint_name],
                    ],
                },
            },
        ]
    }
    return json.dumps(payload)


def main() -> int:
    args = _build_parser().parse_args()
    client = boto3.client("cloudwatch", region_name=args.region)
    body = _dashboard_body(args.region, args.endpoint_name)
    put_result = client.put_dashboard(DashboardName=args.dashboard_name, DashboardBody=body)

    dashboard_url = (
        f"https://{args.region}.console.aws.amazon.com/cloudwatch/home?region={args.region}"
        f"#dashboards:name={args.dashboard_name}"
    )
    print("PutDashboard result:")
    print(json.dumps(put_result, indent=2, default=str))
    print(f"Dashboard URL: {dashboard_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
