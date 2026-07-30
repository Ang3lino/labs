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


REKOGNITION_IMAGE_FILENAME = "03-bedrock-ai-services/images/sample_chart.png"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect labels and text using Amazon Rekognition")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--max-labels", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=70.0)
    return parser


def _load_image_bytes() -> bytes:
    manager = DatasetManager()
    image_path = manager.cache_dir / REKOGNITION_IMAGE_FILENAME
    if not image_path.exists():
        raise FileNotFoundError(
            f"Missing image at {image_path}. Run: uv run python aws/mle/03-bedrock-ai-services/datasets.py --download"
        )
    return image_path.read_bytes()


def main() -> int:
    args = _build_parser().parse_args()
    image_bytes = _load_image_bytes()
    client = boto3.client("rekognition", region_name=args.region)

    label_response = client.detect_labels(
        Image={"Bytes": image_bytes},
        MaxLabels=args.max_labels,
        MinConfidence=args.min_confidence,
    )
    print("Detected labels:")
    for label in label_response.get("Labels", []):
        print(f"- {label['Name']}: {label['Confidence']:.2f}%")

    text_response = client.detect_text(Image={"Bytes": image_bytes})
    print("Detected text:")
    for detection in text_response.get("TextDetections", []):
        text = detection.get("DetectedText", "")
        confidence = detection.get("Confidence", 0.0)
        kind = detection.get("Type", "UNKNOWN")
        print(f"- [{kind}] {text} ({confidence:.2f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
