variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "ml-platform"
}

variable "node_instance_type" {
  description = "Instance type for EKS managed nodes"
  type        = string
  default     = "t3.medium"
}

variable "node_count" {
  description = "Desired node count for EKS managed node group"
  type        = number
  default     = 2

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 5
    error_message = "node_count must be between 1 and 5."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for lab VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "lab"
}
