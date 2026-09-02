# 前端重构 · 开发路线图与决策记录

> 工程侧文档，配套 `FRONTEND_PRD.md`（面向 UI 设计师的功能 PRD）。
> 记录 2026-09-02 需求梳理会话中定下的所有架构决策及理由，供后续实际开发时对齐，
> 避免"为什么当初这么定"的记忆丢失。

## 决策记录

| # | 决策 | 理由 |
|---|---|---|
| 1 | 纯个人工具，本地跑，不做鉴权/多用户 | 当前唯一使用者是本人；但业务逻辑层不要写死"无鉴权"假设，为后续 B 阶段留口子 |
| 2 | "在线查看"是私有预览工具，不对外分享 | 用途是自己对比不同 JD 版本的排版效果，不涉及分享链接、SEO、移动端优化 |
| 3 | Agent 后端复用 `web/` 的 Jinja+CSS 渲染逻辑做预览端点，不在 React 里重新实现简历排版 | 避免"在线查看"和 PDF 导出出现两套渲染实现、样式跑偏的风险 |
| 4 | 本地 localhost 运行；远程访问/鉴权推迟到"B 阶段"评估 | 当前不需要；一旦要做远程访问，鉴权和并发写入问题最好一起解决 |
| 5 | 接入 LangSmith 做 LLM 调用可观测性，以外链形式嵌入 Run 详情页 | 已用 LangGraph，接入成本接近零；LangSmith 解决"调用层"可观测性，不替代业务 UI |
| 6 | Agent 操作台 = React SPA；在线查看 = SPA 内 iframe 嵌入服务端渲染端点 | 操作台交互密集适合 SPA 状态管理；简历渲染继续走服务端保证与 PDF 一致 |
| 7 | Run 管理支持：公司分组/搜索、标记最终版本、归档、同 JD 跨 Run 对比（不做跨公司对比） | 跑多次挑最优版本是真实场景；跨公司对比无实际使用场景，暂不做 |
| 8 | 公司字段：创建时可选填 → 分析完成后用 `job_profile.target_company` 自动回填 → 都没有归"未分类" | 兼顾"懒得填"和"列表别全是未分类" |
| 9 | Human Gate ② 人工 Patch 改为结构化操作构建器（选路径 + 选操作类型 + 填值），弃用裸 JSON textarea | 不用记内部路径语法，出错概率降低 |
| 10 | 状态更新用 SSE 替代轮询 | 后端本身是同步 stream 循环，加 SSE 改动小，体验提升明显 |
| 11 | 继续用文件系统存储，`run.json` 加字段（company / is_final / archived），不引入数据库 | 个人工具量级下文件扫描性能足够；等 B 阶段远程/并发问题一起出现时再评估上 DB |
| 12 | Human Gate ① 不支持新增自定义 action，只能编辑/丢弃 AI 建议 | 低频需求，AI 漏掉的可以靠 retry 策略生成或 Gate ② 人工 Patch 兜底 |
| 13 | "在线查看"包含 Master Resume 本身作为基准版本 | 复用同一渲染端点，成本低；作为所有改写版本的参照系很自然 |
| 14 | 分两期：Phase 1（核心可用）先做，Phase 2（Run 管理增强）后做 | 核心操作台+在线查看是"没有就不能用"的部分，可以先用起来不用等大而全 |
| 15 | PRD 面向 UI 设计师，按页面/流程/状态组织，不暴露 API/Pydantic 细节 | 交付对象是设计师不是工程师 |
| 16 | Resume Viewer 版本历史只保留 Master Resume 和 Run 最终版本，不列分析阶段的伪版本 | JD Analyzer/Resume Matcher/HR Reviewer 不改动简历内容，列出来会是好几个内容相同的"版本"，无信息量 |
| 17 | 不做"策略对齐度评分"（Alignment Score）和"自动审批检查清单"，Phase 1 从设计稿范围里砍掉 | 本质是 AI 给自己生成的策略打分，可信度存疑（不像 Hiring Manager 是独立视角）；且要新增一整个评估节点，成本高收益主要是好看 |
| 18 | SSE 端点实现为"轮询 events.jsonl"，不是从后台 Thread 真正 push | `analyze`/`compile` 跑在 daemon Thread 里，做真 push 需要额外的跨线程队列，复杂度和收益不成正比；文件轮询 400ms 间隔已经比原来 2s 整页轮询快很多 |
| 19 | 前端放在 `agent/frontend/`，技术栈 Vite + React + TypeScript + pnpm + react-router-dom + @tanstack/react-query，开发期用 Vite proxy（不是 CORS）打通后端 | 与 `agent/src`、`agent/templates` 并列，保持 `web/`/`agent/` 顶层分离的现状约定；react-query 的 `invalidateQueries` 让 SSE 只需要当"重新拉取"的信号，不用手写增量合并状态机；proxy 方式让前端代码全用相对路径，天然为以后"打包进同一进程"铺路，也避开 EventSource 跨源的边缘情况 |
| 20 | `/structure` 端点加 `source=input\|candidate`，Patch 构建器的 reorder/replace 用 candidate | 人工 Patch 打在 candidate_resume.yaml 上，不是 Master Resume；AI 的 Rewrite Strategy 常包含 reorder，用 input 的顺序会让用户看到的初始顺序是错的 |
| 21 | Patch 构建器的"目标字段"选择器同时拉 input 和 candidate 两份结构，input-only 的路径单独归"已隐藏（可恢复）"组，且操作类型强制只有 restore | 被 hide 掉的字段从 candidate 结构里彻底消失，只用 candidate 结构会导致"restore"永远选不到任何目标——这是实测中发现的真实可用性问题，不是提前设计出来的 |
| 22 | 视觉还原不引入 UI 框架（不上 Tailwind/shadcn），继续手写 CSS + `theme.css` 里的设计 token；只加 `lucide-react` 做图标 | 个人工具、单人维护，Tailwind/shadcn 主要解决的是团队协作下的设计系统一致性问题，这里不存在；现有 7 个文件已经用纯 CSS 写完并测试过，换框架要么全部重写有回归风险，要么新旧两套混用更乱；剩下要做的视觉都是布局+着色，不需要 Radix 那类复杂交互组件兜底。`lucide-react` 只是图标库不是框架，成本低、直接提升图标还原度，所以留下 |
| 23 | 状态徽章统一显示简短标签（RUNNING/WAITING/COMPLETED/FAILED/REJECTED），不显示后端原始状态枚举值 | 设计稿里徽章都是简短形式；细分状态（ANALYZING/MATCHING/…）改到 `run.stage` 那行文字里显示，徽章只做"大类"指示 |
| 24 | SPA 界面文案 i18n 手写实现（`src/i18n/`），不上 `react-i18next` | 量级不需要专门的 i18n 库（没有复数/懒加载命名空间这些需求），跟决策 #22 一致的"没必要就不加依赖" |
| 25 | i18n 范围只覆盖前端组件的静态文案，不覆盖后端产出的动态内容（`run.stage`、报错信息、AI 生成的策略/评审文字） | 后端那部分是 Python 产出的数据，要翻译得动后端，用户明确说了这次不做 |
| 26 | Run 详情页顶部 7 步进度条、左侧 11 项 Workflow 节点状态，全部从已有的 `run.status` + `events` 的 `last_completed_node` 字段派生，不新增后端接口，不做精确耗时 | `last_completed_node` 是 Milestone 1 就有的稳定机器可读字段（不是会变的中文 `stage` 文本），派生逻辑能跑在纯前端；耗时要更复杂的时间戳配对，留到后面有实际需要再做，先把状态点做对 |
| 27 | 事实校验/Hiring Manager 两张卡片固定挪到右侧栏（不分状态，只要有数据就显示），不复制一份放在主内容区 | 跟设计稿"评估结果固定放右边"的位置约定一致；不分状态显示逻辑更简单，`COMPLETED` 后回看也一样能看到评估结果 |
| 28 | Strategy Summary 不做 Keeping/Discarding 实时计数，Troubleshooting 不做 Recommendations 建议文案 | 前者要把 `StrategyGate` 内部的勾选状态提升到父组件，代价大于收益；后者现有 `ValidationIssue` 数据（只有 code/severity/message/path）撑不起具体建议，硬编通用文案等于编造，不做 |

