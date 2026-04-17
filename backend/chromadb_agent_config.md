# 将 ChromaDB 集成注册到 DeerFlow Agent 中

## 配置步骤

### 1. 安装依赖

```bash
# 安装 ChromaDB
cd /workspace/backend
uv add chromadb>=0.5.0

# 安装 SQL Server 驱动（如果需要从 SQL Server 同步字典数据）
uv add pyodbc
```

### 2. 确保模块可导入

确保 `deerflow_chromadb` 模块可以被 Python 导入。有两种方式：

#### 方式 A：从本地目录安装（开发模式）

```bash
cd /workspace/extensions/chromadb
uv pip install -e .
```

#### 方式 B：添加到 Python 路径

在启动应用前设置 `PYTHONPATH`：

```bash
export PYTHONPATH="/workspace/extensions/chromadb:$PYTHONPATH"
```

### 3. 配置 config.yaml

修改项目根目录的 `config.yaml` 文件，将 `storage_class` 设置为 ChromaMemoryStorage：

```yaml
memory:
  enabled: true
  storage_class: deerflow_chromadb.storage.ChromaMemoryStorage
  # 其他内存配置保持不变
  debounce_seconds: 30
  model_name: null
  max_facts: 100
  fact_confidence_threshold: 0.7
  injection_enabled: true
  max_injection_tokens: 2000
```

### 4. 配置环境变量

根据需要设置以下环境变量：

```bash
# ChromaDB 配置
# 本地持久化模式（默认）
export CHROMADB_PERSIST_DIR="./chromadb_data"

# 或远程服务器模式
# export CHROMADB_HOST="localhost"
# export CHROMADB_PORT="8000"

# SQL Server 配置（如果需要同步字典数据）
export SQL_SERVER_SERVER="your_server"
export SQL_SERVER_DATABASE="your_database"
export SQL_SERVER_USER="your_username"
export SQL_SERVER_PASSWORD="your_password"

# 同步配置
export SYNC_INTERVAL_SECONDS="3600"
export SYNC_NAMESPACE="sql_server_dictionary"

# 意图识别配置
export INTENT_RECOGNITION_TOP_K="5"
export INTENT_RECOGNITION_THRESHOLD="0.7"
```

### 5. 启动 DeerFlow

```bash
cd /workspace/backend
# 启动应用
# 例如：uv run python -m app.gateway.app
```

## 验证配置

启动后，你可以通过以下方式验证 ChromaDB 是否正确集成：

1. 检查日志输出，应该看到类似以下信息：
   ```
   INFO - Connecting to local ChromaDB with persist directory: ./chromadb_data
   INFO - ChromaMemoryStorage initialized successfully
   ```

2. 使用我们提供的示例脚本测试：
   ```bash
   cd /workspace/backend
   uv run python chromadb_optimized_example.py
   ```

## 自动同步 SQL Server 字典数据

要启用 SQL Server 字典数据的自动同步，你需要：

1. 确保 SQL Server 连接配置正确
2. 创建一个启动脚本，在应用启动时启动同步服务

### 启动同步服务的示例代码

```python
# 在应用启动时执行
from deerflow_chromadb import get_sync_manager
import chromadb

# 初始化 ChromaDB 客户端
chroma_client = chromadb.Client()

# 创建同步管理器
sync_manager = get_sync_manager(chroma_client)

# 定义表配置
tables_config = [
    {
        "table_name": "dbo.dictionary_terms",
        "term_column": "term",
        "definition_column": "definition",
        "category_column": "category",
        "example_column": "examples"
    }
]

# 配置并启动同步服务
sync_manager.configure_sync(
    tables_config=tables_config,
    interval_seconds=3600
)
sync_manager.start_sync()

# 手动触发初始同步
sync_manager.sync_now()
```

## 常见问题

### 1. 导入错误：No module named 'deerflow_chromadb'

**解决方案**：确保已正确安装或设置 Python 路径。

### 2. ChromaDB 未安装

**解决方案**：运行 `uv add chromadb>=0.5.0` 安装 ChromaDB。

### 3. SQL Server 连接失败

**解决方案**：确保环境变量配置正确，并且 SQL Server 可以访问。

### 4. 内存数据未持久化

**解决方案**：检查 `CHROMADB_PERSIST_DIR` 目录是否有写权限。

## 总结

通过以上配置，你可以将 ChromaDB 集成到 DeerFlow agent 中，实现：

1. 使用 ChromaDB 存储和检索内存数据
2. 从 SQL Server 自动同步字典数据
3. 利用业务术语进行智能意图识别
4. 提高 agent 对业务领域知识的理解能力
