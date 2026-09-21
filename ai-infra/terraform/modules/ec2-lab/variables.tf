variable "name" {
  description = "Unique name for this lab instance — used as a prefix for all resources."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.2xlarge"
}

variable "ami_id" {
  description = "AMI to use. Defaults to latest Ubuntu 24.04 LTS (us-east-1)."
  type        = string
  default     = "ami-025d99823a4caad37"
}

variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC to deploy into. Uses the default VPC if left empty."
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "Subnet to deploy into. Uses the first default subnet if left empty."
  type        = string
  default     = ""
}

variable "public_key_path" {
  description = "Path to the SSH public key to install on the instance."
  type        = string
  default     = "~/.ssh/ai-infra.pub"
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed SSH access."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_app_ports" {
  description = "TCP ports to open for application traffic (e.g. 8000 for vLLM)."
  type        = list(number)
  default     = [8000]
}

variable "root_volume_gb" {
  description = "Root EBS volume size in GiB."
  type        = number
  default     = 60
}

variable "extra_packages" {
  description = "Extra apt packages to install during bootstrap."
  type        = list(string)
  default     = []
}

variable "bootstrap_script" {
  description = "Additional shell commands to run at the end of user_data."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources."
  type        = map(string)
  default     = {}
}
