#!/usr/bin/env bash
# ==============================================================================
# EC2 Bootstrap Script (cloud-init user_data)
# ==============================================================================
# Purpose:
#   Ensure the Amazon SSM Agent is enabled and running at first boot so the
#   instance registers with AWS Systems Manager. That registration is what
#   enables SSM Session Manager access and lets Ansible reach the host without
#   SSH. Application provisioning (Docker, code, monitoring) is owned
#   exclusively by Ansible, not by this script.
#
# Idempotent: safe to re-run manually for troubleshooting.
# Logs:       /var/log/user-data.log
# ==============================================================================

set -euo pipefail

exec > >(tee -a /var/log/user-data.log) 2>&1

echo "[user-data] started at $(date -Is)"

SSM_SERVICE="snap.amazon-ssm-agent.amazon-ssm-agent.service"

if systemctl list-unit-files "${SSM_SERVICE}" >/dev/null 2>&1; then
  systemctl enable --now "${SSM_SERVICE}"
  echo "[user-data] SSM Agent enabled and running"
else
  echo "[user-data] WARNING: ${SSM_SERVICE} not found; verify the AMI ships the SSM Agent" >&2
fi

echo "[user-data] completed at $(date -Is)"
