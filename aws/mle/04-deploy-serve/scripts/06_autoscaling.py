from __future__ import annotations

import argparse

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure SageMaker endpoint autoscaling")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--endpoint-name", required=True, help="SageMaker endpoint name")
    parser.add_argument("--variant-name", default="AllTraffic", help="Production variant name")
    parser.add_argument("--min-capacity", type=int, default=1, help="Minimum instance count")
    parser.add_argument("--max-capacity", type=int, default=8, help="Maximum instance count")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    autoscaling = session.client("application-autoscaling")

    resource_id = f"endpoint/{args.endpoint_name}/variant/{args.variant_name}"

    autoscaling.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=args.min_capacity,
        MaxCapacity=args.max_capacity,
    )

    response = autoscaling.put_scaling_policy(
        PolicyName="mle-lab-04-target-tracking",
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
            "ScaleOutCooldown": 120,
        },
    )

    print("Scaling policy ARN:", response["PolicyARN"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
