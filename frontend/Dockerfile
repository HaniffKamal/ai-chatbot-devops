# ==============================================================================
# Frontend Image: Static Chatbot Client + Nginx Reverse Proxy
# ==============================================================================
# Architecture & Security Guardrails:
#   1. Unprivileged Runtime: runs as UID 101 (Rule 1.2: never run as root).
#   2. Port 8080: the unprivileged image cannot bind 80; Compose maps host 80 -> 8080.
#   3. Immutable Artifact: assets and config are baked in, so what runs in
#      production is exactly what was built and tagged in CI.
#   4. Explicit COPY list: no README, Dockerfile, or stray files reach the web root.
# ==============================================================================

FROM nginx/nginx-unprivileged:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY index.html style.css script.js marked.min.js purify.min.js /usr/share/nginx/html/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
