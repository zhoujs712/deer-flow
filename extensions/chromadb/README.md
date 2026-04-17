# ChromaDB Memory Storage for DeerFlow

这是 DeerFlow 的 ChromaDB 内存存储集成，完全独立于核心代码。

## 功能特性

- 支持本地持久化 ChromaDB
- 支持远程 ChromaDB 服务器
- 完全兼容 DeerFlow 的 MemoryStorage 接口
- 内置语义搜索功能
- 零核心代码修改

## 安装方式

### 方式 1：在项目中直接添加依赖

```bash
cd /workspace/backend
uv add chromadb>=0.5.0
```

### 方式 2：从本地目录安装（开发模式）

```bash
cd /workspace/extensions/chromadb
uv pip install -e .
```

### 方式 3：使用 uv pip 直接安装

```bash
cd /workspace/backend
uv pip install chromadb>=0.5.0
```

## 配置使用

### 1. 在 config.yaml 中配置

修改项目根目录的 `config.yaml`：

```yaml
memory:
  enabled: true
  storage_class: chromadb.storage:ChromaMemoryStorage
  # 其他原有配置保持不变
  debounce_seconds: 30
  model_name: null
  max_facts: 100
  fact_confidence_threshold: 0.7
  injection_enabled: true
  max_injection_tokens: 2000
```

### 2. 配置环境变量

#### 本地持久化模式（默认）

```bash
# 可选：指定持久化目录（默认：.chromadb）
export CHROMADB_PERSIST_DIR="./my_chromadb_data"
```

#### 远程服务器模式

```bash
export CHROMADB_HOST="localhost"
export CHROMADB_PORT="8000"
```

### 3. 启动 ChromaDB 服务器（可选）

如果使用远程模式，需要先启动 ChromaDB 服务器：

```bash
# 使用 Docker
docker run -p 8000:8000 chromadb/chroma:latest

# 或者使用 Python
pip install chromadb
chroma run --host localhost --port 8000 --path ./chroma_data
```

## 使用示例

### 基本使用

配置好后，DeerFlow 会自动使用 ChromaDB 存储记忆数据，无需额外代码。

### 语义搜索（高级功能）

`ChromaMemoryStorage` 提供了额外的语义搜索功能：

```python
from chromadb import ChromaMemoryStorage

storage = ChromaMemoryStorage()

# 搜索相关的事实
facts = storage.search_facts(
    query="我昨天提到的项目是什么？",
    agent_name="my_agent",
    top_k=5
)

print(f"找到 {len(facts)} 条相关事实")
```

### 业务数据管理

存储和管理业务术语，让 agent 理解业务领域知识：

```python
from chromadb import ChromaMemoryStorage, BusinessDataManager

# 初始化存储
storage = ChromaMemoryStorage()

# 获取 ChromaDB 客户端
client = storage._client

# 初始化业务数据管理器
business_manager = BusinessDataManager(client)

# 存储业务术语
business_terms = [
    {
        "term": "用户留存率",
        "definition": "用户在特定时间段内继续使用产品或服务的比例",
        "examples": ["我们的月留存率达到了 60%", "用户留存率是衡量产品粘性的重要指标"],
        "category": "metrics"
    },
    {
        "term": "转化率",
        "definition": "访问者完成目标操作的比例",
        "examples": ["我们的注册转化率为 25%", "优化着陆页可以提高转化率"],
        "category": "metrics"
    }
]

business_manager.store_business_terms(business_terms, namespace="marketing")

# 存储业务文档
business_documents = [
    {
        "title": "2024 年营销战略",
        "content": "我们的 2024 年营销战略将聚焦于提高用户留存率和转化率。",
        "tags": ["marketing", "strategy"],
        "source": "营销部门"
    }
]

business_manager.store_business_documents(business_documents, namespace="marketing")

# 搜索业务术语
terms = business_manager.search_business_terms(
    query="如何提高用户留存率？",
    namespace="marketing"
)
print("相关业务术语:", terms)
```

