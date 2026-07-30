from __future__ import annotations

import json

import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
import pulumi_kubernetes as k8s


# ponytail: Pulumi for EKS because Python-native IaC is nicer for dynamic K8s config than HCL
config = pulumi.Config()
aws_region = aws.config.region or config.get("awsRegion") or "us-east-1"
cluster_name = config.get("clusterName") or "mle-lab-04-eks"
container_image = config.get("containerImage") or "123456789012.dkr.ecr.us-east-1.amazonaws.com/mle-lab-04-serve:latest"

vpc = aws.ec2.get_vpc(default=True)
subnets = aws.ec2.get_subnets(filters=[{"name": "vpc-id", "values": [vpc.id]}])

cluster_service_role = aws.iam.Role(
    "mleLab04EksClusterRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "eks.amazonaws.com"},
                    "Effect": "Allow",
                }
            ],
        }
    ),
)

aws.iam.RolePolicyAttachment(
    "mleLab04EksClusterPolicyAttachment",
    role=cluster_service_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
)

node_role = aws.iam.Role(
    "mleLab04EksNodeRole",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Effect": "Allow",
                }
            ],
        }
    ),
)

aws.iam.RolePolicyAttachment(
    "mleLab04NodeWorkerPolicyAttachment",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
)
aws.iam.RolePolicyAttachment(
    "mleLab04NodeCniPolicyAttachment",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
)
aws.iam.RolePolicyAttachment(
    "mleLab04NodeEcrReadOnlyPolicyAttachment",
    role=node_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
)

cluster = eks.Cluster(
    "mleLab04EksCluster",
    name=cluster_name,
    version="1.30",
    instance_type="t3.medium",
    desired_capacity=1,
    min_size=1,
    max_size=2,
    vpc_id=vpc.id,
    subnet_ids=subnets.ids,
    create_oidc_provider=True,
    endpoint_private_access=False,
    endpoint_public_access=True,
    skip_default_node_group=False,
    instance_role=node_role,
    service_role=cluster_service_role,
    tags={"Lab": "04-deploy-serve", "Domain": "MLA-C01-D3"},
)

repository = aws.ecr.Repository(
    "mleLab04ServeRepo",
    name="mle-lab-04-serve",
    force_delete=True,
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(scan_on_push=True),
)

namespace = k8s.core.v1.Namespace(
    "mleLab04Namespace",
    metadata={"name": "mle-lab-04"},
    opts=pulumi.ResourceOptions(provider=cluster.provider),
)

labels = {"app": "fraud-serve"}

deployment = k8s.apps.v1.Deployment(
    "mleLab04Deployment",
    metadata={"namespace": namespace.metadata["name"], "name": "fraud-serve"},
    spec={
        "replicas": 2,
        "selector": {"matchLabels": labels},
        "template": {
            "metadata": {"labels": labels},
            "spec": {
                "containers": [
                    {
                        "name": "serve",
                        "image": container_image,
                        "ports": [{"containerPort": 8080}],
                        "resources": {
                            "requests": {"cpu": "250m", "memory": "512Mi"},
                            "limits": {"cpu": "1", "memory": "1Gi"},
                        },
                    }
                ]
            },
        },
    },
    opts=pulumi.ResourceOptions(provider=cluster.provider, depends_on=[namespace]),
)

service = k8s.core.v1.Service(
    "mleLab04Service",
    metadata={"namespace": namespace.metadata["name"], "name": "fraud-serve"},
    spec={
        "type": "LoadBalancer",
        "selector": labels,
        "ports": [{"port": 80, "targetPort": 8080, "protocol": "TCP"}],
    },
    opts=pulumi.ResourceOptions(provider=cluster.provider, depends_on=[deployment]),
)

k8s.autoscaling.v2.HorizontalPodAutoscaler(
    "mleLab04Hpa",
    metadata={"namespace": namespace.metadata["name"], "name": "fraud-serve-hpa"},
    spec={
        "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": "fraud-serve"},
        "minReplicas": 2,
        "maxReplicas": 10,
        "metrics": [
            {
                "type": "Resource",
                "resource": {
                    "name": "cpu",
                    "target": {"type": "Utilization", "averageUtilization": 70},
                },
            }
        ],
    },
    opts=pulumi.ResourceOptions(provider=cluster.provider, depends_on=[deployment]),
)

pulumi.export("region", aws_region)
pulumi.export("clusterName", cluster.eks_cluster.name)
pulumi.export("kubeconfig", cluster.kubeconfig)
pulumi.export("ecrRepositoryUrl", repository.repository_url)
pulumi.export(
    "serviceHostname",
    service.status.apply(
        lambda value: value.get("load_balancer", {})
        .get("ingress", [{}])[0]
        .get("hostname", "pending")
        if isinstance(value, dict)
        else "pending"
    ),
)
