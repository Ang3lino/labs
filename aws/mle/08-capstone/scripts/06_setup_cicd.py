from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3
import sagemaker
from sagemaker.inputs import TrainingInput
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.pytorch import PyTorch
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.parameters import ParameterFloat, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep


SCRIPT_DIR = Path(__file__).resolve().parent
INFRA_OUTPUTS_PATH = SCRIPT_DIR / "infra_outputs.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Set up Lab 08 CI/CD and retraining triggers")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--pipeline-name", default="mle-lab-08-training-pipeline")
    parser.add_argument("--model-package-group", default="mle-lab-08-fraud-models")
    parser.add_argument("--event-rule-name", default="mle-lab-08-retrain-rule")
    parser.add_argument("--create", action="store_true")
    return parser


def _load_infra_outputs() -> dict[str, object]:
    if not INFRA_OUTPUTS_PATH.exists():
        raise FileNotFoundError(f"Missing infrastructure outputs: {INFRA_OUTPUTS_PATH}")
    return json.loads(INFRA_OUTPUTS_PATH.read_text(encoding="utf-8"))


def _build_pipeline(
    *,
    region: str,
    role_arn: str,
    data_bucket: str,
    pipeline_name: str,
    model_package_group: str,
) -> Pipeline:
    boto_session = boto3.Session(region_name=region)
    pipeline_session = PipelineSession(
        boto_session=boto_session,
        sagemaker_client=boto_session.client("sagemaker"),
    )

    processing_instance_type = ParameterString(name="ProcessingInstanceType", default_value="ml.m5.xlarge")
    training_instance_type = ParameterString(name="TrainingInstanceType", default_value="ml.m5.large")
    f1_threshold = ParameterFloat(name="F1Threshold", default_value=0.80)
    input_data_uri = ParameterString(name="InputDataUri", default_value=f"s3://{data_bucket}/processed/")

    process_step = ProcessingStep(
        name="ProcessData",
        processor=SKLearnProcessor(
            framework_version="1.2-1",
            role=role_arn,
            instance_count=1,
            instance_type=processing_instance_type,
            sagemaker_session=pipeline_session,
        ),
        inputs=[
            ProcessingInput(source=input_data_uri, destination="/opt/ml/processing/input"),
        ],
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
            ProcessingOutput(output_name="validation", source="/opt/ml/processing/validation"),
        ],
        code="preprocess.py",
    )

    estimator = PyTorch(
        entry_point="train.py",
        source_dir="src",
        role=role_arn,
        framework_version="2.2",
        py_version="py310",
        instance_count=1,
        instance_type=training_instance_type,
        sagemaker_session=pipeline_session,
    )
    train_step = TrainingStep(
        name="TrainModel",
        estimator=estimator,
        inputs={
            "train": TrainingInput(
                s3_data=process_step.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri
            ),
            "validation": TrainingInput(
                s3_data=process_step.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri
            ),
        },
    )

    evaluation_report = PropertyFile(name="EvaluationReport", output_name="evaluation", path="evaluation.json")
    evaluate_step = ProcessingStep(
        name="EvaluateModel",
        processor=SKLearnProcessor(
            framework_version="1.2-1",
            role=role_arn,
            instance_count=1,
            instance_type=processing_instance_type,
            sagemaker_session=pipeline_session,
        ),
        inputs=[
            ProcessingInput(source=train_step.properties.ModelArtifacts.S3ModelArtifacts, destination="/opt/ml/processing/model"),
            ProcessingInput(
                source=process_step.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri,
                destination="/opt/ml/processing/validation",
            ),
        ],
        outputs=[ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")],
        code="evaluate.py",
        property_files=[evaluation_report],
    )

    register_step = RegisterModel(
        name="RegisterModel",
        estimator=estimator,
        model_data=train_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["application/json"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=model_package_group,
        approval_status="PendingManualApproval",
    )

    gate_step = ConditionStep(
        name="GateOnF1",
        conditions=[
            ConditionGreaterThanOrEqualTo(
                left=JsonGet(
                    step_name=evaluate_step.name,
                    property_file=evaluation_report,
                    json_path="classification_metrics.f1.value",
                ),
                right=f1_threshold,
            )
        ],
        if_steps=[register_step],
        else_steps=[],
    )

    return Pipeline(
        name=pipeline_name,
        parameters=[input_data_uri, processing_instance_type, training_instance_type, f1_threshold],
        steps=[process_step, train_step, evaluate_step, gate_step],
        sagemaker_session=pipeline_session,
    )


def _create_event_rule(
    *,
    region: str,
    data_bucket_name: str,
    rule_name: str,
    pipeline_arn: str,
    role_arn: str,
) -> dict[str, object]:
    events = boto3.client("events", region_name=region)
    pattern = {
        "source": ["aws.s3"],
        "detail-type": ["Object Created"],
        "detail": {
            "bucket": {"name": [data_bucket_name]},
            "object": {"key": [{"prefix": "raw/"}]},
        },
    }
    rule_response = events.put_rule(
        Name=rule_name,
        EventPattern=json.dumps(pattern),
        State="ENABLED",
        Description="Lab 08 retraining trigger on new raw data",
    )
    target_response = events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "SageMakerPipelineTarget",
                "Arn": pipeline_arn,
                "RoleArn": role_arn,
            }
        ],
    )
    return {"rule": rule_response, "targets": target_response}


def main() -> int:
    args = _build_parser().parse_args()
    outputs = _load_infra_outputs()

    region = args.region
    role_arn = str(outputs["sagemakerRoleArn"])
    data_bucket = str(outputs["dataBucketName"])

    pipeline = _build_pipeline(
        region=region,
        role_arn=role_arn,
        data_bucket=data_bucket,
        pipeline_name=args.pipeline_name,
        model_package_group=args.model_package_group,
    )

    definition = json.loads(pipeline.definition())
    print("SageMaker Pipeline definition:")
    print(json.dumps(definition, indent=2))

    if not args.create:
        print("Dry mode: skipping pipeline upsert and EventBridge target creation")
        return 0

    upsert_response = pipeline.upsert(role_arn=role_arn)
    pipeline_arn = str(upsert_response.get("PipelineArn", ""))

    event_response = _create_event_rule(
        region=region,
        data_bucket_name=data_bucket,
        rule_name=args.event_rule_name,
        pipeline_arn=pipeline_arn,
        role_arn=role_arn,
    )

    print(f"Pipeline ARN: {pipeline_arn}")
    print("EventBridge response:")
    print(json.dumps(event_response, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
