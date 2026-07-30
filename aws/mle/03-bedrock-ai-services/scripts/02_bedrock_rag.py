from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import boto3


LAB_ROOT = Path(__file__).resolve().parents[1]
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))
if str(LAB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT.parent))

from shared.datasets import DatasetManager


TEXT_FILENAME = "03-bedrock-ai-services/rag/the-art-of-war.txt"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simplified Bedrock Knowledge Base RAG demo")
    parser.add_argument("--bucket", required=True, help="S3 bucket with Terraform output bucket_name")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--embedding-model-arn", required=True)
    parser.add_argument("--knowledge-base-role-arn", required=True)
    parser.add_argument("--question", default="What is a key strategic principle in this text?")
    parser.add_argument("--name-prefix", default="mle-lab-03")
    return parser


def _upload_document(bucket: str, region: str) -> str:
    manager = DatasetManager()
    local_text_path = manager.cache_dir / TEXT_FILENAME
    if not local_text_path.exists():
        raise FileNotFoundError(
            f"Missing dataset at {local_text_path}. Run: uv run python aws/mle/03-bedrock-ai-services/datasets.py --download"
        )

    s3_key = "rag/input/the-art-of-war.txt"
    s3_client = boto3.client("s3", region_name=region)
    s3_client.upload_file(str(local_text_path), bucket, s3_key)
    return s3_key


def _create_knowledge_base(
    bedrock_agent: boto3.client,
    bucket: str,
    role_arn: str,
    embedding_model_arn: str,
    name_prefix: str,
) -> tuple[str, str]:
    unique_suffix = uuid.uuid4().hex[:8]
    kb_name = f"{name_prefix}-kb-{unique_suffix}"
    ds_name = f"{name_prefix}-ds-{unique_suffix}"

    kb_response = bedrock_agent.create_knowledge_base(
        name=kb_name,
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": embedding_model_arn,
            },
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": "REPLACE_WITH_YOUR_AOSS_COLLECTION_ARN",
                "vectorIndexName": "mle-lab-03-index",
                "fieldMapping": {
                    "vectorField": "embedding",
                    "textField": "text",
                    "metadataField": "metadata",
                },
            },
        },
    )
    knowledge_base_id = kb_response["knowledgeBase"]["knowledgeBaseId"]

    data_source_response = bedrock_agent.create_data_source(
        name=ds_name,
        knowledgeBaseId=knowledge_base_id,
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{bucket}",
                "inclusionPrefixes": ["rag/input/"],
            },
        },
    )
    data_source_id = data_source_response["dataSource"]["dataSourceId"]
    return knowledge_base_id, data_source_id


def _wait_for_ingestion(
    bedrock_agent: boto3.client,
    knowledge_base_id: str,
    data_source_id: str,
) -> str:
    job = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=knowledge_base_id,
        dataSourceId=data_source_id,
    )
    job_id = job["ingestionJob"]["ingestionJobId"]

    terminal_states = {"COMPLETE", "FAILED", "STOPPED"}
    while True:
        status_response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            ingestionJobId=job_id,
        )
        status = status_response["ingestionJob"]["status"]
        if status in terminal_states:
            return status
        time.sleep(5)


def _query_knowledge_base(region: str, knowledge_base_id: str, question: str) -> dict[str, object]:
    runtime = boto3.client("bedrock-agent-runtime", region_name=region)
    response = runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
            },
        },
    )
    return response


def main() -> int:
    args = _build_parser().parse_args()

    uploaded_key = _upload_document(bucket=args.bucket, region=args.region)
    print(f"Uploaded: s3://{args.bucket}/{uploaded_key}")

    bedrock_agent = boto3.client("bedrock-agent", region_name=args.region)
    knowledge_base_id, data_source_id = _create_knowledge_base(
        bedrock_agent=bedrock_agent,
        bucket=args.bucket,
        role_arn=args.knowledge_base_role_arn,
        embedding_model_arn=args.embedding_model_arn,
        name_prefix=args.name_prefix,
    )
    print(f"KnowledgeBaseId: {knowledge_base_id}")
    print(f"DataSourceId: {data_source_id}")

    ingestion_status = _wait_for_ingestion(
        bedrock_agent=bedrock_agent,
        knowledge_base_id=knowledge_base_id,
        data_source_id=data_source_id,
    )
    print(f"Ingestion status: {ingestion_status}")
    if ingestion_status != "COMPLETE":
        raise RuntimeError(f"Ingestion did not complete successfully: {ingestion_status}")

    result = _query_knowledge_base(
        region=args.region,
        knowledge_base_id=knowledge_base_id,
        question=args.question,
    )

    output_text = result.get("output", {}).get("text")
    citations = result.get("citations", [])
    print("Generated answer:")
    print(output_text)
    print("Retrieved context:")
    print(json.dumps(citations, indent=2, default=str))
    return 0


if __name__ == "__main__":
    # ponytail: simplified RAG — real production would use OpenSearch or Pinecone as vector store
    raise SystemExit(main())
