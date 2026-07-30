from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import boto3


SCRIPT_DIR = Path(__file__).resolve().parent
LAB_DIR = SCRIPT_DIR.parent
MLE_ROOT = LAB_DIR.parent
if str(MLE_ROOT) not in sys.path:
    sys.path.insert(0, str(MLE_ROOT))

from shared.datasets import DatasetManager


CHAPTER_PATTERN = re.compile(r"^\s*(chapter|book)\s+([0-9ivxlcdm]+)[\.:\-\s].*$", re.IGNORECASE | re.MULTILINE)
GUTENBERG_START_PATTERN = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE | re.DOTALL)
GUTENBERG_END_PATTERN = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE | re.DOTALL)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preprocess Gutenberg texts into chapter JSON and upload to S3")
    parser.add_argument("--bucket", required=True, help="Target S3 bucket")
    parser.add_argument("--prefix", default="book-analysis/processed", help="S3 key prefix for chapter JSON")
    parser.add_argument("--region", default="us-east-1", help="AWS region for S3 client")
    return parser


def _remove_gutenberg_boilerplate(raw_text: str) -> str:
    start_match = GUTENBERG_START_PATTERN.search(raw_text)
    end_match = GUTENBERG_END_PATTERN.search(raw_text)
    start_index = start_match.end() if start_match is not None else 0
    end_index = end_match.start() if end_match is not None else len(raw_text)
    return raw_text[start_index:end_index].strip()


def _split_into_chapters(clean_text: str) -> list[tuple[int, str]]:
    matches = list(CHAPTER_PATTERN.finditer(clean_text))
    if not matches:
        return [(1, clean_text)]

    chapter_blobs: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        chunk_start = match.start()
        chunk_end = matches[index + 1].start() if index + 1 < len(matches) else len(clean_text)
        chapter_number = index + 1
        chapter_text = clean_text[chunk_start:chunk_end].strip()
        if chapter_text:
            chapter_blobs.append((chapter_number, chapter_text))
    return chapter_blobs


def _tokenize_sentences(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]


def _tokenize_paragraphs(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]


def _chapter_record(book_name: str, chapter_number: int, chapter_text: str) -> dict[str, object]:
    sentence_tokens = _tokenize_sentences(chapter_text)
    paragraph_tokens = _tokenize_paragraphs(chapter_text)
    word_count = len(re.findall(r"\b\w+\b", chapter_text))
    return {
        "book": book_name,
        "chapter_number": chapter_number,
        "word_count": word_count,
        "sentence_count": len(sentence_tokens),
        "paragraph_count": len(paragraph_tokens),
        "text": chapter_text,
    }


def _upload_chapter_json(s3_client: object, bucket: str, key: str, chapter: dict[str, object]) -> None:
    body = json.dumps(chapter, ensure_ascii=False).encode("utf-8")
    s3_client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")


def _process_file(s3_client: object, file_path: Path, bucket: str, prefix: str) -> int:
    raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
    cleaned_text = _remove_gutenberg_boilerplate(raw_text)
    chapters = _split_into_chapters(cleaned_text)
    book_name = file_path.stem

    uploaded_count = 0
    for chapter_number, chapter_text in chapters:
        chapter_payload = _chapter_record(book_name, chapter_number, chapter_text)
        key = f"{prefix}/{book_name}/chapter-{chapter_number:03d}.json"
        _upload_chapter_json(s3_client, bucket, key, chapter_payload)
        uploaded_count += 1

    return uploaded_count


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    manager = DatasetManager()
    text_dir = manager.cache_dir / "07-book-analysis" / "texts"
    if not text_dir.exists():
        raise FileNotFoundError("No cached texts found. Run datasets.py --download first.")

    s3_client = boto3.client("s3", region_name=args.region)
    uploaded_total = 0
    for text_path in sorted(text_dir.glob("*.txt")):
        uploaded_total += _process_file(s3_client, text_path, args.bucket, args.prefix)

    print(f"Uploaded chapter JSON objects: {uploaded_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
