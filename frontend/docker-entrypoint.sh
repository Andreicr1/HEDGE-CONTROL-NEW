#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Runtime env-var injection
# Replaces the build-time placeholder __HC_API_BASE_URL__ in every JS file
# with the value of the HC_API_BASE_URL environment variable.
# ---------------------------------------------------------------------------

HC_API_BASE_URL="${HC_API_BASE_URL:-}"

if [ -n "$HC_API_BASE_URL" ]; then
  echo "[entrypoint] Injecting HC_API_BASE_URL = ${HC_API_BASE_URL}"
  find /usr/share/nginx/html -type f -name '*.js' \
    -exec sed -i "s|__HC_API_BASE_URL__|${HC_API_BASE_URL}|g" {} +
else
  echo "[entrypoint] WARNING: HC_API_BASE_URL is not set – API calls will use relative paths"
  find /usr/share/nginx/html -type f -name '*.js' \
    -exec sed -i 's|__HC_API_BASE_URL__||g' {} +
fi

# Hand off to nginx (or whatever CMD is set)
exec "$@"
