#!/bin/bash
# Поднимает весь продакшен-стек AI-Технолог (backend + Caddy + Cloudflare
# Tunnel) как набор фоновых процессов. Запускается launchd-агентом
# ru.aitehnolog.stack.start в 09:00 по Europe/Moscow (см. README.md рядом).
set -euo pipefail

ROOT_DIR="/Users/bdd/Documents/Работа/Аэромобильность/4. Цифровое производство"
BACKEND_DIR="$ROOT_DIR/dev/backend"
DEPLOY_DIR="$ROOT_DIR/dev/deploy"
LOG_DIR="$DEPLOY_DIR/logs"
PID_DIR="$DEPLOY_DIR/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

is_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

# --- backend (uvicorn) ---
if ! is_running "$PID_DIR/uvicorn.pid"; then
  cd "$BACKEND_DIR"
  nohup .venv/bin/uvicorn app.main:app --port 8000 >> "$LOG_DIR/uvicorn.log" 2>&1 &
  echo $! > "$PID_DIR/uvicorn.pid"
fi

# --- Caddy (раздача фронтенда + прокси /api) ---
if ! is_running "$PID_DIR/caddy.pid"; then
  cd "$DEPLOY_DIR"
  nohup caddy run --config Caddyfile >> "$LOG_DIR/caddy.log" 2>&1 &
  echo $! > "$PID_DIR/caddy.pid"
fi

# --- Cloudflare Tunnel ---
if ! is_running "$PID_DIR/cloudflared.pid"; then
  nohup cloudflared tunnel run ai-tehnolog >> "$LOG_DIR/cloudflared.log" 2>&1 &
  echo $! > "$PID_DIR/cloudflared.pid"
fi
