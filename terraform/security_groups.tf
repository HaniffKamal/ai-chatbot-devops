# ==============================================================================
# Security Groups: Zero-Trust Network Boundary (Strict Rule 1.2)
# ==============================================================================
# Security Guardrails:
#   1. Zero Inbound Administrative Ports: Port 22 (SSH) is 100% CLOSED.
#      Administrative terminal access is managed exclusively via AWS Systems Manager
#      (SSM) Session Manager, eliminating brute-force attacks and SSH key theft.
#   2. Zero Ingress: Cloudflare Tunnel (cloudflared) dials outbound to the edge,
#      so there is no public listener and no inbound rule to maintain.
#   3. Internal Port Cloaking: Ports 8000 (FastAPI), 8080 (Nginx), and 11434
#      (Ollama, local profile) only exist on the private Docker bridge network.
#   4. Outbound Access: Egress is open to allow the tunnel, the SSM Agent, image
#      pulls from GHCR, and calls to the Groq API.
# ==============================================================================

resource "aws_security_group" "web" {
  name        = "${var.project_name}-web-sg"
  description = "Cloudflare Tunnel origin - zero ingress rules"
  vpc_id      = aws_vpc.main.id

  # Ingress: NONE. Cloudflare Tunnel (cloudflared) dials outbound to the edge,
  # so the instance has no listening public service and no inbound rules at all.

  # Egress: All outbound traffic (Required for the tunnel, SSM, GHCR, Groq API, and OS updates)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}
