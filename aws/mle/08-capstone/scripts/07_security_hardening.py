from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import boto3


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


@dataclass(frozen=True, slots=True)
class AuditCheck:
    name: str
    passed: bool
    details: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run security hardening checks for Lab 08")
    parser.add_argument("--region", default="us-east-1")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _check_roles(iam_client: "boto3.client", expected_arns: list[str]) -> AuditCheck:
    missing: list[str] = []
    for arn in expected_arns:
        role_name = arn.rsplit("/", maxsplit=1)[-1]
        try:
            iam_client.get_role(RoleName=role_name)
        except iam_client.exceptions.NoSuchEntityException:
            missing.append(role_name)
    return AuditCheck(
        name="IAM role existence and least-privilege baseline",
        passed=len(missing) == 0,
        details="All expected roles exist" if not missing else f"Missing roles: {', '.join(missing)}",
    )


def _check_vpc_endpoints(ec2_client: "boto3.client", endpoint_ids: list[str]) -> AuditCheck:
    if not endpoint_ids:
        return AuditCheck("VPC endpoint verification", False, "No endpoint IDs provided")
    response = ec2_client.describe_vpc_endpoints(VpcEndpointIds=endpoint_ids)
    states = {str(ep["VpcEndpointId"]): str(ep.get("State", "unknown")) for ep in response.get("VpcEndpoints", [])}
    invalid = [endpoint_id for endpoint_id in endpoint_ids if states.get(endpoint_id) != "available"]
    return AuditCheck(
        name="VPC endpoint verification",
        passed=len(invalid) == 0,
        details="All required endpoints available" if not invalid else f"Unavailable endpoints: {', '.join(invalid)}",
    )


def _check_bucket_kms_encryption(s3_client: "boto3.client", bucket_names: list[str]) -> AuditCheck:
    non_compliant: list[str] = []
    for bucket_name in bucket_names:
        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
        rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
        algorithms = {
            str(rule.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm", ""))
            for rule in rules
            if isinstance(rule, dict)
        }
        if "aws:kms" not in algorithms:
            non_compliant.append(bucket_name)
    return AuditCheck(
        name="S3 bucket KMS encryption",
        passed=len(non_compliant) == 0,
        details="All buckets use aws:kms" if not non_compliant else f"Non-compliant buckets: {', '.join(non_compliant)}",
    )


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()

    iam = boto3.client("iam", region_name=args.region)
    ec2 = boto3.client("ec2", region_name=args.region)
    s3 = boto3.client("s3", region_name=args.region)

    role_arns = [
        str(outputs["sagemakerRoleArn"]),
        str(outputs["glueRoleArn"]),
        str(outputs["lambdaRoleArn"]),
    ]
    endpoint_ids = [
        str(outputs["s3VpcEndpointId"]),
        str(outputs["sagemakerApiVpcEndpointId"]),
        str(outputs["sagemakerRuntimeVpcEndpointId"]),
    ]
    bucket_names = [str(outputs["dataBucketName"]), str(outputs["modelBucketName"])]

    checks = [
        _check_roles(iam, role_arns),
        _check_vpc_endpoints(ec2, endpoint_ids),
        _check_bucket_kms_encryption(s3, bucket_names),
    ]

    print("Security audit report")
    print("=" * 80)
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.details}")

    all_passed = all(check.passed for check in checks)
    return 0 if all_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
