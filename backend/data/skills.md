# Technical Skills & Competencies

## Cloud & Infrastructure as Code (IaC)
- **Amazon Web Services (AWS):** EC2, VPC, Internet Gateways, Route 53, Security Groups, IAM least privilege, S3, Elastic IPs. Focus on AWS Free Tier preservation and strict cost minimization.
- **Terraform:** Declarative infrastructure provisioning, remote state locking, modular architecture, idempotency (`terraform fmt`, `terraform validate`).
- **Ansible:** Automated server configuration, multi-service provisioning playbooks, idempotent state enforcement (`changed=0` on re-runs).

## DevOps & Containerization
- **Docker & Docker Compose:** Multi-stage minimal builds (`python:slim`, `alpine`), non-root container security (`appuser:10001`), persistent volumes, internal bridge networks, health checks.
- **CI/CD Pipelines:** GitHub Actions for automated linting, test suites, Docker image building, and SSH-based zero-downtime deployment.
- **Web & Reverse Proxy:** Nginx configuration, reverse proxying, SSL/TLS termination, CORS management, custom security headers, rate limiting.

## AI, LLM & MLOps
- **Local LLM Inference:** Ollama container orchestration, native NVIDIA GPU acceleration (CUDA, NVIDIA Container Toolkit), model quantizations.
- **Vector Search & RAG:** In-process ChromaDB vector database, semantic embeddings, document chunking, prompt augmentation, contextual grounding.
- **Cloud Fallback Inference:** Groq Cloud API integration for resilient dual-engine failover.
- **Machine Learning Tooling:** PyTorch, Torchaudio, Librosa, Scikit-learn, Hugging Face Transformers.

## Programming & Software Engineering
- **Python:** Modern asynchronous programming (`asyncio`, `httpx`), FastAPI, Pydantic data validation, Uvicorn ASGI server, Pytest test suites.
- **Linux & Shell:** Linux system administration (Ubuntu/Debian), Bash automation scripting, systemd services, SSH key security, process management.
- **Git & GitHub:** Trunk-based development, semantic/conventional commits, branch protection rules.

## Observability & Monitoring
- **Prometheus:** Metrics collection, custom Prometheus FastAPI instrumentator, application latency and throughput tracking.
- **Grafana:** Automated datasource and dashboard provisioning via YAML/JSON, real-time container health and request telemetry.
