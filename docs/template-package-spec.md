# Resume Generator 模板包规范（v1）

模板包是一个 ZIP 文件，只控制固定简历结构的视觉样式，不能修改或新增简历数据字段。

## 目录结构

```text
my-template.zip
├── manifest.json          # 必需：模板元数据与兼容性声明
├── theme.css              # 必需：CSS 样式覆盖
├── preview.png            # 可选：模板管理页缩略图（建议 4:3）
└── assets/                # 可选：本地字体、图片等静态资源
    └── MyFont.woff2
```

## manifest.json

```json
{
  "id": "my-clean-template",
  "name": "我的极简模板",
  "description": "适合技术岗位的一页式布局",
  "unsupported": ["照片", "项目简介"]
}
```

- `id`：必填；只允许小写字母、数字、`-`、`_`，最长 49 个字符，且不能与已有模板重复。
- `name`：必填；显示名称。
- `description`：建议填写；模板卡片中的说明。
- `unsupported`：可选。可选值：`照片`、`联系方式 / 社交链接`、`个人介绍`、`技能`、`教育`、`项目简介`、`项目职责`、`链接`。

## theme.css

系统提供固定的简历 HTML 结构，模板只可覆盖其 CSS。可使用颜色、字体、网格、间距、分页、边框等样式。

引用包内资源时请使用相对路径：

```css
@font-face { font-family: "My Font"; src: url("assets/MyFont.woff2") format("woff2"); }
```

不允许 JavaScript、HTML 模板、`@import`、HTTP/HTTPS 远程资源或路径穿越（`..`）。模板以既有 A4、中英文 HTML/PDF 规则渲染，不能修改纸张、边距、数据字段或文件命名规则。
