from __future__ import annotations

import argparse
import io
import json
import os
import pickle
import time
import zipfile

import boto3


class TinyModel:
    def predict_proba(self, matrix: list[list[float]]) -> list[list[float]]:
        score = matrix[0][-1]
        prob = min(max(score / 1000.0, 0.0), 1.0)
        return [[1.0 - prob, prob]]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy tiny sklearn-style model as Lambda function")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--role-arn", default=os.getenv("LAMBDA_EXECUTION_ROLE_ARN"), help="Lambda execution role ARN")
    parser.add_argument("--function-name", default="mle-lab-04-lambda-serve", help="Lambda function name")
    return parser


def _build_zip_bytes() -> bytes:
    model = TinyModel()
    model_bytes = pickle.dumps(model)

    handler_source = """
import json
import pickle

with open('/tmp/model.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

def lambda_handler(event, context):
    features = event.get('features', {})
    ordered = [float(features.get(f'V{i}', 0.0)) for i in range(1, 31)] + [float(features.get('Amount', 0.0))]
    probability = float(model.predict_proba([ordered])[0][1])
    prediction = int(probability >= 0.5)
    return {'statusCode': 200, 'body': json.dumps({'prediction': prediction, 'probability': probability})}
""".strip()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("handler.py", handler_source)
        zip_file.writestr("model.pkl", model_bytes)
    return buffer.getvalue()


def main() -> int:
    args = _build_parser().parse_args()
    if not args.role_arn:
        raise RuntimeError("--role-arn is required (or set LAMBDA_EXECUTION_ROLE_ARN)")

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    lambda_client = session.client("lambda")

    package_bytes = _build_zip_bytes()

    # ponytail: Lambda model must be tiny — sklearn only, no torch
    lambda_client.create_function(
        FunctionName=args.function_name,
        Runtime="python3.11",
        Role=args.role_arn,
        Handler="handler.lambda_handler",
        Code={"ZipFile": package_bytes},
        Timeout=30,
        MemorySize=512,
        Publish=True,
    )

    payload = {
        "features": {**{f"V{i}": 0.0 for i in range(1, 31)}, "Amount": 150.0}
    }

    first_start = time.time()
    first_response = lambda_client.invoke(
        FunctionName=args.function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    first_latency = (time.time() - first_start) * 1000.0
    first_body = first_response["Payload"].read().decode("utf-8")

    second_start = time.time()
    second_response = lambda_client.invoke(
        FunctionName=args.function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    second_latency = (time.time() - second_start) * 1000.0
    second_body = second_response["Payload"].read().decode("utf-8")

    print("First invoke response:", first_body)
    print(f"First invoke latency (cold): {first_latency:.2f} ms")
    print("Second invoke response:", second_body)
    print(f"Second invoke latency (warm): {second_latency:.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
