# ==============================================================================
# Serverless FinOps Automation: EventBridge + Lambda Auto-Stop (Rule 2.3)
# ==============================================================================
# Modules (versions confirmed through the Terraform MCP registry lookup):
#   terraform-aws-modules/lambda/aws       v8.13.2
#   terraform-aws-modules/eventbridge/aws  v4.4.1
#
# Architectural Guardrails:
#   1. Hybrid Architecture: stateful EC2 compute + serverless Lambda for
#      event-driven cost governance.
#   2. Zero Bill Shock: stops the EC2 instance daily at 14:00 UTC (22:00 MYT).
#   3. Least Privilege: the execution role (trust + inline permissions) is
#      created in iam.tf; the Lambda module never provisions its own role.
#   4. The Lambda module owns the invoke permission via allowed_triggers — the
#      EventBridge module does not create Lambda permissions by design.
#   5. No custom event bus and no EventBridge IAM role: a scheduled rule
#      targeting Lambda needs neither (create_bus/create_role = false).
# ==============================================================================

module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 8.13"

  function_name = "${var.project_name}-auto-stop"
  description   = "Automated off-peak shutdown of the chatbot EC2 instance"
  handler       = "auto_stop.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 128

  # The module packages ${path.module}/lambda and hashes the artifact itself
  source_path    = "${path.module}/lambda"
  create_package = true

  # Reuse the least-privilege role from iam.tf instead of creating a new one
  create_role = false
  lambda_role = module.lambda_role.arn

  # CloudWatch log group is created and retained by the module
  cloudwatch_logs_retention_in_days = 7

  environment_variables = {
    INSTANCE_ID = module.ec2.id
  }

  # EventBridge may invoke this function (the module creates the permission)
  create_current_version_allowed_triggers = false
  allowed_triggers = {
    EventBridge = {
      principal  = "events.amazonaws.com"
      source_arn = module.eventbridge.eventbridge_rule_arns["${var.project_name}-nightly-stop"]
    }
  }

  tags = {
    Name = "${var.project_name}-auto-stop"
  }
}

module "eventbridge" {
  source  = "terraform-aws-modules/eventbridge/aws"
  version = "~> 4.4"

  # Scheduled rules run on the default bus and need no EventBridge IAM role
  create_bus  = false
  create_role = false

  # Keep the rule name exactly "<project>-nightly-stop" (no "-rule" suffix)
  append_rule_postfix = false

  rules = {
    "${var.project_name}-nightly-stop" = {
      description         = "Trigger Lambda to stop EC2 instance off-peak daily"
      schedule_expression = var.auto_stop_cron
    }
  }

  targets = {
    "${var.project_name}-nightly-stop" = [
      {
        name      = "TriggerCostSaverLambda"
        target_id = "TriggerCostSaverLambda"
        arn       = module.lambda.lambda_function_arn
      }
    ]
  }

  tags = {
    Name = "${var.project_name}-nightly-stop"
  }
}
