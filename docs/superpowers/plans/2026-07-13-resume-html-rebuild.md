# 简历 HTML/CSS + Python 重建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用一份 YAML 数据 + Jinja2 模板 + CSS 复刻 Awesome-CV 简历，`python build.py` 一条命令经 Playwright(Chromium) 导出中/英两份 PDF，同一套 HTML 可当网站部署。

**Architecture:** 内容与排版彻底分离 —— `data/resume.yaml`（双语，每段文字为 `{zh,en}`）为唯一日常编辑点；`build.py` 读数据、用自定义 `localize` filter 按语言渲染 `templates/resume.html.j2`（内联 `styles/awesome-cv.css`）为 HTML，再用 Playwright 打印成 A4 PDF。四种 section 类型（paragraph / skills / education / entries）覆盖全部现有内容。

**Tech Stack:** Python 3.13、Jinja2、PyYAML、Playwright(Chromium)、可选 watchdog（--watch）。Latin 字体 Roboto（复用仓库 `fonts/`），CJK 字体 Noto Serif CJK SC（系统已装）。

## Global Constraints

- 所有新文件放在 `resume-web/`；仓库根目录的 LaTeX 文件（`resume.tex`、`resume/*.tex`、`awesome-cv.cls`、`fonts/` 等）**一律不改动**。
- 主色 `#DC3522`；正文 `#333333`；灰 `#5D5D5D`；浅灰 `#999999`；深文字 `#414141`（取自 `awesome-cv.cls`）。
- 页面 A4，边距 `left/right = 1.4cm, top = 0.8cm, bottom = 1.8cm`（对齐原 `\geometry`）。
- 双语一份数据；构建产物命名 `resume.zh.pdf` / `resume.en.pdf` / `resume.zh.html` / `resume.en.html`。
- 所有资源（字体/图标/头像）本地相对路径，无外网依赖（Playwright 与静态托管都要能用）。
- Python 依赖装在 `resume-web/.venv` 虚拟环境里，命令一律用 `resume-web/.venv/bin/python`。
- 测试用 pytest，放在 `resume-web/tests/`。

---

### Task 1: 工程脚手架 + 依赖 + Chromium

**Files:**
- Create: `resume-web/requirements.txt`
- Create: `resume-web/.gitignore`
- Create: `resume-web/tests/test_smoke.py`
- Create: `resume-web/data/.gitkeep`, `resume-web/templates/.gitkeep`, `resume-web/styles/.gitkeep`, `resume-web/assets/.gitkeep`

**Interfaces:**
- Produces: 可用的虚拟环境 `resume-web/.venv`（含 jinja2 / pyyaml / playwright / pytest / watchdog）与已安装的 Chromium。后续所有任务用 `resume-web/.venv/bin/python` 和 `resume-web/.venv/bin/pytest`。

- [ ] **Step 1: 建目录与依赖清单**

创建 `resume-web/requirements.txt`：
```
jinja2>=3.1
pyyaml>=6.0
playwright>=1.40
pytest>=8.0
watchdog>=4.0
```

创建 `resume-web/.gitignore`：
```
.venv/
build/
__pycache__/
*.pyc
```

创建占位文件保证空目录入库：`resume-web/data/.gitkeep`、`resume-web/templates/.gitkeep`、`resume-web/styles/.gitkeep`、`resume-web/assets/.gitkeep`（内容留空）。

- [ ] **Step 2: 建虚拟环境并装依赖**

Run:
```bash
cd resume-web && python3 -m venv .venv && \
  .venv/bin/pip install -q -r requirements.txt && \
  .venv/bin/playwright install chromium
```
Expected: 无报错；末尾 Chromium 下载完成。

- [ ] **Step 3: 写冒烟测试**

创建 `resume-web/tests/test_smoke.py`：
```python
def test_dependencies_importable():
    import jinja2  # noqa: F401
    import yaml  # noqa: F401
    from playwright.sync_api import sync_playwright  # noqa: F401


def test_chromium_launches():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content("<h1>ok</h1>")
        assert page.inner_text("h1") == "ok"
        browser.close()
```

- [ ] **Step 4: 跑测试**

Run: `cd resume-web && .venv/bin/pytest tests/test_smoke.py -v`
Expected: 2 passed。

- [ ] **Step 5: 提交**

```bash
git add resume-web/requirements.txt resume-web/.gitignore resume-web/tests/test_smoke.py resume-web/data/.gitkeep resume-web/templates/.gitkeep resume-web/styles/.gitkeep resume-web/assets/.gitkeep
git commit -m "feat(resume-web): 脚手架、依赖与 Chromium 冒烟测试"
```

---

### Task 2: 数据文件 + 本地化核心逻辑

**Files:**
- Create: `resume-web/data/resume.yaml`
- Create: `resume-web/build.py`
- Create: `resume-web/tests/test_data.py`

**Interfaces:**
- Produces:
  - `load_data(path: str | Path) -> dict` —— 读并解析 YAML，返回 dict。
  - `localize(node, lang: str)` —— 若 `node` 是含 `zh`/`en` 键的 dict 则返回 `node[lang]`，否则原样返回。用作 Jinja2 filter。
  - `data/resume.yaml` —— 全部简历内容（双语），供后续渲染任务消费。

- [ ] **Step 1: 写 `data/resume.yaml`（完整内容）**

