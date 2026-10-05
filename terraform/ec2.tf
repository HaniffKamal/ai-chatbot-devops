# ==============================================================================
# EC2 Compute Engine & Storage Architecture (Rules 2.1 & 1.2)
# ==============================================================================
# Architectural Guardrails:
#   1. Instance Selection: m7i-flex.large (2 vCPU, 8 GiB RAM) provides dedicated
#      memory headroom for Ollama 8B LLM weights and in-process RAG embeddings.
#   2. Dynamic AMI: Resolves latest official Ubuntu 24.04 LTS from Canonical.
#   3. Zero SSH Keys: Uses IAM Instance Profile for SSM Session Manager.
#   4. Free Tier Storage: 30 GB gp3 encrypted EBS root volume.
#   5. User Data Bootstrap: Pre-configures Docker, Docker Compose, and SSM Agent.
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

  # Automated host initialization script
  user_data = <<-EOF
              #!/bin/bash
              set -e
              export DEBIAN_FRONTEND=noninteractive

              # 1. Update system packages
              apt-get update && apt-get upgrade -y

              # 2. Ensure Amazon SSM Agent is active (pre-installed on Ubuntu)
              systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service || true
              systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service || true

              # 3. Install Docker and Docker Compose Plugin
              apt-get install -y ca-certificates curl gnupg
              install -m 0755 -d /etc/apt/keyrings
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
              chmod a+r /etc/apt/keyrings/docker.asc

              echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

              apt-get update
              apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

              # 4. Add ubuntu user to docker group
              usermod -aG docker ubuntu

              # 5. Create application and log directories
              mkdir -p /opt/chatbot/logs
              chown -R ubuntu:ubuntu /opt/chatbot

              # 6. Create 2GB swap file as OOM memory buffer
              fallocate -l 2G /swapfile
              chmod 600 /swapfile
              mkswap /swapfile
              swapon /swapfile
              echo '/swapfile none swap sw 0 0' >> /etc/fstab

              echo "Initialization complete!"
              EOF

  tags = {
    Name = "${var.project_name}-ec2"
  }
}
