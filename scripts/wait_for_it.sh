#!/usr/bin/env bash
# Wait for a host:port to become available
set -euo pipefail

HOST="$1"
PORT="$2"
TIMEOUT="${3:-30}"
START=$(date +%s)

while true; do
  if nc -z "$HOST" "$PORT"; then
    exit 0
  fi
  if [ $(( $(date +%s) - START )) -ge "$TIMEOUT" ]; then
    echo "Timed out waiting for $HOST:$PORT" >&2
    exit 1
  fi
  sleep 1
done