### 意图识别（业务术语感知）

使用业务术语进行智能意图识别：

```python
from chromadb import ChromaMemoryStorage, IntentRecognitionTool

# 初始化
storage = ChromaMemoryStorage()
intent_tool = IntentRecognitionTool(storage)

# 存储业务数据（如果尚未存储）
# 见上面的业务数据管理示例

# 识别意图
result = intent_tool.recognize_intent(
    "如何提高用户留存率？",
    namespace="marketing"
)

print("识别结果:")
print(f"意图: {result['intent']}")
print(f"置信度: {result['confidence']}")
print(f"业务术语: {result['key_business_terms']}")

# 增强提示（用于 agent 上下文）
enhanced_prompt = intent_tool.enhance_prompt(
    "如何提高用户留存率？",
    namespace="marketing"
)
print("\n增强提示:")
print(enhanced_prompt)
```

### 完整示例

运行完整的使用示例：

**方式 1：使用 backend 目录中的示例脚本（推荐）**

```bash
cd /workspace/backend
uv run python chromadb_example.py
```

**方式 2：从 extensions 目录运行**

```bash
cd /workspace/extensions/chromadb
# 添加当前目录到 Python 路径并运行
PYTHONPATH=$(pwd) uv run python -m deerflow_chromadb.example_usage
```

**注意：** ChromaDB 会在首次运行时下载 ONNX 模型（约 80MB），这可能需要一些时间，取决于网络连接速度。

## 目录结构

```
extensions/chromadb/
├── deerflow_chromadb/      # 包目录
│   ├── __init__.py         # 模块入口
│   ├── storage.py          # ChromaMemoryStorage 实现
│   ├── business_data.py    # 业务数据管理
│   ├── intent_recognition.py # 意图识别
│   └── example_usage.py    # 使用示例
├── backend/                # 示例脚本（在 backend 目录中）
│   └── chromadb_example.py # 简化的示例脚本
├── setup.py                # 安装配置
└── README.md               # 本文档
```

## 工作原理

1. **Collection 命名**：
   - 全局记忆：`memory_global`
   - Agent 专属记忆：`memory_{agent_name}`

2. **文档结构**：
   - ID: `memory_main`
   - Document: JSON 序列化的完整记忆数据
   - Metadata: `{"agent": "...", "type": "memory"}`

3. **Embedding**：使用 ChromaDB 默认的 Sentence-BERT 模型

## 迁移现有数据

从 FileMemoryStorage 迁移到 ChromaDB：

```python
from deerflow.agents.memory.storage import FileMemoryStorage
from deerflow_chromadb import ChromaMemoryStorage

# 加载原有数据
old_storage = FileMemoryStorage()
memory_data = old_storage.load()

# 保存到 ChromaDB
new_storage = ChromaMemoryStorage()
new_storage.save(memory_data)
```

## 故障排查

### ImportError: No module named 'chromadb'

解决：安装 ChromaDB
```bash
cd /workspace/backend
uv add chromadb>=0.5.0
```

或者使用 uv pip：
```bash
cd /workspace/backend
uv pip install chromadb>=0.5.0
```

### 连接远程 ChromaDB 失败

检查：
1. ChromaDB 服务器是否启动
2. 主机和端口配置是否正确
3. 防火墙设置

### 数据未持久化

确认：
- 使用本地模式时，`CHROMADB_PERSIST_DIR` 目录有写权限
- 目录路径正确

## 注意事项

1. **独立于核心代码**：本扩展完全独立，无需修改任何核心文件
2. **向后兼容**：可以随时切换回 FileMemoryStorage
3. **性能考虑**：对于大量数据，建议使用远程 ChromaDB 服务器
4. **备份**：定期备份 ChromaDB 数据目录

## 许可证

与 DeerFlow 项目使用相同的许可证。
