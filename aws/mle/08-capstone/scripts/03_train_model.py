from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.tuner import ContinuousParameter, HyperparameterTuner


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Lab 08 consolidated model training + HPO + registry")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--training-image-uri", default="763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.2-cpu-py310-ubuntu20.04-sagemaker")
    parser.add_argument("--entry-point", default="train.py")
    parser.add_argument("--source-dir", default="src")
    parser.add_argument("--instance-type", default="ml.m5.large")
    parser.add_argument("--model-package-group-name", default="mle-lab-08-fraud-models")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _build_training_input(bucket_name: str) -> dict[str, TrainingInput]:
    return {
        "train": TrainingInput(s3_data=f"s3://{bucket_name}/processed/"),
        "validation": TrainingInput(s3_data=f"s3://{bucket_name}/processed/"),
    }


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()

    model_bucket_name = str(outputs["modelBucketName"])
    sagemaker_role_arn = str(outputs["sagemakerRoleArn"])

    boto_session = boto3.Session(region_name=args.region)
    sm_session = sagemaker.Session(boto_session=boto_session)
    sm_client = boto_session.client("sagemaker")

    estimator = Estimator(
        image_uri=args.training_image_uri,
        role=sagemaker_role_arn,
        instance_count=1,
        instance_type=args.instance_type,
        output_path=f"s3://{model_bucket_name}/training-output/",
        sagemaker_session=sm_session,
        hyperparameters={"epochs": 10, "learning-rate": 0.001},
        entry_point=args.entry_point,
        source_dir=args.source_dir,
    )

    tuner = HyperparameterTuner(
        estimator=estimator,
        objective_metric_name="validation:f1",
        objective_type="Maximize",
        hyperparameter_ranges={
            "learning-rate": ContinuousParameter(1e-4, 1e-1, scaling_type="Logarithmic"),
        },
        max_jobs=5,
        max_parallel_jobs=2,
        strategy="Bayesian",
    )

    training_inputs = _build_training_input(str(outputs["dataBucketName"]))
    tuner.fit(training_inputs, wait=False)
    tuning_job_name = tuner.latest_tuning_job.name

    best_training_job_name = sm_client.describe_hyper_parameter_tuning_job(HyperParameterTuningJobName=tuning_job_name)[
        "BestTrainingJob"
    ]["TrainingJobName"]

    best_job_description = sm_client.describe_training_job(TrainingJobName=best_training_job_name)
    model_data_url = str(best_job_description["ModelArtifacts"]["S3ModelArtifacts"])

    sm_client.create_model_package(
        ModelPackageGroupName=args.model_package_group_name,
        ModelPackageDescription="Lab 08 capstone best model from Bayesian HPO",
        InferenceSpecification={
            "Containers": [{"Image": args.training_image_uri, "ModelDataUrl": model_data_url}],
            "SupportedContentTypes": ["text/csv"],
            "SupportedResponseMIMETypes": ["application/json"],
        },
        ModelApprovalStatus="PendingManualApproval",
    )

    print(f"Tuning job started: {tuning_job_name}")
    print(f"Best training job: {best_training_job_name}")
    print(f"Registered model package group: {args.model_package_group_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