创建 `resume-web/data/resume.yaml`（内容逐字来自现有 `resume/*.tex`；`sections` 顺序与 `resume.tex` 一致：介绍→技术栈→教育→工作→项目）：
```yaml
meta:
  name:
    zh: "李祖民"
    en: "Zumin Li"
  name_split_zh: 1        # 段/名着色时中文取前几个字
  position:
    zh: "软件工程师 · 全栈开发"
    en: "Software Engineer · Full Stack Developer"
  color: "#DC3522"
  contacts:
    mobile: "(+86) 13675823946"
    email: "zumin.li.work@gmail.com"
    homepage: "resume.flyingjack.top"
    github: "FlyingJackLee"
    wechat: "13675823946"
  photo: "assets/photo.jpg"
  footer_label:
    zh: "李祖民 · Résumé"
    en: "Zumin Li · Résumé"
  footer_more:
    text:
      zh: "更多信息，烦请访问我的个人网站："
      en: "See my website for more："
    url: "https://resume.flyingjack.top/"

# 段标题默认着色字数：拉丁前 3 个字符 / 中文前 1 个字（可按 section 用 highlight 覆盖）
section_highlight_latin: 3
section_highlight_cjk: 1

sections:
  - type: paragraph
    title: {zh: "个人介绍", en: "Introduction"}
    body:
      zh: "具备五年以上软件开发经验，专注于后端架构设计与云原生技术，精通 Java 语言及分布式高并发微服务系统的开发与优化。具备扎实的计算机基础与系统工程能力，能够在复杂业务场景中快速定位问题并高效解决，提升系统稳定性与性能。同时具备一定的前端开发与 AI 应用开发经验，具备跨技术栈的协作能力与持续学习意识。热衷技术创新，善于团队沟通与项目协同，希望在技术深度与业务价值兼具的岗位中持续成长，创造可衡量的技术成果。"
      en: "5+ years experienced Full-stack Developer skilled in Java, microservices and distributed architecture with well-defined APIs. Built large-scale SPA using Angular, and worked extensively with MySQL/PostgreSQL, Kubernetes, Docker, Kafka, Redis and Jenkins. Gained hands-on experience in AI Agent development. Proficient at troubleshooting complex technical issues, leading team technical discussions and adopting new technologies to drive business optimization. Strong communicator with fluent English."

  - type: skills
    title: {zh: "技术栈", en: "Skills"}
    rows:
      - label: {zh: "后端技术链", en: "Backend"}
        items: {zh: "Mybatis, Spring Cloud, Nacos, Sentinel, Gateway, Spring Security, Kafka", en: "Mybatis, Spring Cloud, Nacos, Sentinel, Gateway, Spring Security, Kafka"}
      - label: {zh: "AI应用", en: "AI Application"}
        items: {zh: "Langchain4j, MCP, AI Agent, RAG", en: "Langchain4j, MCP, AI Agent, RAG"}
      - label: {zh: "存储相关", en: "Persistence"}
        items: {zh: "PostgreSQL, MySQL, Redis, Elasticsearch", en: "PostgreSQL, MySQL, Redis, Elasticsearch"}
      - label: {zh: "云原生", en: "Cloud native"}
        items: {zh: "Kubernetes, istio, Prometheus, Jenkins, GitOps", en: "Kubernetes, istio, Prometheus, Jenkins, GitOps"}
      - label: {zh: "其他", en: "Other"}
        items: {zh: "Angular, Flutter, Linux, Shell, Python, YOLO", en: "Angular, Flutter, Linux, Shell, Python, YOLO"}

  - type: education
    title: {zh: "教育经历", en: "Education"}
    entries:
      - degree: {zh: "软件工程 硕士 - Distinction 一等学位", en: "MSc in Software Engineering - Distinction"}
        org: {zh: "英国格拉斯哥大学", en: "University of Glasgow"}
        location: {zh: "格拉斯哥, 英国", en: "Glasgow, UK"}
        date: {zh: "2020年9月 - 2022年4月", en: "September 2020 – April 2022"}
      - degree: {zh: "通信工程 工学学士 - 优秀毕业生", en: "BEng in Communication Engineering - Outstanding Graduate"}
        org: {zh: "杭州电子科技大学", en: "Hangzhou Dianzi University"}
        location: {zh: "杭州, 中国", en: "Hangzhou, China"}
        date: {zh: "2012年9月 - 2016年6月", en: "September 2012 – June 2016"}

  - type: entries
    title: {zh: "工作经历", en: "Work"}
    entries:
      - title: {zh: "技术合伙人", en: "Technical Lead & Partner"}
        org: {zh: "麒霖通信有限公司", en: "Qilin Communications Co., Ltd."}
        location: {zh: "贵阳, 中国", en: "Guiyang, China"}
        date: {zh: "2023年11月 - 2026年2月", en: "November 2023 – February 2026"}
        items:
          - {zh: "负责智能仓储收银一体化管理系统前后端全栈研发，涵盖业务模块建模、接口设计、数据库表结构设计、业务逻辑开发及联调对接，打通仓储库存、订单结算、收银核销全业务链路。", en: "Led full-stack development of an intelligent integrated warehouse and cashier management platform, focusing on Java backend and distributed microservice architecture."}
          - {zh: "负责系统整体架构梳理、性能调优与架构迭代优化，承担服务容器化部署、环境配置、版本发布及日常运维保障工作，提升系统稳定性、并发承载能力与可维护性。", en: "Optimized microservice architecture and system performance, and delivered iterative upgrades with cloud-native technologies. Managed Kubernetes container orchestration, automated deployment, environment configuration and version release, significantly enhancing system stability, high-concurrency performance, scalability and maintainability."}
      - title: {zh: "高级软件工程师", en: "Senior Software Engineer"}
        org: {zh: "华为云计算技术有限公司", en: "Huawei Cloud Computing Technologies Co., Ltd"}
        location: {zh: "成都, 中国", en: "Chengdu, China"}
        date: {zh: "2022年7月 - 2023年8月", en: "July 2022 – August 2023"}
        items:
          - {zh: "负责 PaaS 云测产品商用环境后端需求迭代与功能开发，保障服务高可用、高性能架构落地，支撑商业化稳定交付。", en: "Developed and iterated backend features for commercial PaaS cloud testing products, ensuring high availability and high-performance architecture to support stable commercial delivery."}
          - {zh: "主导并独立完成部门自研测试工具全流程设计与开发，实现流水线测试数据自动注入、接口 Mock 模拟等核心能力，提升团队测试效能。", en: "Independently led the full-cycle design and development of an in-house testing framework, implementing automated test data injection and API Mock simulation to significantly improve team testing efficiency."}
          - {zh: "承担混合云场景下客户技术对接、现场支撑及项目全周期风险识别与管控，保障业务平稳落地运行。", en: "Provided on-site technical support and end-to-end project risk management for hybrid cloud customers, guaranteeing smooth project deployment and operation."}
      - title: {zh: "软件工程师", en: "Software Engineer"}
        org: {zh: "浙江科普教育广播制作有限公司", en: "Zhejiang Science Education Broadcasting Production Co., Ltd."}
        location: {zh: "杭州, 中国", en: "Hangzhou, China"}
        date: {zh: "2017年8月 - 2020年8月", en: "August 2017 – August 2020"}
        items:
          - {zh: "负责企业 OA 办公审批系统业务流程架构设计与全流程功能开发，优化审批链路逻辑与流转效率。", en: "Designed and developed core approval workflows for the OA system. Supported flexible process configuration and multi-level review to streamline daily office operations."}
          - {zh: "独立负责企业官方网站前端全栈开发，兼顾页面交互逻辑、整体功能实现与视觉界面定制设计。", en: "Independently delivered full-cycle frontend development for the corporate official website. Completed visual layout, interactive features and cross-device adaptation."}

  - type: entries
    title: {zh: "项目经历", en: "Projects"}
    entries:
      - title: {zh: "智能仓储收银管理系统", en: "Smart Inventory and Cashier Management Platform"}
        org: {zh: "全栈开发", en: "Full stack development"}
        location: {zh: "Release @ 2024年11月29日", en: "Release @ November 29, 2024"}
        date: {zh: "", en: ""}
        link: {url: "https://github.com/FlyingJackLee/wms_backend", label: "Github: github.com/FlyingJackLee/wms_backend"}
        items:
          - {zh: "项目分三阶段架构迭代：初期以单体应用快速上线完成业务验证；二期基于 Spring Cloud Alibaba 微服务重构，引入热点缓存优化分布式性能；三期升级 Istio 服务网格，替代传统网关与熔断组件，实现路由调度、流量管控、故障熔断，落地金丝雀与 A/B 灰度发布，保障业务不停机平滑迭代。", en: "Built a Java-based system with PostgreSQL for data persistence, then migrated to Spring Cloud microservices integrated with distributed cache."}
          - {zh: "搭建 Jenkins + GitOps CI/CD 自动化部署流水线，整合代码检查、镜像构建、环境部署及版本回滚等核心流程，实现多环境无缝衔接，提升迭代效率、降低部署误差。", en: "Deployed all services on Kubernetes, adopted Istio for routing, traffic control and circuit breaking, and implemented A/B testing & canary releases."}
          - {zh: "基于 Langchain4j 搭建智能仓储收银业务中枢，通过标准化 Skill 能力封装编排，沉淀库存、订单核销、收银结算等原子能力；依托 AI 智能调度打通仓储收银全链路，实现 Web 管理端与移动作业端多端业务联动及场景自适应调度。", en: "Developed responsive web portal using Angular and Material UI, and cross-platform mobile clients using Flutter; employed Jenkins and GitOps-based CI/CD pipeline to ensure fast development."}
      - title: {zh: "华为云 PaaS CodeArts DevOps 软件生产线", en: "CodeArts DevOps Software Pipeline Tools"}
        org: {zh: "后端开发", en: "Backend development"}
        location: {zh: "Release @ 2023年8月29日", en: "Release @ August 29, 2023"}
        date: {zh: "", en: ""}
        link: {url: "https://www.huaweicloud.com/product/cpts.html", label: "Project site: huaweicloud.com/product/cpts.html"}
        items:
          - {zh: "制定项目测试标准规范，为团队开发测试数据注入工具，实现复杂依赖环境下 Fake 数据的自动多级注入，为团队节约 30% 以上的需求开发时间。", en: "Developed a new test data injection tool, enabling automated multi-level injection of mock data in complex dependency environments, cutting the team's development cycle by over 30%."}
          - {zh: "负责 PaaS 云测产品商用环境后端需求拆解、架构设计与功能开发，聚焦服务高可用、高性能架构落地，优化接口响应效率与并发承载能力。", en: "Implemented backend feature development based on Java/Python and microservice architecture, designed and maintained standardized REST APIs, and optimized business logic for distributed systems to guarantee high availability and performance."}
          - {zh: "承担混合云场景下客户技术对接、现场支撑与问题排查，梳理业务落地全流程风险点，制定针对性管控方案，保障混合云环境下测试业务平稳运行。", en: "Provided API-level technical support and risk management for external customer services."}
      - title: {zh: "Easyimage 在线图片识别分类系统", en: "Easyimage - an online image recognition and classification system"}
        org: {zh: "全栈开发", en: "Full stack development"}
        location: {zh: "Release @ 2021年10月9日", en: "Release @ October 9, 2021"}
        date: {zh: "", en: ""}
        link: {url: "https://github.com/FlyingJackLee/easyimage-backend", label: "Github: github.com/FlyingJackLee/easyimage_backend"}
        items:
          - {zh: "负责 Python 模型程序与 Java 后端服务的跨语言互调适配开发，定义标准化接口协议，实现模型能力与后端业务系统的高效协同、数据互通。", en: "Developed integration logic between Python AI modules and Java microservice backend, supporting core visual business capabilities."}
          - {zh: "基于 YOLO 目标检测算法，开发在线实时对象检测与自动分类模块，优化模型推理效率，实现仓储场景下目标精准识别、多类别自动归类。", en: "Applied YOLO computer vision framework to implement object detection and intelligent classification of images."}
```

