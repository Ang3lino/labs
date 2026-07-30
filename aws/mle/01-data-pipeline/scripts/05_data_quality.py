from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class RuleResult:
    name: str
    passed: bool
    detail: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Glue-style data quality rules (DQDL-inspired)")
    parser.add_argument("--input", required=True, help="CSV input path")
    parser.add_argument("--id-column", default="transaction_id", help="Uniqueness key column")
    return parser


def _evaluate_rules(dataframe: pd.DataFrame, id_column: str) -> list[RuleResult]:
    results: list[RuleResult] = []

    key_columns = ["Class", "Amount"]
    missing_columns = [column for column in key_columns if column not in dataframe.columns]
    completeness_passed = len(missing_columns) == 0 and dataframe[key_columns].notna().all().all()
    results.append(
        RuleResult(
            name="Completeness",
            passed=bool(completeness_passed),
            detail="No nulls in Class and Amount" if completeness_passed else f"Missing/null columns: {missing_columns}",
        )
    )

    if id_column in dataframe.columns:
        unique_passed = dataframe[id_column].is_unique
        unique_detail = f"{id_column} unique={unique_passed}"
    else:
        unique_passed = False
        unique_detail = f"Column not found: {id_column}"
    results.append(RuleResult(name="Uniqueness", passed=bool(unique_passed), detail=unique_detail))

    if "Amount" in dataframe.columns:
        non_negative_passed = (dataframe["Amount"] >= 0).all()
        range_detail = "All Amount values are >= 0" if non_negative_passed else "Found Amount < 0"
    else:
        non_negative_passed = False
        range_detail = "Column not found: Amount"
    results.append(RuleResult(name="ValueRange", passed=bool(non_negative_passed), detail=range_detail))

    return results


def main() -> int:
    args = _build_parser().parse_args()
    dataframe = pd.read_csv(args.input)

    dqdl_rules = [
        "Rules = [IsComplete 'Class', IsComplete 'Amount']",
        f"Rules = [IsUnique '{args.id_column}']",
        "Rules = [ColumnValues 'Amount' >= 0]",
    ]

    print("Glue Data Quality DQDL rules (study preview):")
    for rule in dqdl_rules:
        print(f"- {rule}")

    results = _evaluate_rules(dataframe, args.id_column)
    overall_passed = all(rule_result.passed for rule_result in results)
    for rule_result in results:
        status = "PASS" if rule_result.passed else "FAIL"
        print(f"[{status}] {rule_result.name}: {rule_result.detail}")

    print(f"Overall Data Quality Result: {'PASS' if overall_passed else 'FAIL'}")
    return 0 if overall_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
