# Office Agent 项目规划

## 项目判断

这个项目值得做。

- 对你有用：你本身就有办公文档处理需求，项目不是纯练手题。
- 对学 agent 有用：它会覆盖 `tool calling`、结构化计划、确认闸门、状态流转、结果校验、Web 原型这些核心能力。
- 难度：`中等偏上`。

难点主要在 3 个地方：

1. 文档处理不是纯文本聊天，很多问题来自格式、结构和文件读写。
2. PDF 尤其是扫描版，不稳定性明显高于 Word 和 Excel。
3. 真正的 agent 价值不在“会聊”，而在“能稳定调用工具并可靠执行”。

结论：

- 这是一个很合适的 agent 学习项目。
- 但不适合一开始就做成自由 ReAct 或万能办公助手。
- 最合适的路线是：先做 `受控工作流 agent`，再逐步扩展能力。

## 项目目标

做一个你自己本地使用的办公 agent，先通过 Web 端验证流程，后续再接入微信或飞书机器人。

第一阶段重点：

- 主处理 `Word`
- 辅助处理基础 `Excel`
- `PDF` 先做读取、抽取、分类、导出
- 每次写文件前都必须先确认

## Agent 设计原则

### 1. 不做自由 ReAct

第一版不要做无限循环的 `think -> act -> observe`。

原因：

- 办公场景要求稳定，不适合过度自主。
- 你的项目有强约束：写入前必须确认。
- 可控状态机比自由 agent 更适合第一版。

### 2. 做受控工作流 Agent

推荐流程：

`upload -> analyze -> plan -> await_confirm -> execute -> verify -> done/failed`

说明：

- `analyze`：只读分析文件
- `plan`：生成结构化执行计划
- `await_confirm`：等待你确认
- `execute`：确认后才允许写文件
- `verify`：执行后再检查结果是否正确

## 推荐技术栈

### 前端

- `Next.js`

用途：

- 上传文件
- 展示任务详情
- 展示执行计划
- 提供确认按钮
- 下载输出文件

### 后端

- `FastAPI`

用途：

- 提供 API
- 驱动 agent 流程
- 注册文档工具
- 执行任务编排

### 异步任务

- `RQ + Redis`

用途：

- 跑 OCR
- 跑文档解析
- 跑导出任务
- 避免前端长时间阻塞

### 存储

- `SQLite`
- 本地文件目录

用途：

- 存任务状态
- 存执行计划
- 存确认记录
- 存输入输出文件

### 文档处理库

- Word：`python-docx`
- Excel：`openpyxl`
- PDF 读取：`pypdf`、`pdfplumber`
- PDF 预览：`PDF.js`
- Word 预览：`Mammoth.js`
- OCR：先预留接口，后续接 `PaddleOCR`

## 建议架构

### 1. Web UI 层

负责：

- 文件上传
- 任务展示
- 计划确认
- 结果下载

### 2. Agent Core 层

负责：

- 任务分类
- 工作流状态流转
- 调用模型生成计划
- 控制确认闸门

### 3. Tooling 层

负责：

- 读取 Word
- 写入 Word
- 读取 Excel
- 写入 Excel
- 读取 PDF
- OCR
- 导出结果文件

### 4. Storage 层

负责：

- 保存原文件
- 保存计划
- 保存确认记录
- 保存输出文件

### 5. Channel Adapter 层

第一版先只做 Web。

后续可扩展：

- 微信
- 飞书

注意：

- 机器人入口只做消息适配
- 不要把业务逻辑写死在机器人层

## 推荐目录结构

```text
office-agent/
  apps/
    web/
    api/
  packages/
    agent_core/
    tooling/
    schemas/
  storage/
    files/
    jobs/
  tests/
```

说明：

- `apps/web`：Next.js 前端
- `apps/api`：FastAPI 后端
- `packages/agent_core`：状态机、计划器、执行器、校验器
- `packages/tooling`：Word/Excel/PDF 工具
- `packages/schemas`：Pydantic 数据结构
- `storage`：本地文件和任务数据
- `tests`：工具测试和流程测试

## 核心模块

### 1. Router

判断任务类型，例如：

- 读取文档
- 提取内容
- 填充内容
- 导出结果

### 2. Analyzer

只读分析输入文件，输出：

- 文本内容
- 文档结构
- 字段候选
- 锚点位置
- 文件类型判断

### 3. Planner

基于分析结果生成结构化计划。

建议字段：

- `intent`
- `target_files`
- `proposed_actions`
- `uncertainties`
- `requires_confirmation`
- `expected_output`

### 4. Confirmation Gate

规则：

- 任何写入动作都必须停下来确认
- 计划要以文字形式展示
- 不确定项必须显式列出

### 5. Executor

确认后执行具体工具调用。

要求：

- 尽量走确定性参数
- 不要让模型临场自由发挥写文件

### 6. Verifier

执行后重新读取输出文件，检查：

- 内容是否写入成功
- 格式是否明显损坏
- 输出文件是否可打开

## v0 范围

第一版建议只做这 3 个场景：

1. Word 按锚点写入
2. Excel 填充简单单元格
3. PDF 抽取内容并生成草稿或新文件

先不做：

- 任意 PDF 原位精确编辑
- 复杂表格重建
- PPT 编辑
- 多 agent
- 长期自治
- 模板记忆

## 开发阶段建议

### 阶段 1：先跑通 Word

目标：

- 上传 Word
- 提取结构
- 根据指令生成内容
- 输出执行计划
- 确认后写入
- 再次读取校验

建议优先实现的工具：

- `read_docx`
- `extract_docx_structure`
- `insert_text_by_anchor`
- `fill_template_fields`

### 阶段 2：加入 Excel

目标：

- 读取表格
- 写指定单元格
- 追加简单行

建议工具：

- `read_xlsx`
- `write_xlsx_cells`
- `append_rows`

### 阶段 3：加入 PDF 读取能力

目标：

- 提取文本
- 判断是否需要 OCR
- 识别 PDF 类型
- 生成填写草稿或导出新文件

建议工具：

- `read_pdf_text`
- `classify_pdf_type`
- `ocr_if_needed`
- `export_result_file`

### 阶段 4：再扩入口

目标：

- 保持 agent core 不变
- 新增微信或飞书入口

## 第一周开发顺序

1. 初始化仓库结构
2. 搭好 Next.js 和 FastAPI
3. 定义任务状态机和 Pydantic schema
4. 实现 Word 的读取和按锚点写入
5. 做计划确认页
6. 跑通“上传 -> 分析 -> 计划 -> 确认 -> 执行 -> 校验”

## 成功标准

做到以下几点，第一版就算成功：

- 能稳定处理至少 1 个真实 Word 办公场景
- 执行前一定先输出文字计划
- 确认前不会误写文件
- 执行后能给出结果文件和校验结果
- 前后端流程完整可演示

## 风险点

### PDF 风险

- 扫描版 PDF 强依赖 OCR
- 定位写入不稳定
- 第一版应优先输出新文件，不强改原文件

### 工具风险

- 不同文档格式细节差异大
- 锚点识别和字段识别容易出错

### Agent 风险

- 如果把模型放得太自由，容易误调用工具
- 所以必须坚持“计划先行 + 人工确认 + 确定性执行”

## 最终建议

这个项目对你是合适的，原因很明确：

1. 它不是空想型项目，你自己真会用到。
2. 它能让你学到真正有用的 agent 开发能力，而不是只会做聊天机器人。
3. 它的难度足够锻炼你，但又不至于大到完全无法落地。

一句话结论：

`值得做，难度中等偏上，学习价值很高，而且很适合作为你的第一个偏实战的 agent 项目。`
