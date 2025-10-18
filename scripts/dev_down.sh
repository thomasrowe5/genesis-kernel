#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker-compose >/dev/null 2>&1; then
  echo "docker-compose is required" >&2
  exit 1
fi

docker-compose down -v
