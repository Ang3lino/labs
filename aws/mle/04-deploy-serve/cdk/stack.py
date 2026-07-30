from __future__ import annotations

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct


class DeployServeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        execution_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        )
        execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
        )
        execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly")
        )

        model = sagemaker.CfnModel(
            self,
            "FraudRealtimeModel",
            execution_role_arn=execution_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/mle-lab-04-serve:latest",
                environment={
                    "MODEL_S3_URI": "s3://replace-with-artifact-bucket/lab-02/model/model.tar.gz",
                },
            ),
            model_name=f"mle-lab-04-fraud-model-{self.account}-{self.region}",
        )

        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "FraudEndpointConfig",
            endpoint_config_name=f"mle-lab-04-fraud-config-{self.account}-{self.region}",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    initial_instance_count=1,
                    instance_type="ml.m5.large",
                    model_name=model.model_name,
                    variant_name="AllTraffic",
                    initial_variant_weight=1.0,
                )
            ],
        )
        endpoint_config.add_dependency(model)

        endpoint = sagemaker.CfnEndpoint(
            self,
            "FraudRealtimeEndpoint",
            endpoint_name=f"mle-lab-04-fraud-endpoint-{self.account}-{self.region}",
            endpoint_config_name=endpoint_config.endpoint_config_name,
        )
        endpoint.add_dependency(endpoint_config)

        scalable_target = appscaling.CfnScalableTarget(
            self,
            "SageMakerVariantScalableTarget",
            max_capacity=8,
            min_capacity=1,
            resource_id=f"endpoint/{endpoint.endpoint_name}/variant/AllTraffic",
            role_arn=execution_role.role_arn,
            scalable_dimension="sagemaker:variant:DesiredInstanceCount",
            service_namespace="sagemaker",
        )
        scalable_target.add_dependency(endpoint)

        scaling_policy = appscaling.CfnScalingPolicy(
            self,
            "SageMakerTargetTrackingPolicy",
            policy_name="mle-lab-04-target-tracking",
            policy_type="TargetTrackingScaling",
            resource_id=scalable_target.resource_id,
            scalable_dimension="sagemaker:variant:DesiredInstanceCount",
            service_namespace="sagemaker",
            target_tracking_scaling_policy_configuration=appscaling.CfnScalingPolicy.TargetTrackingScalingPolicyConfigurationProperty(
                predefined_metric_specification=appscaling.CfnScalingPolicy.PredefinedMetricSpecificationProperty(
                    predefined_metric_type="SageMakerVariantInvocationsPerInstance"
                ),
                target_value=70.0,
                scale_in_cooldown=300,
                scale_out_cooldown=120,
            ),
        )
        scaling_policy.add_dependency(scalable_target)

        CfnOutput(self, "SageMakerExecutionRoleArn", value=execution_role.role_arn)
        CfnOutput(self, "EndpointName", value=endpoint.endpoint_name)
