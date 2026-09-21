# terraform/

Reusable Terraform infrastructure for ai-infra labs. Each lab gets its own
root config under `envs/`; shared logic lives in `modules/`.

## Structure

```
terraform/
├── modules/
│   └── ec2-lab/          # Reusable single-node EC2 module
│       ├── main.tf       # VPC lookup, SG, key pair, instance, user_data
│       ├── variables.tf  # All inputs with defaults
│       ├── outputs.tf    # IP, SSH command, bootstrap log hint
│       └── versions.tf   # Provider pins
└── envs/
    └── inf-01/           # INF-01 vLLM CPU PoC
        ├── main.tf       # Calls ec2-lab module, sets bootstrap_script
        ├── variables.tf
        └── outputs.tf
```

## Prerequisites

- Terraform >= 1.5 (`terraform version`)
- AWS CLI configured (`aws sts get-caller-identity`)
- SSH keypair at `~/.ssh/ai-infra` / `~/.ssh/ai-infra.pub`
  — generate with: `ssh-keygen -t ed25519 -f ~/.ssh/ai-infra -N ""`

## Usage

### 1. Deploy

```bash
cd terraform/envs/inf-01
terraform init
terraform apply
```

Terraform prints the SSH command and public IP on completion.

### 2. Wait for bootstrap

Bootstrap runs asynchronously via `user_data`. SSH in and tail the log:

```bash
ssh -i ~/.ssh/ai-infra ubuntu@<public_ip>
tail -f /var/log/bootstrap.log
# Done when: "Bootstrap complete" appears in /var/log/bootstrap.done
```

Bootstrap installs: `docker`, `git`, `kubectl`, `jq`, `htop`,
clones the repo to `/home/ubuntu/labs`, pulls the vLLM CPU image,
and pre-caches `facebook/opt-125m`.

### 3. Run the vLLM PoC

```bash
ssh -i ~/.ssh/ai-infra ubuntu@<public_ip>

docker run -d --name vllm-poc \
  --shm-size=1g \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-cpu:latest \
  vllm serve facebook/opt-125m \
    --port 8000 \
    --dtype float32 \
    --enforce-eager \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.4

# Wait for startup (~60s)
docker logs -f vllm-poc | grep -m1 "Application startup complete"
```

### 4. Test the OpenAI surface

From the EC2 instance:

```bash
bash ~/labs/ai-infra/inf-01/scripts/test-openai-surface.sh localhost:8000
```

Or from your local machine (port-forward over SSH):

```bash
ssh -i ~/.ssh/ai-infra -L 8000:localhost:8000 ubuntu@<public_ip> -N &
bash inf-01/scripts/test-openai-surface.sh localhost:8000
```

### 5. Tear down

```bash
cd terraform/envs/inf-01
terraform destroy
```

The instance costs ~$0.33/hr on-demand. Destroy when not in use.

## Reusing for another lab

1. Copy `envs/inf-01/` to `envs/<new-lab>/`
2. Change `name`, `allowed_app_ports`, `bootstrap_script`, and `tags`
3. Override `instance_type` for GPU workloads:
   - CPU PoC: `t3.2xlarge` ($0.33/hr)
   - Single L40S (exact hardware match): `g6e.xlarge` ($2.19/hr, spot $1.21/hr)
   - 4× L40S (closest to production node): `g6e.12xlarge` ($12.35/hr, spot $5.30/hr)

## Module inputs reference

| Variable | Default | Description |
| --- | --- | --- |
| `name` | required | Resource name prefix |
| `instance_type` | `t3.2xlarge` | EC2 instance type |
| `ami_id` | Ubuntu 24.04 us-east-1 | AMI ID |
| `region` | `us-east-1` | AWS region |
| `public_key_path` | `~/.ssh/ai-infra.pub` | SSH public key |
| `allowed_ssh_cidrs` | `0.0.0.0/0` | CIDR blocks for SSH |
| `allowed_app_ports` | `[8000]` | App TCP ports to open |
| `root_volume_gb` | `60` | Root EBS size (GiB) |
| `extra_packages` | `[]` | Extra apt packages |
| `bootstrap_script` | `""` | Shell commands appended to user_data |
| `tags` | `{}` | Extra resource tags |
