# DeerFlow 代码 Wiki

## 1. 项目概述

DeerFlow (**D**eep **E**xploration and **E**fficient **R**esearch **Flow**) 是一个开源的**超级代理框架**，它协调**子代理**、**内存**和**沙箱**来执行几乎任何任务，由**可扩展的技能**驱动。

### 核心功能

- **技能与工具系统**：支持研究、报告生成、幻灯片创建、网页、图像和视频生成等多种技能
- **子代理**：能够生成子代理来处理复杂任务，并行执行并汇总结果
- **沙箱与文件系统**：每个任务都有自己的执行环境和完整的文件系统视图
- **上下文工程**：管理上下文，总结完成的子任务，减少上下文窗口占用
- **长期记忆**：在会话之间构建持久记忆，存储用户配置文件、偏好和累积知识

## 2. 系统架构

### 整体架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Client (Browser)                             │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Nginx (Port 2026)                               │
│                    Unified Reverse Proxy Entry Point                      │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  /api/langgraph/*  →  LangGraph Server (2024)                      │  │
│  │  /api/*            →  Gateway API (8001)                           │  │
│  │  /*                →  Frontend (3000)                               │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   LangGraph Server  │ │    Gateway API      │ │     Frontend        │
│     (Port 2024)     │ │    (Port 8001)      │ │    (Port 3000)      │
│                     │ │                     │ │                     │
│  - Agent Runtime    │ │  - Models API       │ │  - Next.js App      │
│  - Thread Mgmt      │ │  - MCP Config       │ │  - React UI         │
│  - SSE Streaming    │ │  - Skills Mgmt      │ │  - Chat Interface   │
│  - Checkpointing    │ │  - File Uploads     │ │                     │
│                     │ │  - Thread Cleanup   │ │                     │
│                     │ │  - Artifacts        │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          │                       │
          │     ┌─────────────────┘
          │     │
          ▼     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Shared Configuration                              │
│  ┌─────────────────────────┐  ┌────────────────────────────────────────┐ │
│  │      config.yaml        │  │      extensions_config.json            │ │
│  │  - Models               │  │  - MCP Servers                         │ │
│  │  - Tools                │  │  - Skills State                        │ │
│  │  - Sandbox              │  │                                        │ │
│  │  - Summarization        │  │                                        │ │
│  └─────────────────────────┘  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 启动模式

DeerFlow 支持多种启动模式：

| | **Local Foreground** | **Local Daemon** | **Docker Dev** | **Docker Prod** |
|---|---|---|---|---|
| **Dev** | `./scripts/serve.sh --dev`<br/>`make dev` | `./scripts/serve.sh --dev --daemon`<br/>`make dev-daemon` | `./scripts/docker.sh start`<br/>`make docker-start` | — |
| **Dev + Gateway** | `./scripts/serve.sh --dev --gateway`<br/>`make dev-pro` | `./scripts/serve.sh --dev --gateway --daemon`<br/>`make dev-daemon-pro` | `./scripts/docker.sh start --gateway`<br/>`make docker-start-pro` | — |
| **Prod** | `./scripts/serve.sh --prod`<br/>`make start` | `./scripts/serve.sh --prod --daemon`<br/>`make start-daemon` | — | `./scripts/deploy.sh`<br/>`make up` |
| **Prod + Gateway** | `./scripts/serve.sh --prod --gateway`<br/>`make start-pro` | `./scripts/serve.sh --prod --gateway --daemon`<br/>`make start-daemon-pro` | — | `./scripts/deploy.sh --gateway`<br/>`make up-pro` |

## 3. 核心模块

### 3.1 LangGraph 服务器

**入口点**：`packages/harness/deerflow/agents/lead_agent/agent.py:make_lead_agent`

**核心职责**：
- 代理创建和配置
- 线程状态管理
- 中间件链执行
- 工具执行编排
- SSE 流式传输实时响应

### 3.2 Gateway API

**入口点**：`app/gateway/app.py`

**路由器**：
- `models.py` - `/api/models` - 模型列表和详情
- `mcp.py` - `/api/mcp` - MCP 服务器配置
- `skills.py` - `/api/skills` - 技能管理
- `uploads.py` - `/api/threads/{id}/uploads` - 文件上传
- `threads.py` - `/api/threads/{id}` - LangGraph 删除后清理本地 DeerFlow 线程数据
- `artifacts.py` - `/api/threads/{id}/artifacts` - 工件服务
- `suggestions.py` - `/api/threads/{id}/suggestions` - 后续建议生成

### 3.3 代理架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           make_lead_agent(config)                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Middleware Chain                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 1. ThreadDataMiddleware  - Initialize workspace/uploads/outputs  │   │
│  │ 2. UploadsMiddleware     - Process uploaded files               │   │
│  │ 3. SandboxMiddleware     - Acquire sandbox environment          │   │
│  │ 4. SummarizationMiddleware - Context reduction (if enabled)     │   │
│  │ 5. TitleMiddleware       - Auto-generate titles                 │   │
│  │ 6. TodoListMiddleware    - Task tracking (if plan_mode)         │   │
│  │ 7. ViewImageMiddleware   - Vision model support                 │   │
│  │ 8. ClarificationMiddleware - Handle clarifications              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Agent Core                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │      Model       │  │      Tools       │  │    System Prompt     │   │
│  │  (from factory)  │  │  (configured +   │  │  (with skills)       │   │
│  │                  │  │   MCP + builtin) │  │                      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.4 沙箱系统

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Sandbox Architecture                           │
└─────────────────────────────────────────────────────────────────────────┘

                      ┌─────────────────────────┐
                      │    SandboxProvider      │ (Abstract)
                      │  - acquire()            │
                      │  - get()                │
                      │  - release()            │
                      └────────────┬────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                                         │
              ▼                                         ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│  LocalSandboxProvider   │              │  AioSandboxProvider     │
│  (packages/harness/deerflow/sandbox/local.py) │              │  (packages/harness/deerflow/community/)       │
│                         │              │                         │
│  - Singleton instance   │              │  - Docker-based         │
│  - Direct execution     │              │  - Isolated containers  │
│  - Development use      │              │  - Production use       │
└─────────────────────────┘              └─────────────────────────┘

                      ┌─────────────────────────┐
                      │        Sandbox          │ (Abstract)
                      │  - execute_command()    │
                      │  - read_file()          │
                      │  - write_file()         │
                      │  - list_dir()           │
                      └─────────────────────────┘
```

**虚拟路径映射**：

| 虚拟路径 | 物理路径 |
|---------|---------------|
| `/mnt/user-data/workspace` | `backend/.deer-flow/threads/{thread_id}/user-data/workspace` |
| `/mnt/user-data/uploads` | `backend/.deer-flow/threads/{thread_id}/user-data/uploads` |
| `/mnt/user-data/outputs` | `backend/.deer-flow/threads/{thread_id}/user-data/outputs` |
| `/mnt/skills` | `deer-flow/skills/` |

### 3.5 工具系统

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Tool Sources                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Built-in Tools    │  │  Configured Tools   │  │     MCP Tools       │
│  (packages/harness/deerflow/tools/)       │  │  (config.yaml)      │  │  (extensions.json)  │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ - present_file      │  │ - web_search        │  │ - github            │
│ - ask_clarification │  │ - web_fetch         │  │ - filesystem        │
│ - view_image        │  │ - bash              │  │ - postgres          │
│                     │  │ - read_file         │  │ - brave-search      │
│                     │  │ - write_file        │  │ - puppeteer         │
│                     │  │ - str_replace       │  │ - ...               │
│                     │  │ - ls                │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
           │                       │                       │
           └───────────────────────┴───────────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │   get_available_tools() │
                      │   (packages/harness/deerflow/tools/__init__)  │
                      └─────────────────────────┘
```

### 3.6 模型工厂

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Model Factory                                   │
│                     (packages/harness/deerflow/models/factory.py)                              │
└─────────────────────────────────────────────────────────────────────────┘

config.yaml:
┌─────────────────────────────────────────────────────────────────────────┐
│ models:                                                                  │
│   - name: gpt-4                                                         │
│     display_name: GPT-4                                                 │
│     use: langchain_openai:ChatOpenAI                                    │
│     model: gpt-4                                                        │
│     api_key: $OPENAI_API_KEY                                            │
│     max_tokens: 4096                                                    │
│     supports_thinking: false                                            │
│     supports_vision: true                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │   create_chat_model()   │
                      │  - name: str            │
                      │  - thinking_enabled     │
                      └────────────┬────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │   resolve_class()       │
                      │  (reflection system)    │
                      └────────────┬────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │   BaseChatModel         │
                      │  (LangChain instance)   │
                      └─────────────────────────┘
```

**支持的提供商**：
- OpenAI (`langchain_openai:ChatOpenAI`)
- Anthropic (`langchain_anthropic:ChatAnthropic`)
- DeepSeek (`langchain_deepseek:ChatDeepSeek`)
- 通过 LangChain 集成的自定义提供商

### 3.7 MCP 集成

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MCP Integration                                 │
│                        (packages/harness/deerflow/mcp/manager.py)                              │
└─────────────────────────────────────────────────────────────────────────┘

extensions_config.json:
┌─────────────────────────────────────────────────────────────────────────┐
│ {                                                                        │
│   "mcpServers": {                                                       │
│     "github": {                                                         │
│       "enabled": true,                                                  │
│       "type": "stdio",                                                  │
│       "command": "npx",                                                 │
│       "args": ["-y", "@modelcontextprotocol/server-github"],           │
│       "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"}                          │
│     }                                                                   │
│   }                                                                     │
│ }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │  MultiServerMCPClient   │
                      │  (langchain-mcp-adapters)│
                      └────────────┬────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
       ┌───────────┐        ┌───────────┐        ┌───────────┐
       │  stdio    │        │   SSE     │        │   HTTP    │
       │ transport │        │ transport │        │ transport │
       └───────────┘        └───────────┘        └───────────┘
```

### 3.8 技能系统

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Skills System                                   │
│                       (packages/harness/deerflow/skills/loader.py)                             │
└─────────────────────────────────────────────────────────────────────────┘

Directory Structure:
┌─────────────────────────────────────────────────────────────────────────┐
│ skills/                                                                  │
│ ├── public/                        # Public skills (committed)           │
│ │   ├── pdf-processing/                                                 │
│ │   │   └── SKILL.md                                                    │
│ │   ├── frontend-design/                                                │
│ │   │   └── SKILL.md                                                    │
│ │   └── ...                                                             │
│ └── custom/                        # Custom skills (gitignored)          │
│     └── user-installed/                                                 │
│         └── SKILL.md                                                    │
└─────────────────────────────────────────────────────────────────────────┘

SKILL.md Format:
┌─────────────────────────────────────────────────────────────────────────┐
│ ---                                                                      │
│ name: PDF Processing                                                     │
│ description: Handle PDF documents efficiently                            │
│ license: MIT                                                            │
│ allowed-tools:                                                          │
│   - read_file                                                           │
│   - write_file                                                          │
│   - bash                                                                │
│ ---                                                                      │
│                                                                          │
│ # Skill Instructions                                                     │
│ Content injected into system prompt...                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4. 关键类与函数

### 4.1 代理核心

#### `make_lead_agent(config)`
- **位置**：`packages/harness/deerflow/agents/lead_agent/agent.py`
- **功能**：创建主代理实例，配置中间件链和工具
- **参数**：
  - `config`：代理配置对象
- **返回值**：配置好的代理实例

#### `ThreadState`
- **位置**：`packages/harness/deerflow/agents/thread_state.py`
- **功能**：扩展 LangGraph 的 `AgentState`，添加 DeerFlow 特定字段
- **主要字段**：
  - `messages`：消息列表
  - `sandbox`：沙箱环境信息
  - `artifacts`：生成的文件路径
  - `thread_data`：工作区、上传、输出路径
  - `title`：自动生成的对话标题
  - `todos`：任务跟踪（计划模式）
  - `viewed_images`：视觉模型图像数据

### 4.2 沙箱系统

#### `SandboxProvider` (抽象类)
- **位置**：`packages/harness/deerflow/sandbox/sandbox_provider.py`
- **功能**：定义沙箱提供者的接口
- **主要方法**：
  - `acquire()`：获取沙箱实例
  - `get()`：获取现有沙箱实例
  - `release()`：释放沙箱实例

#### `LocalSandboxProvider`
- **位置**：`packages/harness/deerflow/sandbox/local.py`
- **功能**：本地沙箱提供者，直接在主机上执行命令
- **特点**：单例实例，开发使用

#### `AioSandboxProvider`
- **位置**：`packages/harness/deerflow/community/aio_sandbox.py`
- **功能**：基于 Docker 的沙箱提供者，在隔离容器中执行命令
- **特点**：生产使用推荐

### 4.3 工具系统

#### `get_available_tools()`
- **位置**：`packages/harness/deerflow/tools/__init__.py`
- **功能**：获取所有可用工具
- **返回值**：工具列表

### 4.4 模型工厂

#### `create_chat_model(name, thinking_enabled)`
- **位置**：`packages/harness/deerflow/models/factory.py`
- **功能**：创建聊天模型实例
- **参数**：
  - `name`：模型名称
  - `thinking_enabled`：是否启用思考模式
- **返回值**：聊天模型实例

### 4.5 内存系统

#### `MemoryManager`
- **位置**：`packages/harness/deerflow/agents/memory/storage.py`
- **功能**：管理长期记忆，存储用户上下文和对话历史
- **主要方法**：
  - `add_fact()`：添加事实
  - `get_facts()`：获取事实
  - `update_memory()`：更新记忆

### 4.6 客户端

#### `DeerFlowClient`
- **位置**：`packages/harness/deerflow/client.py`
- **功能**：提供直接的进程内访问所有代理和 Gateway 功能
- **主要方法**：
  - `chat()`：聊天
  - `stream()`：流式聊天
  - `list_models()`：列出模型
  - `list_skills()`：列出技能
  - `update_skill()`：更新技能
  - `upload_files()`：上传文件

## 5. 依赖关系

### 5.1 核心依赖

- **LangChain**：LLM 交互和链
- **LangGraph**：多代理工作流编排
- **FastAPI**：Gateway API
- **Next.js**：前端
- **Docker**：沙箱隔离

### 5.2 模型依赖

- **OpenAI**：GPT 系列模型
- **Anthropic**：Claude 系列模型
- **DeepSeek**：DeepSeek 模型
- **Google**：Gemini 模型
- **Ollama**：本地模型运行
- **vLLM**：模型推理优化

### 5.3 工具依赖

- **Tavily**：网络搜索
- **Exa**：网络搜索和抓取
- **Jina AI**：网页读取
- **Firecrawl**：网页抓取
- **InfoQuest**：智能搜索和抓取

## 6. 项目运行方式

### 6.1 配置

1. **克隆 DeerFlow 仓库**
   ```bash
   git clone https://github.com/bytedance/deer-flow.git
   cd deer-flow
   ```

2. **运行设置向导**
   ```bash
   make setup
   ```
   这将启动一个交互式向导，指导您选择 LLM 提供商、可选的网络搜索以及执行/安全偏好，如沙箱模式、bash 访问和文件写入工具。

### 6.2 运行应用程序

#### Docker（推荐）

**开发**（热重载，源挂载）：
```bash
make docker-init    # 拉取沙箱镜像（仅一次或镜像更新时）
make docker-start   # 启动服务（从 config.yaml 自动检测沙箱模式）
```

**生产**（本地构建镜像，挂载运行时配置和数据）：
```bash
make up     # 构建镜像并启动所有生产服务
make down   # 停止并移除容器
```

访问：http://localhost:2026

#### 本地开发

1. **检查先决条件**：
   ```bash
   make check  # 验证 Node.js 22+、pnpm、uv、nginx
   ```

2. **安装依赖**：
   ```bash
   make install  # 安装后端 + 前端依赖
   ```

3. **（可选）预拉取沙箱镜像**：
   ```bash
   # 如果使用 Docker/容器基础的沙箱，推荐执行
   make setup-sandbox
   ```

4. **（可选）加载示例内存数据供本地查看**：
   ```bash
   python scripts/load_memory_sample.py
   ```

5. **启动服务**：
   ```bash
   make dev
   ```

6. **访问**：http://localhost:2026

## 7. 安全考虑

### 7.1 沙箱隔离

- 代理代码在沙箱边界内执行
- 本地沙箱：直接执行（仅开发）
- Docker 沙箱：容器隔离（推荐生产）
- 文件操作中的路径遍历预防

### 7.2 API 安全

- 线程隔离：每个线程有单独的数据目录
- 文件验证：上传检查路径安全性
- 环境变量解析：配置中不存储密钥

### 7.3 MCP 安全

- 每个 MCP 服务器在自己的进程中运行
- 环境变量在运行时解析
- 服务器可以独立启用/禁用

## 8. 性能考虑

### 8.1 缓存

- MCP 工具使用文件 mtime 失效缓存
- 配置加载一次，文件更改时重新加载
- 技能在启动时解析一次，缓存在内存中

### 8.2 流式传输

- 使用 SSE 进行实时响应流式传输
- 减少首令牌时间
- 为长时间操作启用进度可见性

### 8.3 上下文管理

- 总结中间件在接近限制时减少上下文
- 可配置触发器：令牌、消息或分数
- 保留最近的消息，同时总结较旧的消息

## 9. 高级功能

### 9.1 沙箱模式

DeerFlow 支持多种沙箱执行模式：
- **本地执行**（在主机机器上直接运行沙箱代码）
- **Docker 执行**（在隔离的 Docker 容器中运行沙箱代码）
- **Kubernetes 执行**（通过 provisioner 服务在 Kubernetes Pod 中运行沙箱代码）

### 9.2 MCP 服务器

DeerFlow 支持可配置的 MCP 服务器和技能来扩展其功能。对于 HTTP/SSE MCP 服务器，支持 OAuth 令牌流（`client_credentials`、`refresh_token`）。

### 9.3 IM 渠道

DeerFlow 支持从消息应用程序接收任务。配置后，渠道会自动启动 — 不需要任何公共 IP。

支持的渠道：
- Telegram
- Slack
- Feishu / Lark
- WeChat
- WeCom

### 9.4 跟踪

DeerFlow 内置了 [LangSmith](https://smith.langchain.com) 和 [Langfuse](https://langfuse.com) 集成用于可观察性。启用后，所有 LLM 调用、代理运行和工具执行都会被跟踪并在 LangSmith 或 Langfuse 仪表板中可见。

## 10. 推荐模型

DeerFlow 与模型无关 — 它可以与任何实现 OpenAI 兼容 API 的 LLM 一起工作。不过，它在支持以下功能的模型上表现最佳：

- **长上下文窗口**（100k+ 令牌）用于深度研究和多步骤任务
- **推理能力**用于自适应规划和复杂分解
- **多模态输入**用于图像理解和视频理解
- **强大的工具使用**用于可靠的函数调用和结构化输出

## 11. 嵌入式 Python 客户端

DeerFlow 可以作为嵌入式 Python 库使用，而无需运行完整的 HTTP 服务。`DeerFlowClient` 提供直接的进程内访问所有代理和 Gateway 功能，返回与 HTTP Gateway API 相同的响应架构。

```python
from deerflow.client import DeerFlowClient

client = DeerFlowClient()

# 聊天
response = client.chat("Analyze this paper for me", thread_id="my-thread")

# 流式传输（LangGraph SSE 协议：values, messages-tuple, end）
for event in client.stream("hello"):
    if event.type == "messages-tuple" and event.data.get("type") == "ai":
        print(event.data["content"])

# 配置和管理 — 返回与 Gateway 对齐的字典
models = client.list_models()        # {"models": [...]}
skills = client.list_skills()        # {"skills": [...]}
client.update_skill("web-search", enabled=True)
client.upload_files("thread-1", ["./report.pdf"])  # {"success": True, "files": [...]}
```

## 12. 目录结构

```
├── .agent/            # 代理相关文件
├── .github/           # GitHub 配置
├── backend/           # 后端代码
│   ├── app/           # 应用代码
│   │   ├── channels/  # IM 渠道
│   │   └── gateway/   # Gateway API
│   ├── docs/          # 文档
│   ├── packages/      # 包
│   │   └── harness/   # 核心框架
│   └── tests/         # 测试
├── docker/            # Docker 配置
├── docs/              # 文档
├── frontend/          # 前端代码
│   ├── public/        # 静态文件
│   ├── src/           # 源代码
│   └── tests/         # 测试
├── scripts/           # 脚本
├── skills/            # 技能
│   ├── public/        # 公共技能
│   └── custom/        # 自定义技能
└── config.example.yaml # 配置示例
```

## 13. 总结

DeerFlow 是一个强大的超级代理框架，通过协调子代理、内存和沙箱来执行各种复杂任务。它的核心优势在于：

1. **可扩展性**：通过技能和工具系统，可以轻松扩展功能
2. **强大的执行环境**：沙箱系统提供安全的执行环境
3. **智能上下文管理**：通过中间件和总结系统，有效管理上下文窗口
4. **长期记忆**：在会话之间保持用户偏好和知识
5. **多渠道支持**：可以通过多种消息应用程序访问

DeerFlow 2.0 是一个从头开始重写的版本，不再与 v1 共享代码，提供了更强大、更灵活的架构。它不仅是一个研究工具，更是一个完整的代理框架，为代理提供完成工作所需的基础设施。