# Resume Agent · Frontend

Agent 操作台的 React SPA，覆盖完整流程（Run 管理、Human Gate ①②、在线查看）。旧版
`agent/templates/*.html` Jinja 页面已下线，这是唯一的前端。视觉风格已对齐 `design/`
目录的设计稿，中英文双语（右下角切换）。

## 开发

一键同时起前端+后端见根目录 [`README.md`](../../README.md)（`./dev.sh`）；分开跑的话，
后端先起（另开一个终端，仓库根目录）：

```bash
uv run uvicorn resume_agent.api.main:app --app-dir agent/src --host 127.0.0.1 --port 8010
```

然后：

```bash
pnpm install
pnpm dev
```

打开 <http://localhost:5173>。开发环境下 `/api` 和 `/preview` 会被 Vite 代理到
`127.0.0.1:8010`（见 `vite.config.ts`），前端代码里一律用相对路径请求，不需要处理跨域。

## 现状（Phase 1 完成，2026-09-02）

- Runs 列表（分页）、新建 Run、Run 详情（SSE 实时状态/进度/过程产出/Activity Log/Notes）、
  在线查看（版本选择 + 语言切换 + iframe 嵌入 `/preview`）
- **Human Gate ①**：编辑策略定位/关键词/action 列表（保留或丢弃、调整优先级和说明），保存或
  直接批准
- **Human Gate ②**：批准导出 / 恢复原始版本 / 拒绝，以及"高级：人工微调"结构化 Patch 构建器
  （选字段 → 按字段类型出对应的替换/隐藏/恢复/重排序表单，不用手写 JSON）
- LangSmith 外链（配置了 `RESUME_AGENT_LANGSMITH_PROJECT_URL` 才显示）

已知缺口（记录在根目录 `FRONTEND_ROADMAP.md`）：
- 前端还没有测试框架
- Phase 2（Run 搜索/分组/标记最终版本/归档/跨 run 对比）还没开始

## 构建

```bash
pnpm build
```
