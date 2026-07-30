# ponytail: GNU Make, not cross-platform — user likely has it via Git Bash or WSL on Windows

LABS := 01-data-pipeline 02-model-training 03-bedrock-ai-services 04-deploy-serve 05-mlops-pipeline 06-monitor-secure 07-book-analysis 08-capstone
DOWNLOAD_TARGETS := download-01 download-02 download-03 download-04 download-05 download-06 download-07 download-08
CLEANUP_TARGETS := cleanup-01 cleanup-02 cleanup-03 cleanup-04 cleanup-05 cleanup-06 cleanup-07 cleanup-08
TEARDOWN_TARGETS := teardown-01 teardown-02 teardown-03 teardown-04 teardown-05 teardown-06 teardown-07 teardown-08

.PHONY: setup \
	$(DOWNLOAD_TARGETS) \
	$(CLEANUP_TARGETS) \
	$(TEARDOWN_TARGETS) \
	download-all cleanup-all

setup:
	python -m venv .venv
	pip install -e ".[dev]"

download-01:
	python 01-data-pipeline/datasets.py --download

download-02:
	python 02-model-training/datasets.py --download

download-03:
	python 03-bedrock-ai-services/datasets.py --download

download-04:
	python 04-deploy-serve/datasets.py --download

download-05:
	python 05-mlops-pipeline/datasets.py --download

download-06:
	python 06-monitor-secure/datasets.py --download

download-07:
	python 07-book-analysis/datasets.py --download

download-08:
	python 08-capstone/datasets.py --download

cleanup-01:
	python 01-data-pipeline/datasets.py --cleanup

cleanup-02:
	python 02-model-training/datasets.py --cleanup

cleanup-03:
	python 03-bedrock-ai-services/datasets.py --cleanup

cleanup-04:
	python 04-deploy-serve/datasets.py --cleanup

cleanup-05:
	python 05-mlops-pipeline/datasets.py --cleanup

cleanup-06:
	python 06-monitor-secure/datasets.py --cleanup

cleanup-07:
	python 07-book-analysis/datasets.py --cleanup

cleanup-08:
	python 08-capstone/datasets.py --cleanup

download-all: $(DOWNLOAD_TARGETS)

cleanup-all: $(CLEANUP_TARGETS)

teardown-01:
	cd 01-data-pipeline/terraform && terraform destroy -auto-approve

teardown-02:
	cd 02-model-training/cdk && cdk destroy --force

teardown-03:
	cd 03-bedrock-ai-services/terraform && terraform destroy -auto-approve

teardown-04:
	cd 04-deploy-serve/pulumi && pulumi destroy --yes
	cd 04-deploy-serve/cdk && cdk destroy --force

teardown-05:
	cd 05-mlops-pipeline/cdk && cdk destroy --force

teardown-06:
	cd 06-monitor-secure/terraform && terraform destroy -auto-approve

teardown-07:
	cd 07-book-analysis/terraform && terraform destroy -auto-approve

teardown-08:
	cd 08-capstone/pulumi && pulumi destroy --yes
