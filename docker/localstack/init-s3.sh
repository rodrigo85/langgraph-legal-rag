#!/bin/sh
# Creates the DLQ bucket when LocalStack is ready (Terraform owns it in the cloud)
awslocal s3 mb s3://legal-rag-dlq
