data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  name       = "${var.project_name}-${var.environment}"
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags,
  )

  container_name = "api"
  container_port = 8000

  dlq_bucket_name = coalesce(var.dlq_bucket_name, "${local.name}-dlq-${local.account_id}")

  # Bedrock resources the task role may invoke. Plain model IDs map to a regional
  # foundation-model ARN. Cross-region inference profile IDs (e.g. "us.anthropic...")
  # need both the inference-profile ARN and the underlying foundation model in every
  # region the profile may route to.
  bedrock_model_ids = distinct([var.bedrock_llm_model_id, var.bedrock_embed_model_id])
  bedrock_resource_arns = flatten([
    for id in local.bedrock_model_ids : (
      can(regex("^(us|eu|apac|global|us-gov|jp|au|ca)\\.", id))
      ? [
        "arn:${local.partition}:bedrock:${var.aws_region}:${local.account_id}:inference-profile/${id}",
        "arn:${local.partition}:bedrock:*::foundation-model/${replace(id, "/^[a-z-]+\\./", "")}",
      ]
      : ["arn:${local.partition}:bedrock:${var.aws_region}::foundation-model/${id}"]
    )
  ])
}
