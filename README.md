# resume-generator

简历生成项目，Web 简历与后续 Agent 能力分开维护。

## 项目结构

- `web/`：当前可用的双语 Web/PDF 简历生成器
- `agent/`：预留给后续基于正式 spec 开发的简历 Agent
- `backup/`：停止维护的旧版 LaTeX 工程归档

`web/data/resume.yaml` 是唯一 Master Resume。Web 构建器直接读取它；Agent 只读取它，
并在内存工作副本中生成稳定 ID、事实引用和目标版本。所有目标版本只能写入
`agent/data/runs/<run_id>/`，不得覆盖 Master Resume。

## 环境

```bash
uv sync
uv run playwright install chromium
uv run pytest
```

新版 React 操作台（`agent/frontend/`）额外需要 Node.js 和 `pnpm`（`corepack enable` 或
`npm install -g pnpm` 都可以装）；旧版 Jinja 页面和 `web/` 不需要 Node。

Web 项目的使用方式见 [`web/README.md`](web/README.md)，Agent 的当前实现范围见
[`agent/README.md`](agent/README.md)，正在开发中的 React 操作台见
[`agent/frontend/README.md`](agent/frontend/README.md)。

## 启动 Agent（本地试跑）

1. 起后端（需要一个真实的 LLM API Key，DeepSeek/OpenAI-compatible 均可）：

   ```bash
   cp .env.example .env
   # 编辑 .env，至少填写 RESUME_AGENT_API_KEY
   uv sync
   uv run uvicorn resume_agent.api.main:app --app-dir agent/src --host 127.0.0.1 --port 8010
   ```

2. 两种界面任选（可以同时开，互不影响，数据是同一份）：

   - **旧版页面**（够用、无需额外安装）：浏览器直接打开 <http://127.0.0.1:8010>
   - **新版 React 操作台**（正在替换旧版，Run 列表/新建/实时进度/Human Gate①②/在线查看
     都已可用；开发中，样式还很朴素）：另开一个终端

     ```bash
     cd agent/frontend
     pnpm install
     pnpm dev
     ```

     浏览器打开 <http://localhost:5173>（Vite 会把 API 请求代理到 8010，不用改配置）

详细说明见 [`agent/README.md`](agent/README.md) 和 [`agent/frontend/README.md`](agent/frontend/README.md)；
两套前端目前分别停在哪个阶段、还差什么，记在 [`FRONTEND_ROADMAP.md`](FRONTEND_ROADMAP.md) 里。
