# ==============================================================================
# Makefile: local development, infrastructure, deployment, and monitoring
# ==============================================================================
# Run `make` or `make help` for the target list.
# ==============================================================================

SHELL := /bin/bash
COMPOSE_DEV := docker compose -f docker-compose.yaml -f docker-compose.dev.yaml

.DEFAULT_GOAL := help

.PHONY: help up down logs test fmt tf-init tf-plan tf-apply start stop setup deploy monitoring grafana prometheus

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

# --- Local development --------------------------------------------------------

up: ## Start the local dev stack
	$(COMPOSE_DEV) up -d --build

down: ## Stop the local dev stack
	$(COMPOSE_DEV) down

logs: ## Follow local stack logs
	$(COMPOSE_DEV) logs -f

test: ## Run ruff and pytest
	cd backend && ruff check . && ruff format --check . && pytest

fmt: ## Auto-fix and format backend code
	cd backend && ruff check --fix . && ruff format .

# --- Infrastructure -----------------------------------------------------------

tf-init: ## Initialize Terraform (download modules)
	terraform -chdir=terraform init

tf-plan: ## Terraform plan
	terraform -chdir=terraform plan

tf-apply: ## Terraform apply
	terraform -chdir=terraform apply

tf-destroy:
	terraform -chdir=terraform apply

start: ## Start EC2 and wait for SSM Online
	bash scripts/start-server.sh

stop: ## Stop EC2 (EBS data persists)
	bash scripts/stop-server.sh

# --- Deployment ---------------------------------------------------------------

setup: ## First-time host setup (Docker, directories)
	cd ansible && ansible-playbook playbook.yaml

deploy: ## Deploy the app (secrets, images, restart, health gate)
	cd ansible && ansible-playbook deploy.yaml

monitoring: ## Deploy Prometheus + Grafana + node_exporter
	cd ansible && ansible-playbook monitoring.yaml

# --- Access -------------------------------------------------------------------

grafana: ## Port-forward Grafana to http://localhost:3000
	@aws ssm start-session --target "$$(terraform -chdir=terraform output -raw ec2_instance_id)" \
	  --document-name AWS-StartPortForwardingSession \
	  --parameters '{"portNumber":["3000"],"localPortNumber":["3000"]}' \
	  --region "$$(terraform -chdir=terraform output -raw aws_region)"

prometheus: ## Port-forward Prometheus to http://localhost:9090
	@aws ssm start-session --target "$$(terraform -chdir=terraform output -raw ec2_instance_id)" \
	  --document-name AWS-StartPortForwardingSession \
	  --parameters '{"portNumber":["9090"],"localPortNumber":["9090"]}' \
	  --region "$$(terraform -chdir=terraform output -raw aws_region)"
