from __future__ import annotations

import argparse
import json
from datetime import datetime

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create CodePipeline for Lab 05 MLOps flow")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--pipeline-name", default="mle-lab-05-mlops-codepipeline")
    parser.add_argument("--pipeline-role-arn", required=True)
    parser.add_argument("--artifact-bucket", required=True)
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--source-key", default="source/source.zip")
    parser.add_argument("--codebuild-project-name", required=True)
    parser.add_argument("--codedeploy-application", required=True)
    parser.add_argument("--codedeploy-deployment-group", required=True)
    parser.add_argument("--create", action="store_true", help="Create the pipeline")
    return parser


def _pipeline_definition(args: argparse.Namespace) -> dict[str, object]:
    return {
        "name": args.pipeline_name,
        "roleArn": args.pipeline_role_arn,
        "artifactStore": {
            "type": "S3",
            "location": args.artifact_bucket,
        },
        "stages": [
            {
                "name": "Source",
                "actions": [
                    {
                        "name": "S3Source",
                        "actionTypeId": {
                            "category": "Source",
                            "owner": "AWS",
                            "provider": "S3",
                            "version": "1",
                        },
                        "runOrder": 1,
                        "configuration": {
                            "S3Bucket": args.source_bucket,
                            "S3ObjectKey": args.source_key,
                            "PollForSourceChanges": "true",
                        },
                        "outputArtifacts": [{"name": "SourceArtifact"}],
                        "inputArtifacts": [],
                    }
                ],
            },
            {
                "name": "Build",
                "actions": [
                    {
                        "name": "CodeBuildValidation",
                        "actionTypeId": {
                            "category": "Build",
                            "owner": "AWS",
                            "provider": "CodeBuild",
                            "version": "1",
                        },
                        "runOrder": 1,
                        "configuration": {
                            "ProjectName": args.codebuild_project_name,
                        },
                        "inputArtifacts": [{"name": "SourceArtifact"}],
                        "outputArtifacts": [{"name": "BuildArtifact"}],
                    }
                ],
            },
            {
                "name": "Deploy",
                "actions": [
                    {
                        "name": "CodeDeployBlueGreen",
                        "actionTypeId": {
                            "category": "Deploy",
                            "owner": "AWS",
                            "provider": "CodeDeploy",
                            "version": "1",
                        },
                        "runOrder": 1,
                        "configuration": {
                            "ApplicationName": args.codedeploy_application,
                            "DeploymentGroupName": args.codedeploy_deployment_group,
                        },
                        "inputArtifacts": [{"name": "BuildArtifact"}],
                        "outputArtifacts": [],
                    }
                ],
            },
        ],
        "version": 1,
    }


def main() -> int:
    args = _build_parser().parse_args()
    codepipeline_client = boto3.client("codepipeline", region_name=args.region)
    pipeline_declaration = _pipeline_definition(args)

    print("Pipeline declaration:")
    print(json.dumps(pipeline_declaration, indent=2))

    if args.create:
        response = codepipeline_client.create_pipeline(pipeline={**pipeline_declaration, "metadata": {}})
        metadata = response.get("pipeline", {}).get("metadata", {})
        pipeline_arn = metadata.get("pipelineArn", "")
        print(f"Created pipeline ARN: {pipeline_arn}")
    else:
        account_id = boto3.client("sts", region_name=args.region).get_caller_identity().get("Account", "")
        pipeline_arn = f"arn:aws:codepipeline:{args.region}:{account_id}:{args.pipeline_name}"
        print(f"Planned pipeline ARN: {pipeline_arn}")

    stage_names = [stage["name"] for stage in pipeline_declaration["stages"]]
    print(f"Stages: {stage_names}")
    print(f"Generated at: {datetime.utcnow().isoformat()}Z")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