- [ ] **Step 2: 写 `build.py` 的数据与本地化函数**

创建 `resume-web/build.py`（本任务只放这两个函数；后续任务往同文件追加）：
```python
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent


def load_data(path="data/resume.yaml"):
    """读取并解析简历 YAML，返回 dict。"""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def localize(node, lang):
    """若 node 是含 zh/en 的 dict 则取对应语言，否则原样返回。"""
    if isinstance(node, dict) and "zh" in node and "en" in node:
        return node[lang]
    return node
```

- [ ] **Step 3: 写测试**

创建 `resume-web/tests/test_data.py`：
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import load_data, localize  # noqa: E402


def test_load_data_has_meta_and_sections():
    data = load_data()
    assert data["meta"]["name"]["zh"] == "李祖民"
    assert data["meta"]["name"]["en"] == "Zumin Li"
    assert len(data["sections"]) == 5


def test_localize_picks_language():
    node = {"zh": "个人介绍", "en": "Introduction"}
    assert localize(node, "zh") == "个人介绍"
    assert localize(node, "en") == "Introduction"


def test_localize_passthrough_for_plain_values():
    assert localize("FlyingJackLee", "zh") == "FlyingJackLee"
    assert localize({"url": "x", "label": "y"}, "en") == {"url": "x", "label": "y"}


