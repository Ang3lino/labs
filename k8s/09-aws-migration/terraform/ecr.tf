locals {
  ecr_repositories = [
    "graph-rag/ingestion",
    "graph-rag/rag-api",
    "infra-intel/graph-builder",
    "infra-intel/query-api"
  ]
}

resource "aws_ecr_repository" "repositories" {
  for_each = toset(local.ecr_repositories)

  name                 = each.value
  image_tag_mutability = "MUTABLE" # ponytail: mutable tags keep iteration friction low in labs.

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = each.value
  })
}

resource "aws_ecr_lifecycle_policy" "keep_last_5" {
  for_each = aws_ecr_repository.repositories

  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
