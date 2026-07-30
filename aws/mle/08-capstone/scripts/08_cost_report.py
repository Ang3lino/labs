from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


@dataclass(frozen=True, slots=True)
class CostRow:
    resource: str
    assumption: str
    monthly_usd: float


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Lab 08 monthly cost estimate report")
    parser.add_argument("--s3-gb", type=float, default=200.0, help="Estimated combined S3 storage in GB")
    parser.add_argument("--endpoint-hours", type=float, default=24.0 * 30.0)
    parser.add_argument("--training-hours", type=float, default=20.0)
    parser.add_argument("--monitor-hours", type=float, default=60.0)
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _estimate_cost_rows(args: argparse.Namespace) -> list[CostRow]:
    s3_price_per_gb = 0.023
    endpoint_price_per_hour = 0.115
    training_price_per_hour = 0.115
    monitor_price_per_hour = 0.23
    cloudwatch_dashboard_monthly = 3.0

    return [
        CostRow(
            resource="S3 data + artifacts",
            assumption=f"{args.s3_gb:.1f} GB at $0.023/GB",
            monthly_usd=args.s3_gb * s3_price_per_gb,
        ),
        CostRow(
            resource="SageMaker endpoint (ml.m5.large)",
            assumption=f"{args.endpoint_hours:.1f} hrs at $0.115/hr",
            monthly_usd=args.endpoint_hours * endpoint_price_per_hour,
        ),
        CostRow(
            resource="SageMaker training jobs",
            assumption=f"{args.training_hours:.1f} hrs at $0.115/hr",
            monthly_usd=args.training_hours * training_price_per_hour,
        ),
        CostRow(
            resource="Model Monitor processing",
            assumption=f"{args.monitor_hours:.1f} hrs at $0.23/hr",
            monthly_usd=args.monitor_hours * monitor_price_per_hour,
        ),
        CostRow(
            resource="CloudWatch dashboard + metrics",
            assumption="1 dashboard + baseline custom metrics",
            monthly_usd=cloudwatch_dashboard_monthly,
        ),
    ]


def _print_cost_table(rows: list[CostRow]) -> None:
    header_resource = "Resource"
    header_assumption = "Assumption"
    header_cost = "Monthly USD"

    resource_width = max(len(header_resource), *(len(row.resource) for row in rows))
    assumption_width = max(len(header_assumption), *(len(row.assumption) for row in rows))
    cost_width = max(len(header_cost), *(len(f"{row.monthly_usd:.2f}") for row in rows))

    divider = f"+{'-' * (resource_width + 2)}+{'-' * (assumption_width + 2)}+{'-' * (cost_width + 2)}+"
    print(divider)
    print(
        f"| {header_resource.ljust(resource_width)} | "
        f"{header_assumption.ljust(assumption_width)} | "
        f"{header_cost.rjust(cost_width)} |"
    )
    print(divider)

    for row in rows:
        print(
            f"| {row.resource.ljust(resource_width)} | "
            f"{row.assumption.ljust(assumption_width)} | "
            f"{f'{row.monthly_usd:.2f}'.rjust(cost_width)} |"
        )
    print(divider)


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()
    rows = _estimate_cost_rows(args)
    total = sum(row.monthly_usd for row in rows)

    print("Lab 08 estimated monthly cost report")
    print(f"Data bucket: {outputs['dataBucketName']}")
    print(f"Model bucket: {outputs['modelBucketName']}")
    _print_cost_table(rows)
    print(f"Estimated total: ${total:.2f}/month")
    print("Optimization recommendations:")
    print("- Use Spot Instances for training and processing where interruptions are acceptable")
    print("- Buy Savings Plans for steady endpoint workloads")
    print("- Right-size endpoint instance class using Inference Recommender")
    print("- Apply data lifecycle transitions to lower-cost S3 tiers")
    print("- Tag resources by owner/environment to catch idle spend quickly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
