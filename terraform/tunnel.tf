# ==============================================================================
# Cloudflare Tunnel: Zero Inbound Ports
# ==============================================================================
# Architectural Guardrails:
#   1. Remotely-managed tunnel (config_src = "cloudflare"): ingress is declared
#      here, not in a YAML file on the origin host.
#   2. Outbound-only: cloudflared dials the Cloudflare edge, so the EC2 Security
#      Group has no ingress rules at all.
#   3. The tunnel token is account-scoped and long-lived. It is written to SSM
#      Parameter Store as a SecureString, never committed or baked into an image.
#      Note: it is also present in Terraform state (S3, encrypted + versioned),
#      which is the accepted trade-off for fully automated provisioning.
#   4. The DNS record is a proxied CNAME to <tunnel-id>.cfargotunnel.com;
#      Cloudflare terminates visitor TLS and encrypts edge -> cloudflared.
# ==============================================================================

resource "cloudflare_zero_trust_tunnel_cloudflared" "chatbot" {
  account_id = var.cloudflare_account_id
  name       = "${var.project_name}-tunnel"
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "chatbot" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.chatbot.id
  source     = "cloudflare"

  config = {
    ingress = [
      {
        hostname       = "${var.chatbot_subdomain}.${var.domain_name}"
        service        = "http://frontend:8080"
        origin_request = {
          http_host_header = "${var.chatbot_subdomain}.${var.domain_name}"
        }
      },
      {
        # Required catch-all: unmatched requests are rejected, not proxied.
        service = "http_status:404"
      }
    ]
  }
}

data "cloudflare_zero_trust_tunnel_cloudflared_token" "chatbot" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.chatbot.id
}

resource "cloudflare_dns_record" "chatbot" {
  zone_id = var.cloudflare_zone_id
  name    = "${var.chatbot_subdomain}.${var.domain_name}"
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.chatbot.id}.cfargotunnel.com"
  ttl     = 1 # 1 = automatic
  proxied = true
  comment = "Cloudflare Tunnel to the chatbot origin (managed by Terraform)"
}

resource "aws_ssm_parameter" "cloudflare_tunnel_token" {
  name        = "/chatbot/${var.environment}/cloudflare_tunnel_token"
  description = "Cloudflare Tunnel token consumed by cloudflared on the EC2 host"
  type        = "SecureString"
  value       = data.cloudflare_zero_trust_tunnel_cloudflared_token.chatbot.token

  tags = {
    Name = "${var.project_name}-tunnel-token"
  }
}
