from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Bedrock-based behavioral insights markdown report")
    parser.add_argument("--input-dir", default="output/bedrock", help="Directory with per-chapter personality JSON")
    parser.add_argument("--output-file", default="output/reports/behavioral_insights.md", help="Output markdown file")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    return parser


def _load_analysis_records(input_dir: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(input_dir.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def _build_prompt(records: list[dict[str, object]]) -> str:
    data_blob = json.dumps(records, ensure_ascii=False)
    return (
        "Based on the analyzed texts, generate a concise structured markdown report with exactly these sections: "
        "Key Themes, Personality Models Discussed, Behavioral Patterns Identified, Practical Takeaways. "
        "Ground claims in the provided analysis data. Avoid speculation and keep language interview-ready.\n\n"
        f"ANALYSIS DATA:\n{data_blob}"
    )


def _invoke(runtime_client: object, prompt: str) -> str:
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    response = runtime_client.invoke_model(modelId=MODEL_ID, body=json.dumps(payload))
    decoded = response["body"].read().decode("utf-8")
    parsed = json.loads(decoded)
    content = parsed.get("content", [])
    if not content:
        return "# Behavioral Insights\n\nNo model output returned."
    return str(content[0].get("text", ""))


def main() -> int:
    args = _build_parser().parse_args()
    records = _load_analysis_records(Path(args.input_dir))
    if not records:
        raise FileNotFoundError(f"No analysis JSON files found in {args.input_dir}")

    runtime = boto3.client("bedrock-runtime", region_name=args.region)
    prompt = _build_prompt(records)
    markdown_report = _invoke(runtime, prompt)

    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(markdown_report, encoding="utf-8")
    print(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
