# ==============================================================================
# Serverless FinOps Automation: EventBridge + Lambda Auto-Stop (Rule 2.3)
# ==============================================================================
# Module (version confirmed through the Terraform MCP registry lookup):
#   terraform-aws-modules/lambda/aws  v8.13.2
#
# Architectural Guardrails:
#   1. Hybrid Architecture: Demonstrates combining stateful EC2 compute with
#      serverless AWS Lambda for event-driven cost governance.
#   2. Zero Bill Shock: Automatically issues a graceful StopInstances call daily
#      at 14:00 UTC (22:00 MYT) to ensure the server never runs overnight.
#   3. Principle of Least Privilege: the execution role is created in iam.tf
#      (module.lambda_role) and attached here with create_role = false — the
#      module never provisions its own broad role.
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

  tags = {
    Name = "${var.project_name}-auto-stop"
  }
}

# Amazon EventBridge Scheduled Rule (Cron: 14:00 UTC)
resource "aws_cloudwatch_event_rule" "nightly_stop" {
  name                = "${var.project_name}-nightly-stop"
  description         = "Trigger Lambda to stop EC2 instance off-peak daily"
  schedule_expression = var.auto_stop_cron

  tags = {
    Name = "${var.project_name}-nightly-stop"
  }
}

# Target: Invoke the Lambda function
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.nightly_stop.name
  target_id = "TriggerCostSaverLambda"
  arn       = module.lambda.lambda_function_arn
}

# Permission: Allow EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nightly_stop.arn
}
