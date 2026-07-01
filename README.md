# DocFlow Agent

一个面向 `Word / Excel / PowerPoint / PDF` 的办公助手 Agent。

它的定位不是通用聊天机器人，而是专门负责处理 Office 办公文档和 PDF 相关任务的 Agent。

项目当前选择将 `OfficeCLI` 作为核心文档执行引擎接入，用来支撑 Word、Excel、PowerPoint 的创建、修改、校验、预览和模板处理能力；PDF 和图片则作为辅助输入与处理能力存在。

当前版本重点解决两件事：

- 让 Agent 真的能调用 `officecli` 处理 Office 文档，而不是只会输出文本
- 让文档操作过程可见、可追踪，避免完全黑盒执行

## 当前能力

### 1. 对话式文档处理

- 通过聊天界面驱动文档创建、编辑和查看
- 支持会话上下文，能在同一轮任务里连续操作文件
- 支持文件上传，文档内容会先做提取，再交给模型理解

### 2. OfficeCLI 深度集成

当前项目已经把 `officecli` 作为底层执行引擎接入，支持：

- `docx / xlsx / pptx` 的创建、查看、查询、修改、删除
- `batch` 批量命令
- `merge` 模板合并
- `validate` 结构校验
- `watch / goto / mark / unmark / marks` 预览与定位
- `dump / add-part / refresh`
- `office_command` 透传原生命令，作为兜底入口

也就是说，现在不是“只接了几个简单命令”，而是已经把官方 `officecli` 的主要命令面接进来了。

### 3. 文档任务流

项目里保留了一条受控任务流，适合处理“上传文档 -> 分析 -> 生成计划 -> 人工确认 -> 执行 -> 校验”这类流程：

`upload -> analyze -> plan -> await_confirm -> execute -> verify -> done`

这条链路适合后续继续演进成更强的结构化文档工作流。

### 4. 其他辅助能力

- 联网搜索：适合查实时信息后再写入文档
- 图片分析：识别图片内容、提取图片中的信息
- 图片生成：通过视觉模型生成图片素材
- 会话内文档列表：能看到当前会话创建过的草稿和输出文件

## 项目定位

这是一个专注办公文档处理的 Agent，重点覆盖：

- Word 文档撰写、改写、润色、结构化修改
- Excel 表格读取、填写、整理、汇总
- PowerPoint 演示文稿生成、改写、排版调整
- PDF 内容提取、理解与二次加工
- 办公场景下的模板填充、批量处理、预览校验

当前还处于开发迭代阶段，暂时没有部署到服务器，但这不代表它的目标是“只在本地单机使用”。后续可以继续往服务化、多人使用、长流程办公助手方向演进。

## 技术栈

- 后端：`FastAPI`
- 前端：`Next.js + React + Tailwind CSS`
- 模型调用：兼容 OpenAI 接口
- Office 处理：`OfficeCLI`
- 文件解析：`python-docx / openpyxl / pypdf / pdfplumber / python-pptx`

## 项目结构

```text
docflow-agent/
├── apps/
│   ├── api/                    # FastAPI 后端
│   └── web/                    # Next.js 前端
├── packages/
│   ├── agent_core/             # 对话 Agent、任务流、工具注册
│   ├── tooling/officecli/      # OfficeCLI Python 封装
│   ├── tooling/word/           # 其他文档处理辅助逻辑
│   ├── tooling/excel/
│   └── schemas/                # Pydantic 数据模型
├── storage/                    # 上传文件、输出文件、会话和文档索引
├── tests/                      # 测试
├── ARCHITECTURE.md             # 架构说明
└── config.py                   # 全局配置
```

## 快速开始

### 环境要求

- Python `3.11+`
- Node.js `18+`
- 本机已安装 `officecli`

安装 `officecli` 可参考官方仓库：

- GitHub: [iOfficeAI/OfficeCLI](https://github.com/iOfficeAI/OfficeCLI)

### 1. 安装 Python 依赖

```bash
pip install -e ".[dev]"
```

### 2. 安装前端依赖

```bash
cd apps/web
npm install
cd ../..
```

### 3. 配置环境变量

在项目根目录创建 `.env`，至少补这几个：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

如果你还要启用联网搜索、图片生成、图片理解，可以继续补：

```env
TAVILY_API_KEY=
AGNES_API_KEY=
AGNES_BASE_URL=https://api.agnes-ai.com/v1
AGNES_IMAGE_MODEL=agnes-image-2.1-flash
AGNES_VISION_MODEL=agnes-vision-1.0
```

### 4. 启动后端

```bash
make run-api
```

默认地址：

- API: `http://localhost:8000`

### 5. 启动前端

```bash
cd apps/web
npm run dev
```

默认地址：

- Web: `http://localhost:3000`

## 使用方式

### 聊天创建 Office 文档

你可以直接输入：

- “帮我做一个关于人工智能发展的 PPT”
- “把这份 Word 改成更正式一点”
- “读取这个 Excel，帮我做个总结”

### 上传文件后处理

支持上传：

- 图片：`png / jpg / jpeg / gif / webp / bmp`
- 文档：`docx / doc / xlsx / xls / pptx / ppt / pdf`
- 文本：`txt / md / csv / json / xml / html`

上传后，Agent 会根据文件类型自动走不同处理路径。

### 直接调用完整 OfficeCLI 能力

如果普通工具不够，Agent 也可以通过 `office_command` 直接透传 `officecli` 原生命令。

这意味着后续你不需要每次都先改 Python 封装，很多官方新能力可以先直接打通。

## 开发命令

```bash
make install    # 安装基础依赖
make dev        # 安装开发依赖
make run-api    # 启动后端
make test       # 运行测试
make lint       # Ruff 检查和格式化
make clean      # 清理缓存
```

前端常用命令：

```bash
cd apps/web
npm run dev
npm run build
```

## 路线图

接下来更值得继续做的方向：

- 补齐更稳定的 Word / PPT 生成策略
- 引入模板体系，而不是每次从空白页开始
- 优化前端，把原始工具调试信息和用户视图分层
- 把任务流状态做成可恢复的持久化实现
- 继续缩小“官方 OfficeCLI 演示效果”和“当前项目实际效果”之间的差距
- 为后续服务化部署和多人使用打基础

## 致谢

- [OfficeCLI](https://github.com/iOfficeAI/OfficeCLI)
- FastAPI
- Next.js

## License

MIT
