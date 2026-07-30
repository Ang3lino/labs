from __future__ import annotations

import argparse
import json

import boto3


SAMPLE_TEXTS = [
    "I love how quickly this service solved my issue. Great support!",
    "The deployment failed again and the experience has been frustrating.",
    "The package arrived yesterday and includes all listed components.",
    "The results were okay, but there are both good and bad parts.",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Comprehend demo for sentiment/entities/key phrases/language")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--language", default="en")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    client = boto3.client("comprehend", region_name=args.region)

    for index, text in enumerate(SAMPLE_TEXTS, start=1):
        sentiment = client.detect_sentiment(Text=text, LanguageCode=args.language)
        entities = client.detect_entities(Text=text, LanguageCode=args.language)
        key_phrases = client.detect_key_phrases(Text=text, LanguageCode=args.language)
        dominant_language = client.detect_dominant_language(Text=text)

        print(f"Text #{index}: {text}")
        print(f"Sentiment: {sentiment['Sentiment']}")
        print("Sentiment scores:")
        print(json.dumps(sentiment["SentimentScore"], indent=2, default=str))
        print("Entities:")
        print(json.dumps(entities["Entities"], indent=2, default=str))
        print("Key phrases:")
        print(json.dumps(key_phrases["KeyPhrases"], indent=2, default=str))
        print("Dominant language:")
        print(json.dumps(dominant_language["Languages"], indent=2, default=str))
        print("-" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
