# ==============================================================================
# IAM Roles & Instance Profiles: AWS Systems Manager (SSM) Integration
# ==============================================================================
# Security Guardrails:
#   1. Least Privilege: Attaches only the AWS-managed policy 'AmazonSSMManagedInstanceCore'.
#   2. Zero Key Management: Grants the EC2 instance identity permissions to register
#      with AWS Systems Manager, enabling secure web-based shell and CLI access
#      without distributing or rotating static SSH private keys.
# ==============================================================================

resource "aws_iam_role" "ec2_ssm_role" {
  name        = "${var.project_name}-ec2-ssm-role"
  description = "Allows EC2 instance to communicate with AWS Systems Manager (SSM)"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ec2-ssm-role"
  }
}

# Attach AmazonSSMManagedInstanceCore policy
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# EC2 Instance Profile linking the role to the compute instance
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-instance-profile"
  role = aws_iam_role.ec2_ssm_role.name

  tags = {
    Name = "${var.project_name}-ec2-instance-profile"
  }
}
