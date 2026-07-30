from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass

import boto3


@dataclass(frozen=True)
class InvocationResult:
    model_id: str
    text: str
    elapsed_seconds: float
    input_tokens: int | None
    output_tokens: int | None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Invoke Bedrock model and compare two models")
    parser.add_argument(
        "--model-id",
        default="anthropic.claude-3-haiku-20240307-v1:0",
        help="Primary Bedrock model ID",
    )
    parser.add_argument("--compare-model-id", default="amazon.titan-text-express-v1")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument(
        "--prompt",
        default="Explain Retrieval-Augmented Generation in 4 short bullet points.",
    )
    return parser


def _invoke_model(
    client: boto3.client,
    model_id: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
) -> InvocationResult:
    if model_id.startswith("anthropic."):
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }
    elif model_id.startswith("amazon.titan-text"):
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "temperature": temperature,
                "maxTokenCount": max_tokens,
            },
        }
    else:
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "temperature": temperature,
                "maxTokenCount": max_tokens,
            },
        }

    start_time = time.perf_counter()
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body),
        contentType="application/json",
        accept="application/json",
    )
    elapsed_seconds = time.perf_counter() - start_time

    payload = json.loads(response["body"].read().decode("utf-8"))
    text = ""
    usage = payload.get("usage", {})
    content = payload.get("content")
    if isinstance(content, list) and content:
        first_item = content[0]
        if isinstance(first_item, dict):
            text = str(first_item.get("text", ""))
    elif isinstance(payload.get("results"), list) and payload["results"]:
        first_result = payload["results"][0]
        if isinstance(first_result, dict):
            text = str(first_result.get("outputText", ""))
    elif isinstance(payload.get("outputText"), str):
        text = payload["outputText"]

    return InvocationResult(
        model_id=model_id,
        text=text,
        elapsed_seconds=elapsed_seconds,
        input_tokens=usage.get("input_tokens") or usage.get("inputTokenCount"),
        output_tokens=usage.get("output_tokens") or usage.get("outputTokenCount"),
    )


def _print_result(result: InvocationResult) -> None:
    print(f"Model: {result.model_id}")
    print(f"Elapsed: {result.elapsed_seconds:.2f}s")
    print(f"Input tokens: {result.input_tokens}")
    print(f"Output tokens: {result.output_tokens}")
    print("Response:")
    print(result.text)
    print("-" * 80)


def main() -> int:
    args = _build_parser().parse_args()
    client = boto3.client("bedrock-runtime", region_name=args.region)

    primary = _invoke_model(
        client=client,
        model_id=args.model_id,
        prompt=args.prompt,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    _print_result(primary)

    if args.compare_model_id != args.model_id:
        # ponytail: compare uses same prompt and params for quick latency/token sanity check
        comparison = _invoke_model(
            client=client,
            model_id=args.compare_model_id,
            prompt=args.prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        _print_result(comparison)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
