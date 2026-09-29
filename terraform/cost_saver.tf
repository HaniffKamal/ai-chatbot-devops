# ==============================================================================
# Serverless FinOps Automation: EventBridge + Lambda Auto-Stop (Rule 2.3)
# ==============================================================================
# Architectural Guardrails:
#   1. Hybrid Architecture: Demonstrates combining stateful EC2 compute with
#      serverless AWS Lambda for event-driven cost governance.
#   2. Zero Bill Shock: Automatically issues a graceful StopInstances call daily
#      at 23:00 UTC (07:00 MYT) to ensure the server never runs overnight unmonitored.
#   3. Principle of Least Privilege: Lambda IAM policy is strictly scoped to
#      'ec2:DescribeInstances' and 'ec2:StopInstances' on the specific EC2 instance ARN.
# ==============================================================================

# Package the Python script into a deployment zip
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/auto_stop.py"
  output_path = "${path.module}/lambda/auto_stop.zip"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name        = "${var.project_name}-cost-saver-role"
  description = "Allows Lambda to inspect and stop the chatbot EC2 instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-cost-saver-role"
  }
}

# Least-Privilege IAM Policy for Lambda (CloudWatch Logs + EC2 Stop)
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-cost-saver-policy"
  description = "Permissions to stop EC2 instance and emit CloudWatch logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "EC2Describe"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      {
        Sid    = "EC2StopSpecificInstance"
        Effect = "Allow"
        Action = [
          "ec2:StopInstances"
        ]
        Resource = aws_instance.chatbot.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# AWS Lambda Function
resource "aws_lambda_function" "cost_saver" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-auto-stop"
  role             = aws_iam_role.lambda_role.arn
  handler          = "auto_stop.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      INSTANCE_ID = aws_instance.chatbot.id
    }
  }

  tags = {
    Name = "${var.project_name}-auto-stop"
  }
}

# Amazon EventBridge Scheduled Rule (Cron: 23:00 UTC)
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
  arn       = aws_lambda_function.cost_saver.arn
}

# Permission: Allow EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_saver.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nightly_stop.arn
}
