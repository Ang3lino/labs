terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  bucket_name = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "lab_bucket" {
  bucket = local.bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "lab_bucket_versioning" {
  bucket = aws_s3_bucket.lab_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lab_bucket_encryption" {
  bucket = aws_s3_bucket.lab_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "glue_script" {
  bucket       = aws_s3_bucket.lab_bucket.id
  key          = "scripts/02_glue_etl.py"
  source       = "../scripts/02_glue_etl.py"
  etag         = filemd5("../scripts/02_glue_etl.py")
  content_type = "text/x-python"
}

resource "aws_glue_catalog_database" "lab_database" {
  name = "${replace(var.project_name, "-", "_")}_${var.environment}_db"
}

resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-${var.environment}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project_name}-${var.environment}-glue-s3-policy"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3DataAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.lab_bucket.arn,
          "${aws_s3_bucket.lab_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_glue_crawler" "fraud_crawler" {
  name          = "${var.project_name}-${var.environment}-crawler"
  database_name = aws_glue_catalog_database.lab_database.name
  role          = aws_iam_role.glue_role.arn

  s3_target {
    path = "s3://${aws_s3_bucket.lab_bucket.id}/raw/"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Tables = { AddOrUpdateBehavior = "MergeNewColumns" }
    }
  })

  tags = local.common_tags
}

resource "aws_glue_job" "fraud_etl" {
  name     = "${var.project_name}-${var.environment}-etl-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.lab_bucket.id}/${aws_s3_object.glue_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                      = "python"
    "--TempDir"                           = "s3://${aws_s3_bucket.lab_bucket.id}/tmp/"
    "--enable-continuous-cloudwatch-log"  = "true"
    "--enable-metrics"                    = "true"
    "--source_path"                       = "s3://${aws_s3_bucket.lab_bucket.id}/raw/fraud_data.csv"
    "--target_path"                       = "s3://${aws_s3_bucket.lab_bucket.id}/processed/"
  }

  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
  max_retries       = 0
  timeout           = 30

  tags = local.common_tags
}

# ponytail: single-region, no cross-account — study lab, not production
