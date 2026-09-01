# resume-generator

简历生成项目，Web 简历与后续 Agent 能力分开维护。

## 项目结构

- `web/`：当前可用的双语 Web/PDF 简历生成器
- `agent/`：预留给后续基于正式 spec 开发的简历 Agent
- `backup/`：停止维护的旧版 LaTeX 工程归档

当前稳定版本为 `v1.0`。Web 项目的安装、编辑和构建方式见
[`web/README.md`](web/README.md)。Agent 目录目前不包含实现，等待设计 spec 后再开发。
