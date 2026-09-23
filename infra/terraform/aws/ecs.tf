resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_cluster" "this" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

locals {
  # Non-secret configuration, mapped 1:1 to legal_rag.config.Settings.
  app_environment = [
    { name = "LLM_PROVIDER", value = "bedrock" },
    { name = "EMBEDDING_PROVIDER", value = "bedrock" },
    { name = "BEDROCK_LLM_MODEL_ID", value = var.bedrock_llm_model_id },
    { name = "BEDROCK_EMBED_MODEL_ID", value = var.bedrock_embed_model_id },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "VECTOR_STORE", value = "pgvector" },
    { name = "DLQ_BACKEND", value = "s3" },
    { name = "DLQ_S3_BUCKET", value = aws_s3_bucket.dlq.bucket },
    { name = "LOG_FORMAT", value = "json" },
    { name = "LOG_LEVEL", value = var.log_level },
    { name = "OTEL_ENABLED", value = tostring(var.otel_enabled) },
    { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4318" }, # ADOT sidecar
    { name = "OTEL_SERVICE_NAME", value = local.name },
  ]

  # Secrets are resolved by the ECS agent at task start (execution role) and exposed
  # to the container as environment variables. Values never appear in the task definition.
  app_secrets = [
    { name = "PGVECTOR_DSN", valueFrom = aws_secretsmanager_secret.pgvector_dsn.arn },
    { name = "API_KEY", valueFrom = aws_secretsmanager_secret.api_key.arn },
  ]

  api_container = {
    name        = local.container_name
    image       = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    essential   = true
    environment = local.app_environment
    secrets     = local.app_secrets

    portMappings = [
      { containerPort = local.container_port, protocol = "tcp" },
    ]

    # Liveness via /health; the ALB target group gates traffic on /ready.
    # Uses the Python interpreter already in the image (no curl dependency).
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:${local.container_port}/health', timeout=4)\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
  }

  adot_container = {
    name      = "aws-otel-collector"
    image     = var.adot_collector_image
    essential = false
    command   = ["--config=/etc/ecs/ecs-xray.yaml"]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "otel"
      }
    }
  }

  container_definitions = concat(
    [local.api_container],
    var.otel_enabled ? [local.adot_container] : [],
  )
}

resource "aws_ecs_task_definition" "api" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode(local.container_definitions)
}

resource "aws_ecs_service" "api" {
  name                              = "${local.name}-api"
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.api.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 120
  enable_execute_command            = false
  propagate_tags                    = "SERVICE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = local.container_name
    container_port   = local.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Autoscaling owns desired_count after the first deployment.
  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.https]
}
