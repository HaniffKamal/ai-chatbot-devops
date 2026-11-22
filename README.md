# 🤖 AI Chatbot Microservice & MLOps Infrastructure Platform

[![CI/CD Pipeline](https://github.com/HaniffKamal/ai-chatbot-devops/actions/workflows/ci.yaml/badge.svg)](https://github.com/HaniffKamal/ai-chatbot-devops/actions)
[![FastAPI](https://img.shields.com/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-NVIDIA_GPU-black?style=flat&logo=ollama&logoColor=white)](https://ollama.ai)
[![Terraform](https://img.shields.io/badge/Terraform-AWS_IaC-7B42BC?style=flat&logo=terraform&logoColor=white)](https://www.terraform.io)
[![Ansible](https://img.shields.io/badge/Ansible-Automation-EE0000?style=flat&logo=ansible&logoColor=white)](https://www.ansible.com)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-DNS_%26_SSL-F38020?style=flat&logo=cloudflare&logoColor=white)](https://www.cloudflare.com)

An enterprise-grade, containerized AI Chatbot Microservice featuring **Retrieval-Augmented Generation (RAG)**, dual-engine LLM inference (Local Ollama GPU / Cloud Groq fallback), and a complete DevOps/MLOps delivery pipeline.

### Architectural Model: Decoupled Microservice
This repository operates as an **independent, embeddable AI microservice**. It is designed to cleanly integrate with external frontends—specifically powering the interactive chatbot assistant on the master developer portfolio ([`haniffkamal.my`](https://haniffkamal.my)), which is hosted separately 24/7 on Cloudflare Pages.

---

## 🏛️ System Architecture

```
   [ Master Portfolio: haniffkamal.my ]        [ Localhost / Direct Client ]
     (Hosted 24/7 on Cloudflare Pages)          (Standalone Web Client UI)
                    │                                        │
                    └───────────────────┬────────────────────┘
                                        │ HTTPS / REST API
                                        ▼
                    ┌──────────────────────────────────────────────┐
                    │             CLOUDFLARE EDGE                  │
                    │  • DNS: chatbot.haniffkamal.my (CNAME)       │
                    │  • Tunnel: outbound-only, zero open ports    │
                    │  • DDoS mitigation & edge TLS                │
                    └───────────────────┬──────────────────────────┘
                                        │ QUIC/HTTP2 (EC2 dials out)
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AWS CUSTOM VPC (ISOLATED)                              │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                     Public Subnet + Internet Gateway                              │  │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │           Amazon EC2: m7i-flex.large (2 vCPU, 8 GiB RAM, On-Demand)        │  │  │
│  │  │                                                                            │  │  │
│  │  │  ┌──────────────────────── Docker Compose Runtime ──────────────────────┐  │  │  │
│  │  │  │                                                                      │  │  │  │
│  │  │  │   ┌──────────────┐     ┌──────────────┐     ┌─────────────────────┐  │  │  │  │
│  │  │  │   │ Nginx Proxy  │────▶│ FastAPI API  │────▶│   Ollama Engine     │  │  │  │  │
│  │  │  │   │ (Port 8080)  │     │ (Port 8000)  │     │   (Port 11434)      │  │  │  │  │
│  │  │  │   │ Web Client + │     │ Async Pool + │     │   Llama 3.1 / 3.2   │  │  │  │  │
│  │  │  │   │ Reverse Prox │     │ Embedded RAG │     │ (Local GPU / CPU)   │  │  │  │  │
│  │  │  │   └──────────────┘     └──────┬───────┘     └──────────┬──────────┘  │  │  │  │
│  │  │  │                               │                        │             │  │  │  │
│  │  │  │                          /metrics                      │ Fallback    │  │  │  │
│  │  │  │                               ▼                        ▼             │  │  │  │
│  │  │  │   ┌──────────────┐     ┌──────────────┐     ┌─────────────────────┐  │  │  │  │
│  │  │  │   │ Grafana UI   │◀────│  Prometheus  │     │      Groq Cloud     │  │  │  │  │
│  │  │  │   │ (Port 3000)  │     │ (Port 9090)  │     │ (llama-3.1-8b API)  │  │  │  │  │
│  │  │  │   └──────────────┘     └──────────────┘     └─────────────────────┘  │  │  │  │
│  │  │  │                                                                      │  │  │  │
│  │  │  └──────────────────────────────────────────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

> **Production note:** the EC2 stack runs **cloudflared + Nginx + FastAPI only**. Ingress is a Cloudflare Tunnel, so the Security Group has no inbound rules. Ollama is a local-development profile; production uses the Groq API (`openai/gpt-oss-20b`) because the host is CPU-only with 8 GiB RAM. Prometheus/Grafana are planned, not deployed.

---

## 🌟 Key Engineering Highlights

### 1. 🧠 MLOps & Dual-Engine Resilience
* **Hardware-Accelerated Inference:** Native NVIDIA GPU pass-through (`capabilities: [gpu]`) for local development on an RTX 3060 laptop GPU.
* **Dual-Provider, One Interface:** Locally, FastAPI targets Ollama (`llama3.2:1b`) as primary and falls back to the ultra-low latency **Groq API** (`openai/gpt-oss-20b`). In production the provider is Groq only — the EC2 host is CPU-only — and a failure degrades gracefully instead of returning a 500.
* **In-Process RAG (Zero Extra Containers):** Context retrieval powered by an embedded ChromaDB instance reading structured knowledge bases directly from Markdown files.

### 2. 🛡️ Production Security & Guardrails
* **Non-Root Execution:** The backend runs as `appuser:appgroup` (UID/GID `10001`); the frontend image runs as the unprivileged Nginx user (UID 101).
* **Zero Inbound Ports:** The Security Group has no ingress rules at all. Public traffic arrives through a Cloudflare Tunnel (`cloudflared`, outbound-only) and shell access is IAM-gated through SSM Session Manager.
* **Origin Cloaking:** The tunnel publishes `chatbot.haniffkamal.my` without exposing the EC2 IP or any listening port.
* **Zero Secret Leakage:** Production secrets live in SSM `SecureString` (KMS-encrypted, IAM-gated, CloudTrail-audited) and are rendered into 0600 env files at deploy time. No secret enters Git, an image, or user-data.

### 3. ⚙️ Idempotent Infrastructure as Code (IaC)
* **Terraform:** Declaratively defines the complete AWS topology (VPC, Subnet, Internet Gateway, Route Tables, Security Groups, and EC2 Compute).
* **Ansible:** Fully idempotent server provisioning (Docker Engine installation, application directory, rendered production `.env`).
* **Cost Optimization:** EC2 runs on-demand and is stopped nightly by the EventBridge + Lambda FinOps job. No NAT Gateway and no idle Elastic IP, keeping monthly infrastructure costs at **$0.00**.

### 4. 📊 Full Observability Stack

> **Status:** planned — Prometheus/Grafana are not deployed yet and `/metrics` is not exposed.

* **Prometheus:** Scrapes real-time application throughput, request latency, and HTTP error distributions from `/metrics`.
* **Grafana:** Pre-provisioned dashboards using YAML datasources to visualize server load and inference performance with zero manual UI setup.

---

## 🧰 Technology Stack

| Domain | Technology | Purpose |
|---|---|---|
| **Frontend** | Vanilla HTML5 / CSS3 / ES6 | Dedicated Chatbot UI & embeddable web widget |
| **Reverse Proxy** | Unprivileged Nginx (`alpine`) | Static assets baked into `chatbot-frontend`; `/api` proxy; TLS terminates at Cloudflare |
| **Backend API** | FastAPI (`python:3.10-slim`) | Async HTTP connection pooling, RAG orchestration |
| **LLM Engine (local)** | Ollama (`llama3.2:1b`) | GPU-accelerated private inference during local development |
| **LLM Engine (prod)** | Groq Cloud LPU (`openai/gpt-oss-20b`) | CPU-free inference on EC2; no Ollama container |
| **Edge Ingress** | Cloudflare Tunnel (`cloudflared` 2026.10.3) | Outbound-only connector; origin exposes no inbound ports |
| **Vector Store** | ChromaDB (Embedded) | In-process vector database for resume context search |
| **Infrastructure** | Terraform | AWS Cloud VPC and EC2 provisioning |
| **Configuration** | Ansible | Automated host configuration and Docker orchestration |
| **CI/CD** | GitHub Actions | Automated linting, formatting, testing, and image publishing |
| **Metrics** | Prometheus & Grafana | Endpoint performance and system telemetry |

---

## 📁 Repository Structure

```
ai-chatbot-devops/
├── .github/workflows/
│   └── ci.yaml                 # CI/CD pipeline (Ruff lint/format -> pytest -> GHCR push)
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint, async client, /health, /api/chat
│   │   ├── config.py           # Pydantic Settings environment schema
│   │   ├── llm_client.py       # Dual-engine router (Ollama + Groq fallback)
│   │   └── rag.py              # Chunking, embeddings, ChromaDB search
│   ├── data/                   # Knowledge base documents for RAG
│   │   ├── about.md
│   │   ├── experience.md
│   │   ├── projects.md
│   │   └── skills.md
│   ├── tests/                  # Unit and integration test suites
│   ├── Dockerfile              # Multi-stage, non-root, slim Python build
│   └── requirements.txt        # Production dependencies
├── frontend/
│   ├── Dockerfile              # Unprivileged Nginx image; assets + config baked in
│   ├── index.html              # Dedicated Chatbot Web Client & Widget UI
│   ├── style.css               # Modern dark-mode styling
│   ├── script.js               # Async fetch client with suggestion pills
│   └── nginx.conf              # Reverse proxy routing rules
├── terraform/
│   ├── provider.tf             # AWS provider and version constraints
│   ├── backend.tf              # S3 remote state (encrypted, versioned)
│   ├── vpc.tf                  # VPC, public subnet, IGW, route table
│   ├── security_groups.tf      # Zero ingress rules; tunnel is outbound-only
│   ├── ec2.tf                  # m7i-flex.large, gp3 root volume, SSM profile
│   ├── iam.tf                  # SSM instance role and profile
│   ├── cost_saver.tf           # EventBridge + Lambda auto-stop
│   ├── inventory.tf            # Renders ansible/inventory.ini
│   ├── variables.tf            # Configurable AWS inputs
│   ├── outputs.tf              # EC2 ID, public IP, chatbot URL
│   └── terraform.tfvars.example
├── ansible/
│   ├── playbook.yaml           # Host setup: base packages, Docker role, app directories
│   ├── deploy.yaml             # Release: render .env, pull image, restart, health gate
│   ├── monitoring.yaml         # Monitoring stack + node_exporter
│   └── inventory.ini           # Target host (rendered by Terraform)
├── monitoring/
│   ├── compose.yaml            # Prometheus + Grafana (separate Compose project)
│   └── prometheus.yaml.j2      # Scrape config template (host private IP rendered by Ansible)
├── scripts/
│   ├── inspect_db.py           # ChromaDB inspector & semantic search CLI
│   └── test_rate_limit.sh      # Verifies Nginx returns 429 past the burst
├── docker-compose.yaml         # Core service definitions (Frontend, Backend, Ollama profile)
├── docker-compose.dev.yaml     # Local dev overrides (NVIDIA GPU runtime)
├── docker-compose.prod.yaml    # Production: Groq-only, cloudflared, restart, limits
└── README.md                   # Project documentation
```

---

## 🚀 Quickstart: Local Development

### Prerequisites
* Docker Engine 24.0+ and Docker Compose v2
* NVIDIA Container Toolkit (for local GPU acceleration; optional, falls back to CPU)

### 1. Clone the Repository
```bash
git clone https://github.com/HaniffKamal/ai-chatbot-devops.git
cd ai-chatbot-devops
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env if configuring optional Groq API keys or custom models
```

### 3. Start the Stack
```bash
# Start all containers in the background with GPU acceleration
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
```

### 4. Pull the LLM Model into Ollama
```bash
# Pull the model configured by DEFAULT_MODEL in .env
docker exec -it chatbot-ollama ollama pull llama3.2:1b
```

### 5. Verify Health & Inference
```bash
# Check service health (proxied through Nginx)
curl -s http://localhost/health | jq .

# Send a sample prompt through the chat API
curl -s -X POST http://localhost/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What technical skills does Haniff have?"}' | jq .
```

Access the frontend portfolio directly at: **`http://localhost`**

### 6. Run Linting, Formatting & Tests Locally

```bash
# One-time: install dev tooling (ruff, pytest, coverage)
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

cd backend
ruff check .           # lint (add --fix to auto-correct)
ruff format --check .  # verify formatting (drop --check to apply)
pytest                 # run the test suite
pytest --cov=app       # same, plus a coverage report (what CI prints)
```

These are the exact commands CI runs, so a clean local run means a green pipeline.

---

## 🚢 Production Deployment Workflow

### 0. Cloudflare Tunnel (one-time, manual)

The tunnel is intentionally **not** managed by Terraform, so it survives
`terraform destroy` and rebuilds.

1. Zero Trust → Networks → Tunnels → Create a tunnel (`cloudflared`), copy the token.
2. Add a public hostname: `chatbot.haniffkamal.my` → `http://frontend:8080`
   (the frontend container on the `chatbot-net` Docker network). Cloudflare
   creates the proxied CNAME automatically.
3. Store the production secrets as SSM `SecureString` parameters:

```bash
aws ssm put-parameter --name /chatbot/tunnel-token \
  --type SecureString --value '<TUNNEL_TOKEN>' --region ap-southeast-1 --overwrite

aws ssm put-parameter --name /chatbot/groq-api-key \
  --type SecureString --value '<GROQ_API_KEY>' --region ap-southeast-1 --overwrite
```

### 1. Infrastructure Provisioning (Terraform)
```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Terraform provisions AWS only (VPC, SG, IAM, EC2, Lambda, EventBridge).
# ansible/inventory.ini is rendered automatically on apply — no manual step.
```

### 2. Server Configuration & Deployment (Ansible)

Requires `ansible-core >= 2.17`.

Install the pinned Galaxy dependencies once per controller:

```bash
ansible-galaxy role install geerlingguy.docker,8.0.1
ansible-galaxy collection install 'community.docker:==5.4.0'
```

Then:

```bash
cd ../ansible
ansible-playbook -i inventory.ini playbook.yaml   # first-time host setup (Docker, dirs)
ansible-playbook -i inventory.ini deploy.yaml     # render env files, pull images, restart
```

`deploy.yaml` reads both production secrets from SSM Parameter Store
(`/chatbot/groq-api-key`, `/chatbot/tunnel-token`), so the AWS CLI on the
controller must be authenticated. It renders `.env` and `cloudflared.env`
(0600), runs `docker compose pull`, and gates on `http://127.0.0.1:8080/health`.

```bash
curl -s https://chatbot.haniffkamal.my/health
```

If an old `api.haniffkamal.my` A record still exists in Cloudflare, delete it — the
tunnel's CNAME is the only record that should point at the chatbot.

### 3. Monitoring (phase 1)

Prometheus + Grafana run as a separate Compose project in `/opt/monitoring`;
node_exporter is installed on the host by the Ansible role, and Ansible renders
the host's private IP into `prometheus.yaml` at deploy time.

```bash
cd ansible
ansible-galaxy collection install 'prometheus.prometheus:==0.30.2'
ansible-playbook -i inventory.ini monitoring.yaml
```

Reach the UIs through SSM port forwarding (never through Cloudflare):

```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["3000"],"localPortNumber":["3000"]}'

aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["9090"],"localPortNumber":["9090"]}'
```

Grafana: `http://localhost:3000` (`admin/admin` on first login — change it).
Add the Prometheus datasource `http://prometheus:9090`, build dashboards in the
UI, then export them to `monitoring/dashboards/<name>.json` for the repo.

### 4. Automated CI/CD (GitHub Actions)
Every push to `main` and every pull request targeting it executes:
1. **Linting & Formatting:** `ruff check` and `ruff format --check`.
2. **Automated Testing:** `pytest` on FastAPI routes and RAG logic, with coverage reporting.
3. **Container Image Build & Push:** On `main`, builds the affected images and pushes both `:latest` and an immutable `:<commit-sha>` to GHCR using the built-in `GITHUB_TOKEN` — `chatbot` when `backend/**` changes, `chatbot-frontend` when `frontend/**` changes.
4. **Deployment:** Manual for now — `ansible-playbook -i inventory.ini ansible/deploy.yaml` over SSM pulls the freshly tagged backend and frontend images and restarts services. Automated CD and post-deploy verification are still pending.

---

## 👤 Author

**Haniff Kamal**
* Focus: DevOps, Cloud Infrastructure & MLOps Engineering
* Portfolio: [haniffkamal.my](https://haniffkamal.my)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
