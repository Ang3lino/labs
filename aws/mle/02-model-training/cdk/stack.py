from __future__ import annotations

from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct


# ponytail: CDK for SageMaker because exam tests CDK+SageMaker integration (Domain 3.2)
class ModelTrainingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        artifact_bucket = s3.Bucket(
            self,
            "ModelArtifactBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        sagemaker_execution_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        )
        sagemaker_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
        )
        artifact_bucket.grant_read_write(sagemaker_execution_role)

        model_package_group = sagemaker.CfnModelPackageGroup(
            self,
            "FraudModelPackageGroup",
            model_package_group_name=f"mle-lab-02-fraud-models-{self.account}-{self.region}",
            model_package_group_description="Model group for Lab 02 fraud detection training models",
        )

        CfnOutput(self, "ModelArtifactBucketName", value=artifact_bucket.bucket_name)
        CfnOutput(self, "SageMakerExecutionRoleArn", value=sagemaker_execution_role.role_arn)
        CfnOutput(self, "ModelPackageGroupName", value=model_package_group.model_package_group_name or "")
