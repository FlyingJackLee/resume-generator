# Resume Agent

基于 `AI_Resume_Compiler_Spec_V1.1.docx` 实现的事实安全简历编译器。

## 已实现

- 将 `web/data/resume.yaml` 作为只读且唯一的 Master Resume。
- 在内存工作副本中生成稳定 ID、facts 和 `supported_by`，不迁移或重写 Master。
- Pydantic Patch 契约：`replace / reorder / hide / restore`。
- ID 路径解析、白名单 Patch Engine、受保护字段检查。
- 对事实引用、技术词、数字和角色强度进行 program-first 校验。
- 结构化 Diff 和以 JD 标识命名的 run 输出，例如
  `google_ai_agent_resume.yaml`。
- 根目录 `pyproject.toml` 和 `uv.lock` 统一管理 Web 与 Agent 依赖。
- DeepSeek/OpenAI-compatible Provider，配置项不绑定特定厂商。
- JD Analyzer → Matcher → HR Reviewer → Rewrite Strategy 的 LangGraph 分析图。
- Human Gate ① 后才运行 Editor → Patch → Validator → Hiring Manager 编译图。
- Validator/Hiring Manager 最多触发两次 Editor 尝试，Critical/High 事实问题阻断导出。
- FastAPI、简单操作页面和 spec 中的 run/strategy/final/diff/manual-edit API。
- Human Gate ② 支持批准、拒绝、恢复原始版本和受事实约束的人工 Patch。
- Run 列表分页、事件时间线（`events.jsonl`）、SSE 实时状态流、简历预览渲染端点
  （复用 `web/` 的排版逻辑）、简历结构树/事实查询端点——这些是给 `agent/frontend/`
  新版操作台用的 API，见下方"新版前端"。

## 新版前端（agent/frontend/，开发中）

正在用 React SPA 替换 `agent/templates/*.html` 这套 Jinja 页面，两者当前共存。已经覆盖：
Run 列表、新建 Run、实时进度（SSE）、Human Gate ①（策略编辑审批）、Human Gate ②（批准/驳回/
恢复原始版本 + 结构化人工 Patch 构建器）、在线查看。启动方式和现状见
[`agent/frontend/README.md`](frontend/README.md)。分期规划和已知缺口见根目录
[`FRONTEND_ROADMAP.md`](../FRONTEND_ROADMAP.md)。

## 配置与启动

```bash
cp .env.example .env
# 编辑 .env，至少填写 RESUME_AGENT_API_KEY
uv sync
uv run uvicorn resume_agent.api.main:app --app-dir agent/src --host 127.0.0.1 --port 8010
```

浏览器打开 <http://127.0.0.1:8010>，填写类似 `Google AI Agent` 的 JD 标识并粘贴
JD。最终批准后，文件写入：

```text
agent/data/runs/<run_id>/google_ai_agent_resume.yaml
```

主要环境变量：

- `RESUME_AGENT_API_KEY`
- `RESUME_AGENT_BASE_URL`，DeepSeek 默认为 `https://api.deepseek.com`
- `RESUME_AGENT_MODEL`，默认为 `deepseek-chat`
- `RESUME_AGENT_HIRING_THRESHOLD`，默认为 `85`
- `RESUME_AGENT_MAX_ITERATIONS`，默认为 `2`
- `RESUME_AGENT_LOG_LEVEL`，默认为 `INFO`；设为 `DEBUG` 可记录 LangGraph 事件、
  每个节点输出、完整模型请求和原始模型响应。
- `RESUME_AGENT_LOG_FILE`，默认为 `agent/data/logs/resume-agent.log`，使用滚动日志。

> `DEBUG` 日志会包含 JD、简历工作副本、模型返回和 Patch，适合本机排障，但可能包含
> 联系方式等个人信息。日志永远不会记录 API Key；分享日志前仍应先检查和脱敏。

## 开发命令

```bash
uv sync
uv run pytest agent/tests
```
