variable "region" {
  type        = string
  description = "AWS region for Lab 06"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project prefix for Lab 06 resources"
  default     = "mle-lab-06"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for Lab 06 VPC"
  default     = "10.0.0.0/16"
}
