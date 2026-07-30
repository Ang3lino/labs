from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate comparative report across analyzed books")
    parser.add_argument("--comprehend-json", default="output/comprehend_results.json", help="Comprehend results JSON")
    parser.add_argument("--personality-dir", default="output/bedrock", help="Directory with personality analysis JSON files")
    parser.add_argument("--output-dir", default="output/reports", help="Directory for generated report artifacts")
    return parser


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sentiment_to_score(label: str) -> float:
    mapping = {"POSITIVE": 1.0, "MIXED": 0.25, "NEUTRAL": 0.0, "NEGATIVE": -1.0}
    return mapping.get(label.upper(), 0.0)


def _plot_sentiment_arc(comprehend_payload: dict[str, object], output_dir: Path) -> Path:
    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    chapters = comprehend_payload.get("chapters", [])
    for chapter in chapters:
        chapter_dict = dict(chapter)
        book = str(chapter_dict.get("book", "unknown"))
        chapter_number = int(chapter_dict.get("chapter_number", 0))
        sentiment_label = str(chapter_dict.get("sentiment", "NEUTRAL"))
        grouped[book].append((chapter_number, _sentiment_to_score(sentiment_label)))

    plt.figure(figsize=(10, 5))
    for book_name, arc in grouped.items():
        sorted_arc = sorted(arc, key=lambda item: item[0])
        xs = [point[0] for point in sorted_arc]
        ys = [point[1] for point in sorted_arc]
        plt.plot(xs, ys, marker="o", label=book_name)

    plt.title("Sentiment Arc Through Chapters")
    plt.xlabel("Chapter")
    plt.ylabel("Sentiment Score")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()

    output_path = output_dir / "sentiment_arc.png"
    plt.savefig(output_path, dpi=140)
    plt.close()
    return output_path


def _trait_coverage(personality_dir: Path) -> dict[str, set[str]]:
    coverage: dict[str, set[str]] = defaultdict(set)
    for path in sorted(personality_dir.glob("*.json")):
        payload = _load_json(path)
        book = str(payload.get("book", "unknown"))
        analysis = payload.get("analysis", {})
        analysis_dict = dict(analysis) if isinstance(analysis, dict) else {}
        traits = analysis_dict.get("big_five_traits", {})
        traits_dict = dict(traits) if isinstance(traits, dict) else {}
        for trait_name in traits_dict:
            coverage[book].add(str(trait_name))
    return coverage


def _shared_entities_and_phrases(comprehend_payload: dict[str, object]) -> tuple[set[str], set[str]]:
    per_book_entities: dict[str, set[str]] = defaultdict(set)
    per_book_phrases: dict[str, set[str]] = defaultdict(set)

    for chapter in comprehend_payload.get("chapters", []):
        chapter_dict = dict(chapter)
        book = str(chapter_dict.get("book", "unknown"))
        entities = chapter_dict.get("entities", [])
        key_phrases = chapter_dict.get("key_phrases", [])
        for entity in entities if isinstance(entities, list) else []:
            entity_dict = dict(entity)
            per_book_entities[book].add(str(entity_dict.get("Text", "")).strip())
        for phrase in key_phrases if isinstance(key_phrases, list) else []:
            phrase_dict = dict(phrase)
            per_book_phrases[book].add(str(phrase_dict.get("Text", "")).strip())

    books = list(per_book_entities.keys())
    if len(books) < 2:
        return set(), set()

    shared_entities = per_book_entities[books[0]].intersection(per_book_entities[books[1]])
    shared_phrases = per_book_phrases[books[0]].intersection(per_book_phrases[books[1]])
    return shared_entities, shared_phrases


def main() -> int:
    args = _build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    comprehend_payload = _load_json(Path(args.comprehend_json))
    sentiment_plot = _plot_sentiment_arc(comprehend_payload, output_dir)
    trait_map = _trait_coverage(Path(args.personality_dir))
    shared_entities, shared_phrases = _shared_entities_and_phrases(comprehend_payload)

    summary_lines = [
        "# Comparative Book NLP Report",
        "",
        "## Personality Trait Coverage by Book",
    ]
    for book_name, traits in trait_map.items():
        summary_lines.append(f"- {book_name}: {', '.join(sorted(traits)) if traits else 'none detected'}")

    summary_lines.extend(
        [
            "",
            "## Theme Overlap",
            f"- Shared entities: {', '.join(sorted(item for item in shared_entities if item)) or 'none'}",
            f"- Shared key phrases: {', '.join(sorted(item for item in shared_phrases if item)) or 'none'}",
            "",
            f"## Sentiment Arc Plot\nSaved to `{sentiment_plot}`",
        ]
    )

    report_path = output_dir / "comparative_report.md"
    report_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(report_path)
    print(sentiment_plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