## Milestone 8（Phase 1 收尾：LangSmith 外链 + 两个已知 bug + 下线旧版 Jinja UI + 在线查看视觉）完成记录（2026-09-02）

对照 `FRONTEND_PRD.md` 原定 Phase 1 范围做完整性检查，发现 5 项缺口，前端测试框架那项定位
不同（"后续补充项"而非"补齐原定范围"）不在这次收尾内，其余 4 项这次全部收掉。

完成内容：
- **LangSmith 外链**：不加新 pip 依赖（`langsmith` 已是 `langgraph`/`langchain-core` 的
  传递依赖）；`workflow_service.py` 的 `analyze()`/`compile()` 调用图时的 `config` 加
  `tags=[run_id], run_name=run_id`；新增 `Settings.langsmith_project_url`（对应
  `RESUME_AGENT_LANGSMITH_PROJECT_URL`），`WorkflowService.get()` 动态注入
  `metadata["langsmith_trace_url"]`（不落盘）；`RunHeader.tsx` 加"View in LangSmith"按钮，
  仅在该字段非空时渲染
- **两个已知 bug 修复**：见下方 Phase 1 清单里对应条目的更新说明（`all_operations.json`
  累积文件方案 + `stage` 字段补全）
- **下线旧版 Jinja UI**：删除 `main.py` 里全部 `/ui/*` 路由和 `_split_keywords` 辅助函数、
  `Jinja2Templates`/`Form`/`RedirectResponse` 等未用 import，`GET /` 换成极简 JSON 提示；
  删除 `agent/templates/` 整个目录；删除前端 `client.ts` 里零调用点的 `legacyRunViewUrl()`；
  `test_api.py` 两处测试改成断言 JSON API（`test_api_executes_both_human_gates` 改查
  `/artifacts` 里的 `rewrite_strategy`，原 `test_ui_loads_without_api_key_...` 改名为
  `test_root_loads_without_api_key_...` 断言新的 `/` JSON 消息）
