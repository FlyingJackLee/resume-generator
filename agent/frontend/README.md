# Resume Agent · Frontend

Agent 操作台的 React SPA，取代 `agent/templates/*.html` 那套 Jinja 页面（迁移完成前两者
共存，互不影响）。视觉风格尚未设计，目前是纯功能性样式。

## 开发

后端要先跑起来（另开一个终端，仓库根目录）：

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

## 现状（Milestone 4 已完成，2026-09-02）

已经覆盖完整流程，不再需要跳回旧版页面：

- Runs 列表（分页）、新建 Run、Run 详情（SSE 实时状态/进度/过程产出/Activity Log）、在线查看
  （版本选择 + 语言切换 + iframe 嵌入 `/preview`）
- **Human Gate ①**：编辑策略定位/关键词/action 列表（保留或丢弃、调整优先级和说明），保存或
  直接批准
- **Human Gate ②**：批准导出 / 恢复原始版本 / 拒绝，以及"高级：人工微调"结构化 Patch 构建器
  （选字段 → 按字段类型出对应的替换/隐藏/恢复/重排序表单，不用手写 JSON）

已知缺口（不影响使用，记录在根目录 `FRONTEND_ROADMAP.md`）：
- 人工 Patch 提交后，"最终 Diff" 卡片不会显示这次改动（后端 `manual_edit()` 没有重新计算
  `final_diff.json`）——新旧两套页面都有这个问题，可以通过"在线查看"或校验状态间接确认已生效
- 前端还没有测试框架
- Phase 2（Run 搜索/分组/标记最终版本/归档/跨 run 对比）还没开始

## 构建

```bash
pnpm build
```
