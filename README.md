# 🤖 AI Chatbot Microservice & MLOps Infrastructure Platform

[![CI/CD Pipeline](https://github.com/HaniffKamal/ai-chatbot-devops/actions/workflows/ci.yaml/badge.svg)](https://github.com/HaniffKamal/ai-chatbot-devops/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
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

> **Production note:** the EC2 stack runs **cloudflared + Nginx + FastAPI**, plus a separate
> monitoring Compose project (`/opt/monitoring`) with Prometheus + Grafana. Ingress is a
> Cloudflare Tunnel, so the Security Group has no inbound rules. Ollama is a
> local-development profile; production uses the Groq API (`openai/gpt-oss-20b`) because the
> host is CPU-only with 8 GiB RAM. Monitoring UIs are loopback-only and reached via SSM
> port forwarding.

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
* **Terraform:** Official `terraform-aws-modules` for VPC, security group, IAM, Lambda, EventBridge, and EC2; direct resources only where no module fits (Cloudflare tunnel is manual/out-of-band).
* **Ansible:** Docker Engine + Compose plugin via the pinned `geerlingguy.docker` Galaxy role; node_exporter via `prometheus.prometheus`; idempotent host directories and rendered production `.env`.
* **Cost Optimization:** EC2 runs on-demand and is stopped nightly by the EventBridge + Lambda FinOps job. No NAT Gateway and no idle Elastic IP, keeping monthly infrastructure costs at **$0.00**.

### 4. 📊 Observability Stack

* **Prometheus:** Scrapes itself, the host-installed node_exporter, and the backend `/metrics` (15s interval), with a 5 GB TSDB cap.
* **node_exporter:** Host system metrics (CPU, memory, disk, network) installed by Ansible.
* **Grafana:** Public via `grafana.haniffkamal.my` (login required) or SSM; datasource and dashboards are built manually, then exported as JSON into `monitoring/dashboards/`.
* **Backend `/metrics`:** FastAPI instrumented (request count, latency, status) plus a `chatbot_rag_indexed_chunks` gauge; scraped over the VPC private IP.

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
| **Infrastructure** | Terraform | VPC, SG, IAM, EC2, Lambda, EventBridge (official modules) |
| **Configuration** | Ansible | Host setup (Docker Galaxy role), secrets, deploys, monitoring |
| **CI/CD** | GitHub Actions | Automated linting, formatting, testing, and image publishing |
| **Metrics** | Prometheus, Grafana, node_exporter | Host and system telemetry |

---

## 📁 Repository Structure

```
ai-chatbot-devops/
├── .github/workflows/
│   ├── ci.yaml                 # CI: Ruff lint/format -> pytest -> GHCR push
│   └── deploy.yaml             # CD: OIDC -> SSM -> Ansible deploy
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
│   ├── ec2.tf                  # EC2 module: m7i-flex.large, gp3 root, SSM profile
│   ├── iam.tf                  # SSM role/profile + Lambda inline permissions
│   ├── cost_saver.tf           # EventBridge + Lambda auto-stop
│   ├── github_oidc.tf          # GitHub OIDC deploy role + instance-id parameter
│   ├── inventory.tf            # Renders ansible/inventory.ini
│   ├── userdata.sh             # First-boot SSM Agent bootstrap
│   ├── variables.tf            # Configurable AWS inputs
│   ├── outputs.tf              # EC2 ID/IPs and SSM connect command
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
│   ├── test_rate_limit.sh      # Verifies Nginx returns 429 past the burst
│   ├── start-server.sh         # Start EC2 and wait for SSM Online
│   └── stop-server.sh          # Stop EC2 (EBS data persists)
├── Makefile                    # Dev, Terraform, Ansible, monitoring shortcuts
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

# or simply
make up
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

## 🛠️ Make Targets

`make` (or `make help`) lists every shortcut:

| Target | What it does |
|---|---|
| `make up` / `make down` / `make logs` | Local dev stack (build, stop, follow logs) |
| `make test` / `make fmt` | `ruff check` + `ruff format --check` + `pytest`; auto-fix variant |
| `make tf-init` / `make tf-plan` / `make tf-apply` | Terraform |
| `make tf-destroy` | Destroy all Terraform resources (prompts; deletes EC2 + EBS data) |
| `make start` / `make stop` | Start EC2 and wait for SSM Online; stop EC2 |
| `make setup` / `make deploy` | First-time host setup; application release |
| `make monitoring` | Prometheus + Grafana + node_exporter |
| `make grafana` / `make prometheus` | SSM port-forward the UIs to localhost |

Shell scripts behind the power targets live in `scripts/` (`start-server.sh`, `stop-server.sh`).

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
ansible-playbook playbook.yaml   # first-time host setup (Docker, dirs)
ansible-playbook deploy.yaml     # render env files, pull images, restart
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

### 3. Monitoring

Prometheus + Grafana run as a separate Compose project in `/opt/monitoring`;
node_exporter is installed on the host by the Ansible role, and Ansible renders
the host's private IP into `prometheus.yaml` at deploy time. Prometheus scrapes
`node_exporter` (`:9100`) and the backend (`/metrics` on `:8000`) over that
private IP; the backend port is VPC-only because the SG has zero ingress.

```bash
cd ansible
ansible-galaxy collection install 'prometheus.prometheus:==0.30.2'
ansible-playbook monitoring.yaml
```

Access:

- **Grafana:** `https://grafana.haniffkamal.my` through the Cloudflare Tunnel
  (login required — `admin` password was changed from the default), or
  `http://localhost:3000` via SSM port forwarding.
- **Prometheus:** SSM port forwarding only — never exposed through the tunnel.

The tunnel's public hostname `grafana.haniffkamal.my` points to
`http://host.docker.internal:3000`; `cloudflared` has the `host-gateway` entry
for that. The Security Group keeps zero ingress.

> Recommended: add a Cloudflare Access policy (email OTP) to
> `grafana.haniffkamal.my` — the admin login is currently the only gate.

```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["9090"],"localPortNumber":["9090"]}'
```

Add the Prometheus datasource `http://prometheus:9090` in Grafana, build
dashboards in the UI, then export them to `monitoring/dashboards/<name>.json`.

Shortcut: `make grafana` and `make prometheus` run the port-forward commands for you.

### 4. Automated CI/CD (GitHub Actions)
Every push to `main` and every pull request targeting it executes:
1. **Linting & Formatting:** `ruff check` and `ruff format --check`.
2. **Automated Testing:** `pytest` on FastAPI routes and RAG logic, with coverage reporting.
3. **Container Image Build & Push:** On `main`, builds the affected images and pushes both `:latest` and an immutable `:<commit-sha>` to GHCR using the built-in `GITHUB_TOKEN` — `chatbot` when `backend/**` changes, `chatbot-frontend` when `frontend/**` changes.
4. **Deployment (CD):** After CI succeeds on `main`, `.github/workflows/deploy.yaml` assumes an IAM role via GitHub OIDC (no stored AWS keys), pushes a 60-second EC2 Instance Connect key, and runs `ansible-playbook deploy.yaml` over SSM. It fails fast if the instance is stopped and gates on `/health` + `rag_indexed_chunks > 0`.

One-time CD setup: `terraform apply` creates the OIDC role and `/chatbot/instance-id`; set the repository variable `AWS_DEPLOY_ROLE_ARN` to `terraform output -raw github_deploy_role_arn`.

---

## 👤 Author

**Haniff Kamal**
* Focus: DevOps, Cloud Infrastructure & MLOps Engineering
* Portfolio: [haniffkamal.my](https://haniffkamal.my)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
