#!/usr/bin/env bash
# Verify ECharts chunk gzipped size stays under budget (200KB).
# Run after `npm run build` in CI.
set -euo pipefail

BUILD_DIR=".svelte-kit/output/client/_app/immutable/chunks"
BUDGET_KB=200

# Find the echarts chunk (largest chunk, >400KB raw)
echarts_chunk=$(find "$BUILD_DIR" -name '*.js' -size +400k 2>/dev/null | head -1)

if [ -z "$echarts_chunk" ]; then
  echo "⚠ No large chunk found (echarts may have been split). Checking all chunks..."
  max_gz=0
  for f in "$BUILD_DIR"/*.js; do
    gz_size=$(gzip -c "$f" | wc -c)
    gz_kb=$((gz_size / 1024))
    if [ "$gz_kb" -gt "$max_gz" ]; then
      max_gz=$gz_kb
      max_file=$(basename "$f")
    fi
  done
  echo "Largest chunk: $max_file = ${max_gz}KB gzipped"
  if [ "$max_gz" -gt "$BUDGET_KB" ]; then
    echo "✗ FAIL: ${max_file} exceeds ${BUDGET_KB}KB budget (${max_gz}KB)"
    exit 1
  fi
  echo "✓ All chunks under ${BUDGET_KB}KB budget"
  exit 0
fi

gz_size=$(gzip -c "$echarts_chunk" | wc -c)
gz_kb=$((gz_size / 1024))
chunk_name=$(basename "$echarts_chunk")

echo "ECharts chunk: $chunk_name = ${gz_kb}KB gzipped (budget: ${BUDGET_KB}KB)"

if [ "$gz_kb" -gt "$BUDGET_KB" ]; then
  echo "✗ FAIL: ECharts chunk exceeds ${BUDGET_KB}KB budget"
  exit 1
fi

echo "✓ ECharts chunk within budget"
