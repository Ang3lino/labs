from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path


# ponytail: DatasetManager is just download+cleanup, not a framework
class DatasetManager:
    def __init__(self, cache_dir: Path | str | None = None) -> None:
        if cache_dir is None:
            cache_path = Path("~/.cache/aws-mle-labs/").expanduser()
        else:
            cache_path = Path(cache_dir).expanduser()
        self._cache_dir = cache_path
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def download(self, url: str, dest_filename: str, checksum: str | None = None) -> Path:
        destination = self._cache_dir / dest_filename
        if destination.exists():
            if checksum is not None:
                self._verify_checksum(destination, checksum)
            return destination

        destination.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, destination)

        if checksum is not None:
            self._verify_checksum(destination, checksum)

        return destination

    def cleanup(self, dest_filename: str | None = None) -> None:
        if dest_filename is None:
            if self._cache_dir.exists():
                shutil.rmtree(self._cache_dir)
            return

        target = self._cache_dir / dest_filename
        if target.exists():
            target.unlink()

    def _verify_checksum(self, file_path: Path, expected_sha256: str) -> None:
        digest = hashlib.sha256()
        with file_path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Checksum mismatch for {file_path.name}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local cached datasets for AWS MLE labs")
    parser.add_argument(
        "--download",
        nargs=2,
        metavar=("URL", "FILENAME"),
        help="Download a dataset URL into cache as FILENAME",
    )
    parser.add_argument(
        "--cleanup",
        nargs="?",
        metavar="FILENAME",
        const="__ALL__",
        help="Remove FILENAME from cache, or all files if omitted",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print cache location and list cached files",
    )
    return parser


def _handle_cli() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    manager = DatasetManager()

    if args.download is not None:
        url, filename = args.download
        saved_path = manager.download(url, filename)
        print(saved_path)

    if args.cleanup is not None:
        cleanup_target = None if args.cleanup == "__ALL__" else args.cleanup
        manager.cleanup(cleanup_target)

    if args.check:
        print(manager.cache_dir)
        if manager.cache_dir.exists():
            for entry in sorted(manager.cache_dir.rglob("*")):
                if entry.is_file():
                    print(entry.relative_to(manager.cache_dir))

    if args.download is None and args.cleanup is None and not args.check:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(_handle_cli())
