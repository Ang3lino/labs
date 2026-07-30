from __future__ import annotations

import argparse
import json
import uuid

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hands-on script for X-Ray, CloudTrail, Macie, and Secrets Manager")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--lambda-function-name", required=True)
    parser.add_argument("--macie-bucket-name", required=True)
    parser.add_argument("--secret-name", default="mle-lab-06/api-key")
    parser.add_argument("--secret-value", default="replace-me-with-real-key")
    return parser


def _enable_xray_tracing(lambda_client: "boto3.client", function_name: str) -> dict[str, object]:
    return lambda_client.update_function_configuration(
        FunctionName=function_name,
        TracingConfig={"Mode": "Active"},
    )


def _lookup_cloudtrail_events(cloudtrail_client: "boto3.client") -> dict[str, object]:
    return cloudtrail_client.lookup_events(
        LookupAttributes=[
            {
                "AttributeKey": "EventSource",
                "AttributeValue": "sagemaker.amazonaws.com",
            }
        ],
        MaxResults=10,
    )


def _create_macie_job(
    macie_client: "boto3.client",
    bucket_name: str,
    account_id: str,
) -> dict[str, object]:
    job_name = f"mle-lab-06-macie-{uuid.uuid4().hex[:8]}"
    return macie_client.create_classification_job(
        jobType="ONE_TIME",
        name=job_name,
        s3JobDefinition={
            "bucketDefinitions": [{"accountId": account_id, "buckets": [bucket_name]}],
            "scoping": {
                "includes": {
                    "and": [
                        {
                            "simpleScopeTerm": {
                                "comparator": "STARTS_WITH",
                                "key": "OBJECT_KEY",
                                "values": [""],
                            }
                        }
                    ]
                }
            },
        },
    )


def _store_and_retrieve_secret(
    secrets_client: "boto3.client",
    secret_name: str,
    secret_value: str,
) -> tuple[dict[str, object], dict[str, object], str]:
    create_response = secrets_client.create_secret(Name=secret_name, SecretString=secret_value)
    read_response = secrets_client.get_secret_value(SecretId=secret_name)
    resolved_secret = str(read_response.get("SecretString", ""))
    masked = "*" * max(0, len(resolved_secret) - 4) + resolved_secret[-4:]
    return create_response, read_response, masked


def main() -> int:
    args = _build_parser().parse_args()
    lambda_client = boto3.client("lambda", region_name=args.region)
    cloudtrail_client = boto3.client("cloudtrail", region_name=args.region)
    macie_client = boto3.client("macie2", region_name=args.region)
    secrets_client = boto3.client("secretsmanager", region_name=args.region)
    sts_client = boto3.client("sts", region_name=args.region)
    account_id = str(sts_client.get_caller_identity()["Account"])

    xray_response = _enable_xray_tracing(lambda_client, args.lambda_function_name)
    cloudtrail_events = _lookup_cloudtrail_events(cloudtrail_client)
    # ponytail: one script touches all 4 services — just enough to know what they do
    macie_job = _create_macie_job(macie_client, args.macie_bucket_name, account_id)
    secret_create, secret_read, masked_secret = _store_and_retrieve_secret(
        secrets_client,
        args.secret_name,
        args.secret_value,
    )

    print("X-Ray tracing configuration updated:")
    print(json.dumps(xray_response, indent=2, default=str))
    print("CloudTrail SageMaker API events:")
    print(json.dumps(cloudtrail_events, indent=2, default=str))
    print("Macie classification job created:")
    print(json.dumps(macie_job, indent=2, default=str))
    print("Secrets Manager create/get results:")
    print(json.dumps(secret_create, indent=2, default=str))
    print(json.dumps(secret_read, indent=2, default=str))
    print(f"Masked secret value: {masked_secret}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
