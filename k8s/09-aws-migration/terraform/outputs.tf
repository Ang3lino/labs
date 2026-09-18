output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "ecr_repository_urls" {
  description = "Map of repository names to ECR repository URLs"
  value = {
    for name, repo in aws_ecr_repository.repositories :
    name => repo.repository_url
  }
}

output "kubectl_config_command" {
  description = "Command to configure kubectl against this EKS cluster"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${var.region}"
}

output "region" {
  description = "AWS region in use"
  value       = var.region
}