def test_section_types_are_known():
    data = load_data()
    types = {s["type"] for s in data["sections"]}
    assert types <= {"paragraph", "skills", "education", "entries"}
```

- [ ] **Step 4: 跑测试**

Run: `cd resume-web && .venv/bin/pytest tests/test_data.py -v`
Expected: 4 passed。

- [ ] **Step 5: 提交**

```bash
git add resume-web/data/resume.yaml resume-web/build.py resume-web/tests/test_data.py
git commit -m "feat(resume-web): 双语数据文件与本地化核心逻辑"
```

---

### Task 3: Jinja2 模板 + CSS → HTML 渲染

**Files:**
- Create: `resume-web/templates/resume.html.j2`
- Create: `resume-web/styles/awesome-cv.css`
- Modify: `resume-web/build.py`（追加 `render_html`）
- Create: `resume-web/tests/test_render.py`

**Interfaces:**
- Consumes: `load_data`、`localize`（Task 2）。
- Produces: `render_html(data: dict, lang: str) -> str` —— 返回内联好 CSS 的完整 HTML 字符串。

- [ ] **Step 1: 写 CSS `styles/awesome-cv.css`**

创建 `resume-web/styles/awesome-cv.css`（复刻 Awesome-CV；print 为主，screen 在 Task 5 增强）：
```css
:root {
  --awesome: #DC3522;
  --text: #333333;
  --darktext: #414141;
  --gray: #5D5D5D;
  --light: #999999;
}
@page { size: A4; margin: 0.8cm 1.4cm 1.8cm 1.4cm; }
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; color: var(--text);
  font-family: "Roboto", "Noto Serif CJK SC", sans-serif;
  font-size: 9pt; line-height: 1.35;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.page { padding: 0.8cm 1.4cm 1.8cm 1.4cm; }
@media print { .page { padding: 0; } }

/* 页头 */
.header { position: relative; text-align: center; margin-bottom: 14px; }
.header .name { font-size: 16pt; letter-spacing: 1px; }
.header .name .first { color: var(--gray); font-weight: 300; }
.header .name .last { color: var(--text); font-weight: 700; }
.header .position {
  color: var(--awesome); font-size: 7.6pt; font-variant: small-caps;
  letter-spacing: .5px; margin-top: 4px;
}
.header .contacts {
  color: var(--text); font-size: 9pt; margin-top: 6px;
  display: flex; justify-content: center; flex-wrap: wrap; gap: 0 6px;
}
.header .contacts .sep { color: var(--light); }
.header .contacts .item { display: inline-flex; align-items: center; gap: 4px; }
.header .contacts svg { width: 9pt; height: 9pt; fill: var(--text); }
.header .photo {
  position: absolute; top: 0; right: 0; width: 2.2cm; height: 2.2cm;
  object-fit: cover; border-radius: 3px;
}

/* 段标题 */
.section { margin-top: 16px; }
.section-title {
  display: flex; align-items: center; gap: 10px;
  font-size: 16pt; font-weight: 700; color: var(--text); margin-bottom: 8px;
}
.section-title .hl { color: var(--awesome); }
.section-title::after {
  content: ""; flex: 1 1 auto; height: 1px; background: var(--text); opacity: .85;
}

/* 段落 */
.paragraph { color: var(--text); text-align: justify; }

