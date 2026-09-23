terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Remote state is intentionally not configured: this module is validated only,
  # never applied. For a real deployment, use an encrypted S3 backend with state locking:
  #
  # backend "s3" {
  #   bucket       = "my-tfstate-bucket"
  #   key          = "legal-rag/aws/terraform.tfstate"
  #   region       = "us-east-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
