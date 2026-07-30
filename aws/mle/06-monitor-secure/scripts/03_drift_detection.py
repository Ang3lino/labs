from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FeatureStats:
    feature: str
    mean: float
    stddev: float


@dataclass(frozen=True, slots=True)
class ConstraintViolation:
    feature: str
    baseline_mean: float
    current_mean: float
    allowed_delta: float


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate drift and generate a constraint violation report")
    parser.add_argument("--baseline-csv", required=True)
    parser.add_argument("--max-rows", type=int, default=5000)
    return parser


def _read_rows(path: Path, max_rows: int) -> list[dict[str, float]]:
    parsed_rows: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            numeric_row = {key: float(value) for key, value in row.items() if key is not None and value is not None}
            parsed_rows.append(numeric_row)
            if len(parsed_rows) >= max_rows:
                break
    return parsed_rows


def _stats_for_feature(rows: list[dict[str, float]], feature: str) -> FeatureStats:
    values = [row[feature] for row in rows]
    mean_value = sum(values) / len(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return FeatureStats(feature=feature, mean=mean_value, stddev=variance**0.5)


def _simulate_drift(rows: list[dict[str, float]]) -> list[dict[str, float]]:
    drifted_rows: list[dict[str, float]] = []
    baseline_v1 = _stats_for_feature(rows, "V1")
    for row in rows:
        drifted = dict(row)
        drifted["Amount"] = row["Amount"] * 10.0
        drifted["V1"] = row["V1"] + (3.0 * baseline_v1.stddev)
        drifted_rows.append(drifted)
    return drifted_rows


def _detect_violations(
    baseline_stats: list[FeatureStats],
    current_stats: list[FeatureStats],
) -> list[ConstraintViolation]:
    baseline_by_feature = {stat.feature: stat for stat in baseline_stats}
    violations: list[ConstraintViolation] = []
    for current in current_stats:
        baseline = baseline_by_feature[current.feature]
        allowed_delta = baseline.stddev * 2.0
        observed_delta = abs(current.mean - baseline.mean)
        if observed_delta > allowed_delta:
            violations.append(
                ConstraintViolation(
                    feature=current.feature,
                    baseline_mean=baseline.mean,
                    current_mean=current.mean,
                    allowed_delta=allowed_delta,
                )
            )
    return violations


def main() -> int:
    args = _build_parser().parse_args()
    baseline_rows = _read_rows(Path(args.baseline_csv), args.max_rows)
    drifted_rows = _simulate_drift(baseline_rows)

    baseline_stats = [_stats_for_feature(baseline_rows, "Amount"), _stats_for_feature(baseline_rows, "V1")]
    drifted_stats = [_stats_for_feature(drifted_rows, "Amount"), _stats_for_feature(drifted_rows, "V1")]
    violations = _detect_violations(baseline_stats, drifted_stats)

    print("Constraint violation report")
    print("=" * 80)
    print("Baseline statistics:")
    for stat in baseline_stats:
        print(f"- {stat.feature}: mean={stat.mean:.6f}, stddev={stat.stddev:.6f}")
    print("Drifted statistics:")
    for stat in drifted_stats:
        print(f"- {stat.feature}: mean={stat.mean:.6f}, stddev={stat.stddev:.6f}")
    if not violations:
        print("No constraint violations detected.")
        return 0

    print("Violations detected:")
    for violation in violations:
        delta = abs(violation.current_mean - violation.baseline_mean)
        print(
            f"- {violation.feature}: baseline_mean={violation.baseline_mean:.6f}, "
            f"current_mean={violation.current_mean:.6f}, observed_delta={delta:.6f}, "
            f"allowed_delta={violation.allowed_delta:.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