/* 技能 */
.skills { display: table; width: 100%; }
.skill-row { display: table-row; }
.skill-label {
  display: table-cell; white-space: nowrap; padding: 2px 12px 2px 0;
  font-weight: 700; color: var(--darktext); font-size: 10pt; width: 1%; vertical-align: baseline;
}
.skill-items { display: table-cell; color: var(--text); vertical-align: baseline; padding: 2px 0; }

/* 条目通用 */
.entry { margin-bottom: 10px; }
.entry-head { display: flex; justify-content: space-between; align-items: baseline; }
.entry-head .left { display: flex; flex-direction: column; }
.entry-head .right { text-align: right; white-space: nowrap; padding-left: 12px; }
.entry-title { font-size: 10pt; font-weight: 700; color: var(--darktext); }
.entry-org { font-size: 8pt; font-variant: small-caps; color: var(--gray); margin-top: 2px; }
.entry-location { font-size: 9pt; font-style: italic; color: var(--awesome); }
.entry-date { font-size: 8pt; font-style: italic; color: var(--gray); margin-top: 2px; }
.entry-link a { font-family: monospace; font-size: 8pt; color: var(--darktext); text-decoration: none; }
.entry-items { margin: 4px 0 0; padding-left: 16px; }
.entry-items li { margin: 2px 0; color: var(--text); }
.entry-items li::marker { color: var(--text); }

/* 教育（两行无 bullet）：结构同 entry，但左侧只有 degree + org */
.edu .entry-title { font-weight: 700; }

/* 底部“更多信息” */
.more { text-align: center; margin-top: 28px; }
.more a { color: var(--awesome); }

/* 页脚（screen 显示；print 用 Playwright footer 生成页码） */
.footer { display: none; }
```

- [ ] **Step 2: 写模板 `templates/resume.html.j2`**

创建 `resume-web/templates/resume.html.j2`（图标用内联 SVG，无外部依赖；`L` 为 localize 的简写 filter）：
```jinja
<!doctype html>
<html lang="{{ lang }}">
<head>
<meta charset="utf-8">
<title>{{ meta.name | L }}</title>
<style>{{ css }}</style>
</head>
<body>
<div class="page">

  <header class="header">
    {% if photo_exists %}<img class="photo" src="{{ meta.photo }}" alt="">{% endif %}
    <div class="name">
      {% set full = meta.name | L %}
      {% if lang == 'en' %}
        {% set parts = full.split(' ', 1) %}
        <span class="first">{{ parts[0] }}</span> <span class="last">{{ parts[1] if parts|length > 1 else '' }}</span>
      {% else %}
        <span class="first">{{ full[:meta.name_split_zh] }}</span><span class="last">{{ full[meta.name_split_zh:] }}</span>
      {% endif %}
    </div>
    <div class="position">{{ meta.position | L }}</div>
    <div class="contacts">
      {% set c = meta.contacts %}
      {% set items = [] %}
      <span class="item">{{ icon('phone') }}{{ c.mobile }}</span><span class="sep">|</span>
      <span class="item">{{ icon('email') }}{{ c.email }}</span><span class="sep">|</span>
      <span class="item">{{ icon('home') }}{{ c.homepage }}</span><span class="sep">|</span>
      <span class="item">{{ icon('github') }}{{ c.github }}</span><span class="sep">|</span>
      <span class="item">{{ icon('wechat') }}{{ c.wechat }}</span>
    </div>
  </header>

  {% for s in sections %}
  <section class="section {{ 'edu' if s.type == 'education' else '' }}">
    <div class="section-title">{{ section_title(s.title | L) }}</div>

    {% if s.type == 'paragraph' %}
      <div class="paragraph">{{ s.body | L }}</div>

    {% elif s.type == 'skills' %}
      <div class="skills">
        {% for row in s.rows %}
        <div class="skill-row">
          <div class="skill-label">{{ row.label | L }}</div>
          <div class="skill-items">{{ row.items | L }}</div>
        </div>
        {% endfor %}
      </div>

    {% elif s.type == 'education' %}
      {% for e in s.entries %}
      <div class="entry">
        <div class="entry-head">
          <div class="left">
            <span class="entry-title">{{ e.degree | L }}</span>
            <span class="entry-org">{{ e.org | L }}</span>
          </div>
          <div class="right">
            <div class="entry-location">{{ e.location | L }}</div>
            <div class="entry-date">{{ e.date | L }}</div>
          </div>
        </div>
      </div>
      {% endfor %}

    {% elif s.type == 'entries' %}
      {% for e in s.entries %}
      <div class="entry">
        <div class="entry-head">
          <div class="left">
            <span class="entry-title">{{ e.title | L }}</span>
            <span class="entry-org">{{ e.org | L }}</span>
            {% if e.link %}<span class="entry-link"><a href="{{ e.link.url }}">{{ e.link.label }}</a></span>{% endif %}
          </div>
          <div class="right">
            <div class="entry-location">{{ e.location | L }}</div>
            {% if (e.date | L) %}<div class="entry-date">{{ e.date | L }}</div>{% endif %}
          </div>
        </div>
        {% if e.get('items') %}
        <ul class="entry-items">
          {% for it in e['items'] %}<li>{{ it | L }}</li>{% endfor %}
        </ul>
        {% endif %}
      </div>
      {% endfor %}
    {% endif %}
  </section>
  {% endfor %}

  <div class="more">
    {{ footer_more.text | L }}<a href="{{ footer_more.url }}">{{ footer_more.url }}</a>
  </div>

