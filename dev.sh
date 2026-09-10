#!/usr/bin/env bash
# 一键启动 Agent 后端（FastAPI，8010）和前端（Vite，5173）。
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

uv run uvicorn resume_agent.api.main:app --app-dir agent/src --host 127.0.0.1 --port 8010 --reload --reload-dir agent/src &
BACKEND_PID=$!

BACKEND_READY=""
for _ in {1..120}; do
  if curl --fail --silent --show-error http://127.0.0.1:8010/ >/dev/null 2>&1; then
    BACKEND_READY="true"
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    wait "$BACKEND_PID"
    exit 1
  fi
  sleep 0.25
done

if [ -z "$BACKEND_READY" ]; then
  echo "后端未能在 30 秒内就绪，请检查启动日志。" >&2
  exit 1
fi

(cd agent/frontend && pnpm dev) &
FRONTEND_PID=$!

cat <<'EOF'

────────────────────────────────────────────────
  Resume Generator 已启动

  前端工作台  http://localhost:5173
  后端 API    http://127.0.0.1:8010
  API 文档    http://127.0.0.1:8010/docs

  请在浏览器中打开前端工作台开始使用。
  按 Ctrl+C 可安全停止前端、后端及其子进程。
────────────────────────────────────────────────
EOF

wait "$BACKEND_PID" "$FRONTEND_PID"
