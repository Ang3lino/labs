from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Comprehend analysis on chapter JSON files")
    parser.add_argument("--input-dir", default="output/chapters", help="Directory with chapter JSON files")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--language", default="en", help="Language code for Comprehend")
    return parser


def _chunk_for_comprehend(text: str, max_bytes: int = 5000) -> list[str]:
    chunks: list[str] = []
    current = ""
    for sentence in text.split(". "):
        candidate = sentence if not current else f"{current}. {sentence}"
        if len(candidate.encode("utf-8")) > max_bytes:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _summarize_entities(entities: list[dict[str, object]]) -> dict[str, int]:
    counts = {"PERSON": 0, "ORGANIZATION": 0, "CONCEPT": 0}
    for entity in entities:
        entity_type = str(entity.get("Type", ""))
        if entity_type in counts:
            counts[entity_type] += 1
    return counts


def _load_chapter_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.json"))


def main() -> int:
    args = _build_parser().parse_args()
    chapter_files = _load_chapter_files(Path(args.input_dir))
    if not chapter_files:
        raise FileNotFoundError(f"No chapter JSON files found in {args.input_dir}")

    comprehend = boto3.client("comprehend", region_name=args.region)

    print("chapter\tlanguage\tsentiment\tperson\torganization\tconcept\tkey_phrases")
    for chapter_file in chapter_files:
        payload = json.loads(chapter_file.read_text(encoding="utf-8"))
        text = str(payload.get("text", ""))
        chunks = _chunk_for_comprehend(text)
        if not chunks:
            continue

        dominant_language_response = comprehend.detect_dominant_language(Text=chunks[0])
        detected_language = dominant_language_response["Languages"][0]["LanguageCode"]

        sentiment_response = comprehend.batch_detect_sentiment(TextList=chunks, LanguageCode=args.language)
        sentiment_labels = [row["Sentiment"] for row in sentiment_response.get("ResultList", [])]
        dominant_sentiment = sentiment_labels[0] if sentiment_labels else "UNKNOWN"

        entities: list[dict[str, object]] = []
        key_phrases_total = 0
        for chunk in chunks:
            entity_response = comprehend.detect_entities(Text=chunk, LanguageCode=args.language)
            phrase_response = comprehend.detect_key_phrases(Text=chunk, LanguageCode=args.language)
            entities.extend(entity_response.get("Entities", []))
            key_phrases_total += len(phrase_response.get("KeyPhrases", []))

        entity_summary = _summarize_entities(entities)
        print(
            f"{chapter_file.stem}\t{detected_language}\t{dominant_sentiment}\t"
            f"{entity_summary['PERSON']}\t{entity_summary['ORGANIZATION']}\t"
            f"{entity_summary['CONCEPT']}\t{key_phrases_total}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
