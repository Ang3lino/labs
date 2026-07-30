variable "region" {
  description = "AWS region for Lab 01 resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "mle-lab-01"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}