- **在线查看页面视觉对齐**：补 `page-header`（标题+说明文字）；版本下拉+语言切换合并成同一行
  工具栏卡片；iframe 包一层卡片，跟其余页面视觉一致。不做设计稿里没有真实功能支撑的元素
  （缩放/打印控件、独立的 Version History 面板——后者内容跟版本下拉重复，决策 #16 已定）
- 验证：`pytest agent/tests web/tests` 60 个全绿（新增 4 个测试）；`pnpm build` 零类型错误；
  用 Claude in Chrome 配合临时 `HappyProvider` 脚本实测——确认 `GET /`、`/ui/*` 旧路由行为
  符合预期、SPA 不受影响；提交一次人工 Patch 后"最终 Diff"卡片同时显示 AI 原始改动
  （`/sections/introduction/body`）和新的人工改动（`hide` 一条 work entry）两条记录；批准
  导出后确认 Run Info 面板"当前阶段"文字从审批前文案更新为"已批准导出"；LangSmith 按钮在
  配置了假 URL 时正确渲染并指向该 URL；在线查看页面新布局截图确认；中英文都过了一遍；验证
  用的临时 run 数据清理，真实后端已用真实 `.env` 重新起好

未完成：前端测试框架（性质不同，留在"Phase 1 技术任务清单"里作为独立后续项，不算这次
"收尾"范围）。到这里 `FRONTEND_PRD.md` 原定 Phase 1 功能范围已全部覆盖。

## Milestone 7（Run 详情页视觉还原·状态特有的右侧内容）完成记录（2026-09-02）

Milestone 6 做完外壳后，右侧栏一直只有 `RunInfoPanel`。这次把设计稿里其余的右侧栏内容补上：
Gate①的 Strategy Summary 统计、失败态的 Troubleshooting 面板，以及把"事实校验"/
"Hiring Manager"两张卡片从主内容区挪到右侧栏（决策 #27）。

完成内容：
- `components/StrategySummaryPanel.tsx`（新建）：Total Actions + 优先级分桶计数（1-2 高/
  3 中/4-5 低），只在 Gate①（`WAITING_STRATEGY_APPROVAL`）渲染，纯前端从
  `artifacts.rewrite_strategy.actions` 算，不需要新后端数据
- `components/TroubleshootingPanel.tsx`（新建）：按 severity（critical/high/low）分组计数，
  只在 `FAILED` 且有 `artifacts.error.issues` 时渲染
- `RunDetailPage.tsx`：右侧栏从单卡片变成纵向堆叠（`RunInfoPanel` 常驻 + 按状态追加其余卡片），
  `ValidationCard`/`HiringReviewCard` 从主内容区移到右侧栏（决策 #27），组件本身不用改
- 明确不做的部分见决策 #28
- 验证：`pnpm build` 零类型错误；用 Claude in Chrome 分两轮跑——一轮用现有的
  `HappyProvider` 临时脚本验证 Gate①的 Strategy Summary 计数、以及编译完成后
  事实校验/Hiring Manager 卡片确实从主内容区移到了右侧栏（用 `querySelector` 直接核对
  `.run-detail-main`/`.run-detail-side` 各自包含哪些卡片标题，不只是肉眼看截图）；另一轮
  新写了一个基于 `AlwaysInvalidProvider`（复用 `test_workflow_service.py` 里现成的失败
  provider 逻辑）的临时脚本，把一个 run 逼到 `FAILED`，确认 Troubleshooting 面板的问题
  计数（critical 1/high 1）和主内容区"运行失败"卡片里列出的问题一致；中英文都过了一遍；
  两轮都在验证前确认 Runs 列表为空、验证完把真实后端换回来；`pytest agent/tests web/tests`
  56 个全绿（没碰后端逻辑）

未完成、留给后续：Workflow 节点精确耗时、LangSmith 按钮（功能本身还没接）、公司 Logo、
Resume Viewer 页面视觉。到这里 Run 详情页的主要视觉工作基本完成，剩下的都是相对独立的小块，
可以按需单独排期。

