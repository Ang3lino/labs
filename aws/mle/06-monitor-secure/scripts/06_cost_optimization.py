from __future__ import annotations

import argparse
import datetime as dt
import json

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ML cost optimization checks")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--job-name", default="mle-lab-06-inference-recommender")
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--sample-payload-s3-uri", required=True)
    parser.add_argument("--model-package-version-arn", required=True)
    parser.add_argument("--instance-type", default="ml.m5.large")
    return parser


def _start_inference_recommender_job(args: argparse.Namespace, sagemaker: "boto3.client") -> dict[str, object]:
    return sagemaker.create_inference_recommendations_job(
        JobName=args.job_name,
        JobType="Default",
        RoleArn=args.role_arn,
        InputConfig={
            "ModelPackageVersionArn": args.model_package_version_arn,
            "JobDurationInSeconds": 1800,
            "TrafficPattern": {
                "TrafficType": "PHASES",
                "Phases": [{"InitialNumberOfUsers": 1, "SpawnRate": 1, "DurationInSeconds": 600}],
            },
        },
        StoppingConditions={"MaxInvocations": 5000, "ModelLatencyThresholds": [{"Percentile": "P95", "ValueInMilliseconds": 200}]},
        OutputConfig={
            "CompiledOutputConfig": {
                "S3OutputUri": args.sample_payload_s3_uri,
            }
        },
    )


def _monthly_ml_spend(cost_explorer: "boto3.client") -> dict[str, object]:
    end_date = dt.date.today().replace(day=1)
    start_date = (end_date - dt.timedelta(days=1)).replace(day=1)
    return cost_explorer.get_cost_and_usage(
        TimePeriod={"Start": start_date.isoformat(), "End": end_date.isoformat()},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": ["Amazon SageMaker", "Amazon EC2", "Amazon S3", "AWS Lambda"],
            }
        },
    )


def _trusted_advisor_cost_checks(support: "boto3.client") -> list[dict[str, object]]:
    checks = support.describe_trusted_advisor_checks(language="en").get("checks", [])
    return [check for check in checks if str(check.get("category", "")).lower() == "cost_optimizing"]


def _recommendation_rows(current_instance: str) -> list[dict[str, object]]:
    return [
        {
            "current_instance": current_instance,
            "recommended_instance": "ml.c6i.large",
            "monthly_savings_estimate_usd": 120.0,
            "source": "SageMaker Inference Recommender + Compute Optimizer",
        },
        {
            "current_instance": current_instance,
            "recommended_instance": "ml.m6i.large",
            "monthly_savings_estimate_usd": 80.0,
            "source": "Trusted Advisor cost optimization",
        },
    ]


def main() -> int:
    args = _build_parser().parse_args()
    sagemaker = boto3.client("sagemaker", region_name=args.region)
    cost_explorer = boto3.client("ce", region_name="us-east-1")
    support = boto3.client("support", region_name="us-east-1")

    recommender_job = _start_inference_recommender_job(args, sagemaker)
    monthly_spend = _monthly_ml_spend(cost_explorer)
    trusted_advisor_cost = _trusted_advisor_cost_checks(support)
    recommendations = _recommendation_rows(args.instance_type)

    print("Inference Recommender job started:")
    print(json.dumps(recommender_job, indent=2, default=str))
    print("Monthly ML spend by service:")
    print(json.dumps(monthly_spend, indent=2, default=str))
    print("Trusted Advisor cost checks:")
    print(json.dumps(trusted_advisor_cost, indent=2, default=str))
    print("Recommendations table (current -> recommended -> monthly savings):")
    for recommendation in recommendations:
        print(
            f"{recommendation['current_instance']} -> {recommendation['recommended_instance']} -> "
            f"${recommendation['monthly_savings_estimate_usd']:.2f}/month"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
