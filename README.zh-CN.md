# Resume Generator

[English](README.md) · [简体中文](README.zh-CN.md)

> 将一份可信简历安全定制为更匹配目标 JD 的版本：可审核、可对比、可回退。

Resume Generator 是一个本地优先的 AI 简历定制工作台。它将你的基线简历与目标 Job Description 对照分析，识别匹配点与缺口，生成更贴合岗位要求的候选版本，并在导出前对每一项修改进行事实校验。

你不需要为每个岗位从头改简历，也不必接受 AI 编造的经历：系统只在已确认的简历事实范围内，帮助你重组重点、优化表达。每次修改都可审核、查看差异并随时回退。

## 目录

- [界面预览](#界面预览)
- [核心能力](#核心能力)
- [工作流](#工作流)
- [快速开始](#快速开始)
- [使用手册](#使用手册)
- [模板包编辑手册](#模板包编辑手册)
- [模板与署名](#模板与署名)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [配置说明](#配置说明)

## 界面预览

模板管理页可统一切换基线预览、目标版本预览和 HTML/PDF 导出所使用的展示样式。下图仅使用内置占位文案，不包含任何真实简历信息。

![模板管理工作台](docs/images/template-management.png)

## 核心能力

| 能力 | 说明 |
| --- | --- |
| **面向 JD 的精准定制** | 解析岗位要求，识别现有经历中可匹配、待强化和无法支撑的部分。 |
| **不编造的 AI 改写** | 所有修改受基线事实约束；没有依据的技能、项目、数字和经历不会被写入。 |
| **两次人工审核** | 先审改写策略，再审最终候选简历；你始终掌握发布权。 |
| **版本化与一键回退** | 每次发布基线或生成岗位版本都保留历史与差异；不满意可随时恢复，不会覆盖原始内容。 |
| **一份基线，多份投递版本** | 每个目标岗位独立保存候选简历、评估与导出文件，互不干扰。 |
| **快速导入与双语维护** | 可从现有 PDF、DOCX、图片或 YAML 开始；单语内容不会被擅自翻译或补全。 |

## 工作流

```text
基线简历 ── 编辑草稿 ── 发布 ──> web/data/resume.yaml
   │                                  │
   ├── 版本历史 / 回退                  └── 唯一事实来源
   │
   └── 目标 JD
          │
          ▼
JD 分析 → 匹配评估 → HR 审核 → 改写策略
                                 │
                           人工审批策略
                                 │
                                 ▼
                      结构化补丁 → 事实校验 → 招聘评估
                                 │
                         人工批准最终版本 / 导出
                                 ▼
                             HTML / PDF
```

流程包含两道人工关卡：先审核改写策略，后审核已通过事实校验的最终版本。事实校验失败会使候选版本返回修订；系统绝不会因此改写基线简历。

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 20+ 与 `pnpm`
- 用于 PDF 渲染的 Chromium

### 安装

```bash
cp .env.example .env
# 使用 ATS JD 匹配功能时，在 .env 中填写 RESUME_AGENT_API_KEY。
uv sync
uv run playwright install chromium
pnpm --dir agent/frontend install
```

首次启动时，系统会将 `web/data/resume.sample.yaml` 复制为本地且被 Git 忽略的 `web/data/resume.yaml`。请将生成后的文件替换为自己的双语简历；它不会被提交到 Git。

### 本地运行

macOS / Linux：

```bash
./dev.sh
```

Windows PowerShell：

```powershell
.\dev.ps1
```

若本机执行策略阻止脚本运行，可仅对本次启动使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

浏览器访问 <http://localhost:5173>；API 地址为 <http://127.0.0.1:8010>。

## 使用手册

### 1. 创建并发布基线简历

1. 在侧边栏进入 **修改基线版本**。
2. 可选择 **导入简历**，上传 PDF、DOCX、PNG/JPG/WEBP 图片或 YAML；系统会将内容解析至草稿，不会直接覆盖基线。扫描 PDF 和图片默认在本机经 RapidOCR 提取文字；也可在 `.env` 切换为 MinerU 精准解析 API（会将原始文件上传至 MinerU），再交给模型归一化。
3. 单语来源不会被自动翻译或补写：缺失语言字段会留空，待你核对补充。
4. 在草稿中编辑中英文信息并预览结果。
5. 仅在确认后点击 **发布**，将其设为唯一事实来源。
6. 需要时可在版本列表中查看或恢复任意已发布的基线版本。

发布后的文件是 `web/data/resume.yaml`。Agent Run 只读取它，绝不会写入、格式化或迁移该文件。

#### 扫描件解析方式

默认的 `rapidocr` 完全在本机运行，适合常规扫描简历，安装项目依赖后即可使用，原始文件不会离开设备。若遇到复杂多栏、表格或版式，可在 `.env` 切换为 `mineru_api`；它会上传原始文件到 MinerU 并返回结构化 Markdown，因此需要自行创建 MinerU Token，并确认数据处理许可。

```env
# 默认：轻量、本地、隐私优先
RESUME_AGENT_SCAN_PARSER=rapidocr

# 可选：复杂版式优先，原始文件将上传至 MinerU
RESUME_AGENT_SCAN_PARSER=mineru_api
RESUME_AGENT_MINERU_API_TOKEN=your_token
RESUME_AGENT_MINERU_MODEL_VERSION=vlm
```

### 2. 根据 JD 定制简历

1. 进入 **ATS JD 匹配**，为目标岗位新建一个 Run。
2. 粘贴职位描述并启动分析。
3. 查看匹配分析与改写策略；可批准、要求修改或停止该 Run。
4. 查看候选简历、补丁/差异、事实校验结果和招聘评估。
5. 批准最终版本后，选择语言并导出 HTML 或 PDF；也可恢复原始的基线派生版本。

每个岗位 Run 都独立保存在 `agent/data/runs/<run_id>/` 下，因此不会覆盖基线简历，也不会互相干扰。

### 3. 选择或导入模板

1. 进入 **模板管理**。
2. 应用一套内置主题，或导入本地 ZIP 模板包。
3. 所选主题会立即统一用于预览和之后的导出。

自定义模板包包含 `manifest.json`、`theme.css` 与可选 `assets/`。它只能为固定简历 DOM 提供样式，不能执行代码、新增字段、修改 A4 纸张设置、加载远程资源或使用 CSS `@import`。完整格式见[模板包规范](docs/template-package-spec.md)。

### 4. 模板包编辑手册

自定义模板包只调整简历的视觉呈现，不会读取、修改或新增简历数据。模板包是一个 ZIP 文件，根目录必须包含 `manifest.json` 和 `theme.css`；也可附带本地字体或图片资源。

### 1. 创建目录

```text
my-template/
├── manifest.json
├── theme.css
├── preview.png            # 可选：建议使用 4:3 模板缩略图
└── assets/                # 可选：本地字体、图片等资源
    └── MyFont.woff2
```

压缩时请直接压缩目录内的文件，使 ZIP 根目录包含 `manifest.json` 与 `theme.css`；不要额外嵌套一层 `my-template/` 目录。

### 2. 编写模板信息

新建 `manifest.json`：

```json
{
  "id": "my-clean-template",
  "name": "我的极简模板",
  "description": "适合技术岗位的一页式布局",
  "unsupported": ["照片", "项目简介"]
}
```

- `id` 必填，只能使用小写字母、数字、`-`、`_`，最长 49 个字符，且不能与已有或内置模板重复。
- `name` 必填，用于模板管理页显示。
- `description` 建议填写，用于说明模板适用场景。
- `unsupported` 可选，用于声明不展示的字段；可选值见[模板包规范](docs/template-package-spec.md)。

### 3. 编写样式

在 `theme.css` 中覆盖固定简历 DOM 的样式。可调整字体、颜色、间距、网格、边框与分页等视觉效果。

```css
@font-face {
  font-family: "My Font";
  src: url("assets/MyFont.woff2") format("woff2");
}

body { font-family: "My Font", "Noto Sans SC", sans-serif; }
.header { border-bottom: 2px solid #2563eb; }
.section-title { color: #1d4ed8; }
```

引用包内资源时使用相对路径，例如 `assets/MyFont.woff2`。建议先检查中文、英文、长文本与跨页内容，再以 PDF 导出结果作为最终版式依据。

### 4. 打包与导入

1. 将目录内容压缩为 ZIP 文件。
2. 打开 **模板管理**，选择导入本地模板包。
3. 导入后应用模板，检查基线预览、候选版本预览及 HTML/PDF 导出效果。
4. 需要迭代时，修改源目录后重新压缩并导入。

### 限制与排查

模板包只能提供 CSS 与本地静态资源，不能包含 JavaScript、HTML 模板或远程资源；不支持 CSS `@import`、`http/https` URL、路径穿越（`..`），也不能改变 A4 纸张、页面边距、数据字段或导出文件命名规则。

导入失败时，请依次确认 ZIP 根目录结构、`manifest.json` 是否为有效 JSON、模板 `id` 是否重复，以及资源路径是否均为包内相对路径。完整约束见[模板包规范](docs/template-package-spec.md)。

### 5. 导出

在基线或已批准的候选版本中选择目标语言，即可下载 A4 HTML 或 PDF。HTML 方便继续通过浏览器打印，PDF 则是最终可交付文件。

## 模板与署名

内置的 **经典简历** 模板采用 [Awesome-CV](https://github.com/posquit0/Awesome-CV) 的视觉风格。Awesome-CV 是 `posquit0` 创作的优秀 LaTeX 简历模板；本项目将该表现风格适配到固定的 HTML/CSS 渲染链路，并非 Awesome-CV 的关联项目。上游项目的许可与署名要求请以其仓库为准。

另有现代极简和专业侧栏两套内置主题。模板只影响表现层：无论切换哪一套，都不会修改简历事实、YAML 内容或 A4 导出约定。

## 技术架构

```text
┌──────────────────────────── 浏览器工作台 ────────────────────────────┐
│ React + TypeScript                                                     │
│ 基线编辑 · 简历预览 · 模板管理 · ATS Run 审核                         │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ HTTP / 本地预览 URL
┌─────────────────────────────────▼────────────────────────────────────┐
│ FastAPI 应用                                                           │
│ 草稿/版本 API · Run API · 模板服务 · 下载/预览 API                    │
└───────────────┬──────────────────────────────┬────────────────────────┘
                │                              │
     ┌──────────▼──────────┐       ┌───────────▼────────────────────────┐
     │ 简历服务             │       │ LangGraph Agent 工作流             │
     │ YAML + 版本          │       │ JD 分析 → 策略 → 补丁 → 校验       │
     │ 模板 + 渲染          │       │ → 评估 → 人工审批                  │
     └──────────┬──────────┘       └───────────┬────────────────────────┘
                │                              │
     web/data/resume.yaml            agent/data/runs/<run_id>/
     （已发布基线）                  （隔离的本地流程产物）
```

后端使用 FastAPI 提供本地 API，浏览器工作台基于 React + TypeScript，分阶段 Agent 流程由 LangGraph 编排，结构化校验基于 Pydantic，文档由 Jinja2/CSS 渲染，PDF 由 Playwright/Chromium 生成。模型服务采用可配置的 OpenAI 兼容接口，`.env.example` 默认示例为 DeepSeek。

## 项目结构

```text
agent/
  src/resume_agent/       # FastAPI API、工作流、校验与模板服务
  frontend/               # React + TypeScript 浏览器工作台
  prompts/                # Agent 工作流使用的版本化角色提示词
  data/runs/              # 本地、被忽略的岗位 Run 产物
web/
  data/resume.yaml        # 已发布的基线简历（不进入 Git）
  data/resume.sample.yaml # 可提交的脱敏示例
  templates/              # 固定的简历 HTML 结构
  styles/                 # 基础 A4 简历样式
docs/
  images/                 # README 图片
  template-package-spec.md
```

本地归档、导入模板、日志、生成的 Run、`.env` 与 PDF 构建产物均不会进入版本控制。

## 配置说明

将 `.env.example` 复制为 `.env` 后，常用配置如下：

| 变量 | 用途 |
| --- | --- |
| `RESUME_AGENT_API_KEY` | OpenAI 兼容模型服务的 API Key；使用 ATS 匹配时必填。 |
| `RESUME_AGENT_BASE_URL` | 模型服务端点；示例文件默认使用 DeepSeek。 |
| `RESUME_AGENT_MODEL` | 工作流使用的模型名称。 |
| `RESUME_AGENT_HIRING_THRESHOLD` | 可选自动最终审批所使用的分数阈值。 |
| `RESUME_AGENT_AUTO_APPROVE_MINUTES` | 可选自动处理关卡前的等待时间；设为 `0` 关闭。 |
| `RESUME_AGENT_SCAN_PARSER` | 扫描 PDF/图片解析器：`rapidocr`（默认，本地）或 `mineru_api`（MinerU 云端精准解析）。 |
| `RESUME_AGENT_MINERU_API_TOKEN` | 选择 `mineru_api` 时必填；原始简历会上传至 MinerU，请确认数据处理许可。 |
| `RESUME_AGENT_MINERU_MODEL_VERSION` | MinerU 模型：`pipeline` 或 `vlm`（默认，复杂版式效果更好）。 |
| `RESUME_AGENT_LANGSMITH_PROJECT_URL` | 配置 LangSmith tracing 后，Run 页面显示的可选项目链接。 |

请妥善保管 `.env`。本项目面向个人本地使用，不应直接暴露在公网。

## 开发与测试

```bash
uv run pytest -q
pnpm --dir agent/frontend build
```

## 开源许可

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。
