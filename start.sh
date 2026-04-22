#!/usr/bin/env bash
# kbgen — start script.
#
# Port precedence:
#   1. --port <n>           CLI arg
#   2. $PORT or $BACKEND_PORT env var
#   3. 8004 (App Registry dev default)
set -euo pipefail

cd "$(dirname "$0")"

PORT_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT_ARG="$2"; shift 2 ;;
    *)
      echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

RESOLVED_PORT="${PORT_ARG:-${PORT:-${BACKEND_PORT:-8004}}}"

source ~/.appregistry/venvs/ai-full/bin/activate
exec uvicorn src.main:app --host 0.0.0.0 --port "$RESOLVED_PORT" --reload
