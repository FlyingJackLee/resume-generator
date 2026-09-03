# Resume Generator

[English](README.md) · [简体中文](README.zh-CN.md)

> 一个本地优先的双语简历工作台：维护基线简历、基于 JD 安全定制版本，并导出专业 A4 HTML/PDF 简历。

Resume Generator 将结构化 YAML 简历与 AI 辅助审核流程结合，面向单人本地使用。简历数据始终保留在你的设备上，所有 AI 生成的修改均可追溯到基线事实。

## 核心功能

- **基线简历工作台**：在浏览器中编辑唯一的基线简历；明确发布后才生效，并可回退至任一已发布版本。
- **双语简历**：在同一份数据中维护中英文内容，独立预览和导出任意语言版本。
- **事实安全的 JD 定制**：解析职位描述、人工审核改写策略、用基线事实校验修改，最后再批准目标简历。
- **全局简历模板**：可切换内置模板或导入纯 CSS 模板包；选择会统一应用到所有预览和导出。
- **便携导出**：下载 A4 HTML、PDF，以及当前已发布的 `resume.yaml`。
- **本地优先**：不需要数据库、认证服务或远程存储。

## 工作流

```text
基线简历 ── 编辑草稿 ── 发布 ──> web/data/resume.yaml
   │                                  │
   ├── 版本历史 / 回退                  └── 唯一事实来源
   │
   └── ATS JD 匹配 ── 策略审批 ── 事实校验 ── 最终版本
                                          │
                                          └── HTML / PDF 导出
```

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 20+ 与 `pnpm`
- 用于 PDF 生成的 Chromium

### 安装

```bash
cp .env.example .env
# 使用 ATS JD 匹配功能时，在 .env 中填写 RESUME_AGENT_API_KEY。
uv sync
uv run playwright install chromium
pnpm --dir agent/frontend install
```

首次启动时，系统会把 `web/data/resume.sample.yaml` 自动复制为本地且被 Git 忽略的 `web/data/resume.yaml`。请将生成后的文件替换为你自己的双语简历；它不会被提交到 Git。

### 本地运行

```bash
./dev.sh
```

浏览器访问 <http://localhost:5173>；API 地址为 <http://127.0.0.1:8010>。

若之前的进程占用了开发端口：

```bash
lsof -ti:8010,5173 | xargs kill
```

## 核心概念

| 概念 | 说明 |
| --- | --- |
| **基线简历** | 唯一当前事实来源，位于 `web/data/resume.yaml`。浏览器编辑后须显式发布才会更新。 |
| **编辑草稿** | 基线编辑器使用的本地唯一草稿，自动保存并检测本地 YAML 修改。 |
| **Run** | 面向一个目标岗位的 ATS JD 匹配流程；产物隔离在 `agent/data/runs/<run_id>/`。 |
| **事实校验** | 根据基线简历生成的稳定事实，验证目标简历的每项修改。 |
| **模板** | 全局、仅影响表现层的主题；不会修改简历数据或 A4 导出约定。 |

## 简历模板

项目内置经典简历、现代极简、专业侧栏三套模板。在 **模板管理** 页面选择后，会统一应用于基线编辑、所有版本预览以及下载导出。

自定义模板以本地 ZIP 包导入，包含 `manifest.json`、`theme.css` 和可选的本地资源。模板只能为固定简历 DOM 提供样式，不能执行代码、引入远程资源、新增字段或修改纸张设置。

可在模板管理页下载完整规范，或直接阅读[模板包规范](docs/template-package-spec.md)。

## 项目结构

```text
agent/
  src/resume_agent/       # FastAPI API、工作流、校验与模板服务
  frontend/               # React + TypeScript 工作台
  data/runs/              # 本地、被忽略的流程产物
web/
  data/resume.yaml        # 已发布的基线简历（不进入 Git）
  data/resume.sample.yaml # 可提交的脱敏示例
  templates/              # 固定的简历 HTML 结构
  styles/                 # 基础 A4 简历样式
docs/                     # 公开项目文档
```

本地归档、导入模板、日志、生成的 Run、`.env` 和 PDF 构建产物均不会进入版本控制。

## 开发

```bash
uv run pytest -q
pnpm --dir agent/frontend build
```

## 数据与安全说明

- 本项目面向个人本地使用，请勿直接暴露到公网。
- 请妥善保存 `.env`；它已被 Git 忽略。
- 导入模板仅允许 CSS 与本地资源，远程资源和 `@import` 会被拒绝。
- 发布基线简历前会自动生成版本快照，可在编辑器中回退。

## 版本

当前开发版本：**1.2.0**。

## 开源许可

当前尚未选择许可证。对外分发或接受外部贡献前，请补充许可证文件。
