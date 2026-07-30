from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy Lab 08 model to SageMaker real-time endpoint")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-name", default="mle-lab-08-fraud-endpoint")
    parser.add_argument("--model-name", default="mle-lab-08-fraud-model")
    parser.add_argument("--endpoint-config-name", default="mle-lab-08-fraud-endpoint-config")
    parser.add_argument("--instance-type", default="ml.m5.large")
    parser.add_argument("--instance-count", type=int, default=1)
    parser.add_argument("--model-package-group-name", default="mle-lab-08-fraud-models")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _latest_approved_or_pending_package_arn(client: "boto3.client", group_name: str) -> str:
    response = client.list_model_packages(
        ModelPackageGroupName=group_name,
        ModelApprovalStatus="PendingManualApproval",
        SortBy="CreationTime",
        SortOrder="Descending",
    )
    summaries = response.get("ModelPackageSummaryList", [])
    if not summaries:
        raise RuntimeError(f"No model packages found in group: {group_name}")
    return str(summaries[0]["ModelPackageArn"])


def _configure_autoscaling(region: str, endpoint_name: str, variant_name: str) -> None:
    app_scaling = boto3.client("application-autoscaling", region_name=region)
    resource_id = f"endpoint/{endpoint_name}/variant/{variant_name}"
    app_scaling.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=1,
        MaxCapacity=5,
    )
    app_scaling.put_scaling_policy(
        PolicyName=f"{endpoint_name}-target-tracking",
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": 70.0,
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance",
            },
            "ScaleInCooldown": 300,
            "ScaleOutCooldown": 300,
        },
    )


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()

    sagemaker_role_arn = str(outputs["sagemakerRoleArn"])
    sm_client = boto3.client("sagemaker", region_name=args.region)

    model_package_arn = _latest_approved_or_pending_package_arn(sm_client, args.model_package_group_name)
    sm_client.create_model(
        ModelName=args.model_name,
        PrimaryContainer={"ModelPackageName": model_package_arn},
        ExecutionRoleArn=sagemaker_role_arn,
    )

    sm_client.create_endpoint_config(
        EndpointConfigName=args.endpoint_config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": args.model_name,
                "InitialInstanceCount": args.instance_count,
                "InstanceType": args.instance_type,
                "InitialVariantWeight": 1.0,
            }
        ],
    )

    sm_client.create_endpoint(
        EndpointName=args.endpoint_name,
        EndpointConfigName=args.endpoint_config_name,
    )

    _configure_autoscaling(args.region, args.endpoint_name, "AllTraffic")

    invoke_url = (
        f"https://runtime.sagemaker.{args.region}.amazonaws.com/endpoints/{args.endpoint_name}/invocations"
    )
    print(f"Endpoint name: {args.endpoint_name}")
    print(f"Invoke URL: {invoke_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
