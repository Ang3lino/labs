from __future__ import annotations

import argparse
import json
from datetime import datetime

import boto3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create EventBridge retraining trigger for Lab 05")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--rule-name", default="mle-lab-05-raw-data-trigger")
    parser.add_argument("--data-bucket", required=True)
    parser.add_argument("--target-arn", required=True, help="Pipeline, Lambda, or Step Functions target ARN")
    parser.add_argument("--target-role-arn", default=None, help="IAM role ARN if target requires invocation role")
    parser.add_argument("--create", action="store_true", help="Create rule and attach target")
    parser.add_argument("--test-event-bus", default="default")
    return parser


def _rule_pattern(bucket_name: str) -> dict[str, object]:
    return {
        "source": ["aws.s3"],
        "detail-type": ["Object Created"],
        "detail": {
            "bucket": {"name": [bucket_name]},
            "object": {"key": [{"prefix": "raw/"}]},
        },
    }


def main() -> int:
    args = _build_parser().parse_args()
    events_client = boto3.client("events", region_name=args.region)
    rule_event_pattern = _rule_pattern(args.data_bucket)

    print("Rule pattern:")
    print(json.dumps(rule_event_pattern, indent=2))

    if args.create:
        put_rule_response = events_client.put_rule(
            Name=args.rule_name,
            EventPattern=json.dumps(rule_event_pattern),
            State="ENABLED",
            Description="Trigger MLOps retraining on new raw data arrival",
        )
        rule_arn = put_rule_response.get("RuleArn", "")

        target_definition = {
            "Id": "MlopsRetrainingTarget",
            "Arn": args.target_arn,
        }
        if args.target_role_arn:
            target_definition["RoleArn"] = args.target_role_arn

        put_targets_response = events_client.put_targets(
            Rule=args.rule_name,
            Targets=[target_definition],
        )
        print(f"Rule ARN: {rule_arn}")
        print("put_targets response:")
        print(json.dumps(put_targets_response, indent=2, default=str))
    else:
        account_id = boto3.client("sts", region_name=args.region).get_caller_identity().get("Account", "")
        rule_arn = f"arn:aws:events:{args.region}:{account_id}:rule/{args.rule_name}"
        print(f"Planned rule ARN: {rule_arn}")

    test_event = {
        "Source": "custom.mle.lab05",
        "DetailType": "raw-data-arrival-test",
        "Detail": json.dumps(
            {
                "bucket": args.data_bucket,
                "key": "raw/test-sample.csv",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ),
        "EventBusName": args.test_event_bus,
    }
    test_response = events_client.put_events(Entries=[test_event])
    print("Test put_events response:")
    print(json.dumps(test_response, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
