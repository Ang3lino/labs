from __future__ import annotations

import argparse
import json

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Register and inspect SageMaker Model Registry entries for Lab 02")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--model-package-group", required=True)
    parser.add_argument("--model-data-url", required=True, help="S3 model.tar.gz or model artifact URL")
    parser.add_argument("--inference-image", required=True, help="Container image URI for inference")
    parser.add_argument("--approve", action="store_true", help="Approve the newly created model package")
    return parser


def _ensure_model_package_group(sm_client: boto3.client, group_name: str) -> None:
    try:
        sm_client.describe_model_package_group(ModelPackageGroupName=group_name)
    except sm_client.exceptions.ResourceNotFound:
        sm_client.create_model_package_group(
            ModelPackageGroupName=group_name,
            ModelPackageGroupDescription="Lab 02 model registry group",
        )


def _register_model(
    sm_client: boto3.client,
    group_name: str,
    model_data_url: str,
    inference_image: str,
) -> str:
    response = sm_client.create_model_package(
        ModelPackageGroupName=group_name,
        ModelApprovalStatus="PendingManualApproval",
        InferenceSpecification={
            "Containers": [
                {
                    "Image": inference_image,
                    "ModelDataUrl": model_data_url,
                }
            ],
            "SupportedContentTypes": ["text/csv"],
            "SupportedResponseMIMETypes": ["application/json"],
        },
    )
    return response["ModelPackageArn"]


def _list_versions(sm_client: boto3.client, group_name: str) -> list[dict[str, str]]:
    paginator = sm_client.get_paginator("list_model_packages")
    versions: list[dict[str, str]] = []
    for page in paginator.paginate(ModelPackageGroupName=group_name, SortBy="CreationTime", SortOrder="Descending"):
        for package in page.get("ModelPackageSummaryList", []):
            versions.append(
                {
                    "ModelPackageArn": package.get("ModelPackageArn", ""),
                    "ModelPackageVersion": str(package.get("ModelPackageVersion", "")),
                    "ModelApprovalStatus": package.get("ModelApprovalStatus", ""),
                }
            )
    return versions


def main() -> int:
    args = _build_parser().parse_args()
    sm_client = boto3.client("sagemaker", region_name=args.region)

    _ensure_model_package_group(sm_client, args.model_package_group)
    package_arn = _register_model(
        sm_client,
        group_name=args.model_package_group,
        model_data_url=args.model_data_url,
        inference_image=args.inference_image,
    )

    if args.approve:
        sm_client.update_model_package(
            ModelPackageArn=package_arn,
            ModelApprovalStatus="Approved",
        )

    description = sm_client.describe_model_package(ModelPackageName=package_arn)
    versions = _list_versions(sm_client, args.model_package_group)

    print(f"Registered model package: {package_arn}")
    print("Model package description:")
    print(json.dumps(description, indent=2, default=str))
    print("Model versions in package group:")
    print(json.dumps(versions, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
