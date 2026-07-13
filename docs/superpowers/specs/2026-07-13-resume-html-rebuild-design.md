# 简历从 LaTeX 迁移到 HTML/CSS + Python 构建 — 设计文档

日期：2026-07-13
作者：Zumin Li（协作：Claude）

## 背景与目标

现有简历用 Awesome-CV LaTeX 模板（`resume.tex` + `resume/*.tex`）编写，双语（中文/英文）通过 `\IfLanguageName` 开关在同一份 `.tex` 里切换。痛点是**每次改内容、编译都很麻烦**（xelatex + ctex 工具链重、报错难懂、编辑体验差）。

目标：
- **改内容简单** —— 内容集中在一份数据文件里，非技术性编辑。
- **编译一条命令** —— `python build.py` 直接出 PDF。
- **排版接近现在** —— 尽量复刻 Awesome-CV 的观感（红色段标题、右侧红色地点+灰色日期、bullet、页脚等）。
- **保留双语能力** —— 一份数据导出中/英两个 PDF。
- **兼做个人网站** —— 同一套 HTML/CSS 既能打印成 PDF，也能部署到 `resume.flyingjack.top`。

不做（YAGNI）：
- 不重写 cover letter / cv.tex（本次只迁移 `resume`）。
- 不做在线编辑器、后台、数据库。
- 不追求与 LaTeX 输出像素级完全一致，只求观感接近、可微调。

## 技术选型（已确认）

| 决策点 | 选择 |
|---|---|
| 内容与排版分离 | HTML/CSS 模板 + YAML 数据文件（Jinja2 渲染） |
| PDF 渲染器 | Playwright + Python（真实 Chromium 内核，浏览器预览 = PDF 输出） |
| 双语 | 一份 `resume.yaml`，构建时 `--lang zh/en/all` 分别导出 |
| 头像 | 需要，右上角（`assets/photo.jpg`） |
| 网站兼用 | 需要，screen 与 print 两套样式 |

选 Playwright 而非 WeasyPrint 的原因：Chromium 对 CSS（flex/grid、字体、中文排版）支持完整，且**浏览器里看到的就是 PDF 里的样子**，所见即所得，调排版最省心。代价是首次需下载一个 Chromium（`playwright install chromium`）。

## 目录结构

旧 LaTeX 文件全部保留不动，新工程放在 `resume-web/`：

```
resume-web/
  data/
    resume.yaml            # 唯一需要日常编辑的文件（双语内容 + 顺序）
  templates/
    resume.html.j2         # Jinja2 模板：把数据渲染成 HTML
  styles/
    awesome-cv.css         # 复刻 Awesome-CV 外观（颜色/字号/间距/print+screen）
  assets/
    icons/                 # 内联/本地 SVG：phone, email, homepage, github, wechat
    photo.jpg              # 头像（用户放置）
    fonts/                 # 可选：打包 Roboto，保证拉丁字体一致
  build.py                 # 构建脚本：数据 + 模板 → HTML → PDF
  requirements.txt
  README.md
  build/                   # 输出目录（git 忽略）
    resume.zh.html / resume.en.html
    resume.zh.pdf  / resume.en.pdf
```

## 数据模型（resume.yaml）

设计原则：双语文本统一写成 `{zh: "...", en: "..."}` 映射；构建时按 `--lang` 取对应值。`sections` 是**有序列表**，调整顺序或注释掉某段直接改 YAML。

```yaml
meta:
  name:     {zh: "李祖民", en: "Zumin Li"}
  position: {zh: "软件工程师 · 全栈开发", en: "Software Engineer · Full Stack Developer"}
  color: "#DC3522"          # awesome 主色，可换
  contacts:
    mobile:   "(+86) 13675823946"
    email:    "zumin.li.work@gmail.com"
    homepage: "resume.flyingjack.top"
    github:   "FlyingJackLee"
    wechat:   "13675823946"
  footer_more:              # 底部“更多信息”行
    zh: "更多信息，烦请访问我的个人网站："
    en: "See my website for more："
    url: "https://resume.flyingjack.top/"

sections:
  # 1) 段落型（个人介绍）
  - type: paragraph
    title: {zh: "个人介绍", en: "Introduction"}
    body:  {zh: "…", en: "…"}

  # 2) 技能型（技术栈）
  - type: skills
    title: {zh: "技术栈", en: "Skills"}
    rows:
      - {label: {zh: "后端技术链", en: "Backend"}, items: {zh: "…", en: "…"}}
      # …

  # 3) 教育型（两行，无 bullet）—— 对应 \cventryfour
  - type: education
    title: {zh: "教育经历", en: "Education"}
    entries:
      - degree:   {zh: "软件工程 硕士 - Distinction一等学位", en: "MSc in Software Engineering - Distinction"}
        org:      {zh: "英国格拉斯哥大学", en: "University of Glasgow"}
        location: {zh: "格拉斯哥, 英国", en: "Glasgow, UK"}
        date:     {zh: "2020年9月 - 2022年4月", en: "September 2020 – April 2022"}

  # 4) 条目型（工作/项目，带 bullet）—— 对应 \cventry + \cvitems
  - type: entries
    title: {zh: "工作经历", en: "Work"}
    entries:
      - title:    {zh: "技术合伙人", en: "Technical Lead & Partner"}
        org:      {zh: "麒霖通信有限公司", en: "Qilin Communications Co., Ltd."}
        location: {zh: "贵阳, 中国", en: "Guiyang, China"}
        date:     {zh: "2023年11月 - 2026年2月", en: "November 2023 – February 2026"}
        link:     null            # 可选：项目/GitHub 链接（项目段用）
        items:
          - {zh: "…", en: "…"}
          - {zh: "…", en: "…"}
```

