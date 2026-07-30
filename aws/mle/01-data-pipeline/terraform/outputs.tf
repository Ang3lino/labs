output "bucket_name" {
  description = "S3 bucket used for data lake objects"
  value       = aws_s3_bucket.lab_bucket.bucket
}

output "glue_database_name" {
  description = "Glue catalog database name"
  value       = aws_glue_catalog_database.lab_database.name
}

output "glue_crawler_name" {
  description = "Glue crawler name"
  value       = aws_glue_crawler.fraud_crawler.name
}
