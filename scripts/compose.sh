#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/compose.sh [compose-subcommand] [args...]
  ./scripts/compose.sh -- [compose args...]

Description:
  Thin wrapper around "docker compose" / "podman compose".
  - Auto-detects engine in this order: docker, then podman
  - Passes all compose arguments through unchanged
  - Supports "--" to pass explicit compose args directly

Examples:
  ./scripts/compose.sh up -d --build
  ./scripts/compose.sh logs -f
  ./scripts/compose.sh -- -f compose.yaml config

Environment:
  CONTAINER_ENGINE   Optional override (docker or podman)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ENGINE="${CONTAINER_ENGINE:-}"
if [[ -z "$ENGINE" ]]; then
  if command -v docker >/dev/null 2>&1; then
    ENGINE="docker"
  elif command -v podman >/dev/null 2>&1; then
    ENGINE="podman"
  else
    echo "Error: neither docker nor podman was found in PATH." >&2
    exit 1
  fi
fi

if [[ "$ENGINE" != "docker" && "$ENGINE" != "podman" ]]; then
  echo "Error: unsupported CONTAINER_ENGINE '$ENGINE' (expected: docker or podman)." >&2
  exit 2
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

exec "$ENGINE" compose "$@"
