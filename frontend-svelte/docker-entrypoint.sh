#!/bin/sh
set -e

# Generate runtime config from environment variables
# This avoids sed-injection of env vars into built JS
cat > /usr/share/nginx/html/config.json <<EOCONFIG
{
  "apiBaseUrl": "${VITE_API_BASE_URL:-http://localhost:8000}"
}
EOCONFIG

exec "$@"
