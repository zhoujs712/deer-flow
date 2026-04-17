"""业务数据管理 - 用于 ChromaDB 集成"""

import json
import logging
from typing import Any, Dict, List, Optional

from .config import get_config

logger = logging.getLogger(__name__)


class BusinessDataManager:
    """业务数据管理器 - 用于在 ChromaDB 中存储和检索业务数据"""

    def __init__(self, chroma_client):
        """初始化业务数据管理器

        Args:
            chroma_client: ChromaDB 客户端实例
        """
        self._client = chroma_client
        self._collection = self._client.get_or_create_collection(
            name="business_terms",
            metadata={"purpose": "business terminology and domain knowledge"}
        )
        self._config = get_config()

    def store_business_terms(
        self,
        terms: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> bool:
        """在 ChromaDB 中存储业务术语

        Args:
            terms: 业务术语列表，包含定义
            namespace: 用于组织术语的命名空间

        每个术语应包含：
            - term: str - 业务术语
            - definition: str - 定义
            - examples: List[str] - 使用示例（可选）
            - category: str - 类别（可选）

        Returns:
            bool: 成功状态
        """
        try:
            documents = []
            metadatas = []
            ids = []

            for i, term_data in enumerate(terms):
                term = term_data.get("term")
                definition = term_data.get("definition")
                examples = term_data.get("examples", [])
                category = term_data.get("category", "general")

                if not term or not definition:
                    logger.warning(f"跳过缺少术语或定义的条目: {term_data}")
                    continue

                # 创建文档内容
                content_parts = [f"Term: {term}", f"Definition: {definition}"]
                if examples:
                    content_parts.append(f"Examples: {', '.join(examples)}")
                if category:
                    content_parts.append(f"Category: {category}")
                content = "\n".join(content_parts)

                documents.append(content)
                metadatas.append({
                    "term": term,
                    "category": category,
                    "namespace": namespace,
                    "type": "business_term"
                })
                ids.append(f"{namespace}_{term}_{i}")

            if documents:
                self._collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"已存储 {len(documents)} 个业务术语到命名空间 '{namespace}'")
                return True
            return False

        except Exception as e:
            logger.error("存储业务术语失败: %s", e, exc_info=True)
            return False

    def store_business_documents(
        self,
        documents: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> bool:
        """在 ChromaDB 中存储业务文档

        Args:
            documents: 业务文档列表
            namespace: 用于组织文档的命名空间

        每个文档应包含：
            - title: str - 文档标题
            - content: str - 文档内容
            - tags: List[str] - 标签（可选）
            - source: str - 来源（可选）

        Returns:
            bool: 成功状态
        """
        try:
            doc_contents = []
            metadatas = []
            ids = []

            for i, doc in enumerate(documents):
                title = doc.get("title")
                content = doc.get("content")
                tags = doc.get("tags", [])
                source = doc.get("source", "unknown")

                if not title or not content:
                    logger.warning(f"跳过缺少标题或内容的文档: {doc}")
                    continue

                doc_content = f"Title: {title}\nContent: {content}"
                if tags:
                    doc_content += f"\nTags: {', '.join(tags)}"
                if source:
                    doc_content += f"\nSource: {source}"

                doc_contents.append(doc_content)
                metadatas.append({
                    "title": title,
                    "source": source,
                    "tags": tags,
                    "namespace": namespace,
                    "type": "business_document"
                })
                ids.append(f"{namespace}_doc_{i}")

            if doc_contents:
                self._collection.upsert(
                    documents=doc_contents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"已存储 {len(doc_contents)} 个业务文档到命名空间 '{namespace}'")
                return True
            return False

        except Exception as e:
            logger.error("存储业务文档失败: %s", e, exc_info=True)
            return False

    def search_business_terms(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索与查询相关的业务术语

        Args:
            query: 搜索查询
            namespace: 可选的命名空间过滤器
            top_k: 最大结果数
            category: 可选的类别过滤器

        Returns:
            匹配的业务术语列表
        """
        try:
            # 使用配置管理模块的默认值
            intent_config = self._config.get_intent_recognition_config()
            if top_k <= 0:
                top_k = intent_config["top_k"]

            where = {"type": "business_term"}
            if namespace:
                where["namespace"] = namespace
            if category:
                where["category"] = category

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where
            )

            matched_terms = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # 解析文档内容
                term_info = {}
                lines = doc.split('\n')
                for line in lines:
                    if line.startswith("Term: "):
                        term_info["term"] = line[6:].strip()
                    elif line.startswith("Definition: "):
                        term_info["definition"] = line[11:].strip()
                    elif line.startswith("Examples: "):
                        term_info["examples"] = line[10:].strip().split(", ")
                    elif line.startswith("Category: "):
                        term_info["category"] = line[10:].strip()
                
                term_info["metadata"] = metadata
                term_info["similarity"] = 1.0 - distance  # 将距离转换为相似度
                matched_terms.append(term_info)

            return matched_terms

        except Exception as e:
            logger.error("搜索业务术语失败: %s", e, exc_info=True)
            return []

    def search_business_documents(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 3,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """搜索与查询相关的业务文档

        Args:
            query: 搜索查询
            namespace: 可选的命名空间过滤器
            top_k: 最大结果数
            tags: 可选的标签过滤器

        Returns:
            匹配的业务文档列表
        """
        try:
            where = {"type": "business_document"}
            if namespace:
                where["namespace"] = namespace

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where
            )

            matched_docs = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # 如果指定了标签，进行过滤
                if tags and "tags" in metadata:
                    doc_tags = metadata["tags"]
                    if not any(tag in doc_tags for tag in tags):
                        continue
                
                doc_info = {
                    "title": metadata.get("title", ""),
                    "source": metadata.get("source", ""),
                    "tags": metadata.get("tags", []),
                    "content": doc,
                    "similarity": 1.0 - distance
                }
                matched_docs.append(doc_info)

            return matched_docs

        except Exception as e:
            logger.error("搜索业务文档失败: %s", e, exc_info=True)
            return []

    def get_all_terms(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有业务术语

        Args:
            namespace: 可选的命名空间过滤器

        Returns:
            所有业务术语列表
        """
        try:
            where = {"type": "business_term"}
            if namespace:
                where["namespace"] = namespace

            results = self._collection.get(
                where=where
            )

            terms = []
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i]
                term_info = {"metadata": metadata, "content": doc}
                terms.append(term_info)

            return terms

        except Exception as e:
            logger.error("获取所有术语失败: %s", e, exc_info=True)
            return []

    def clear_namespace(self, namespace: str) -> bool:
        """清除命名空间中的所有数据

        Args:
            namespace: 要清除的命名空间

        Returns:
            bool: 成功状态
        """
        try:
            results = self._collection.get(
                where={"namespace": namespace}
            )

            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info(f"已清除命名空间 '{namespace}' 中的 {len(results['ids'])} 个项目")
            return True

        except Exception as e:
            logger.error(f"清除命名空间 '{namespace}' 失败: %s", e, exc_info=True)
            return False
