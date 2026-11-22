#!/usr/bin/env bash
# ==============================================================================
# Start the EC2 instance and wait until SSM reports it Online.
# Prints the instance ID and region; exits non-zero if SSM never registers.
# ==============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

instance_id=$(terraform -chdir=terraform output -raw ec2_instance_id)
region=$(terraform -chdir=terraform output -raw aws_region)

echo "Starting ${instance_id} (${region})..."
aws ec2 start-instances --region "${region}" --instance-ids "${instance_id}" >/dev/null
aws ec2 wait instance-running --region "${region}" --instance-ids "${instance_id}"

echo "Waiting for SSM agent to come online..."
for _ in $(seq 1 30); do
  status=$(aws ssm describe-instance-information \
    --region "${region}" \
    --filters "Key=InstanceIds,Values=${instance_id}" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null || true)
  if [[ "${status}" == "Online" ]]; then
    echo "Ready: ${instance_id} (SSM Online)"
    exit 0
  fi
  sleep 5
done

echo "ERROR: SSM agent did not come online within 150s" >&2
exit 1
