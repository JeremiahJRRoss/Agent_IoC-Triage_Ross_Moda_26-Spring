#!/usr/bin/env bash
set -euo pipefail

ENGINE="${CONTAINER_ENGINE:-}"
if [ -z "$ENGINE" ]; then
  if command -v docker >/dev/null 2>&1; then
    ENGINE="docker"
  elif command -v podman >/dev/null 2>&1; then
    ENGINE="podman"
  else
    echo "Neither docker nor podman found." >&2
    exit 1
  fi
fi

SUBCOMMAND="${1:-up}"
shift || true

case "$SUBCOMMAND" in
  up|down|build|logs|ps|pull|config)
    exec "$ENGINE" compose "$SUBCOMMAND" "$@"
    ;;
  test)
    exec "$ENGINE" compose run --rm flowrun pytest "$@"
    ;;
  *)
    echo "Usage: ./scripts/compose.sh {up|down|build|test|logs|ps|pull|config} [args...]"
    exit 1
    ;;
esac
