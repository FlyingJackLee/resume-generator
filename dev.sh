#!/usr/bin/env bash
# 一键启动 Agent 后端（FastAPI，8010）+ 前端（Vite，5173）。
# Ctrl+C 一次性关闭两个进程。
set -euo pipefail
set -m  # 让每个后台任务拿到独立进程组，这样才能把 pnpm dev 派生出的孙进程（vite）一起杀掉

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

if [ ! -f .env ]; then
  echo "未找到 .env，先执行: cp .env.example .env 并填写 RESUME_AGENT_API_KEY" >&2
  exit 1
fi

if [ ! -d agent/frontend/node_modules ]; then
  echo "未安装前端依赖，先执行: cd agent/frontend && pnpm install" >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "正在关闭..."
  [ -n "$BACKEND_PID" ] && kill -- "-$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill -- "-$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn resume_agent.api.main:app --app-dir agent/src --host 127.0.0.1 --port 8010 &
BACKEND_PID=$!

(cd agent/frontend && pnpm dev) &
FRONTEND_PID=$!

echo "后端: http://127.0.0.1:8010"
echo "前端: http://localhost:5173"
echo "按 Ctrl+C 同时关闭两个进程"

wait "$BACKEND_PID" "$FRONTEND_PID"