四种 `type` 覆盖现有全部内容：`paragraph`（个人介绍）、`skills`（技术栈）、`education`（教育，两行无 bullet）、`entries`（工作/项目，带 bullet，可选链接）。

## 构建流程（build.py）

```
python build.py --lang zh      # 只出中文
python build.py --lang en      # 只出英文
python build.py --lang all     # 两个都出（默认）
python build.py --watch        # 起本地服务 + 监听 YAML，浏览器自动刷新调排版
```

步骤：
1. 读 `data/resume.yaml`，用 Jinja2 环境（自定义 filter 按 `lang` 取 `{zh,en}` 里的值）渲染 `templates/resume.html.j2` → `build/resume.<lang>.html`。
2. HTML `<head>` 内联 `styles/awesome-cv.css`；图标、头像、字体用本地相对路径（部署网站时可用，Playwright 加载本地文件也可用）。
3. Playwright 启动 Chromium，`page.goto("file://…/resume.<lang>.html")`，等字体就绪，`page.pdf()` 导出：A4、边距 `left/right 1.4cm, top 0.8cm, bottom 1.8cm`（对齐现有 `\geometry`）、`print_background=True`（保留红色）。
4. `--watch`：用简单 HTTP server 提供 `build/`，文件监听 YAML/模板/CSS 变化则重渲染 HTML，浏览器自带刷新。（PDF 只在显式构建时生成。）

## 排版还原细节（CSS）

从 `awesome-cv.cls` 提取的精确参数：

- **颜色**：主色 `awesome-red #DC3522`；正文 `#333333`；灰 `#5D5D5D`；浅灰 `#999999`；深文字 `#414141`。
- **页头**：名字（first name 浅灰细体 + last name 深色粗体）、职位（红色 small-caps 小字，`·` 分隔）、地址（浅灰斜体，可选）、联系行（图标 + 文本，`|` 分隔）、可选 quote（斜体）。头像右上角。
- **段标题**：粗体，**前几个字用主色**（如 Edu→红、cation→深；中文如“教育”前 1–2 字），后接一条延伸到右边距的横线。着色字数做成可配置（默认拉丁 3 字 / 中文 1 字），可按段覆盖。
- **条目（entries）**：左列标题（10pt 粗）+ 机构（8pt small-caps 灰）；右列地点（9pt 红斜）+ 日期（8pt 灰斜）；下方 `•` bullet 列表（9pt）。项目段标题可为链接（等宽字体显示 URL）。
- **教育（education）**：学位（粗）与机构同区，右侧地点（红斜）+ 日期（灰斜），无 bullet。
- **技能（skills）**：每行 label（10pt 粗）+ 逗号分隔技能（9pt）。
- **页脚**：顶部横线 + 居中 `<name> · Résumé` + 右下页码（打印时用 CSS `@page`/running element 或 Playwright footerTemplate 生成页码）。
- **字体**：拉丁用 Roboto（打包到 `assets/fonts/` 用 `@font-face` 保证一致）；中文用 Noto Serif CJK / Noto Sans CJK（依赖系统安装，README 给 WSL 的 `apt install fonts-noto-cjk` 命令）。为打印保色加 `-webkit-print-color-adjust: exact`。
- **screen vs print**：`@media print` / `@media screen` 分离。print 严格复刻 A4 观感；screen 版做成适合网页浏览的居中卡片式布局，隐藏打印页脚页码，可选加一个中/英语言切换链接（纯静态，link 到另一语言 HTML）。

## 网站部署

`build/` 里的 `resume.zh.html` / `resume.en.html` + `assets/` 即为静态站点，可直接托管（如把 `resume.zh.html` 复制为 `index.html`）。本设计不含 CI/托管配置，仅保证产物是可托管的自包含静态文件。

## 验收标准

1. `python build.py --lang all` 一条命令产出 `resume.zh.pdf` 和 `resume.en.pdf`，无手动步骤。
2. 两个 PDF 内容与现有 `resume/*.tex` 一致（个人介绍、技术栈、教育、工作、项目全部搬过来）。
3. 观感接近现有 Awesome-CV：红色段标题、右侧红地点+灰日期、bullet、页脚、头像位置。
4. 只改 `data/resume.yaml` 即可增删/改内容与调整段落顺序，无需碰模板或 CSS。
5. 浏览器直接打开 `build/resume.zh.html` 观感与 PDF 基本一致（所见即所得）。
6. HTML 产物可作为静态网页部署。

## 迁移范围

本次搬运这些现有段落（按当前 `resume.tex` 顺序）：个人介绍(`summary`)、技术栈(`prompt_skill`)、教育(`education`)、工作(`internships`)、项目(`projects`)、以及底部“更多信息”行。`publications`/`committees`/`honors`/`extracurricular` 当前已注释，不迁移（数据模型支持，需要时再加）。