## Milestone 6（Run 详情页视觉还原·外壳）完成记录（2026-09-02）

Run 详情页是设计稿里最复杂的一块（8 张里 5 张是它的不同状态），这次先做"外壳"——所有状态下
结构相同、只是内容变化的部分：面包屑、Header、顶部 7 步进度条、左侧 Workflow 节点面板、右侧
Run Info 面板、底部 Activity Log/Notes 标签页。内容区继续用 Milestone 3/4/5.5 已经做好、
测过、翻译过的 `JobProfileCard`/`StrategyGate`/`FinalGate`/`PatchBuilder` 等组件，没有重做，
只是从"一列到底"布局挪进新外壳的主内容区。

完成内容：
- `lib/workflowSteps.ts`（新建）：`deriveWorkflowSteps()` 把 11 个细粒度节点的状态
  （done/active/pending）从 `run.status` + `events` 派生出来（决策 #26）；`deriveMacroSteps()`
  把这 11 项归到顶部 7 步进度条的 7 个大类
- 新组件：`RunHeader`（面包屑+头像+标题+状态徽章）、`StepStrip`（顶部 7 步条）、
  `WorkflowRail`（左侧 11 项节点列表，带 lucide 图标：完成=勾、进行中=旋转 loader、待处理=
  空心圆）、`RunInfoPanel`（右侧状态/阶段/创建时间/已耗时，耗时前端简单计算不做实时刷新）、
  `RunTabs`（Activity Log + **Notes**——Milestone 1 就做好的 `updateNotes` 接口一直没有前端
  UI，这次顺手补上）
- `RunDetailPage.tsx` 布局改三栏 `220px 1fr 280px`（Workflow / 主内容 / Run Info）
- `translations.ts` 补 `workflow.*`（11 个节点名 + 7 步简称，两个语言都用相同的英文技术名，
  跟 `JD`/`Resume Editor` 这类专有名词的既有处理方式一致，不强行翻成中文）和
  `runDetail.notes/tabs/runInfo/breadcrumbRuns`
- 验证：`pnpm build` 零类型错误；用 Claude in Chrome 把一个 run 从创建走到 COMPLETED 全程
  截图，每个状态下步骤条和 Workflow 侧栏的高亮/勾选都对（用 `.className` 直接查每个
  workflow-rail-item 的状态类名核对，不只是肉眼看截图）；中英文各截了一遍确认新文案都翻了；
  Notes 标签页测试保存后刷新页面、甚至重新打开页面内容都还在（真的调用了后端接口，不是本地
  状态）；`pytest agent/tests web/tests` 56 个全绿（没碰后端逻辑）

未完成、留给 Milestone 7：Gate① 右侧 Strategy Summary 统计卡片、Gate② 右侧 Diff Detail
点击详情面板、失败态右侧 Troubleshooting 环形图、Workflow 节点精确耗时、LangSmith 按钮（功能
本身还没接）、公司 Logo、Resume Viewer 页面视觉。

## Milestone 5.5（SPA 界面文案 i18n）完成记录（2026-09-02）

用户实际跑起来试用后发现界面中英文混杂（表单标签中文、"How it works"和状态词是抄设计稿的
英文），要求做真正能切换的双语界面。范围明确限定在前端静态文案，后端动态内容不翻译（决策
#25）。

完成内容：
- `src/i18n/translations.ts`（新建）：`zh`/`en` 两个字典，显式 `Translations` 接口保证两边
  key 结构完全对齐（一开始想用 `as const` + `typeof zh` 推导类型，会把每个字符串推成字面量
  类型导致 `en` 怎么写都类型报错，改成显式接口 + 两边都标注 `Translations` 类型）
- `src/i18n/LanguageContext.tsx`（新建）：`LanguageProvider` + `useTranslation()`，状态叫
  `uiLang`（不叫 `lang`，跟 `ResumeViewerPage` 里"预览简历用什么语言"的局部 state 区分开，
  那个改名成 `previewLang` 了），存 `localStorage`（key `resume-agent-ui-lang`），默认中文；
  `t(path, params?)` 按点分路径查字典 + 简单 `{name}` 插值；同时导出 `dict`（当前语言完整
  对象树）给需要结构化数据（比如 `newRun.steps` 数组、`hiringReview.scoreLabels`、
  `patchBuilder.kindLabels` 这几个不是单条字符串的地方）的组件直接用
