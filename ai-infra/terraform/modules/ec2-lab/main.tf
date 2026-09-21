data "aws_vpc" "target" {
  id      = var.vpc_id != "" ? var.vpc_id : null
  default = var.vpc_id == "" ? true : null
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.target.id]
  }
  filter {
    name   = "defaultForAz"
    values = ["true"]
  }
}

locals {
  subnet_id = var.subnet_id != "" ? var.subnet_id : tolist(data.aws_subnets.default.ids)[0]

  base_tags = merge(
    { Name = var.name, ManagedBy = "terraform", Lab = var.name },
    var.tags
  )

  extra_packages_str = length(var.extra_packages) > 0 ? join(" ", var.extra_packages) : ""

  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail
    exec > /var/log/bootstrap.log 2>&1

    export DEBIAN_FRONTEND=noninteractive

    apt-get update -qq
    apt-get install -y -qq \
      curl git unzip jq htop \
      ca-certificates gnupg lsb-release \
      ${local.extra_packages_str}

    # Docker
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io
    systemctl enable --now docker
    usermod -aG docker ubuntu

    # kubectl
    curl -fsSL "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
      -o /usr/local/bin/kubectl
    chmod +x /usr/local/bin/kubectl

    # Clone lab repo
    git clone https://github.com/Ang3lino/labs.git /home/ubuntu/labs
    chown -R ubuntu:ubuntu /home/ubuntu/labs

    ${var.bootstrap_script}

    echo "Bootstrap complete" > /var/log/bootstrap.done
  EOF
}

resource "aws_key_pair" "lab" {
  key_name   = var.name
  public_key = file(pathexpand(var.public_key_path))
  tags       = local.base_tags
}

resource "aws_security_group" "lab" {
  name        = var.name
  description = "Lab ${var.name} - SSH and app ports"
  vpc_id      = data.aws_vpc.target.id
  tags        = local.base_tags

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  dynamic "ingress" {
    for_each = var.allowed_app_ports
    content {
      description = "App port ${ingress.value}"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "lab" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = local.subnet_id
  key_name                    = aws_key_pair.lab.key_name
  vpc_security_group_ids      = [aws_security_group.lab.id]
  associate_public_ip_address = true
  user_data                   = local.user_data
  user_data_replace_on_change = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_gb
    delete_on_termination = true
  }

  tags = local.base_tags
}
