data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    # Confused-deputy protection
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

# ------------------------------------------------------------------------------
# Task EXECUTION role: used by the ECS agent to pull the image, ship logs and
# resolve the task definition `secrets` into environment variables.
# Written inline (instead of AmazonECSTaskExecutionRolePolicy) to scope every
# action to this service's own repository, log group and secrets.
# ------------------------------------------------------------------------------
resource "aws_iam_role" "execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"] # GetAuthorizationToken does not support resource-level permissions
  }

  statement {
    sid = "EcrPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.app.arn}:*"]
  }

  statement {
    sid     = "InjectSecrets"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.api_key.arn,
      aws_secretsmanager_secret.pgvector_dsn.arn,
    ]
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "least-privilege"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

# ------------------------------------------------------------------------------
# TASK role: the identity of the application code itself (boto3 / langchain-aws).
# ------------------------------------------------------------------------------
resource "aws_iam_role" "task" {
  name               = "${local.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

data "aws_iam_policy_document" "task" {
  statement {
    sid = "InvokeConfiguredBedrockModels"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = local.bedrock_resource_arns
  }

  statement {
    sid       = "WriteDlqIncidents"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.dlq.arn}/incidents/*"]
  }

  dynamic "statement" {
    for_each = var.otel_enabled ? [1] : []

    content {
      sid = "XRayTracing"
      actions = [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
      ]
      resources = ["*"] # X-Ray does not support resource-level permissions for these actions
    }
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "least-privilege"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task.json
}
