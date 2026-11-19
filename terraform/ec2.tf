# ==============================================================================
# EC2 Compute Engine & Storage Architecture (Rules 2.1 & 1.2)
# ==============================================================================
# Module (version confirmed through the Terraform MCP registry lookup):
#   terraform-aws-modules/ec2-instance/aws  v6.4.1
#
# Architectural Guardrails:
#   1. Instance Selection: m7i-flex.large (2 vCPU, 8 GiB RAM) provides dedicated
#      memory headroom for Ollama 8B LLM weights and in-process RAG embeddings.
#   2. Dynamic AMI: Resolves latest official Ubuntu 26.04 LTS from Canonical.
#   3. Zero SSH Keys: Uses IAM Instance Profile for SSM Session Manager.
#   4. Free Tier Storage: 30 GB gp3 encrypted EBS root volume.
#   5. Thin Bootstrap: Minimal SSM agent startup; Docker & apps managed by Ansible.
#   6. The module must NOT create its own security group, IAM profile, or EIP —
#      those are owned by security_groups.tf, iam.tf, and the VPC module.
# ==============================================================================

# Lookup latest official Ubuntu 26.04 LTS AMI from Canonical
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*"]
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

module "ec2" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "~> 6.4"

  name          = "${var.project_name}-ec2"
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  key_name               = aws_key_pair.ansible.key_name
  subnet_id              = module.vpc.public_subnets[0]
  vpc_security_group_ids = [module.web_sg.id]
  iam_instance_profile   = module.ec2_ssm_role.instance_profile_name

  associate_public_ip_address = true

  # Do not let the module create additional resources — all are owned elsewhere
  create_security_group       = false
  create_iam_instance_profile = false
  create_eip                  = false

  # 30 GB gp3 EBS Volume (AWS Free Tier Maximum).
  # enable_volume_tags must stay false because volume_tags conflicts with
  # root_block_device tags in the AWS provider.
  enable_volume_tags = false

  root_block_device = {
    volume_type           = "gp3"
    size                  = var.root_volume_size
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  # Thin bootstrap: start the SSM Agent so Session Manager and Ansible (over
  # SSM) can reach the instance. Application provisioning lives in Ansible.
  user_data = file("${path.module}/userdata.sh")

  tags = {
    Name = "${var.project_name}-ec2"
  }
}
