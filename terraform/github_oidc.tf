# ==============================================================================
# GitHub Actions CD: OIDC provider, deploy role, and instance-id parameter
# ==============================================================================
# Security Guardrails:
#   1. No static AWS keys: the workflow exchanges a short-lived GitHub OIDC
#      token for temporary role credentials.
#   2. Trust is scoped to pushes on main of this repository only.
#   3. The role can only open SSH-over-SSM to this instance, push a 60-second
#      ephemeral key for the `ubuntu` user, and read the instance-id parameter.
# ==============================================================================

module "github_oidc" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-oidc-provider"
  version = "~> 6.11"

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]

  tags = {
    Name = "${var.project_name}-github-oidc"
  }
}

module "github_deploy_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role"
  version = "~> 6.11"

  name            = "${var.project_name}-github-deploy"
  description     = "GitHub Actions CD: deploy over SSM with an ephemeral SSH key"
  use_name_prefix = false

  enable_github_oidc = true
  # Immutable subject claims are enabled account-wide, so the `sub` claim carries
  # immutable owner/repo IDs instead of plain names:
  #   repo:HaniffKamal@129153396/ai-chatbot-devops@1368494525:ref:refs/heads/main
  # The module prepends "repo:" itself, so the value below omits it.
  # Verify with: gh api repos/<owner>/<repo>/actions/oidc/customization/sub
  # (use_default=true, use_immutable_subject=true, sub_claim_prefix=<this value>).
  oidc_subjects = ["HaniffKamal@129153396/ai-chatbot-devops@1368494525:ref:refs/heads/main"]

  create_inline_policy = true

  inline_policy_permissions = {
    StartSshSession = {
      actions = ["ssm:StartSession"]
      resources = [
        module.ec2.arn,
        "arn:aws:ssm:*::document/AWS-StartSSHSession",
      ]
    }

    PushEphemeralKey = {
      actions   = ["ec2-instance-connect:SendSSHPublicKey"]
      resources = [module.ec2.arn]
      condition = [{
        test     = "StringEquals"
        variable = "ec2:osuser"
        values   = ["ubuntu"]
      }]
    }

    Describe = {
      actions   = ["ec2:DescribeInstances", "ssm:DescribeInstanceInformation"]
      resources = ["*"]
    }

    ReadInstanceId = {
      actions   = ["ssm:GetParameter"]
      resources = [aws_ssm_parameter.instance_id.arn]
    }
  }

  tags = {
    Name = "${var.project_name}-github-deploy"
  }

  # The module builds the trust-policy ARN from the provider URL; it does not
  # reference the provider resource, so make the dependency explicit.
  depends_on = [module.github_oidc]
}

# The CI runner cannot see the locally-rendered inventory.ini, so publish the
# instance ID and let the workflow rebuild the inventory from it.
resource "aws_ssm_parameter" "instance_id" {
  name  = "/chatbot/instance-id"
  type  = "String"
  value = module.ec2.id

  tags = {
    Name = "${var.project_name}-instance-id"
  }
}

output "github_deploy_role_arn" {
  description = "IAM role assumed by the CD workflow (set as the AWS_DEPLOY_ROLE_ARN repo variable)"
  value       = module.github_deploy_role.arn
}
