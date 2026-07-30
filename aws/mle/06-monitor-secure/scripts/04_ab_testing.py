from __future__ import annotations

import argparse
import json

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and manage SageMaker A/B testing variants")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-name", default="mle-lab-06-ab-endpoint")
    parser.add_argument("--endpoint-config-name", default="mle-lab-06-ab-config")
    parser.add_argument("--model-a", required=True)
    parser.add_argument("--model-b", required=True)
    parser.add_argument("--apply", action="store_true", help="Create endpoint config and update endpoint")
    return parser


def _variants_config(model_a: str, model_b: str) -> list[dict[str, object]]:
    return [
        {
            "VariantName": "variant-A",
            "ModelName": model_a,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.m5.large",
            "InitialVariantWeight": 0.9,
        },
        {
            "VariantName": "variant-B",
            "ModelName": model_b,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.m5.large",
            "InitialVariantWeight": 0.1,
        },
    ]


def _invoke_specific_variants(runtime_client: "boto3.client", endpoint_name: str) -> dict[str, dict[str, float]]:
    payload = json.dumps({"features": {f"V{index}": 0.0 for index in range(1, 31)} | {"Amount": 120.0}})
    responses: dict[str, dict[str, float]] = {}
    for variant in ("variant-A", "variant-B"):
        response = runtime_client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Body=payload.encode("utf-8"),
            TargetVariant=variant,
        )
        raw_body = response["Body"].read().decode("utf-8")
        parsed = json.loads(raw_body)
        score = float(parsed.get("score", 0.0)) if isinstance(parsed, dict) else 0.0
        responses[variant] = {"score": score}
    return responses


def _mock_variant_metrics() -> dict[str, dict[str, float]]:
    return {
        "variant-A": {"invocations": 9000.0, "latency_p99_ms": 115.0, "error_rate": 0.003, "auc": 0.941},
        "variant-B": {"invocations": 1000.0, "latency_p99_ms": 108.0, "error_rate": 0.002, "auc": 0.949},
    }


def main() -> int:
    args = _build_parser().parse_args()
    sagemaker_client = boto3.client("sagemaker", region_name=args.region)
    runtime_client = boto3.client("sagemaker-runtime", region_name=args.region)
    variants = _variants_config(args.model_a, args.model_b)

    if args.apply:
        create_response = sagemaker_client.create_endpoint_config(
            EndpointConfigName=args.endpoint_config_name,
            ProductionVariants=variants,
        )
        update_response = sagemaker_client.update_endpoint(
            EndpointName=args.endpoint_name,
            EndpointConfigName=args.endpoint_config_name,
        )
        print("Created endpoint config:")
        print(json.dumps(create_response, indent=2, default=str))
        print("Updated endpoint:")
        print(json.dumps(update_response, indent=2, default=str))

    variant_invocations = _invoke_specific_variants(runtime_client, args.endpoint_name)
    metrics = _mock_variant_metrics()
    shift_plan = {
        "from": {"variant-A": 0.9, "variant-B": 0.1},
        "to": {"variant-A": 0.5, "variant-B": 0.5},
        "reason": "variant-B has better AUC with similar latency/error profile",
    }

    print("Variant invocation outputs:")
    print(json.dumps(variant_invocations, indent=2))
    print("Variant comparison metrics:")
    print(json.dumps(metrics, indent=2))
    print("Suggested traffic shift:")
    print(json.dumps(shift_plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
