from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run chapter-level topic modeling with TF-IDF + KMeans")
    parser.add_argument("--input-dir", default="output/chapters", help="Directory containing chapter JSON files")
    parser.add_argument("--clusters", type=int, default=4, help="Number of topic clusters")
    parser.add_argument("--top-terms", type=int, default=8, help="Top terms per cluster")
    return parser


def _load_chapter_payloads(input_dir: Path) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in sorted(input_dir.glob("*.json")):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def _topic_terms(model: KMeans, features: list[str], top_n: int) -> dict[int, list[str]]:
    terms: dict[int, list[str]] = {}
    for cluster_id, centroid in enumerate(model.cluster_centers_):
        sorted_indexes = centroid.argsort()[::-1][:top_n]
        terms[cluster_id] = [features[index] for index in sorted_indexes]
    return terms


def main() -> int:
    args = _build_parser().parse_args()
    payloads = _load_chapter_payloads(Path(args.input_dir))
    if not payloads:
        raise FileNotFoundError(f"No chapter JSON files found in {args.input_dir}")

    texts = [str(payload.get("text", "")) for payload in payloads]
    labels = [f"{payload.get('book')}:ch{payload.get('chapter_number')}" for payload in payloads]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    matrix = vectorizer.fit_transform(texts)

    cluster_count = min(args.clusters, len(texts))
    model = KMeans(n_clusters=cluster_count, n_init=20, random_state=42)
    assignments = model.fit_predict(matrix)

    feature_names = vectorizer.get_feature_names_out().tolist()
    top_terms = _topic_terms(model, feature_names, args.top_terms)

    print("cluster\ttop_terms")
    for cluster_id, terms in top_terms.items():
        print(f"{cluster_id}\t{', '.join(terms)}")

    print("\nchapter\tcluster")
    for chapter_label, cluster_id in zip(labels, assignments, strict=True):
        print(f"{chapter_label}\t{cluster_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
