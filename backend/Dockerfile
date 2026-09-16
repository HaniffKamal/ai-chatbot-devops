# ==============================================================================
# Multi-Stage Dockerfile for FastAPI Backend
# ==============================================================================
# Architecture:
#   Stage 1 (builder): Installs build tools and compiles Python wheel packages.
#   Stage 2 (runner):  Lightweight production image containing ONLY runtime files,
#                      excluding compilers to keep the image slim and secure.
# ==============================================================================

# ==============================================================================
# STAGE 1: Builder (Build & Compile Dependencies)
# ==============================================================================
FROM python:3.10-slim AS builder

# PYTHONDONTWRITEBYTECODE=1: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED=1: Flushes logs directly to stdout/stderr without buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build-essential (gcc, g++, make) needed for compiling any C-extensions in Python wheels
# Clean apt cache immediately to keep this intermediate layer clean
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements.txt first to take advantage of Docker layer caching
COPY requirements.txt .

# Install dependencies into an isolated directory (/install)
# --no-cache-dir: Prevents storing pip download cache inside the image
# --prefix=/install: Installs libraries to /install so we can copy them in Stage 2 cleanly
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ==============================================================================
# STAGE 2: Runner (Minimal Secure Production Runtime)
# ==============================================================================
FROM python:3.10-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.10/site-packages:$PYTHONPATH"

# Install 'curl' strictly for the container HEALTHCHECK instruction below
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Security Guardrail: Non-Root Execution
# ------------------------------------------------------------------------------
# Running as root inside a container is a security vulnerability (risk of container escape).
# We create a dedicated, unprivileged system user and group (UID/GID: 10001).
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

WORKDIR /app

# Copy installed Python packages from the builder stage (no compiler tools brought over)
COPY --from=builder /install /install

# Copy application source code
COPY ./app /app/app

# Change ownership of /app to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Document that this container listens on port 8000
EXPOSE 8000

# ------------------------------------------------------------------------------
# Healthcheck Instruction
# ------------------------------------------------------------------------------
# Allows Docker, Docker Compose, and Kubernetes to monitor container health.
# If /health returns non-200 three times in a row, Docker flags the container as 'unhealthy'.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Exec form (JSON array) ensures uvicorn runs as PID 1, allowing it to receive OS signals (SIGTERM)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
