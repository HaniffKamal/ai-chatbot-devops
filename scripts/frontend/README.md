# Frontend & Nginx Reverse Proxy Architecture

This directory contains the client-facing static portfolio assets and the Nginx reverse proxy configuration.

---

## 1. Overview & Purpose

Nginx serves as the single entrypoint on **Port 80**, performing two distinct roles:
1. **Static Web Server:** Serves HTML, CSS, JavaScript, and asset files with minimal memory footprint (~15 MB RAM).
2. **Reverse Proxy:** Safely forwards API requests (`/api/*`) and health checks (`/health`) to the private FastAPI backend container on port 8000.

---

## 2. Request Routing Architecture

```
User Browser
     │
     │ HTTP Port 80
     ▼
┌────────────── Nginx Reverse Proxy ──────────────┐
│                                                 │
│  location /       ──► Serves index.html, CSS    │
│  location /api/   ──► Proxies to backend:8000   │
│  location /health ──► Proxies to backend:8000   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 3. Configuration Breakdown (`nginx.conf`)

### Route 1: Static Frontend Delivery (`location /`)
* **`root /usr/share/nginx/html;`**: Directory inside the container where static assets live.
* **`index index.html;`**: Serves `index.html` by default when root is accessed.
* **`try_files $uri $uri/ /index.html;`**:
  * Tries exact file (`$uri`).
  * Tries directory index (`$uri/`).
  * Falls back to `/index.html` to eliminate 404 errors during client-side navigation.

### Route 2: Reverse Proxy (`location /api/`)
* **`proxy_pass http://backend:8000/api/;`**: Forwards requests to the backend using Docker's internal DNS resolution.
* **`proxy_http_version 1.1;`**: Enables HTTP/1.1 persistent connections for lower latency and token streaming.
* **`proxy_read_timeout 120s;`**: LLM buffer allowing up to 120 seconds for text generation without triggering `504 Gateway Timeout`.
* **`proxy_connect_timeout 10s;`**: Fails fast if the backend container is unreachable.

### Route 3: Healthcheck (`location /health`)
* Forwards directly to FastAPI's `/health` endpoint to allow external monitoring services (AWS, Docker, Prometheus) to check application readiness.

---

## 4. Security Hardening

* **`server_tokens off;`**: Hides the Nginx version number from HTTP response headers, preventing vulnerability scanning.
* **Network Cloaking**: The FastAPI backend (`:8000`) and Ollama (`:11434`) are isolated behind Nginx and never directly exposed to the public internet.
* **Origin Preservation Headers**:
  * `Host`: Preserves requested domain name.
  * `X-Real-IP`: Passes real client IP for backend rate-limiting.
  * `X-Forwarded-For`: Maintains client-to-proxy audit trail.
  * `X-Forwarded-Proto`: Informs backend if user connected over HTTP or HTTPS.
