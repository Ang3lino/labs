from __future__ import annotations

import argparse
import binascii
import struct
import sys
import zlib
from pathlib import Path
import shutil


CURRENT_DIR = Path(__file__).resolve().parent
SHARED_PARENT = CURRENT_DIR.parent
if str(SHARED_PARENT) not in sys.path:
    sys.path.insert(0, str(SHARED_PARENT))

from shared.datasets import DatasetManager


TEXT_URL = "https://www.gutenberg.org/cache/epub/132/pg132.txt"
TEXT_FILENAME = "03-bedrock-ai-services/rag/the-art-of-war.txt"
REKOGNITION_IMAGE_FILENAME = "03-bedrock-ai-services/images/sample_chart.png"
TEXTRACT_IMAGE_FILENAME = "03-bedrock-ai-services/images/sample_text_document.png"


def _build_chart_image(target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt

        x_values = [1, 2, 3, 4, 5]
        y_values = [2, 3, 5, 4, 6]
        plt.figure(figsize=(8, 4.5))
        plt.plot(x_values, y_values, marker="o", linewidth=2)
        plt.title("Sample Trend for Rekognition Lab")
        plt.xlabel("Week")
        plt.ylabel("Signal")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.savefig(target_path, dpi=120)
        plt.close()
    except ModuleNotFoundError:
        _write_fallback_png(target_path)


def _build_text_image(target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt

        lines = [
            "Invoice #INV-0007",
            "Customer: Alex Example",
            "Item A: 3 x 19.99 = 59.97",
            "Item B: 1 x 12.50 = 12.50",
            "Tax: 7.25%",
            "Total: 77.17 USD",
        ]
        fig = plt.figure(figsize=(8.5, 5.5))
        fig.patch.set_facecolor("white")
        for index, line in enumerate(lines):
            fig.text(0.08, 0.90 - (index * 0.12), line, fontsize=16, color="black", family="monospace")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(target_path, dpi=140)
        plt.close(fig)
    except ModuleNotFoundError:
        _write_fallback_png(target_path)


def _write_fallback_png(target_path: Path) -> None:
    width = 256
    height = 128
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            r = (x * 255) // (width - 1)
            g = (y * 255) // (height - 1)
            b = 180
            if 20 < x < 235 and 15 < y < 112 and ((x + y) % 41 < 3):
                r, g, b = 20, 20, 20
            rows.extend((r, g, b))

    def chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
        checksum = binascii.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        return struct.pack(">I", len(chunk_data)) + chunk_type + chunk_data + struct.pack(">I", checksum)

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(
        chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
        )
    )
    png.extend(chunk(b"IDAT", zlib.compress(bytes(rows), level=9)))
    png.extend(chunk(b"IEND", b""))
    target_path.write_bytes(bytes(png))


def download() -> dict[str, Path]:
    manager = DatasetManager()
    text_path = manager.download(TEXT_URL, TEXT_FILENAME)
    chart_path = manager.cache_dir / REKOGNITION_IMAGE_FILENAME
    text_image_path = manager.cache_dir / TEXTRACT_IMAGE_FILENAME
    _build_chart_image(chart_path)
    _build_text_image(text_image_path)
    # ponytail: small sample files, not a real corpus — just enough to see the APIs work
    return {
        "text": text_path,
        "rekognition_image": chart_path,
        "textract_image": text_image_path,
    }


def cleanup() -> None:
    manager = DatasetManager()
    target = manager.cache_dir / "03-bedrock-ai-services"
    if target.exists():
        shutil.rmtree(target)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage datasets for Lab 03 Bedrock & AI Services")
    parser.add_argument("--download", action="store_true", help="Download and generate sample files")
    parser.add_argument("--cleanup", action="store_true", help="Remove Lab 03 cached files")
    return parser


def _handle_cli() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.download:
        paths = download()
        for name, path in paths.items():
            print(f"{name}: {path}")

    if args.cleanup:
        cleanup()
        print("Removed cache for 03-bedrock-ai-services")

    if not args.download and not args.cleanup:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(_handle_cli())
