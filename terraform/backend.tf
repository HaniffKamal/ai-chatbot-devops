# ==============================================================================
# Terraform Remote State & Distributed Locking Configuration
# ==============================================================================
# Architecture & Security Guardrails:
#   1. Remote State: Stored securely in S3 (haniff-invader) with AES-256 encryption.
#   2. Disaster Recovery: S3 Versioning enabled for point-in-time state rollback.
#   3. Distributed Locking: DynamoDB (chatbot-tf-locks) prevents concurrent apply races.
# ==============================================================================

terraform {
  required_version = ">= 1.16.0"

  backend "s3" {
    bucket         = "haniff-invader"
    key            = "dev/chatbot.tfstate"
    region         = "ap-southeast-1"
    use_lockfile   = true
    encrypt        = true
  }
}
