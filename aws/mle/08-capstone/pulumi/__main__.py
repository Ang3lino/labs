from __future__ import annotations

import json

import pulumi
import pulumi_aws as aws


# ponytail: Pulumi for the capstone because it shows Python-native IaC for the whole stack — best interview demo
config = pulumi.Config()
project_tag = "08-capstone"

aws_region = aws.config.region or config.get("awsRegion") or "us-east-1"
base_name = config.get("baseName") or "mle-lab-08-capstone"
vpc_cidr = config.get("vpcCidr") or "10.80.0.0/16"
public_subnet_1_cidr = config.get("publicSubnet1Cidr") or "10.80.1.0/24"
public_subnet_2_cidr = config.get("publicSubnet2Cidr") or "10.80.2.0/24"
private_subnet_1_cidr = config.get("privateSubnet1Cidr") or "10.80.11.0/24"
private_subnet_2_cidr = config.get("privateSubnet2Cidr") or "10.80.12.0/24"
az1 = config.get("availabilityZone1") or f"{aws_region}a"
az2 = config.get("availabilityZone2") or f"{aws_region}b"

tags = {
    "Lab": project_tag,
    "Project": base_name,
    "DomainCoverage": "MLA-C01-D1-D2-D3-D4",
}

kms_key = aws.kms.Key(
    "capstoneKmsKey",
    description="KMS key for Lab 08 capstone encryption",
    deletion_window_in_days=7,
    enable_key_rotation=True,
    tags=tags,
)

kms_alias = aws.kms.Alias(
    "capstoneKmsAlias",
    target_key_id=kms_key.key_id,
    name=f"alias/{base_name}-kms",
)

data_bucket = aws.s3.BucketV2(
    "capstoneDataBucket",
    bucket_prefix=f"{base_name}-data-",
    force_destroy=True,
    tags=tags,
)

model_bucket = aws.s3.BucketV2(
    "capstoneModelBucket",
    bucket_prefix=f"{base_name}-models-",
    force_destroy=True,
    tags=tags,
)

for logical_name, bucket in (("data", data_bucket), ("model", model_bucket)):
    aws.s3.BucketServerSideEncryptionConfigurationV2(
        f"capstone{logical_name.title()}BucketEncryption",
        bucket=bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="aws:kms",
                    kms_master_key_id=kms_key.arn,
                ),
                bucket_key_enabled=True,
            )
        ],
    )
    aws.s3.BucketVersioningV2(
        f"capstone{logical_name.title()}BucketVersioning",
        bucket=bucket.id,
        versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(status="Enabled"),
    )

assume_role_policy = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": [
                        "sagemaker.amazonaws.com",
                        "glue.amazonaws.com",
                        "lambda.amazonaws.com",
                        "events.amazonaws.com",
                    ]
                },
            }
        ],
    }
)

sagemaker_role = aws.iam.Role(
    "capstoneSageMakerRole",
    assume_role_policy=assume_role_policy,
    tags=tags,
)

glue_role = aws.iam.Role(
    "capstoneGlueRole",
    assume_role_policy=assume_role_policy,
    tags=tags,
)

lambda_role = aws.iam.Role(
    "capstoneLambdaRole",
    assume_role_policy=assume_role_policy,
    tags=tags,
)

for role_name, role in (
    ("SageMaker", sagemaker_role),
    ("Glue", glue_role),
    ("Lambda", lambda_role),
):
    aws.iam.RolePolicyAttachment(
        f"capstone{role_name}BasicExecution",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

aws.iam.RolePolicyAttachment(
    "capstoneSageMakerManagedPolicy",
    role=sagemaker_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
)
aws.iam.RolePolicyAttachment(
    "capstoneGlueManagedPolicy",
    role=glue_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
)

vpc = aws.ec2.Vpc(
    "capstoneVpc",
    cidr_block=vpc_cidr,
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={**tags, "Name": f"{base_name}-vpc"},
)

internet_gateway = aws.ec2.InternetGateway(
    "capstoneIgw",
    vpc_id=vpc.id,
    tags={**tags, "Name": f"{base_name}-igw"},
)

public_subnet_1 = aws.ec2.Subnet(
    "capstonePublicSubnet1",
    vpc_id=vpc.id,
    cidr_block=public_subnet_1_cidr,
    availability_zone=az1,
    map_public_ip_on_launch=True,
    tags={**tags, "Tier": "public", "Name": f"{base_name}-public-a"},
)

public_subnet_2 = aws.ec2.Subnet(
    "capstonePublicSubnet2",
    vpc_id=vpc.id,
    cidr_block=public_subnet_2_cidr,
    availability_zone=az2,
    map_public_ip_on_launch=True,
    tags={**tags, "Tier": "public", "Name": f"{base_name}-public-b"},
)

private_subnet_1 = aws.ec2.Subnet(
    "capstonePrivateSubnet1",
    vpc_id=vpc.id,
    cidr_block=private_subnet_1_cidr,
    availability_zone=az1,
    map_public_ip_on_launch=False,
    tags={**tags, "Tier": "private", "Name": f"{base_name}-private-a"},
)

private_subnet_2 = aws.ec2.Subnet(
    "capstonePrivateSubnet2",
    vpc_id=vpc.id,
    cidr_block=private_subnet_2_cidr,
    availability_zone=az2,
    map_public_ip_on_launch=False,
    tags={**tags, "Tier": "private", "Name": f"{base_name}-private-b"},
)

public_route_table = aws.ec2.RouteTable(
    "capstonePublicRouteTable",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=internet_gateway.id)],
    tags={**tags, "Name": f"{base_name}-public-rt"},
)

