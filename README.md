# 🤖 AI Portfolio Chatbot & DevOps Pipeline

[![CI/CD Pipeline](https://github.com/HaniffKamal/ai-chatbot-devops/actions/workflows/deploy.yml/badge.svg)](https://github.com/HaniffKamal/ai-chatbot-devops/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-NVIDIA_GPU-black?style=flat&logo=ollama&logoColor=white)](https://ollama.ai)
[![Terraform](https://img.shields.io/badge/Terraform-AWS_IaC-7B42BC?style=flat&logo=terraform&logoColor=white)](https://www.terraform.io)
[![Ansible](https://img.shields.io/badge/Ansible-Automation-EE0000?style=flat&logo=ansible&logoColor=white)](https://www.ansible.com)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-DNS_%26_SSL-F38020?style=flat&logo=cloudflare&logoColor=white)](https://www.cloudflare.com)

An enterprise-grade, containerized full-stack portfolio platform featuring an interactive AI assistant powered by **Retrieval-Augmented Generation (RAG)** and local/cloud LLM inference.

This repository serves a dual purpose:
1. **Interactive Portfolio:** A live website hosted at [`haniffkamal.my`](https://haniffkamal.my) allowing visitors and recruiters to interactively query my background, audio deepfake detection research, and engineering projects.
2. **End-to-End DevOps / MLOps Showcase:** A comprehensive implementation of Infrastructure as Code (IaC), Configuration Management, Continuous Deployment, Container Security, and Observability.

---

## 🏛️ System Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │              CLIENT BROWSER                  │
                    └──────────────────────┬───────────────────────┘
                                           │ HTTPS (Port 443)
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │             CLOUDFLARE EDGE                  │
                    │   • DNS Management (haniffkamal.my)          │
                    │   • Strict SSL/TLS Encryption                │
                    │   • Origin Shield & DDoS Mitigation          │
                    └──────────────────────┬───────────────────────┘
                                           │ HTTP (Port 80)
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
│  │  │  │   │  (Port 80)   │     │ (Port 8000)  │     │   (Port 11434)      │  │  │  │  │
│  │  │  │   │ Static Web + │     │ Async Pool + │     │   Llama 3.1 8B      │  │  │  │  │
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

---

## 🌟 Key Engineering Highlights

### 1. 🧠 MLOps & Dual-Engine Resilience
* **Hardware-Accelerated Inference:** Native NVIDIA GPU pass-through (`capabilities: [gpu]`) for local development on an RTX 3060 laptop GPU.
* **Dual-Provider Failover:** High-availability design where FastAPI targets the local Ollama instance as primary, with automatic timeout-triggered fallback to the ultra-low latency **Groq API** (`llama-3.1-8b-instant`).
* **In-Process RAG (Zero Extra Containers):** Context retrieval powered by an embedded ChromaDB instance reading structured knowledge bases directly from Markdown files.

### 2. 🛡️ Production Security & Guardrails
* **Non-Root Execution:** All application containers execute as dedicated unprivileged users (`appuser:appgroup` UID/GID `10001`).
* **Principle of Least Privilege:** AWS Security Groups restrict SSH access strictly to the operator's public IP.
* **Origin Cloaking:** Cloudflare proxy masks the origin EC2 IP address to prevent direct DDoS attacks.
* **Zero Secret Leakage:** Strict separation of configuration and secrets via environment variables and masked GitHub Actions secrets.

### 3. ⚙️ Idempotent Infrastructure as Code (IaC)
* **Terraform:** Declaratively defines the complete AWS topology (VPC, Subnet, Internet Gateway, Route Tables, Security Groups, and EC2 Compute).
* **Ansible:** Fully idempotent server provisioning (Docker Engine installation, 2GB swap space allocation to prevent OOM, application deployment).
* **Cost Optimization:** EC2 instance managed on-demand with one-click operational scripts (`start-server.sh` / `stop-server.sh`), keeping monthly infrastructure costs at **$0.00**.

### 4. 📊 Full Observability Stack
* **Prometheus:** Scrapes real-time application throughput, request latency, and HTTP error distributions from `/metrics`.
* **Grafana:** Pre-provisioned dashboards using YAML datasources to visualize server load and inference performance with zero manual UI setup.

---

## 🧰 Technology Stack

| Domain | Technology | Purpose |
|---|---|---|
| **Frontend** | Vanilla HTML5 / CSS3 / ES6 | Fast, lightweight UI with interactive chat suggestions |
| **Reverse Proxy** | Nginx (`alpine`) | SSL termination point, static file serving, upstream proxying |
| **Backend API** | FastAPI (`python:3.10-slim`) | Async HTTP connection pooling, RAG orchestration |
| **LLM Engine** | Ollama (`llama3.1:8b`) | On-premise / containerized private LLM inference |
| **Cloud Fallback** | Groq Cloud LPU | Zero-cost serverless inference failover |
| **Vector Store** | ChromaDB (Embedded) | In-process vector database for resume context search |
| **Infrastructure** | Terraform | AWS Cloud VPC and EC2 provisioning |
| **Configuration** | Ansible | Automated host configuration and Docker orchestration |
| **CI/CD** | GitHub Actions | Automated linting, testing, image building, and SSH deployment |
| **Metrics** | Prometheus & Grafana | Endpoint performance and system telemetry |

---

## 📁 Repository Structure

```
ai-chatbot-devops/
├── .github/workflows/
│   └── deploy.yml              # CI/CD pipeline (Lint -> Test -> Build -> Deploy)
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
│   ├── index.html              # Portfolio single-page layout with chat widget
│   ├── style.css               # Modern dark-mode styling
│   ├── script.js               # Async fetch client with suggestion pills
│   └── nginx.conf              # Reverse proxy routing rules
├── terraform/
│   ├── main.tf                 # VPC, Subnet, IGW, Security Group, EC2
│   ├── variables.tf            # Configurable inputs (region, instance type)
│   └── outputs.tf              # Instance public IP and connection string
├── ansible/
│   ├── playbook.yml            # System updates, Docker install, swapfile, deploy
│   └── inventory.ini           # Target host inventory
├── monitoring/
│   ├── prometheus.yml          # Scrape configuration
│   └── grafana/                # Auto-provisioned datasources and dashboards
├── scripts/
│   ├── start-server.sh         # One-click on-demand EC2 starter
│   └── stop-server.sh          # One-click server teardown to save hours
├── docker-compose.yml          # Core service definitions (Frontend, Backend, Ollama)
├── docker-compose.dev.yml      # Local dev overrides (NVIDIA GPU runtime)
├── docker-compose.prod.yml     # Production overrides (Restart policies, limits)
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
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 4. Pull the LLM Model into Ollama
```bash
# Pull lightweight Llama 3.1 model into the Ollama container volume
docker exec -it chatbot-ollama ollama pull llama3.1:8b
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

---

## 🚢 Production Deployment Workflow

### 1. Infrastructure Provisioning (Terraform)
```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Export EC2 public IP into Ansible inventory
terraform output -raw ec2_public_ip > ../ansible/inventory.ini
```

### 2. Server Configuration & Deployment (Ansible)
```bash
cd ../ansible
ansible-playbook -i inventory.ini playbook.yml
```

### 3. Automated CI/CD (GitHub Actions)
Every push to `main` executes:
1. **Linting & Code Quality:** `flake8` and `black --check`.
2. **Automated Testing:** `pytest` on FastAPI routes and RAG logic.
3. **Container Image Build & Push:** Authenticates and pushes images to Docker Hub / GHCR.
4. **Zero-Downtime Deployment:** SSH execution on the EC2 instance pulling fresh images and restarting services.

---

## 👤 Author

**Haniff Kamal**
* Degree: Computer Engineering (Graduate 2025)
* Specialization: Audio Deepfake Detection & AI/ML Research
* Focus: DevOps, Cloud Infrastructure & MLOps Engineering
* Portfolio: [haniffkamal.my](https://haniffkamal.my)
* GitHub: [@HaniffKamal](https://github.com/HaniffKamal)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
