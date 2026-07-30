from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use Bedrock for chapter-level psychology trait analysis")
    parser.add_argument("--input-dir", default="output/chapters", help="Directory containing chapter JSON files")
    parser.add_argument("--output-dir", default="output/bedrock", help="Directory for Bedrock analysis outputs")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--max-chars", type=int, default=6000, help="Max chapter chars sent to model")
    return parser


def _prompt_for_text(text_excerpt: str) -> str:
    return (
        "Analyze the following psychology text excerpt and return strict JSON with keys: "
        "big_five_traits, attachment_styles, cognitive_biases, evidence_quotes. "
        "big_five_traits must include openness, conscientiousness, extraversion, agreeableness, neuroticism, each with "
        "a score from 0 to 1 and rationale. attachment_styles must include any of secure, anxious, avoidant, disorganized "
        "with confidence and rationale. cognitive_biases is a list of likely biases mentioned in the text. evidence_quotes "
        "is a list of short direct excerpts. Return only JSON.\n\n"
        f"TEXT:\n{text_excerpt}"
    )


def _invoke_bedrock(runtime_client: object, prompt: str, max_tokens: int = 800) -> str:
    request_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    response = runtime_client.invoke_model(modelId=MODEL_ID, body=json.dumps(request_payload))
    body_text = response["body"].read().decode("utf-8")
    parsed = json.loads(body_text)
    content = parsed.get("content", [])
    if not content:
        return "{}"
    text_output = content[0].get("text", "{}")
    return str(text_output)


def _load_chapters(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.json"))


def main() -> int:
    args = _build_parser().parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chapter_files = _load_chapters(input_dir)
    if not chapter_files:
        raise FileNotFoundError(f"No chapter JSON files found in {input_dir}")

    runtime = boto3.client("bedrock-runtime", region_name=args.region)

    for chapter_file in chapter_files:
        chapter_payload = json.loads(chapter_file.read_text(encoding="utf-8"))
        text_excerpt = str(chapter_payload.get("text", ""))[: args.max_chars]
        prompt = _prompt_for_text(text_excerpt)
        model_response_text = _invoke_bedrock(runtime, prompt)

        try:
            structured_result = json.loads(model_response_text)
        except json.JSONDecodeError:
            structured_result = {"raw_output": model_response_text}

        output_payload = {
            "book": chapter_payload.get("book"),
            "chapter_number": chapter_payload.get("chapter_number"),
            "analysis": structured_result,
        }
        target = output_dir / f"{chapter_file.stem}.personality.json"
        target.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(target)

    # ponytail: simplified analysis — a real system would need fine-tuned models
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
