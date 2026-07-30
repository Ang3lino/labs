from __future__ import annotations

import argparse
import json

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show and optionally apply SageMaker deployment strategies")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--new-endpoint-config-name", required=True)
    parser.add_argument("--apply", action="store_true", help="Call update_endpoint with blue/green canary shift")
    return parser


def _strategy_configs() -> dict[str, dict[str, object]]:
    return {
        "blue_green_canary": {
            "BlueGreenUpdatePolicy": {
                "TrafficRoutingConfiguration": {
                    "Type": "CANARY",
                    "CanarySize": {"Type": "CAPACITY_PERCENT", "Value": 10},
                    "WaitIntervalInSeconds": 300,
                },
                "TerminationWaitInSeconds": 600,
                "MaximumExecutionTimeoutInSeconds": 3600,
            },
            "AutoRollbackConfiguration": {
                "Alarms": [{"AlarmName": "mle-lab-05-endpoint-5xx-alarm"}],
            },
        },
        "canary": {
            "TrafficRoutingConfiguration": {
                "Type": "CANARY",
                "CanarySize": {"Type": "CAPACITY_PERCENT", "Value": 10},
                "WaitIntervalInSeconds": 300,
            }
        },
        "linear": {
            "TrafficRoutingConfiguration": {
                "Type": "LINEAR",
                "LinearStepSize": {"Type": "CAPACITY_PERCENT", "Value": 20},
                "WaitIntervalInSeconds": 300,
            }
        },
        "all_at_once": {
            "TrafficRoutingConfiguration": {
                "Type": "ALL_AT_ONCE",
                "WaitIntervalInSeconds": 0,
            }
        },
    }


def main() -> int:
    args = _build_parser().parse_args()
    strategy_configs = _strategy_configs()

    print("Deployment strategy configurations:")
    print(json.dumps(strategy_configs, indent=2))

    guardrails = {
        "alarm_names": ["mle-lab-05-endpoint-5xx-alarm", "mle-lab-05-endpoint-latency-p99"],
        "rollback_on_alarm": True,
        "notes": "Use CloudWatch alarms to auto-rollback if canary health degrades.",
    }
    print("Deployment guardrails:")
    print(json.dumps(guardrails, indent=2))

    if args.apply:
        sagemaker_client = boto3.client("sagemaker", region_name=args.region)
        update_response = sagemaker_client.update_endpoint(
            EndpointName=args.endpoint_name,
            EndpointConfigName=args.new_endpoint_config_name,
            DeploymentConfig={
                "BlueGreenUpdatePolicy": strategy_configs["blue_green_canary"]["BlueGreenUpdatePolicy"],
                "AutoRollbackConfiguration": strategy_configs["blue_green_canary"]["AutoRollbackConfiguration"],
            },
        )
        print("update_endpoint response:")
        print(json.dumps(update_response, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
