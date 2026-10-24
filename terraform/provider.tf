# ==============================================================================
# Terraform Providers Configuration
# ==============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.8"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

# The Cloudflare provider authenticates with CLOUDFLARE_API_TOKEN from the
# environment. Never commit the token or pass it as a variable.
provider "cloudflare" {}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
