from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and validate CodeBuild buildspec.yml for Lab 05")
    parser.add_argument("--output", default="buildspec.yml")
    return parser


def _buildspec_object() -> dict[str, object]:
    return {
        "version": "0.2",
        "phases": {
            "install": {
                "commands": [
                    "echo Installing dependencies",
                    "pip install -r requirements.txt",
                ]
            },
            "pre_build": {
                "commands": [
                    "echo Running validation tests",
                    "pytest -q",
                ]
            },
            "build": {
                "commands": [
                    "echo Packaging model artifact",
                    "tar -czf model-package.tar.gz model/",
                ]
            },
            "post_build": {
                "commands": [
                    "echo Deploying approved model package",
                    "echo Deploy command placeholder for CodeDeploy/SageMaker rollout",
                ]
            },
        },
        "artifacts": {
            "files": ["model-package.tar.gz"],
            "name": "mlops-model-package",
        },
    }


def main() -> int:
    args = _build_parser().parse_args()
    output_path = Path(args.output)

    buildspec = _buildspec_object()
    output_path.write_text(yaml.safe_dump(buildspec, sort_keys=False), encoding="utf-8")

    loaded = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RuntimeError("Generated buildspec.yml is not a valid YAML mapping")

    print(f"Generated buildspec at: {output_path.resolve()}")
    print("YAML validation passed via yaml.safe_load")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
