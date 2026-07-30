from __future__ import annotations

import argparse
import json

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Step Functions state machine for Lab 05")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--state-machine-name", default="mle-lab-05-mlops-orchestrator")
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--training-job-name", default="mle-lab-05-training-job")
    parser.add_argument("--training-image", required=True)
    parser.add_argument("--training-output-path", required=True)
    parser.add_argument("--create", action="store_true", help="Create state machine")
    return parser


def _state_machine_definition(args: argparse.Namespace) -> dict[str, object]:
    return {
        "Comment": (
            "Lab 05 MLOps state machine. "
            "Step Functions is general-purpose cross-service orchestration; "
            "SageMaker Pipelines is ML-native with lineage and model registry focus."
        ),
        "StartAt": "StartTraining",
        "States": {
            "StartTraining": {
                "Type": "Task",
                "Resource": "arn:aws:states:::sagemaker:createTrainingJob.sync",
                "Parameters": {
                    "TrainingJobName": args.training_job_name,
                    "AlgorithmSpecification": {
                        "TrainingImage": args.training_image,
                        "TrainingInputMode": "File",
                    },
                    "RoleArn": args.role_arn,
                    "ResourceConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.m5.large",
                        "VolumeSizeInGB": 30,
                    },
                    "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
                    "OutputDataConfig": {"S3OutputPath": args.training_output_path},
                    "InputDataConfig": [
                        {
                            "ChannelName": "train",
                            "DataSource": {
                                "S3DataSource": {
                                    "S3DataType": "S3Prefix",
                                    "S3Uri": f"{args.training_output_path}/input",
                                    "S3DataDistributionType": "FullyReplicated",
                                }
                            },
                        }
                    ],
                },
                "Next": "WaitForTraining",
            },
            "WaitForTraining": {
                "Type": "Wait",
                "Seconds": 10,
                "Next": "EvaluateModel",
            },
            "EvaluateModel": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "mle-lab-05-evaluate-model",
                    "Payload": {
                        "trainingJobName": args.training_job_name,
                    },
                },
                "ResultPath": "$.evaluation",
                "Next": "F1ThresholdChoice",
            },
            "F1ThresholdChoice": {
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.evaluation.Payload.f1",
                        "NumericGreaterThanEquals": 0.8,
                        "Next": "RegisterModel",
                    }
                ],
                "Default": "FailPipeline",
            },
            "RegisterModel": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "mle-lab-05-register-model",
                    "Payload": {
                        "trainingJobName": args.training_job_name,
                        "f1.$": "$.evaluation.Payload.f1",
                    },
                },
                "End": True,
            },
            "FailPipeline": {
                "Type": "Fail",
                "Error": "ModelQualityBelowThreshold",
                "Cause": "F1 score below required threshold",
            },
        },
    }


def main() -> int:
    args = _build_parser().parse_args()
    state_machine = _state_machine_definition(args)

    print("State machine definition:")
    print(json.dumps(state_machine, indent=2))

    if args.create:
        stepfunctions_client = boto3.client("stepfunctions", region_name=args.region)
        response = stepfunctions_client.create_state_machine(
            name=args.state_machine_name,
            definition=json.dumps(state_machine),
            roleArn=args.role_arn,
            type="STANDARD",
        )
        print(f"State machine ARN: {response.get('stateMachineArn', '')}")
        print("Create response:")
        print(json.dumps(response, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
