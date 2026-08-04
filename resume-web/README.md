# resume-web — 简历（HTML/CSS + Python）

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

## 结构
- `data/resume.yaml` 内容（双语）
- `templates/resume.html.j2` 排版
- `styles/awesome-cv.css` 外观
- `build.py` 构建脚本