</div>
</body>
</html>
```

- [ ] **Step 3: 往 `build.py` 追加 `render_html` 与辅助（图标、段标题着色）**

在 `resume-web/build.py` 末尾追加：
```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ICONS = {
    "phone": '<svg viewBox="0 0 512 512"><path d="M164 32 32 96c0 212 152 384 384 384l64-132-108-44-40 48c-72-32-128-88-160-160l48-40L164 32z"/></svg>',
    "email": '<svg viewBox="0 0 512 512"><path d="M48 96h416v320H48z" fill="none"/><path d="M48 96l208 160L464 96H48zm0 40v280h416V136L256 296 48 136z"/></svg>',
    "home": '<svg viewBox="0 0 576 512"><path d="M288 48 32 256h64v208h128V336h128v128h128V256h64L288 48z"/></svg>',
    "github": '<svg viewBox="0 0 496 512"><path d="M248 24C111 24 0 135 0 272c0 110 71 203 170 236 12 2 17-5 17-12v-42c-69 15-84-33-84-33-11-29-28-37-28-37-23-16 2-16 2-16 25 2 38 26 38 26 22 38 59 27 73 21 2-16 9-27 16-33-55-6-113-27-113-122 0-27 10-49 26-67-3-6-11-31 2-65 0 0 21-7 69 26 20-6 41-9 62-9s42 3 62 9c48-33 69-26 69-26 13 34 5 59 2 65 16 18 26 40 26 67 0 95-58 116-113 122 9 8 17 23 17 47v69c0 7 5 14 17 12 99-33 170-126 170-236 0-137-111-248-248-248z"/></svg>',
    "wechat": '<svg viewBox="0 0 576 512"><path d="M385 118C230 118 111 219 111 344c0 45 15 87 41 121l-16 62 72-37c26 8 54 12 84 12 155 0 274-101 274-226S540 118 385 118z"/></svg>',
}


def icon(name):
    return Markup(ICONS.get(name, ""))


def make_section_title(data):
    def _title(text):
        first = text[0] if text else ""
        if first and ("一" <= first <= "鿿"):
            n = data.get("section_highlight_cjk", 1)
        else:
            n = data.get("section_highlight_latin", 3)
        return Markup(f'<span class="hl">{text[:n]}</span>{text[n:]}')
    return _title


def render_html(data, lang):
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["L"] = lambda node: localize(node, lang)
    env.globals["icon"] = icon
    env.globals["section_title"] = make_section_title(data)
    css = (ROOT / "styles" / "awesome-cv.css").read_text(encoding="utf-8")
    photo = data["meta"].get("photo")
    photo_exists = bool(photo) and (ROOT / photo).exists()
    tpl = env.get_template("resume.html.j2")
    return tpl.render(
        lang=lang, css=css, photo_exists=photo_exists,
        meta=data["meta"], sections=data["sections"],
        footer_more=data["meta"]["footer_more"],
    )
```

- [ ] **Step 4: 写测试**

创建 `resume-web/tests/test_render.py`：
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import load_data, render_html  # noqa: E402


def test_render_zh_contains_key_content():
    html = render_html(load_data(), "zh")
    assert "李祖民" in html
    assert "个人介绍" in html
    assert "技术合伙人" in html
    assert "麒霖通信有限公司" in html
    assert 'class="hl"' in html  # 段标题着色


def test_render_en_contains_key_content():
    html = render_html(load_data(), "en")
    assert "Zumin Li" in html
    assert "Introduction" in html
    assert "Technical Lead" in html


def test_render_includes_inline_css_and_icons():
    html = render_html(load_data(), "zh")
    assert "--awesome: #DC3522" in html
    assert "<svg" in html  # 内联图标
```

- [ ] **Step 5: 跑测试**

Run: `cd resume-web && .venv/bin/pytest tests/test_render.py -v`
Expected: 3 passed。

- [ ] **Step 6: 提交**

```bash
git add resume-web/templates/resume.html.j2 resume-web/styles/awesome-cv.css resume-web/build.py resume-web/tests/test_render.py
git commit -m "feat(resume-web): Jinja2 模板与 CSS，渲染双语 HTML"
```

---

### Task 4: PDF 导出 + 命令行入口

**Files:**
- Modify: `resume-web/build.py`（追加 `export_pdf`、`build_one`、`main`）
- Create: `resume-web/tests/test_pdf.py`

**Interfaces:**
- Consumes: `render_html`（Task 3）。
- Produces:
  - `build_one(lang: str) -> tuple[Path, Path]` —— 写 `build/resume.<lang>.html` 与 `build/resume.<lang>.pdf`，返回两者路径。
  - CLI：`python build.py --lang {zh,en,all}`（默认 all）、`--html-only`。

- [ ] **Step 1: 往 `build.py` 追加导出与 CLI**

