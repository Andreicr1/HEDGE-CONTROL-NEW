#!/usr/bin/env bash
# Checks if schema.d.ts is in sync with the backend OpenAPI spec.
# Requires backend to be running at $API_BASE_URL (default: http://localhost:8000)
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
SCHEMA_FILE="src/lib/api/schema.d.ts"
TMP_FILE="/tmp/schema-check.d.ts"

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "ERROR: $SCHEMA_FILE not found. Run 'npm run api:types' first."
  exit 1
fi

echo "Fetching OpenAPI spec from ${API_BASE_URL}/openapi.json ..."
npx openapi-typescript "${API_BASE_URL}/openapi.json" -o "$TMP_FILE"

if diff -q "$SCHEMA_FILE" "$TMP_FILE" > /dev/null 2>&1; then
  echo "OK: schema.d.ts is in sync with backend."
  rm -f "$TMP_FILE"
  exit 0
else
  echo "DRIFT DETECTED: schema.d.ts is out of sync with backend."
  echo ""
  echo "Diff (current vs generated):"
  diff --unified "$SCHEMA_FILE" "$TMP_FILE" || true
  echo ""
  echo "Run 'npm run api:types' to regenerate."
  rm -f "$TMP_FILE"
  exit 1
fi
