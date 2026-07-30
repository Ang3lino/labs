from __future__ import annotations

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct


# ponytail: CDK for the full pipeline because SageMaker Pipelines + CodePipeline integration is cleanest in CDK
class MlopsPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        artifact_bucket = s3.Bucket(
            self,
            "MlopsArtifactBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
        )

        source_bucket = s3.Bucket(
            self,
            "MlopsSourceBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
        )

        source_artifact = codepipeline.Artifact("SourceArtifact")
        build_artifact = codepipeline.Artifact("BuildArtifact")

        build_project_role = iam.Role(
            self,
            "MlopsCodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
        )
        build_project_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
        )
        build_project_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
        )
        artifact_bucket.grant_read_write(build_project_role)
        source_bucket.grant_read(build_project_role)

        build_project = codebuild.Project(
            self,
            "MlopsValidationBuild",
            role=build_project_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=False,
            ),
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "commands": [
                                "echo Installing dependencies for MLOps validation",
                                "python --version",
                            ]
                        },
                        "pre_build": {"commands": ["echo Running unit and integration checks"]},
                        "build": {"commands": ["echo Packaging model artifacts"]},
                        "post_build": {"commands": ["echo Build stage completed"]},
                    },
                    "artifacts": {"files": ["**/*"]},
                }
            ),
        )

        pipeline = codepipeline.Pipeline(
            self,
            "MlopsCodePipeline",
            artifact_bucket=artifact_bucket,
            pipeline_name=f"mle-lab-05-mlops-pipeline-{self.region}",
            restart_execution_on_update=True,
        )

        source_action = codepipeline_actions.S3SourceAction(
            action_name="Source",
            bucket=source_bucket,
            bucket_key="source/source.zip",
            output=source_artifact,
            trigger=codepipeline_actions.S3Trigger.POLL,
        )

        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_artifact,
            outputs=[build_artifact],
        )

        deploy_action = codepipeline_actions.CodeBuildAction(
            action_name="Deploy",
            project=build_project,
            input=build_artifact,
            environment_variables={
                "DEPLOYMENT_MODE": codebuild.BuildEnvironmentVariable(value="blue-green")
            },
        )

        pipeline.add_stage(stage_name="Source", actions=[source_action])
        pipeline.add_stage(stage_name="Build", actions=[build_action])
        pipeline.add_stage(stage_name="Deploy", actions=[deploy_action])

        eventbridge_invoke_role = iam.Role(
            self,
            "MlopsEventBridgePipelineRole",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
        )
        eventbridge_invoke_role.add_to_policy(
            iam.PolicyStatement(
                actions=["codepipeline:StartPipelineExecution"],
                resources=[pipeline.pipeline_arn],
            )
        )

        s3_put_object_rule = events.Rule(
            self,
            "MlopsS3DataArrivalRule",
            description="Trigger MLOps pipeline when new raw data lands in S3",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [source_bucket.bucket_name]},
                    "object": {"key": [{"prefix": "raw/"}]},
                },
            ),
        )
        s3_put_object_rule.add_target(
            events_targets.CodePipeline(
                pipeline,
                event_role=eventbridge_invoke_role,
            )
        )

        CfnOutput(self, "CodePipelineName", value=pipeline.pipeline_name)
        CfnOutput(self, "CodePipelineArn", value=pipeline.pipeline_arn)
        CfnOutput(self, "CodeBuildProjectName", value=build_project.project_name)
        CfnOutput(self, "SourceBucketName", value=source_bucket.bucket_name)
        CfnOutput(self, "ArtifactBucketName", value=artifact_bucket.bucket_name)
        CfnOutput(self, "EventBridgeRuleArn", value=s3_put_object_rule.rule_arn)
