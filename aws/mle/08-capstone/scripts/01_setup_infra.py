from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CAPSTONE_DIR = SCRIPT_DIR.parent
PULUMI_DIR = CAPSTONE_DIR / "pulumi"
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy Lab 08 Pulumi stack and save outputs")
    parser.add_argument("--stack", default=None, help="Optional Pulumi stack name")
    return parser


def _run_pulumi_up(stack: str | None) -> None:
    commands = [["pulumi", "up", "--yes"]]
    if stack:
        commands.insert(0, ["pulumi", "stack", "select", stack])

    for command in commands:
        subprocess.run(command, check=True, cwd=PULUMI_DIR)


def _collect_outputs() -> dict[str, object]:
    result = subprocess.run(
        ["pulumi", "stack", "output", "--json"],
        check=True,
        cwd=PULUMI_DIR,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    args = _build_parser().parse_args()
    _run_pulumi_up(args.stack)
    outputs = _collect_outputs()
    INFRA_OUTPUTS_PATH.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    print(f"Saved infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
