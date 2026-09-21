terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

module "ec2" {
  source = "../../modules/ec2-lab"

  name          = "inf-01-vllm-poc"
  instance_type = var.instance_type
  region        = var.region

  allowed_app_ports = [8000]
  root_volume_gb    = 80

  # Pull vLLM CPU image and pre-cache opt-125m during bootstrap so the
  # first docker run is instant.
  bootstrap_script = <<-EOF
    docker pull vllm/vllm-openai-cpu:latest
    docker run --rm \
      -e HF_HUB_CACHE=/home/ubuntu/.cache/huggingface \
      -v /home/ubuntu/.cache/huggingface:/home/ubuntu/.cache/huggingface \
      vllm/vllm-openai-cpu:latest \
      python3 -c "from huggingface_hub import snapshot_download; snapshot_download('facebook/opt-125m')"
    chown -R ubuntu:ubuntu /home/ubuntu/.cache
  EOF

  tags = {
    Epic = "EPIC-05"
    Story = "INF-01"
  }
}
