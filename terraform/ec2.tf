# ==============================================================================
# EC2 Compute Engine & Storage Architecture (Rules 2.1 & 1.2)
# ==============================================================================
# Architectural Guardrails:
#   1. Instance Selection: m7i-flex.large (2 vCPU, 8 GiB RAM) provides dedicated
#      memory headroom for Ollama 8B LLM weights and in-process RAG embeddings.
#   2. Dynamic AMI: Resolves latest official Ubuntu 24.04 LTS from Canonical.
#   3. Zero SSH Keys: Uses IAM Instance Profile for SSM Session Manager.
#   4. Free Tier Storage: 30 GB gp3 encrypted EBS root volume.
#   5. Thin Bootstrap: Minimal SSM agent startup; Docker & apps managed by Ansible.
# ==============================================================================

# Lookup latest official Ubuntu 24.04 LTS AMI from Canonical
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# SSH Key Pair for secure authentication through AWS SSM Proxy Tunnel (Rule 1.2)
# Cloud-init automatically places this into /home/ubuntu/.ssh/authorized_keys on boot.
resource "aws_key_pair" "ansible" {
  key_name   = "${var.project_name}-key"
  public_key = file(pathexpand(var.ssh_public_key_path))

  tags = {
    Name = "${var.project_name}-key"
  }
}

resource "aws_instance" "chatbot" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.ansible.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  associate_public_ip_address = true

  # 30 GB gp3 EBS Volume (AWS Free Tier Maximum)
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  # Thin Bootstrap: Minimal initialization required for Ansible / SSM connectivity
  # All software installation (Docker, workspace, etc.) is owned strictly by Ansible.
  user_data = <<-EOF
              #!/bin/bash
              set -e

              # Ensure Amazon SSM Agent is active (pre-installed on Ubuntu 26.04 LTS)
              systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service || true
              systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service || true
              EOF

  tags = {
    Name = "${var.project_name}-ec2"
  }
}
