output "vpc_id" {
  description = "VPC ID for Lab 06"
  value       = aws_vpc.main.id
}

output "private_subnet_id" {
  description = "Private subnet ID for SageMaker workloads"
  value       = aws_subnet.private.id
}

output "public_subnet_id" {
  description = "Public subnet ID for NAT gateway"
  value       = aws_subnet.public.id
}

output "kms_key_arn" {
  description = "KMS key ARN used for encryption"
  value       = aws_kms_key.lab06.arn
}

output "dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.monitoring.dashboard_name
}
