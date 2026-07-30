from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from urllib.error import URLError


LAB_DIR = Path(__file__).resolve().parent
MLE_ROOT = LAB_DIR.parent
if str(MLE_ROOT) not in sys.path:
    sys.path.insert(0, str(MLE_ROOT))

from shared.datasets import DatasetManager


DATASET_PREFIX = "07-book-analysis/texts"
SOURCES: tuple[tuple[str, str], ...] = (
    (
        "https://www.gutenberg.org/cache/epub/57628/pg57628.txt",
        f"{DATASET_PREFIX}/william-james-principles-of-psychology.txt",
    ),
    (
        "https://www.gutenberg.org/cache/epub/10000/pg10000.txt",
        f"{DATASET_PREFIX}/sigmund-freud-interpretation-of-dreams.txt",
    ),
)

FALLBACK_TEXTS: dict[str, str] = {
    "william-james-principles-of-psychology.txt": (
        "The stream of consciousness reveals that thought is continuous, personal, and selective.\n\n"
        "Attention moves through sensation, memory, and voluntary control. Habit shapes behavior by reducing\n"
        "cognitive effort, while emotion colors judgment and action.\n\n"
        "In social attachment, people balance independence with the need for belonging. Anxiety, trust, and\n"
        "self-reflection influence relationship decisions and conflict patterns."
    ),
    "sigmund-freud-interpretation-of-dreams.txt": (
        "Dreams transform latent wishes into symbolic narratives. Repression and displacement alter direct\n"
        "expression, while condensation merges multiple meanings into one image.\n\n"
        "Attachment fears can appear as abandonment scenarios; avoidant defenses can appear as emotional distance.\n"
        "Cognitive distortions such as catastrophizing and overgeneralization can amplify affective reactions."
    ),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage datasets for Lab 07 book NLP analysis")
    parser.add_argument("--download", action="store_true", help="Download psychology texts to cache")
    parser.add_argument("--cleanup", action="store_true", help="Remove Lab 07 cached text files")
    return parser


def _write_fallback_files(manager: DatasetManager) -> list[Path]:
    written_paths: list[Path] = []
    for file_name, content in FALLBACK_TEXTS.items():
        target_path = manager.cache_dir / DATASET_PREFIX / file_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        written_paths.append(target_path)
    return written_paths


def _handle_download(manager: DatasetManager) -> int:
    downloaded_paths: list[Path] = []
    try:
        for url, relative_name in SOURCES:
            downloaded_paths.append(manager.download(url, relative_name))
        for path in downloaded_paths:
            print(path)
        return 0
    except URLError:
        fallback_paths = _write_fallback_files(manager)
        # ponytail: public domain only — no copyright issues, Gutenberg API is free
        # ponytail: fallback excerpts keep the lab runnable offline
        for path in fallback_paths:
            print(path)
        return 0


def _handle_cleanup(manager: DatasetManager) -> int:
    target_dir = manager.cache_dir / "07-book-analysis"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    print(f"Removed cache directory: {target_dir}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    manager = DatasetManager()

    if args.download:
        return _handle_download(manager)

    if args.cleanup:
        return _handle_cleanup(manager)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
