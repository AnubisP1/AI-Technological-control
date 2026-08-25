#!/bin/bash
# Останавливает весь продакшен-стек AI-Технолог. Запускается launchd-агентом
# ru.aitehnolog.stack.stop в 20:00 по Europe/Moscow (см. README.md рядом).
set -uo pipefail

DEPLOY_DIR="/Users/bdd/Documents/Работа/Аэромобильность/4. Цифровое производство/dev/deploy"
PID_DIR="$DEPLOY_DIR/pids"

stop_pid_file() {
  local pid_file="$1"
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
    fi
    rm -f "$pid_file"
  fi
}

stop_pid_file "$PID_DIR/cloudflared.pid"
stop_pid_file "$PID_DIR/caddy.pid"
stop_pid_file "$PID_DIR/uvicorn.pid"
