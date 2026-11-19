# ==============================================================================
# Security Groups: Zero-Trust Network Boundary (Strict Rule 1.2)
# ==============================================================================
# Module: terraform-aws-modules/security-group/aws (v6.0.0, AWS provider v6
# rule model). Schemas verified against the module's tf-docs — no guessed keys.
#
# Security Guardrails:
#   1. Zero Ingress: Cloudflare Tunnel (cloudflared) dials outbound to the edge,
#      so there is no public listener and no inbound rule to maintain.
#   2. Internal Port Cloaking: Ports 8000 (FastAPI), 8080 (Nginx), and 11434
#      (Ollama, local profile) only exist on the private Docker bridge network.
#   3. Egress is explicit all-outbound (tunnel, SSM agent, GHCR pulls, Groq API,
#      OS updates). The v6 module creates NO implicit egress — it is declared
#      here on purpose.
#   4. enable_exclusive_rules (module default: true) reverts any out-of-band
#      rule added via the console, keeping the zero-ingress guarantee enforced.
#
# State-migration note: use_name_prefix stays false so the SG name is byte-for-
# byte identical to the pre-module resource, allowing a clean
# `terraform state mv` without replacing the SG or the EC2 instance.
# ==============================================================================

module "web_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.project_name}-web-sg"
  description = "Cloudflare Tunnel origin - zero ingress rules"
  vpc_id      = module.vpc.vpc_id

  use_name_prefix = false

  # Ingress: NONE. cloudflared dials outbound to the edge, so the instance has
  # no listening public service and no inbound rules at all.

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound traffic"
    }
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}
