from __future__ import annotations

import argparse

import boto3


# ponytail: no ALB setup — just task def + service for the study lab
# ponytail: compared to EKS, ECS Fargate removes cluster node management at the cost of fewer K8s-native controls
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy fraud serving container to ECS Fargate")
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--cluster", required=True, help="ECS cluster name")
    parser.add_argument("--service", default="mle-lab-04-fargate-service", help="ECS service name")
    parser.add_argument("--task-family", default="mle-lab-04-fraud-task", help="Task definition family")
    parser.add_argument("--image-uri", required=True, help="ECR image URI")
    parser.add_argument("--subnet-ids", nargs="+", required=True, help="Subnets for awsvpc networking")
    parser.add_argument("--security-group-ids", nargs="+", required=True, help="Security groups for awsvpc networking")
    parser.add_argument("--execution-role-arn", required=True, help="ECS task execution role ARN")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    ecs = session.client("ecs")

    task_definition = ecs.register_task_definition(
        family=args.task_family,
        requiresCompatibilities=["FARGATE"],
        networkMode="awsvpc",
        cpu="512",
        memory="1024",
        executionRoleArn=args.execution_role_arn,
        containerDefinitions=[
            {
                "name": "fraud-model",
                "image": args.image_uri,
                "essential": True,
                "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
            }
        ],
    )

    task_definition_arn = task_definition["taskDefinition"]["taskDefinitionArn"]

    ecs.create_service(
        cluster=args.cluster,
        serviceName=args.service,
        taskDefinition=task_definition_arn,
        desiredCount=2,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": args.subnet_ids,
                "securityGroups": args.security_group_ids,
                "assignPublicIp": "ENABLED",
            }
        },
    )

    print(f"Created ECS Fargate service {args.service} with task {task_definition_arn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
