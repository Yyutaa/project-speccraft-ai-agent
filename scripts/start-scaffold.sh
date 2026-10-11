#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT="$REPO_ROOT/apps/web"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3.12 || true)}"
VENV_ROOT="$REPO_ROOT/.venv"

available_port() {
  local port="$1"
  while nc -z 127.0.0.1 "$port" >/dev/null 2>&1; do
    port=$((port + 1))
  done
  printf '%s' "$port"
}

API_PORT="$(available_port "${API_PORT:-8765}")"
WEB_PORT="$(available_port "${WEB_PORT:-5173}")"

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "需要 Python 3.12。"
  exit 1
fi

if [[ ! -x "$VENV_ROOT/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_ROOT"
fi

if ! "$VENV_ROOT/bin/python" -c "import fastapi, deliveryflow_speccraft" >/dev/null 2>&1; then
  "$VENV_ROOT/bin/python" -m pip install \
    -e "$REPO_ROOT/packages/contracts[dev]" \
    -e "$REPO_ROOT/packages/agent-kernel" \
    -e "$REPO_ROOT/packages/speccraft"
fi

if [[ ! -d "$WEB_ROOT/node_modules" ]]; then
  npm --prefix "$WEB_ROOT" install
fi

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  [[ -z "${WEB_PID:-}" ]] || kill "$WEB_PID" 2>/dev/null || true
  [[ -z "${API_PID:-}" ]] || kill "$API_PID" 2>/dev/null || true
  wait "${WEB_PID:-}" "${API_PID:-}" 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT INT TERM

(
  cd "$REPO_ROOT"
  exec "$VENV_ROOT/bin/uvicorn" apps.api.main:app --host 127.0.0.1 --port "$API_PORT"
) &
API_PID=$!

(
  cd "$WEB_ROOT"
  VITE_API_TARGET="http://127.0.0.1:$API_PORT" exec npm run dev -- --port "$WEB_PORT"
) &
WEB_PID=$!

echo "SpecCraft 项目脚手架已启动"
echo "前端: http://127.0.0.1:$WEB_PORT"
echo "API:  http://127.0.0.1:$API_PORT/docs"
echo "按 Ctrl+C 停止"

wait "$API_PID" "$WEB_PID"
