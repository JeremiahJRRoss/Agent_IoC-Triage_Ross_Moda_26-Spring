#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/compose.sh <compose-subcommand> [args...]
  ./scripts/compose.sh [--] [compose-args...]

Examples:
  ./scripts/compose.sh up -d --build
  ./scripts/compose.sh logs -f
  ./scripts/compose.sh -- config --services

Notes:
  - Auto-detects engine in this order: docker, then podman.
  - Set CONTAINER_ENGINE to override detection.
  - Everything after '--' is passed directly to '<engine> compose'.
USAGE
}

detect_engine() {
  if [ -n "${CONTAINER_ENGINE:-}" ]; then
    printf '%s\n' "$CONTAINER_ENGINE"
    return 0
  fi

  if command -v docker >/dev/null 2>&1; then
    printf '%s\n' docker
    return 0
  fi

  if command -v podman >/dev/null 2>&1; then
    printf '%s\n' podman
    return 0
  fi

  echo "Error: neither 'docker' nor 'podman' was found in PATH." >&2
  return 1
}

if [ "$#" -eq 0 ]; then
  usage
  exit 0
fi

case "${1:-}" in
  -h|--help|help)
    usage
    exit 0
    ;;
esac

if [ "${1:-}" = "--" ]; then
  shift
fi

ENGINE="$(detect_engine)"

# Intentionally avoid exec so this script can directly propagate compose's exit code.
"$ENGINE" compose "$@"
exit $?
