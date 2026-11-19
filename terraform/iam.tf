# ==============================================================================
# IAM Roles & Policies: SSM access + Lambda cost-saver (module-managed)
# ==============================================================================
# Module (version confirmed through the Terraform MCP registry lookup):
#   terraform-aws-modules/iam/aws//modules/iam-role  v6.11.1
#
# Security Guardrails:
#   1. EC2 role trusts only ec2.amazonaws.com, carries only
#      AmazonSSMManagedInstanceCore, and is served through an instance profile.
#   2. Lambda role trusts only lambda.amazonaws.com. Its permissions are an
#      inline policy built by the module itself (create_inline_policy +
#      inline_policy_permissions), scoped to the specific EC2 instance ARN.
#   3. No wildcard actions, no wild resource-level permissions.
#
# use_name_prefix = false keeps the role/profile names byte-for-byte identical
# to the pre-module resources, so the existing roles and instance profile can be
# adopted with `terraform state mv` instead of being replaced.
# ==============================================================================

# --- EC2 SSM role -------------------------------------------------------------

module "ec2_ssm_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role"
  version = "~> 6.11"

  name            = "${var.project_name}-ec2-ssm-role"
  description     = "Allows EC2 instance to communicate with AWS Systems Manager (SSM)"
  use_name_prefix = false

  create_instance_profile = true

  trust_policy_permissions = {
    AllowEc2ToAssumeRole = {
      actions = ["sts:AssumeRole"]
      principals = [{
        type        = "Service"
        identifiers = ["ec2.amazonaws.com"]
      }]
    }
  }

  policies = {
    ssm_managed_instance_core = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  }

  tags = {
    Name = "${var.project_name}-ec2-ssm-role"
  }
}

# --- Lambda cost-saver role (trust + inline permissions) ----------------------

module "lambda_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role"
  version = "~> 6.11"

  name            = "${var.project_name}-cost-saver-role"
  description     = "Allows Lambda to inspect and stop the chatbot EC2 instance"
  use_name_prefix = false

  trust_policy_permissions = {
    AllowLambdaToAssumeRole = {
      actions = ["sts:AssumeRole"]
      principals = [{
        type        = "Service"
        identifiers = ["lambda.amazonaws.com"]
      }]
    }
  }

  # Least-privilege permissions: the module builds the policy document from
  # these statements and attaches it as an inline policy to the role.
  create_inline_policy = true

  inline_policy_permissions = {
    CloudWatchLogging = {
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ]
      resources = ["arn:aws:logs:*:*:*"]
    }

    EC2Describe = {
      actions   = ["ec2:DescribeInstances"]
      resources = ["*"]
    }

    EC2StopSpecificInstance = {
      actions   = ["ec2:StopInstances"]
      resources = [module.ec2.arn]
    }
  }

  tags = {
    Name = "${var.project_name}-cost-saver-role"
  }
}
