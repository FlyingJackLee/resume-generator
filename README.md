# Web 简历（HTML/CSS + Python）

用一份 `data/resume.yaml` 生成中/英文简历 PDF，同一套 HTML 可当网站。

## 首次安装
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/playwright install chromium

中文优先使用 MiSans，英文使用项目内置的 Roboto。MiSans 字体文件受小米官方
许可约束，不能随仓库再次分发，因此 `assets/fonts-local/` 已加入 Git 忽略。

首次使用时，请从 [MiSans 官方页面](https://hyperos.mi.com/font/zh/download/)
下载字体包，将以下三个文件放到 `assets/fonts-local/`：

    MiSans-Regular.woff2
    MiSans-Medium.woff2
    MiSans-Semibold.woff2

使用 MiSans 即表示接受其官方许可协议。若本地未提供 MiSans，样式会依次回退到
系统 MiSans、Noto Sans CJK SC、思源黑体、微软雅黑或苹方。

## 日常使用

- 改内容：只编辑 `data/resume.yaml`。
- 出 PDF：`.venv/bin/python build.py --lang all` → `build/resume.zh.pdf`、`build/resume.en.pdf`
- 只出某语言：`--lang zh` 或 `--lang en`
- 调排版预览：`.venv/bin/python build.py --html-only && .venv/bin/python build.py --watch`，浏览器开 http://127.0.0.1:8000/build/resume.zh.html ，改 YAML 后重建 HTML，手动刷新浏览器即可（所见即 PDF）。
- 头像：放 `assets/photo.jpg`（不放则不显示）。

也可以构建任意定制版 YAML，而不替换基准文件：

    .venv/bin/python build.py --data variants/acme-ai/resume.yaml \
      --output-dir variants/acme-ai/build --lang all

## 根据岗位 JD 生成定制版

`data/resume.yaml` 是唯一的基准简历。`tailor.py` 会把 JD 与基准简历发送给
DeepSeek，生成匹配分析和有证据支持的文案修改；它不会覆盖基准文件，也不允许
模型修改联系方式、公司、职位、时间、学校、项目名称等事实字段。

先在当前 shell 设置 API Key：

    export DEEPSEEK_API_KEY="你的 API Key"

准备一个 UTF-8 文本文件，例如 `jd/acme-ai-agent.txt`，然后运行：

    .venv/bin/python tailor.py jd/acme-ai-agent.txt --name acme-ai-agent

同时生成中英文 HTML/PDF：

    .venv/bin/python tailor.py jd/acme-ai-agent.txt \
      --name acme-ai-agent --build

也可以从标准输入读取 JD：

    pbpaste | .venv/bin/python tailor.py - --name acme-ai-agent

默认使用 `deepseek-v4-pro`。可以通过 `--model` 或 `DEEPSEEK_MODEL` 改为
`deepseek-v4-flash`；Base URL 默认是 `https://api.deepseek.com`。接口配置参见
[DeepSeek 官方首次调用文档](https://api-docs.deepseek.com/)和
[JSON Output 文档](https://api-docs.deepseek.com/guides/json_mode/)。

每个版本输出到 `variants/<名称>/`：

- `resume.yaml`：岗位定制简历
- `suggestions.md`：匹配度、差距、关键词、面试风险和逐项修改说明
- `analysis.json`：模型、Token 用量和机器可读审计记录
- `jd.txt`：本次使用的原始岗位信息
- `build/`：使用 `--build` 时生成的 HTML/PDF

`variants/`、`.env` 和本地 API Key 已加入 Git 忽略。注意：调用 API 时，基准简历
与 JD 会发送给 DeepSeek；请先确认其中不含不希望提交给第三方服务的信息。生成结果
仍应人工审核，特别是技能表述、量化成果和岗位匹配度。

## 结构

- `data/resume.yaml` 内容（双语）
- `templates/resume.html.j2` 排版
- `styles/awesome-cv.css` 外观
- `build.py` 构建脚本
- `tailor.py` JD 分析与定制版生成

## LaTeX 归档

旧版 LaTeX 工程已停止维护，完整文件保存在 `backup/` 中。
