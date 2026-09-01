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

Web 项目的使用方式见 [`web/README.md`](web/README.md)，Agent 的当前实现范围见
[`agent/README.md`](agent/README.md)。

启动 Agent：

```bash
cp .env.example .env
uv run uvicorn resume_agent.api.main:app --app-dir agent/src --port 8010
```