aws.ec2.RouteTableAssociation(
    "capstonePublicAssoc1",
    route_table_id=public_route_table.id,
    subnet_id=public_subnet_1.id,
)

aws.ec2.RouteTableAssociation(
    "capstonePublicAssoc2",
    route_table_id=public_route_table.id,
    subnet_id=public_subnet_2.id,
)

private_route_table = aws.ec2.RouteTable(
    "capstonePrivateRouteTable",
    vpc_id=vpc.id,
    tags={**tags, "Name": f"{base_name}-private-rt"},
)

aws.ec2.RouteTableAssociation(
    "capstonePrivateAssoc1",
    route_table_id=private_route_table.id,
    subnet_id=private_subnet_1.id,
)

aws.ec2.RouteTableAssociation(
    "capstonePrivateAssoc2",
    route_table_id=private_route_table.id,
    subnet_id=private_subnet_2.id,
)

endpoint_security_group = aws.ec2.SecurityGroup(
    "capstoneEndpointSecurityGroup",
    vpc_id=vpc.id,
    description="Interface endpoint SG for capstone",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=[vpc_cidr],
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
    tags=tags,
)

s3_endpoint = aws.ec2.VpcEndpoint(
    "capstoneS3GatewayEndpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{aws_region}.s3",
    vpc_endpoint_type="Gateway",
    route_table_ids=[public_route_table.id, private_route_table.id],
    tags=tags,
)

sagemaker_api_endpoint = aws.ec2.VpcEndpoint(
    "capstoneSageMakerApiEndpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{aws_region}.sagemaker.api",
    vpc_endpoint_type="Interface",
    subnet_ids=[private_subnet_1.id, private_subnet_2.id],
    private_dns_enabled=True,
    security_group_ids=[endpoint_security_group.id],
    tags=tags,
)

sagemaker_runtime_endpoint = aws.ec2.VpcEndpoint(
    "capstoneSageMakerRuntimeEndpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{aws_region}.sagemaker.runtime",
    vpc_endpoint_type="Interface",
    subnet_ids=[private_subnet_1.id, private_subnet_2.id],
    private_dns_enabled=True,
    security_group_ids=[endpoint_security_group.id],
    tags=tags,
)

dashboard_body = pulumi.Output.json_dumps(
    {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Capstone Endpoint Invocations",
                    "metrics": [["AWS/SageMaker", "Invocations", "EndpointName", "capstone-fraud-endpoint"]],
                    "region": aws_region,
                    "view": "timeSeries",
                },
            },
            {
                "type": "metric",
                "x": 12,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Model Latency p95",
                    "metrics": [
                        ["AWS/SageMaker", "ModelLatency", "EndpointName", "capstone-fraud-endpoint", {"stat": "p95"}]
                    ],
                    "region": aws_region,
                    "view": "timeSeries",
                },
            },
        ]
    }
)

cloudwatch_dashboard = aws.cloudwatch.Dashboard(
    "capstoneMonitoringDashboard",
    dashboard_name=f"{base_name}-dashboard",
    dashboard_body=dashboard_body,
)

event_rule = aws.cloudwatch.EventRule(
    "capstoneRetrainingRule",
    description="Trigger retraining flow on new raw data objects",
    event_pattern=data_bucket.bucket.apply(
        lambda bucket_name: json.dumps(
            {
                "source": ["aws.s3"],
                "detail-type": ["Object Created"],
                "detail": {
                    "bucket": {"name": [bucket_name]},
                    "object": {"key": [{"prefix": "raw/"}]},
                },
            }
        )
    ),
)

pulumi.export("region", aws_region)
pulumi.export("dataBucketName", data_bucket.bucket)
pulumi.export("modelBucketName", model_bucket.bucket)
pulumi.export("sagemakerRoleArn", sagemaker_role.arn)
pulumi.export("glueRoleArn", glue_role.arn)
pulumi.export("lambdaRoleArn", lambda_role.arn)
pulumi.export("kmsKeyArn", kms_key.arn)
pulumi.export("kmsAliasName", kms_alias.name)
pulumi.export("vpcId", vpc.id)
pulumi.export("publicSubnetIds", pulumi.Output.all(public_subnet_1.id, public_subnet_2.id))
pulumi.export("privateSubnetIds", pulumi.Output.all(private_subnet_1.id, private_subnet_2.id))
pulumi.export("s3VpcEndpointId", s3_endpoint.id)
pulumi.export("sagemakerApiVpcEndpointId", sagemaker_api_endpoint.id)
pulumi.export("sagemakerRuntimeVpcEndpointId", sagemaker_runtime_endpoint.id)
pulumi.export("cloudwatchDashboardName", cloudwatch_dashboard.dashboard_name)
pulumi.export("retrainingEventRuleArn", event_rule.arn)
