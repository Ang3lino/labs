from __future__ import annotations

import argparse
import json
import os
import time

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy and invoke SageMaker serverless endpoint")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--role-arn", default=os.getenv("SAGEMAKER_EXECUTION_ROLE_ARN"), help="SageMaker execution role ARN")
    parser.add_argument("--image-uri", default=os.getenv("MODEL_IMAGE_URI"), help="Container image URI")
    parser.add_argument("--model-name", default="mle-lab-04-serverless-model", help="SageMaker model name")
    parser.add_argument("--endpoint-config-name", default="mle-lab-04-serverless-config", help="Endpoint config name")
    parser.add_argument("--endpoint-name", default="mle-lab-04-serverless-endpoint", help="Endpoint name")
    return parser


def _invoke(runtime: boto3.client, endpoint_name: str, payload: dict[str, object]) -> tuple[str, float]:
    started = time.time()
    response = runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps(payload).encode("utf-8"),
    )
    latency_ms = (time.time() - started) * 1000.0
    body = response["Body"].read().decode("utf-8")
    return body, latency_ms


def main() -> int:
    args = _build_parser().parse_args()
    if not args.role_arn or not args.image_uri:
        raise RuntimeError("--role-arn and --image-uri are required (or set SAGEMAKER_EXECUTION_ROLE_ARN and MODEL_IMAGE_URI)")

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    sagemaker = session.client("sagemaker")
    runtime = session.client("sagemaker-runtime")

    sagemaker.create_model(
        ModelName=args.model_name,
        ExecutionRoleArn=args.role_arn,
        PrimaryContainer={"Image": args.image_uri},
    )

    sagemaker.create_endpoint_config(
        EndpointConfigName=args.endpoint_config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": args.model_name,
                "ServerlessConfig": {
                    "MemorySizeInMB": 2048,
                    "MaxConcurrency": 5,
                },
            }
        ],
    )

    sagemaker.create_endpoint(
        EndpointName=args.endpoint_name,
        EndpointConfigName=args.endpoint_config_name,
    )

    payload = {
        "features": {**{f"V{i}": 0.0 for i in range(1, 31)}, "Amount": 0.0}
    }

    cold_body, cold_ms = _invoke(runtime, args.endpoint_name, payload)
    warm_body, warm_ms = _invoke(runtime, args.endpoint_name, payload)

    print("Cold start response:", cold_body)
    print(f"Cold start latency: {cold_ms:.2f} ms")
    print("Warm response:", warm_body)
    print(f"Warm latency: {warm_ms:.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
