from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import boto3


@dataclass(frozen=True, slots=True)
class AuditCheck:
    name: str
    passed: bool
    details: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Lab 06 security audit checks")
    parser.add_argument("--region", default="us-east-1")
    return parser


def _is_overly_permissive(statement: dict[str, object]) -> bool:
    action = statement.get("Action")
    resource = statement.get("Resource")
    action_is_star = action == "*" or (isinstance(action, list) and "*" in action)
    resource_is_star = resource == "*" or (isinstance(resource, list) and "*" in resource)
    return action_is_star and resource_is_star


def _check_iam_policies(iam_client: "boto3.client") -> AuditCheck:
    offending_policies: list[str] = []
    policies = iam_client.list_policies(Scope="Local", OnlyAttached=False).get("Policies", [])
    for policy in policies:
        policy_arn = str(policy.get("Arn", ""))
        if not policy_arn:
            continue
        versions = iam_client.list_policy_versions(PolicyArn=policy_arn).get("Versions", [])
        default_version = next((version for version in versions if bool(version.get("IsDefaultVersion"))), None)
        if default_version is None:
            continue
        version_id = str(default_version.get("VersionId", ""))
        document = iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=version_id)["PolicyVersion"]["Document"]
        statements = document.get("Statement", [])
        statement_list = statements if isinstance(statements, list) else [statements]
        if any(_is_overly_permissive(statement) for statement in statement_list if isinstance(statement, dict)):
            offending_policies.append(policy_arn)

    return AuditCheck(
        name="IAM least-privilege policy check",
        passed=len(offending_policies) == 0,
        details="No wildcard Action+Resource policies found" if not offending_policies else json.dumps(offending_policies),
    )


def _check_sagemaker_vpc_endpoints(ec2_client: "boto3.client") -> AuditCheck:
    endpoints = ec2_client.describe_vpc_endpoints().get("VpcEndpoints", [])
    service_names = {str(endpoint.get("ServiceName", "")) for endpoint in endpoints}
    required = {"com.amazonaws.us-east-1.sagemaker.api", "com.amazonaws.us-east-1.sagemaker.runtime"}
    missing = sorted(required - service_names)
    return AuditCheck(
        name="VPC endpoint check for SageMaker",
        passed=not missing,
        details="All required SageMaker endpoints present" if not missing else f"Missing: {', '.join(missing)}",
    )


def _check_bucket_kms_encryption(s3_client: "boto3.client") -> AuditCheck:
    non_compliant: list[str] = []
    buckets = s3_client.list_buckets().get("Buckets", [])
    for bucket in buckets:
        bucket_name = str(bucket.get("Name", ""))
        if not bucket_name:
            continue
        try:
            encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            algorithms = {
                str(rule.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm", ""))
                for rule in rules
                if isinstance(rule, dict)
            }
            if "aws:kms" not in algorithms:
                non_compliant.append(bucket_name)
        except s3_client.exceptions.ClientError:
            non_compliant.append(bucket_name)

    return AuditCheck(
        name="S3 KMS encryption check",
        passed=len(non_compliant) == 0,
        details="All buckets have aws:kms encryption" if not non_compliant else json.dumps(non_compliant),
    )


def _check_sagemaker_execution_roles(iam_client: "boto3.client") -> AuditCheck:
    roles = iam_client.list_roles().get("Roles", [])
    execution_roles = [role for role in roles if "sagemaker" in str(role.get("RoleName", "")).lower()]
    mapped: list[dict[str, object]] = []
    for role in execution_roles:
        role_name = str(role.get("RoleName", ""))
        attached = iam_client.list_attached_role_policies(RoleName=role_name).get("AttachedPolicies", [])
        mapped.append({"role": role_name, "policies": [policy.get("PolicyName", "") for policy in attached]})

    return AuditCheck(
        name="SageMaker execution role inventory",
        passed=len(mapped) > 0,
        details=json.dumps(mapped, default=str),
    )


def main() -> int:
    args = _build_parser().parse_args()
    iam = boto3.client("iam", region_name=args.region)
    ec2 = boto3.client("ec2", region_name=args.region)
    s3 = boto3.client("s3", region_name=args.region)

    checks = [
        _check_iam_policies(iam),
        _check_sagemaker_vpc_endpoints(ec2),
        _check_bucket_kms_encryption(s3),
        _check_sagemaker_execution_roles(iam),
    ]

    print("Security audit report")
    print("=" * 80)
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.details}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
