from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3


LAB_ROOT = Path(__file__).resolve().parents[1]
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))
if str(LAB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT.parent))

from shared.datasets import DatasetManager


TEXTRACT_IMAGE_FILENAME = "03-bedrock-ai-services/images/sample_text_document.png"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract text from sample document with Textract")
    parser.add_argument("--region", default="us-east-1")
    return parser


def _load_document_bytes() -> bytes:
    manager = DatasetManager()
    document_path = manager.cache_dir / TEXTRACT_IMAGE_FILENAME
    if not document_path.exists():
        raise FileNotFoundError(
            f"Missing document image at {document_path}. Run: uv run python aws/mle/03-bedrock-ai-services/datasets.py --download"
        )
    return document_path.read_bytes()


def main() -> int:
    args = _build_parser().parse_args()
    document_bytes = _load_document_bytes()
    client = boto3.client("textract", region_name=args.region)

    detect_response = client.detect_document_text(Document={"Bytes": document_bytes})
    print("detect_document_text blocks:")
    for block in detect_response.get("Blocks", []):
        if block.get("BlockType") == "LINE":
            print(f"- {block.get('Text', '')} ({block.get('Confidence', 0.0):.2f}%)")

    analyze_response = client.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["FORMS", "TABLES"],
    )
    print("analyze_document blocks:")
    for block in analyze_response.get("Blocks", []):
        block_type = block.get("BlockType", "UNKNOWN")
        text = block.get("Text", "")
        confidence = block.get("Confidence", 0.0)
        if block_type in {"LINE", "KEY_VALUE_SET", "CELL", "TABLE"}:
            print(f"- [{block_type}] {text} ({confidence:.2f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
