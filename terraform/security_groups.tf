# ==============================================================================
# Security Groups: Zero-Trust Network Boundary (Strict Rule 1.2)
# ==============================================================================
# Security Guardrails:
#   1. Zero Inbound Administrative Ports: Port 22 (SSH) is 100% CLOSED.
#      Administrative terminal access is managed exclusively via AWS Systems Manager
#      (SSM) Session Manager, eliminating brute-force attacks and SSH key theft.
#   2. Web Traffic Only: Ingress is restricted to Port 80 (HTTP) and Port 443 (HTTPS).
#   3. Internal Port Cloaking: Ports 8000 (FastAPI), 11434 (Ollama), 9090 (Prometheus),
#      and 3000 (Grafana) are NEVER exposed to the public internet; they communicate
#      strictly across the private internal Docker bridge network.
#   4. Outbound Access: Egress is open to allow the SSM Agent to establish outbound
#      HTTPS tunnels, pull Docker images from Docker Hub, and reach the Groq API.
# ==============================================================================

resource "aws_security_group" "web" {
  name        = "${var.project_name}-web-sg"
  description = "Security group for AI Chatbot reverse proxy and web gateway (Zero SSH ports)"
  vpc_id      = aws_vpc.main.id

  # Ingress: HTTP (Port 80)
  ingress {
    description = "HTTP web traffic from Cloudflare / Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Ingress: HTTPS (Port 443)
  ingress {
    description = "HTTPS web traffic from Cloudflare / Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress: All outbound traffic (Required for SSM, Docker Hub, Groq API, and OS updates)
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

s
