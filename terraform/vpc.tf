# ==============================================================================
# VPC & Networking Architecture (Strict Rule 2.1: Free Tier Preservation)
# ==============================================================================
# Module: terraform-aws-modules/vpc/aws (v6.8.0) — resource addresses verified
# against the module source for state migration.
#
# Architectural Guardrails:
#   1. Zero NAT Gateway: An AWS NAT Gateway costs ~$32.40/month ($0.045/hr).
#      We strictly deploy a single public subnet connected to an Internet Gateway ($0.00).
#   2. DNS Support: Enables internal DNS hostnames required by AWS SSM endpoints.
#   3. Single AZ: The old hand-written subnet was pinned to `${region}a`, and
#      `azs` must resolve to the identical AZ so the state migration does not
#      replace the subnet.
# ==============================================================================

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.8"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  # Same AZ the hand-written subnet used (${var.aws_region}a)
  azs            = ["${var.aws_region}a"]
  public_subnets = [var.public_subnet_cidr]

  enable_dns_support   = true
  enable_dns_hostnames = true

  # Public subnet hands out public IPs on launch (EC2 egress + tunnel origin)
  map_public_ip_on_launch = true

  # Free Tier preservation: NO NAT Gateway (Rule 2.1)
  enable_nat_gateway = false

  # Internet Gateway created by the module (create_igw defaults to true)
  igw_tags = {
    Name = "${var.project_name}-igw"
  }

  public_subnet_tags = {
    Name = "${var.project_name}-public-subnet"
    Tier = "Public"
  }

  public_route_table_tags = {
    Name = "${var.project_name}-public-rt"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}
