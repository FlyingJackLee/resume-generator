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

React 操作台（`agent/frontend/`）额外需要 Node.js 和 `pnpm`（`corepack enable` 或
`npm install -g pnpm` 都可以装）；`web/` 不需要 Node。

Web 项目的使用方式见 [`web/README.md`](web/README.md)，Agent 的当前实现范围见
[`agent/README.md`](agent/README.md)，React 操作台见
[`agent/frontend/README.md`](agent/frontend/README.md)。

## 启动 Agent（本地试跑）

首次运行需要装依赖、填 API Key：

```bash
cp .env.example .env
# 编辑 .env，至少填写 RESUME_AGENT_API_KEY
uv sync
cd agent/frontend && pnpm install && cd ../..
```

之后一键启动前后端（同一个终端，`Ctrl+C` 一次性关闭两个进程）：

```bash
./dev.sh
```

后端 <http://127.0.0.1:8010>（纯 API，不再提供网页）、前端 <http://localhost:5173>
（Vite 会把 API 请求代理到 8010，不用改配置）。

需要分开跑（比如只测后端接口）时，两个进程也可以照旧各自起：

```bash
uv run uvicorn resume_agent.api.main:app --app-dir agent/src --host 127.0.0.1 --port 8010
# 另开一个终端
cd agent/frontend && pnpm dev
```

> 如果 8010/5173 端口已被占用（比如 AI 助手验证功能时临时起的服务忘了关），先释放端口再自己起：
>
> ```bash
> lsof -ti:8010,5173 | xargs kill
> ```

详细说明见 [`agent/README.md`](agent/README.md) 和 [`agent/frontend/README.md`](agent/frontend/README.md)；
开发进度和分期规划记在 [`FRONTEND_ROADMAP.md`](FRONTEND_ROADMAP.md) 里。
