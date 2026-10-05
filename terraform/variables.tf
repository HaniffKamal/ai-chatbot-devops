# ==============================================================================
# Input Variables: AI Chatbot DevOps Infrastructure
# ==============================================================================

variable "aws_region" {
  description = "The target AWS Region for all infrastructure resources"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Name prefix and identifier tag for all infrastructure components"
  type        = string
  default     = "ai-chatbot-devops"
}

variable "environment" {
  description = "Deployment lifecycle environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "Base CIDR block for the custom isolated VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet (Rule 2.1: Single subnet, no NAT Gateway)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "instance_type" {
  description = "EC2 compute instance type tailored for Ollama LLM and RAG inference"
  type        = string
  default     = "m7i-flex.large" # 2 vCPU, 8 GiB RAM
}

variable "root_volume_size" {
  description = "Size of the root EBS gp3 volume in GB (AWS Free Tier allows up to 30 GB)"
  type        = number
  default     = 30
}

variable "auto_stop_cron" {
  description = "Amazon EventBridge cron expression for automated off-peak EC2 shutdown (Rule 2.3)"
  type        = string
  default     = "cron(0 14 * * ? *)" # Daily at 23:00 UTC (07:00 MYT)
}

variable "ssh_public_key_path" {
  description = "Path to the local SSH public key for SSM-tunneled authentication (Rule 1.2)"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}