在 `resume-web/build.py` 末尾追加：
```python
import argparse
from playwright.sync_api import sync_playwright

BUILD_DIR = ROOT / "build"

FOOTER_HTML = (
    '<div style="width:100%;font-size:7pt;color:#999;'
    'font-variant:small-caps;padding:0 1.4cm;display:flex;'
    'justify-content:space-between;align-items:center;">'
    '<span></span><span>{label}</span>'
    '<span class="pageNumber"></span></div>'
)


def export_pdf(html_path: Path, pdf_path: Path, footer_label: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri())
        page.emulate_media(media="print")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=FOOTER_HTML.format(label=footer_label),
            margin={"top": "0.8cm", "right": "1.4cm", "bottom": "1.8cm", "left": "1.4cm"},
        )
        browser.close()


def build_one(lang: str, html_only: bool = False):
    data = load_data()
    BUILD_DIR.mkdir(exist_ok=True)
    html = render_html(data, lang)
    html_path = BUILD_DIR / f"resume.{lang}.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = BUILD_DIR / f"resume.{lang}.pdf"
    if not html_only:
        label = localize(data["meta"]["footer_label"], lang)
        export_pdf(html_path, pdf_path, label)
    return html_path, pdf_path


def main():
    ap = argparse.ArgumentParser(description="Build resume PDF/HTML from resume.yaml")
    ap.add_argument("--lang", choices=["zh", "en", "all"], default="all")
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()
    langs = ["zh", "en"] if args.lang == "all" else [args.lang]
    for lang in langs:
        html_path, pdf_path = build_one(lang, html_only=args.html_only)
        print(f"[{lang}] {html_path.name}" + ("" if args.html_only else f" + {pdf_path.name}"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 写测试**

创建 `resume-web/tests/test_pdf.py`：
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import build_one  # noqa: E402


def test_build_one_zh_creates_pdf_and_html():
    html_path, pdf_path = build_one("zh")
    assert html_path.exists()
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 20_000  # 非空 PDF（含 CJK）


def test_pdf_contains_text():
    from pypdf import PdfReader  # noqa
    _, pdf_path = build_one("en")
    reader = PdfReader(str(pdf_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Zumin" in text
```

在 `requirements.txt` 追加一行 `pypdf>=4.0` 并安装：
```bash
cd resume-web && echo "pypdf>=4.0" >> requirements.txt && .venv/bin/pip install -q pypdf
```

- [ ] **Step 3: 跑测试**

Run: `cd resume-web && .venv/bin/pytest tests/test_pdf.py -v`
Expected: 2 passed（首次较慢，Chromium 渲染）。

- [ ] **Step 4: 手动构建并肉眼核对**

Run: `cd resume-web && .venv/bin/python build.py --lang all`
Expected: 输出 `[zh] resume.zh.html + resume.zh.pdf` 与 `[en] ...`；`build/` 下出现 4 个文件。打开 `build/resume.zh.pdf` 与仓库根 `resume.pdf` 对比，段落齐全、红色标题、右侧红地点+灰日期、bullet、页脚页码均在。

- [ ] **Step 5: 提交**

```bash
git add resume-web/build.py resume-web/tests/test_pdf.py resume-web/requirements.txt
git commit -m "feat(resume-web): Playwright 导出 PDF 与命令行入口"
```

---

### Task 5: 网页(screen)样式 + 语言切换 + 字体打包 + --watch + README

**Files:**
- Modify: `resume-web/styles/awesome-cv.css`（追加 `@media screen` 与 `@font-face`）
- Create: `resume-web/assets/fonts/`（从仓库 `fonts/` 复制 Roboto 子集）
- Modify: `resume-web/templates/resume.html.j2`（screen 语言切换链接）
- Modify: `resume-web/build.py`（追加 `--watch`）
- Create: `resume-web/README.md`
- Create: `resume-web/tests/test_screen.py`

**Interfaces:**
- Consumes: `build_one`（Task 4）。
- Produces: `--watch` 起本地服务 + 监听重建；README 使用说明。

- [ ] **Step 1: 打包 Roboto 字体并加 @font-face**

Run（复制仓库已有 Roboto，避免联网字体）：
```bash
mkdir -p resume-web/assets/fonts && \
cp fonts/Roboto-Regular.ttf fonts/Roboto-Bold.ttf fonts/Roboto-Italic.ttf fonts/Roboto-Light.ttf resume-web/assets/fonts/
```

在 `resume-web/styles/awesome-cv.css` **顶部**追加：
```css
@font-face { font-family: "Roboto"; font-weight: 400; font-style: normal; src: url("../assets/fonts/Roboto-Regular.ttf"); }
@font-face { font-family: "Roboto"; font-weight: 700; font-style: normal; src: url("../assets/fonts/Roboto-Bold.ttf"); }
@font-face { font-family: "Roboto"; font-weight: 300; font-style: normal; src: url("../assets/fonts/Roboto-Light.ttf"); }
@font-face { font-family: "Roboto"; font-weight: 400; font-style: italic; src: url("../assets/fonts/Roboto-Italic.ttf"); }
```
注意：CSS 经 `render_html` 内联进 HTML，`url("../assets/...")` 相对 `build/resume.*.html` 解析 → 指向 `resume-web/assets/fonts/`，路径正确。

- [ ] **Step 2: 加 screen 样式与语言切换**

在 `resume-web/styles/awesome-cv.css` **末尾**追加：
```css
@media screen {
  body { background: #ececec; }
  .page {
    width: 21cm; min-height: 29.7cm; margin: 20px auto; background: #fff;
    box-shadow: 0 2px 16px rgba(0,0,0,.18); padding: 0.8cm 1.4cm 1.8cm;
  }
  .lang-toggle { position: fixed; top: 16px; right: 16px; }
  .lang-toggle a {
    background: var(--awesome); color: #fff; text-decoration: none;
    padding: 6px 12px; border-radius: 4px; font-size: 12px;
  }
}
@media print { .lang-toggle { display: none; } }
```

在 `resume.html.j2` 的 `<div class="page">` 之后加一行：
```jinja
  <div class="lang-toggle"><a href="resume.{{ 'en' if lang == 'zh' else 'zh' }}.html">{{ 'English' if lang == 'zh' else '中文' }}</a></div>
```

- [ ] **Step 3: 加 `--watch` 到 build.py**

