output "bucket_name" {
  description = "S3 bucket name for Lab 07 book text storage"
  value       = aws_s3_bucket.book_texts.bucket
}

output "comprehend_role_arn" {
  description = "IAM role ARN for Comprehend analysis"
  value       = aws_iam_role.comprehend_role.arn
}
