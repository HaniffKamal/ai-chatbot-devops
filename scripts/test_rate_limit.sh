#!/usr/bin/env bash
# ==============================================================================
# Rate Limiting Diagnostic & Verification Script
# ==============================================================================
# Sends 10 rapid concurrent requests to the Nginx reverse proxy /api/chat.
# Expected behavior:
#   - First ~5-6 requests: HTTP 200 (allowed by burst=5)
#   - Subsequent requests: HTTP 429 Too Many Requests (rate-limited by Nginx)
# ==============================================================================

TARGET_URL="http://localhost/api/chat"
echo "========================================================"
echo "Testing Rate Limiting against: $TARGET_URL"
echo "Sending 10 concurrent requests..."
echo "========================================================"

for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" -X POST "$TARGET_URL" \
    -H "Content-Type: application/json" \
    -d '{"message": "ping"}' &
done

wait
echo "========================================================"
echo "Test completed. You should observe HTTP 200 followed by HTTP 429 (Too Many Requests)."
echo "========================================================"