- 侧边栏底部加"中/EN"切换（复用已有 `.lang-toggle` 样式），全局生效
- 逐个替换了 `App.tsx`、`RunsListPage`、`NewRunPage`、`RunDetailPage`（含内部子组件和
  `SCORE_LABELS`）、`StrategyGate`、`FinalGate`、`PatchBuilder`（含 `KIND_LABEL`）、
  `ResumeViewerPage`、`StatusBadge`、`lib/format.ts`（`formatDate` 按 `uiLang` 传
  `zh-CN`/`en-US` locale）里的硬编码文案，`ResumeViewerPage` 自己的"中文/English"按钮
  （切换的是被预览简历的语言，不是 UI 语言）保留原样不翻
- 验证：`pnpm build` 零类型错误；用 Claude in Chrome 实测——默认中文、切到英文、刷新页面
  确认 `localStorage` 生效持久化；借复用 Milestone 3/4 的 `HappyProvider` 临时脚本（临时
  换下真实后端、验证完再换回来，没有影响用户自己起的真实服务）把一个 run 走到 Gate①②，
  确认 `StrategyGate`/`FinalGate`/`PatchBuilder`（含操作类型下拉、字段分组 optgroup 标签）
  在英文模式下都正确翻译，`run.stage` 等后端产出的中文内容按预期没有被动；
  `pytest agent/tests web/tests` 56 个全绿（本次没碰后端逻辑）

## Milestone 5（视觉还原·第一批：设计系统 + 侧边栏 + Runs 列表 + 新建 Run）完成记录（2026-09-02）

补一个之前没做好的地方：Milestone 2-4 的每个计划都写了"视觉设计另行讨论"，但实际做出来的是
完全通用的顶部导航+红色按钮样式，跟 `design/` 目录里 UI 设计师交付的 8 张设计稿没有对齐——这
是判断失误，"另行讨论"不等于"随便糊"。这次开始补，按用户要求"保留设计稿整体风格和布局思路，
细节可以自由发挥"。

完成内容：
- `theme.css`（新建）：从设计稿里提炼的设计 token——主色蓝（`#2563eb`，替换掉沿用自 `web/`
  PDF 主题的红色 `#b52b1d`）、状态语义色（绿/橙/蓝/红/紫，浅底深字）、中性色、圆角、间距刻度
- `index.css` 大幅重写，`.card`/`.badge`/`button`/表格/表单等基础类全部换用 token
- 加 `lucide-react` 依赖做图标（决策 #22）
- `App.tsx`：顶部导航换成侧边栏（Logo、Runs/Resume Viewer 导航、"MASTER RESUME" 分组 + 链接
  到 `/viewer?token=master`、底部静态用户条——不接真实账号系统）
- `ResumeViewerPage.tsx` 加读 `token` query 参数，配合侧边栏的 Master Resume 链接
- `RunsListPage.tsx` 重做：状态圆点图标 + JD 占位头像、状态徽章新配色、Hiring Score 数字+迷你
  进度条、数字页码分页 + 每页条数下拉（不是摆设，真实升级了原来的"上一页/下一页"）
- `NewRunPage.tsx` 重做：两栏布局，左表单卡片，右 "How it works" 四步说明 + 隐私提示卡片
- `StatusBadge.tsx` 徽章文字简化（决策 #23）
- 验证：`pnpm build` 零类型错误；用 Claude in Chrome 通过 API 直接建了 3 个不同终态的 run
  （COMPLETED/WAITING/REJECTED）截图跟设计稿 `22aa18b6...png`（Runs 列表）、
  `4c4389ec...png`（对应 New Run 的两栏布局参考）对比，侧边栏/主色/卡片/徽章/分页基本还原；
  `pytest agent/tests web/tests` 56 个全绿（本里程碑没碰后端逻辑）

未完成、留给 Milestone 6：Run 详情页的五种状态视觉（运行中的 7 步顶部进度条 + 左侧 Workflow
面板逐节点状态/耗时——这部分数据可以从已有的 `events.jsonl` 在前端派生，不需要新后端接口、
失败态、Gate①策略审批、编译中、Gate②最终审批）、Resume Viewer 页面视觉、公司 Logo 图标资源。

## Milestone 1（后端基础设施）完成记录（2026-09-02）

按 `agent` 计划执行完毕：`web/build.py` 拆出 `web/resume_render.py`；`run_store.py` 加
`company`/`notes` 字段和自动事件日志（`events.jsonl`）；`workflow_service.py` 加分页
`list_runs`、`update_notes`、`get_events`、公司自动回填；新增
`services/resume_labels.py`（从 `main.py` 抽取）、`services/preview_service.py`；`main.py`
新增 5 个端点（列表分页、结构树、事件、笔记、预览）+ 1 个 SSE 端点 + CORS。测试从 38 个增加到
52 个，全绿（`uv run pytest agent/tests web/tests`），手动验证过 `/`、`/api/v1/resume/runs`、
`/preview/master` 均正常返回、Jinja 首页无回归。

