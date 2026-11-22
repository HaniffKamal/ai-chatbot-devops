# ==============================================================================
# Infrastructure Outputs: Operational & DNS Exports
# ==============================================================================

output "ec2_instance_id" {
  description = "The EC2 Instance ID (used for AWS SSM Session Manager and Ansible inventory)"
  value       = module.ec2.id
}

output "ec2_public_ip" {
  description = "The EC2 public IPv4 (egress only; no DNS record or inbound rule depends on it)"
  value       = module.ec2.public_ip
}

output "ec2_private_ip" {
  description = "The EC2 private IPv4 (node_exporter target rendered by Ansible)"
  value       = module.ec2.private_ip
}

output "vpc_id" {
  description = "The ID of the custom VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_id" {
  description = "The ID of the public subnet"
  value       = module.vpc.public_subnets[0]
}

output "security_group_id" {
  description = "The ID of the security group (zero inbound rules)"
  value       = module.web_sg.id
}

output "cost_saver_lambda_name" {
  description = "Name of the automated FinOps Lambda shutdown function"
  value       = module.lambda.lambda_function_name
}

output "ssm_connect_command" {
  description = "Command to connect directly into the EC2 instance via AWS SSM Session Manager"
  value       = "aws ssm start-session --target ${module.ec2.id} --region ${var.aws_region}"
}

output "grafana_port_forward_command" {
  description = "Copy/paste to open Grafana at http://localhost:3000 (SSM port forwarding, no open SG ports)"
  value       = "aws ssm start-session --target ${module.ec2.id} --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\":[\"3000\"],\"localPortNumber\":[\"3000\"]}' --region ${var.aws_region}"
}

output "prometheus_port_forward_command" {
  description = "Copy/paste to open Prometheus at http://localhost:9090 (SSM port forwarding, no open SG ports)"
  value       = "aws ssm start-session --target ${module.ec2.id} --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\":[\"9090\"],\"localPortNumber\":[\"9090\"]}' --region ${var.aws_region}"
}
