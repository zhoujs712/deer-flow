"""ChromaDB 内存存储提供者"""

import json
import logging
from typing import Any

from deerflow.agents.memory.storage import (
    MemoryStorage,
    create_empty_memory,
    utc_now_iso_z,
)
from deerflow.config.agents_config import AGENT_NAME_PATTERN

from .config import get_config

logger = logging.getLogger(__name__)


class ChromaMemoryStorage(MemoryStorage):
    """ChromaDB 内存存储提供者

    此实现使用 ChromaDB 存储和检索内存数据。
    支持内存和持久化 ChromaDB 实例。

    配置方式：
    - 环境变量：CHROMADB_HOST, CHROMADB_PORT, CHROMADB_PERSIST_DIR
    - 或通过 ChromaDBConfig 配置类
    """

    def __init__(self):
        """初始化 ChromaDB 内存存储"""
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            raise ImportError(
                "ChromaDB 未安装。 "
                "使用以下命令安装：uv pip install chromadb>=0.5.0"
            )

        self._client = None
        self._embedding_fn = None
        self._collections = {}

        # 使用配置管理模块
        config = get_config()
        chromadb_config = config.get_chromadb_config()

        if "host" in chromadb_config and "port" in chromadb_config:
            logger.info("连接到 ChromaDB 服务器: %s:%s", chromadb_config["host"], chromadb_config["port"])
            self._client = chromadb.HttpClient(
                host=chromadb_config["host"], 
                port=int(chromadb_config["port"])
            )
        else:
            logger.info("使用本地 ChromaDB，持久化目录: %s", chromadb_config["persist_dir"])
            self._client = chromadb.PersistentClient(path=chromadb_config["persist_dir"])

        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        logger.info("ChromaMemoryStorage 初始化成功")

    def _get_collection_name(self, agent_name: str | None) -> str:
        """获取指定代理的集合名称"""
        if agent_name:
            if not AGENT_NAME_PATTERN.match(agent_name):
                raise ValueError(f"无效的代理名称: {agent_name!r}")
            return f"memory_{agent_name}"
        return "memory_global"

    def _get_or_create_collection(self, agent_name: str | None):
        """获取或创建代理的 ChromaDB 集合"""
        name = self._get_collection_name(agent_name)
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._embedding_fn,
            )
        return self._collections[name]

    def load(self, agent_name: str | None = None) -> dict[str, Any]:
        """从 ChromaDB 加载指定代理的内存数据

        Args:
            agent_name: 代理名称（None 表示全局内存）

        Returns:
            内存数据字典
        """
        try:
            collection = self._get_or_create_collection(agent_name)
            results = collection.get(ids=["memory_main"], limit=1)

            if not results["documents"]:
                logger.debug("未找到代理 %s 的内存数据，返回空内存", agent_name)
                return create_empty_memory()

            memory_data = json.loads(results["documents"][0])
            logger.debug("已加载代理 %s 的内存数据", agent_name)
            return memory_data

        except Exception as e:
            logger.warning("从 ChromaDB 加载内存失败: %s", e, exc_info=True)
            return create_empty_memory()

    def reload(self, agent_name: str | None = None) -> dict[str, Any]:
        """强制从 ChromaDB 重新加载内存数据

        Args:
            agent_name: 代理名称（None 表示全局内存）

        Returns:
            内存数据字典
        """
        return self.load(agent_name)

    def save(self, memory_data: dict[str, Any], agent_name: str | None = None) -> bool:
        """将内存数据保存到 ChromaDB

        Args:
            memory_data: 要保存的内存数据
            agent_name: 代理名称（None 表示全局内存）

        Returns:
            保存成功返回 True，否则返回 False
        """
        try:
            collection = self._get_or_create_collection(agent_name)
            memory_data["lastUpdated"] = utc_now_iso_z()
            doc = json.dumps(memory_data, ensure_ascii=False)

            collection.upsert(
                documents=[doc],
                ids=["memory_main"],
                metadatas=[{"agent": agent_name or "global", "type": "memory"}],
            )

            logger.info("内存已保存到 ChromaDB，代理: %s", agent_name)
            return True

        except Exception as e:
            logger.error("保存内存到 ChromaDB 失败: %s", e, exc_info=True)
            return False

    def search_facts(
        self,
        query: str,
        agent_name: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """在内存中进行语义搜索

        Args:
            query: 搜索查询文本
            agent_name: 代理名称（None 表示全局内存）
            top_k: 返回结果数量

        Returns:
            匹配的事实列表及其元数据
        """
        try:
            collection = self._get_or_create_collection(agent_name)
            memory_data = self.load(agent_name)
            facts = memory_data.get("facts", [])

            if not facts:
                return []

            fact_texts = [f.get("content", "") for f in facts]
            fact_ids = [str(i) for i in range(len(facts))]

            temp_collection = self._client.create_collection(
                name=f"temp_search_{agent_name or 'global'}",
                embedding_function=self._embedding_fn,
            )

            try:
                temp_collection.add(
                    documents=fact_texts,
                    ids=fact_ids,
                    metadatas=[{"index": i} for i in range(len(facts))],
                )

                results = temp_collection.query(
                    query_texts=[query],
                    n_results=min(top_k, len(facts)),
                )

                matched_facts = []
                for idx_str in results["ids"][0]:
                    idx = int(idx_str)
                    if idx < len(facts):
                        matched_facts.append(facts[idx])

                return matched_facts

            finally:
                self._client.delete_collection(temp_collection.name)

        except Exception as e:
            logger.error("搜索事实失败: %s", e, exc_info=True)
            return []
