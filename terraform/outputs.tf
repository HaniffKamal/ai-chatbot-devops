# ==============================================================================
# Infrastructure Outputs: Operational & DNS Exports
# ==============================================================================

output "ec2_instance_id" {
  description = "The EC2 Instance ID (used for AWS SSM Session Manager and Ansible inventory)"
  value       = aws_instance.chatbot.id
}

output "ec2_public_ip" {
  description = "The EC2 public IPv4 (egress only; no DNS record or inbound rule depends on it)"
  value       = aws_instance.chatbot.public_ip
}

output "chatbot_url" {
  description = "Public HTTPS endpoint served through the Cloudflare Tunnel"
  value       = "https://${var.chatbot_subdomain}.${var.domain_name}"
}

output "tunnel_id" {
  description = "Cloudflare Tunnel UUID (shown in Networking → Tunnels)"
  value       = cloudflare_zero_trust_tunnel_cloudflared.chatbot.id
}

output "tunnel_token_ssm_parameter" {
  description = "SSM Parameter Store name holding the tunnel token (SecureString)"
  value       = aws_ssm_parameter.cloudflare_tunnel_token.name
}

output "vpc_id" {
  description = "The ID of the custom VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "The ID of the public subnet"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "The ID of the security group (zero inbound rules)"
  value       = aws_security_group.web.id
}

output "cost_saver_lambda_name" {
  description = "Name of the automated FinOps Lambda shutdown function"
  value       = aws_lambda_function.cost_saver.function_name
}

output "ssm_connect_command" {
  description = "Command to connect directly into the EC2 instance via AWS SSM Session Manager"
  value       = "aws ssm start-session --target ${aws_instance.chatbot.id} --region ${var.aws_region}"
}