未完成、留给后续里程碑：LangSmith 接入、公司 Logo 图标资源、剩余时间预估、React SPA 本身。

## 设计稿评审（2026-09-02）发现的新增任务

UI 设计师产出了 8 张设计稿（存于 `design/` 目录），整体和 PRD 一致，但用到了几处现有后端完全
没有的数据，评审后确认要在 Phase 1 一并补上：

- **Activity Log（活动时间线）**：设计稿 Run 详情页有一个按时间倒序的事件流（"10:37:12 AM
  Completed · Patch Engine (Round 1) · Applied 12 patches..." + 可点击跳转到对应产出），现在
  `run.json` 每次 `update_metadata` 是覆盖而不是追加，没有历史事件流，需要新增一个事件日志
  （建议：每个 run 目录下加一个 `events.jsonl`，按行追加，而不是改造 `run.json` 本身）
- **单节点耗时**（"Completed · 8s"）：现在没有记录每个节点的开始/结束时间，只有笼统的
  `updated_at`；需要在事件日志里记录每个节点的 started_at / completed_at
- **剩余时间预估**（"Est. Remaining ~3-5 min"）：全新指标，没有历史数据基础做不了准确预估，
  Phase 1 用"过去几次 run 里同节点的平均耗时"做粗略估算即可，做不到就先隐藏这个字段而不是编数字
- **Notes 标签页**（人工笔记）：`run.json` 没有对应字段，需要新增 `notes` 字段 + 一个更新接口
- **公司 Logo 图标**：Runs 列表按公司展示品牌图标（Google/Meta/Microsoft…），需要准备一批常见
  公司的 SVG 图标或接入图标服务，不认识的公司要有文字缩写兜底（不要因为找不到图标而报错/留白）
- **列表分页**：设计稿 Runs 列表有分页（"Showing 1 to 5 of 18 runs" + 每页数量选择），现在
  `list_runs()` 一次性返回全部，需要在 Phase 1 就加分页参数，不要等 Phase 2 数据量大了才补

## Phase 1 技术任务清单（核心可用）

### 后端（`agent/src/resume_agent/`）—— Milestone 1 已完成（2026-09-02）
- [x] 新增 SSE 端点 `GET /api/v1/resume/runs/{run_id}/stream`——实现方式是轮询
      `events.jsonl`（每 ~400ms 重读一次新行），不是从后台 Thread 里真正 push；到终态
      status 或客户端断开才关闭连接。详见决策 #18
- [x] 新增预览渲染端点 `GET /preview/{token}?lang=zh|en`（`token` 为 `master` 或
      `run_id`），复用重构出来的 `web/resume_render.py::render_html()`
- [x] `run.json` 新增 `company` 字段：创建时可选传入；`analyze()` 跑完 `analyze_jd` 节点后，若
      `company` 为空则用 `job_profile.target_company` 自动回填
- [x] 新增"简历结构树"端点 `GET /api/v1/resume/runs/{run_id}/structure`，复用已有的
      `catalog.py::editable_catalog()` + 新抽出的 `resume_labels.py::path_label()`
- [x] 新增 `events.jsonl` 事件日志——改造 `run_store.update_metadata()`，每次调用自动追加一条
      事件，不需要在 `workflow_service.py` 各处插桩；`read_events()` 读取，
      `WorkflowService.get_events()` / `GET .../events` 暴露出去
- [x] `run.json` 新增 `notes` 字段 + `POST .../notes` 更新接口
- [x] `GET /api/v1/resume/runs` 新增分页参数（page / page_size），`list_runs()` 内部逻辑同步改造
- [x] 本地开发 CORS（允许 `localhost:5173` / `127.0.0.1:5173`），为后续 SPA 铺路
- [x] 接入 LangSmith（Milestone 8，2026-09-02 完成）：`analyze()`/`compile()` 调用图时加
      `tags=[run_id], run_name=run_id`，靠 tag 在 LangSmith 项目页按 run_id 搜索定位 trace，
      不猜测精确的深链接 URL 编码；`Settings.langsmith_project_url`（可选，用户从自己的
      LangSmith 项目页复制粘贴）驱动 Run 详情页的"View in LangSmith"外链按钮，未配置时按钮
      不渲染
- [ ] 准备公司 Logo 图标资源（常见公司 SVG 集 + 未知公司文字缩写兜底）——**未做**，纯前端资源，
      留到 SPA 脚手架里程碑
- [ ] "剩余时间预估"（Est. Remaining）——**未做**，需要跨 run 历史耗时统计，不是必需项

