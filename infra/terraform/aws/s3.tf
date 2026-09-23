# Dead-letter queue for hallucination incidents (DLQ_BACKEND=s3).
# The app writes one immutable JSON object per incident under incidents/YYYY/MM/DD/<id>.json.

resource "aws_s3_bucket" "dlq" {
  bucket        = local.dlq_bucket_name
  force_destroy = false
}

resource "aws_s3_bucket_ownership_controls" "dlq" {
  bucket = aws_s3_bucket.dlq.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "dlq" {
  bucket = aws_s3_bucket.dlq.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "dlq" {
  bucket = aws_s3_bucket.dlq.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dlq" {
  bucket = aws_s3_bucket.dlq.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "dlq" {
  bucket = aws_s3_bucket.dlq.id

  # Versioning must be enabled before noncurrent-version rules apply.
  depends_on = [aws_s3_bucket_versioning.dlq]

  rule {
    id     = "archive-incidents"
    status = "Enabled"

    filter {
      prefix = "incidents/"
    }

    transition {
      days          = var.dlq_glacier_transition_days
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = var.dlq_glacier_transition_days
      storage_class   = "GLACIER"
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "aws_iam_policy_document" "dlq_bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.dlq.arn,
      "${aws_s3_bucket.dlq.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "dlq" {
  bucket = aws_s3_bucket.dlq.id
  policy = data.aws_iam_policy_document.dlq_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.dlq]
}
