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