### 前端 —— Milestone 2 已完成（2026-09-02）：脚手架 + 只读页面
- [x] React SPA 工程：`agent/frontend/`，Vite + React + TypeScript + pnpm，`react-router-dom`
      路由，`@tanstack/react-query` 数据请求（SSE 消息到达时 `invalidateQueries` 触发重新拉取，
      不手动维护增量合并状态）。Vite dev server 把 `/api`、`/preview` 代理到 `127.0.0.1:8010`，
      前端一律用相对路径，避免 CORS/EventSource 跨域细节
- [x] 页面：Runs 列表（分页表格）/ 新建 Run（表单）/ Run 详情（订阅 SSE 实时状态+进度、展示
      岗位画像/匹配报告/HR评审/策略/校验/评分/最终diff、Activity Log 时间线）/ 在线查看
      （版本选择 + 语言切换 + iframe 嵌入 `/preview/{token}`）
- [x] SSE 客户端：浏览器原生 `EventSource`，收到终态 status 后主动 `close()`，避免断线重连
      死循环
- [x] 新增后端只读端点 `GET /api/v1/resume/runs/{run_id}/artifacts`，把过程产出（含此前哪里
      都没暴露过的 job_profile/match_report/hr_review）统一开放给前端
- [x] Run 详情页处于 Human Gate ①/② 等待审批状态时，显示链接跳回旧版 `/runs/{id}/view`
      （8010 端口）完成审批——结构化审批 UI 留到下一个里程碑，两套页面此时共存验证通过
      （手动用 Claude in Chrome 走了一遍：建 run → SSE 实时推进到 FAILED → 错误详情正确展示 →
      旧版页面能看到同一个 run → 在线查看正确渲染 Master Resume）
- [x] Human Gate ① 策略审批交互（`components/StrategyGate.tsx`，2026-09-02 完成）：编辑
      positioning/keywords/actions（保留/丢弃、优先级、说明），"保存修改" 和 "批准并生成简历"
      两个独立按钮——后者直接把当前表单状态当 override 提交给 `approve-strategy`，不要求先保存，
      比旧版 Jinja 页面的两步流程更顺手
- [x] Human Gate ② 基础动作（`components/FinalGate.tsx`，2026-09-02 完成）：批准导出 / 恢复
      原始版本 / 拒绝，三个按钮直接调用已有的 `approve-final`/`restore-original`/`reject-final`
      接口。"高级：人工 Patch" 结构化构建器还没做，暂时保留一个跳旧版页面的链接
- [x] 新增只读端点 `GET /api/v1/resume/runs/{run_id}/facts`，把 `supported_by`（事实 ID 列表）
      换成人话，Gate① 的 action 证据、最终 Diff 卡片的证据都用它——顺带修了 Milestone 2 漏掉的
      "Diff 卡片没显示事实依据"这个小缺口
- [x] 用 Claude in Chrome 走通完整流程验证（因为没有真实 LLM key，写了一个不提交的临时脚本
      复用 `agent/tests/fakes.py::HappyProvider` 起真实 uvicorn 服务）：建 run → Gate①编辑并
      批准 → 全自动编译 → Gate②批准导出 → COMPLETED，全程没跳旧版页面；旧版 Jinja 页面交叉
      验证同一个 run 状态一致，没有回归
- [x] 顺手修了一个真实 CSS bug：`label`/`input`/`textarea` 的基础样式原来只在 `form label`
      作用域下生效，`StrategyGate`/`FinalGate` 这种不用原生 `<form>` 的组件里标签和输入框会
      挤成一行——改成不限定 `form` 前缀的全局选择器
- [x] Human Gate ② 结构化 Patch 构建器（`components/PatchBuilder.tsx`，2026-09-02 完成）：选
      目标字段 → 按字段 kind 动态过滤操作类型 → 按类型出对应输入（replace 要中英文+理由+勾选
      支撑事实；reorder 要上移/下移调整顺序；hide/restore 直接提交）；支持一次攒多条操作再
      提交。**FinalGate 里那个跳旧版页面的链接已删除**——Gate② 全部操作现在都在 SPA 内完成
- [x] `/structure` 端点加 `source=input|candidate` 参数，`source=candidate` 读
      `candidate_resume.yaml`——这是本里程碑动手前就识别出来的正确性问题（AI 的 Rewrite
      Strategy 经常包含 reorder，候选简历的实际顺序很可能已经和原始 Master Resume 不一样），
      用一条新测试验证了两种 source 在已 reorder 场景下返回顺序确实不同
- [x] 手动验证时发现并修了两个真实问题（都不在原计划里，是测试过程中暴露出来的）：
      1) **restore 目标选不到**——最初只从候选结构里选目标字段，但"要 restore 的东西"定义上
      已经不在候选结构里了（比如刚被 hide 掉的条目）。改成同时拉 `input` 和 `candidate` 两次
      结构，`input` 中有但 `candidate` 中没有的路径单独归一组"已隐藏（可恢复）"，且该组的操作
      类型被强制只能是 `restore`；
      2) 浏览器里 React 受控 `<select>`/`<input type=checkbox>` 用非标准方式派发事件时
      （比如只 `dispatchEvent(new Event('change'))` 而不经过原生 value/checked setter）状态
      更新不可靠——这是自动化测试脚本的坑，不是产品代码问题，记在这里防止以后重复踩
