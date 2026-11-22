#!/usr/bin/env bash
# ==============================================================================
# Stop the EC2 instance. EBS volumes and all data persist; only compute stops.
# ==============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

instance_id=$(terraform -chdir=terraform output -raw ec2_instance_id)
region=$(terraform -chdir=terraform output -raw aws_region)

echo "Stopping ${instance_id} (${region})..."
aws ec2 stop-instances --region "${region}" --instance-ids "${instance_id}" >/dev/null
aws ec2 wait instance-stopped --region "${region}" --instance-ids "${instance_id}"
echo "Stopped: ${instance_id}"
