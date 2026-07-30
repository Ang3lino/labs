from __future__ import annotations

import argparse
import json

import boto3
import sagemaker
from sagemaker.inputs import TrainingInput
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.parameters import ParameterFloat, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.step_collections import RegisterModel


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create SageMaker Pipeline for Lab 05")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--pipeline-name", default="mle-lab-05-mlops-pipeline")
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--model-package-group", default="mle-lab-05-models")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--create", action="store_true", help="Create or update pipeline in SageMaker")
    return parser


def _build_pipeline(
    *,
    region: str,
    role_arn: str,
    bucket: str,
    pipeline_name: str,
    model_package_group_name: str,
) -> Pipeline:
    boto_session = boto3.Session(region_name=region)
    sagemaker_session = sagemaker.session.Session(boto_session=boto_session)
    pipeline_session = PipelineSession(boto_session=boto_session, sagemaker_client=boto_session.client("sagemaker"))

    processing_instance_type = ParameterString(name="ProcessingInstanceType", default_value="ml.m5.xlarge")
    training_instance_type = ParameterString(name="TrainingInstanceType", default_value="ml.c5.xlarge")
    model_approval_status = ParameterString(name="ModelApprovalStatus", default_value="PendingManualApproval")
    f1_threshold = ParameterFloat(name="F1Threshold", default_value=0.8)
    input_data_uri = ParameterString(name="InputDataUri", default_value=f"s3://{bucket}/raw/train.csv")

    preprocess_processor = SKLearnProcessor(
        framework_version="1.2-1",
        role=role_arn,
        instance_type=processing_instance_type,
        instance_count=1,
        sagemaker_session=pipeline_session,
    )
    preprocessing_step = ProcessingStep(
        name="PreprocessData",
        processor=preprocess_processor,
        inputs=[ProcessingInput(source=input_data_uri, destination="/opt/ml/processing/input")],
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
            ProcessingOutput(output_name="validation", source="/opt/ml/processing/validation"),
        ],
        code="preprocess.py",
    )

    pytorch_estimator = sagemaker.pytorch.PyTorch(
        entry_point="train.py",
        source_dir="src",
        role=role_arn,
        framework_version="2.2",
        py_version="py310",
        instance_count=1,
        instance_type=training_instance_type,
        sagemaker_session=pipeline_session,
    )
    training_step = TrainingStep(
        name="TrainModel",
        estimator=pytorch_estimator,
        inputs={
            "train": TrainingInput(
                s3_data=preprocessing_step.properties.ProcessingOutputConfig.Outputs[
                    "train"
                ].S3Output.S3Uri
            ),
            "validation": TrainingInput(
                s3_data=preprocessing_step.properties.ProcessingOutputConfig.Outputs[
                    "validation"
                ].S3Output.S3Uri
            ),
        },
    )

    evaluation_processor = SKLearnProcessor(
        framework_version="1.2-1",
        role=role_arn,
        instance_type=processing_instance_type,
        instance_count=1,
        sagemaker_session=pipeline_session,
    )
    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="evaluation.json",
    )
    evaluation_step = ProcessingStep(
        name="EvaluateModel",
        processor=evaluation_processor,
        inputs=[
            ProcessingInput(
                source=training_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source=preprocessing_step.properties.ProcessingOutputConfig.Outputs[
                    "validation"
                ].S3Output.S3Uri,
                destination="/opt/ml/processing/validation",
            ),
        ],
        outputs=[ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")],
        code="evaluate.py",
        property_files=[evaluation_report],
    )

    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=(
                f"{evaluation_step.properties.ProcessingOutputConfig.Outputs['evaluation'].S3Output.S3Uri}"
                "/evaluation.json"
            ),
            content_type="application/json",
        )
    )
    register_step = RegisterModel(
        name="RegisterModelStep",
        estimator=pytorch_estimator,
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["application/json"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=model_package_group_name,
        approval_status=model_approval_status,
        model_metrics=model_metrics,
    )

    condition_step = ConditionStep(
        name="EvaluateF1Threshold",
        conditions=[
            ConditionGreaterThanOrEqualTo(
                left=JsonGet(
                    step_name=evaluation_step.name,
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
        parameters=[
            input_data_uri,
            processing_instance_type,
            training_instance_type,
            model_approval_status,
            f1_threshold,
        ],
        steps=[preprocessing_step, training_step, evaluation_step, condition_step],
        sagemaker_session=pipeline_session,
    )


def main() -> int:
    args = _build_parser().parse_args()
    pipeline = _build_pipeline(
        region=args.region,
        role_arn=args.role_arn,
        bucket=args.bucket,
        pipeline_name=args.pipeline_name,
        model_package_group_name=args.model_package_group,
    )

    definition_json = pipeline.definition()
    print("Pipeline definition:")
    print(json.dumps(json.loads(definition_json), indent=2))

    if args.create:
        response = pipeline.upsert(role_arn=args.role_arn)
        pipeline_arn = response.get("PipelineArn", "")
        print(f"Created/updated pipeline: {pipeline_arn}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