- [x] 用 Claude in Chrome 对四种操作类型逐一实测，直接读 `candidate_resume.yaml` 磁盘文件核对
      （不只看 UI 反馈）：hide 移除条目、restore 原位置恢复、reorder 顺序生效、replace 中英文
      都写入且校验通过——全部确认正确
- [x] **已知遗留缺口，Milestone 8（2026-09-02）修复**：`WorkflowService.manual_edit()`
      原来只用当次 patch 算 `final_diff.json`，丢弃 AI Editor 之前的改动。改法：新增
      `all_operations.json` 累积文件（`compile()` 结尾用 `editor_patch.operations` 初始化，
      `manual_edit()` 按 `path` 合并本次操作后重算 diff 并写回，`restore_original()` 清空），
      新增测试 `test_manual_edit_accumulates_diff_with_editor_patch` 验证合并后的 diff 同时
      包含 AI 原始改动和人工改动两条
- [ ] 前端测试框架 —— 未搭建，留作后续补充项
- [x] 已知小问题，Milestone 8（2026-09-02）修复：`approve_final`/`reject_final` 的
      `update_metadata()` 补上 `stage="已批准导出"`/`stage="已拒绝"`

### 现有代码里需要注意的点
- `agent/templates/index.html` / `run.html`：Milestone 8（2026-09-02）已删除，SPA 全面接管
- `agent/src/resume_agent/api/main.py` 里 `/ui/*` 系列路由：Milestone 8（2026-09-02）已删除，
  `GET /` 换成极简 JSON 提示（`{"message": "API only — SPA dev server: ..."}`），只保留
  `/api/v1/*` JSON API + `/preview/*`
- `models/workflow.py::ManualEditRequest` / `ResumePatch` 结构不需要变，只是前端不再手写 JSON，
  而是通过结构化表单生成同样的对象提交

## Phase 2 技术任务清单（Run 管理增强）

- [ ] `run.json` 新增 `is_final` / `archived` 字段 + 对应 API（标记最终版本 / 归档/取消归档）
- [ ] Run 列表接口支持按 `company` 筛选、关键词搜索（文件扫描 + 内存 filter 即可，不引入 DB）
- [ ] 跨 Run 对比：新增 diff 端点，接受两个 `run_id`，对比各自最终产出（`candidate_resume.yaml`）
- [ ] 列表页 UI：按公司分组视图、星标标记展示、归档筛选开关（默认隐藏已归档）

## 待定事项（暂不需要现在决定，实际动手前再定）

- **SPA 与 FastAPI 的部署整合方式**：目前开发期是 Vite dev server（5173）+ 独立跑的 FastAPI
  （8010），靠 Vite 的 `server.proxy` 转发 `/api`、`/preview`。生产/日常使用时要不要 `pnpm
  build` 出静态文件、让 FastAPI 顺手 serve 那个 `dist/` 目录合并成一个进程，还是继续两个进程
  分开跑？两种都不难，等 Human Gate 交互（Milestone 3）做完、SPA 功能对等旧版 Jinja 页面、
  准备切换默认入口时再定
- **B 阶段（远程可访问）**：届时需要重新评估——鉴权方案（token/密码）、是否要上 SQLite 索引层
  （文件系统方案在多设备/并发写入场景下可能不够用）、HTTPS/反向代理
- **B 阶段（远程可访问）**：届时需要重新评估——鉴权方案（token/密码）、是否要上 SQLite 索引层
  （文件系统方案在多设备/并发写入场景下可能不够用）、HTTPS/反向代理
- **移动端适配**：目前默认不需要，如果实际使用中发现有移动端查看简历的需求，再单独评估
- **导航栏的用户头像/设置入口**（设计稿左下角"Yizhou Zhang" + 齿轮图标）：当前决定是纯个人
  工具、无账号系统（决策 #1），这块大概率是设计模板带的通用 UI chrome，不需要真的接一个账号/
  设置后端。实现时按静态展示处理（或者干脆去掉），除非后续发现有具体用途（比如给它挂
  `.env` 配置项的可视化入口）

## 关联文档

- 功能 PRD（面向 UI 设计师）：`FRONTEND_PRD.md`
- UI 设计稿（8 张，2026-09-02 交付）：`design/`
- 原始 Agent 设计 spec：`agent/AI_Resume_Compiler_Spec_V1.1.docx`
- 现有实现说明：`agent/README.md`、`web/README.md`
