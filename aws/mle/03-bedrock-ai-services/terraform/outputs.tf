output "bucket_name" {
  description = "S3 bucket name for RAG documents"
  value       = aws_s3_bucket.rag_documents.bucket
}

output "bedrock_role_arn" {
  description = "IAM role ARN for Bedrock invocation"
  value       = aws_iam_role.bedrock_role.arn
}

output "comprehend_role_arn" {
  description = "IAM role ARN for Comprehend usage"
  value       = aws_iam_role.comprehend_role.arn
}