在 `main()` 里 `args` 解析后、`langs` 之前加参数与分支。先在 argparse 处追加：
```python
    ap.add_argument("--watch", action="store_true", help="起本地服务并监听改动重建 HTML")
```
在 `main()` 末尾（`for lang ...` 循环之后）追加：
```python
    if args.watch:
        _serve_and_watch(langs)


def _serve_and_watch(langs):
    import http.server, socketserver, threading, functools
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    def rebuild():
        for lang in langs:
            build_one(lang, html_only=True)
        print("rebuilt:", ", ".join(langs))

    class H(FileSystemEventHandler):
        def on_any_event(self, e):
            if str(e.src_path).endswith((".yaml", ".j2", ".css", ".py")):
                try:
                    rebuild()
                except Exception as ex:
                    print("build error:", ex)

    obs = Observer()
    for d in ("data", "templates", "styles"):
        obs.schedule(H(), str(ROOT / d), recursive=True)
    obs.start()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(BUILD_DIR))
    httpd = socketserver.TCPServer(("127.0.0.1", 8000), handler)
    url = f"http://127.0.0.1:8000/resume.{langs[0]}.html"
    print(f"serving {url}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        obs.stop()
        obs.join()
```
注意：assets（字体/头像）在 `resume-web/` 下、HTML 在 `build/` 下，`../assets` 相对路径在 http server 根为 `build/` 时会指向 `resume-web/assets`，需服务 `resume-web` 根。将 `directory=str(BUILD_DIR)` 改为 `directory=str(ROOT)`，并把 `url` 改为 `http://127.0.0.1:8000/build/resume.{langs[0]}.html`。

- [ ] **Step 4: 写 README**

创建 `resume-web/README.md`：
```markdown
# resume-web — 简历（HTML/CSS + Python）

用一份 `data/resume.yaml` 生成中/英文简历 PDF，同一套 HTML 可当网站。

## 首次安装
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/playwright install chromium

中文字体需系统装 Noto Serif CJK（本机已装）。若缺失：
    sudo apt install fonts-noto-cjk

## 日常使用
- 改内容：只编辑 `data/resume.yaml`。
- 出 PDF：`.venv/bin/python build.py --lang all` → `build/resume.zh.pdf`、`build/resume.en.pdf`
- 只出某语言：`--lang zh` 或 `--lang en`
- 调排版预览：`.venv/bin/python build.py --html-only && .venv/bin/python build.py --watch`，浏览器开 http://127.0.0.1:8000/build/resume.zh.html ，改 YAML 自动刷新（所见即 PDF）。
- 头像：放 `assets/photo.jpg`（不放则不显示）。

## 结构
- `data/resume.yaml` 内容（双语）
- `templates/resume.html.j2` 排版
- `styles/awesome-cv.css` 外观
- `build.py` 构建脚本
```

- [ ] **Step 5: 写 screen 测试**

创建 `resume-web/tests/test_screen.py`：
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import load_data, render_html  # noqa: E402


def test_lang_toggle_present_and_crosslinks():
    zh = render_html(load_data(), "zh")
    assert "resume.en.html" in zh
    en = render_html(load_data(), "en")
    assert "resume.zh.html" in en


def test_font_face_bundled():
    html = render_html(load_data(), "zh")
    assert "@font-face" in html
    assert "Roboto-Regular.ttf" in html
```

- [ ] **Step 6: 跑全部测试**

Run: `cd resume-web && .venv/bin/pytest -v`
Expected: 全部 passed（smoke 2 + data 4 + render 3 + pdf 2 + screen 2）。

- [ ] **Step 7: 提交**

```bash
git add resume-web/styles/awesome-cv.css resume-web/templates/resume.html.j2 resume-web/build.py resume-web/README.md resume-web/assets/fonts resume-web/tests/test_screen.py
git commit -m "feat(resume-web): 网页样式、语言切换、字体打包、--watch 与 README"
```

---

## Self-Review

**Spec coverage:**
- HTML/CSS + YAML 数据分离 → Task 2/3 ✓
- Playwright+Python 导 PDF → Task 4 ✓
- 双语一份数据出两 PDF → Task 4（`--lang all`）✓
- 四种 section 类型（paragraph/skills/education/entries）→ Task 2 数据 + Task 3 模板 ✓
- 头像右上角 → Task 3 模板 `.photo` + `photo_exists` ✓
- 网站兼用（screen/print 两套样式 + 语言切换）→ Task 5 ✓
- 排版还原（颜色/字号/段标题两色/页脚页码）→ Task 3 CSS + Task 4 footer ✓
- 字体（Roboto 打包 + 系统 Noto CJK）→ Task 5 ✓
- 迁移范围（介绍/技术栈/教育/工作/项目 + 更多信息行）→ Task 2 数据齐全 ✓
- 只改 YAML 即可增删内容 → 数据驱动，✓
- LaTeX 文件不动 → Global Constraints ✓

**Placeholder scan:** 无 TBD/TODO；所有步骤含实际代码与命令。

**Type consistency:** `load_data`/`localize`(T2) → `render_html`(T3) → `build_one`/`export_pdf`(T4) → `_serve_and_watch`(T5) 签名一致；模板变量（`meta`/`sections`/`footer_more`/`photo_exists`/`icon`/`section_title`/`L`）与 `render_html` 传入的上下文一致。

备注（执行时留意）：段标题两色着色、行距与间距为观感项，Task 4 Step 4 肉眼对比 `resume.pdf` 后可在 `awesome-cv.css` 里微调，属预期内的视觉打磨，不算返工。
