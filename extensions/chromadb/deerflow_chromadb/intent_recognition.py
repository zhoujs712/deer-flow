"""意图识别 - 具有业务术语感知能力"""

import logging
from typing import Dict, List, Optional, Any

from deerflow_chromadb.storage import ChromaMemoryStorage
from deerflow_chromadb.business_data import BusinessDataManager
from deerflow_chromadb.config import get_config

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """意图识别器 - 具有业务术语感知能力"""

    def __init__(self, memory_storage: ChromaMemoryStorage):
        """初始化意图识别器

        Args:
            memory_storage: ChromaMemoryStorage 实例
        """
        self._memory_storage = memory_storage
        # 从存储实例访问 ChromaDB 客户端
        self._client = memory_storage._client
        self._business_manager = BusinessDataManager(self._client)
        self._config = get_config()

    def recognize_intent(
        self,
        user_input: str,
        namespace: str = "default",
        top_k_terms: int = 5,
        top_k_docs: int = 2
    ) -> Dict[str, Any]:
        """识别具有业务术语感知的意图

        Args:
            user_input: 用户输入文本
            namespace: 业务数据命名空间
            top_k_terms: 返回的业务术语数量
            top_k_docs: 返回的业务文档数量

        Returns:
            包含意图分析结果的字典
        """
        try:
            # 使用配置管理模块的默认值
            intent_config = self._config.get_intent_recognition_config()
            threshold = intent_config["threshold"]

            # 搜索相关业务术语
            business_terms = self._business_manager.search_business_terms(
                query=user_input,
                namespace=namespace,
                top_k=top_k_terms
            )

            # 搜索相关业务文档
            business_docs = self._business_manager.search_business_documents(
                query=user_input,
                namespace=namespace,
                top_k=top_k_docs
            )

            # 提取关键业务术语
            key_terms = [term["term"] for term in business_terms if term.get("similarity", 0) > threshold]

            # 基于业务术语和输入确定意图
            intent = self._infer_intent(user_input, key_terms, business_terms, threshold)

            return {
                "user_input": user_input,
                "intent": intent,
                "key_business_terms": key_terms,
                "relevant_terms": business_terms,
                "relevant_documents": business_docs,
                "confidence": self._calculate_confidence(business_terms, threshold)
            }

        except Exception as e:
            logger.error("识别意图失败: %s", e, exc_info=True)
            return {
                "user_input": user_input,
                "intent": "general_inquiry",
                "key_business_terms": [],
                "relevant_terms": [],
                "relevant_documents": [],
                "confidence": 0.0,
                "error": str(e)
            }

    def _infer_intent(
        self,
        user_input: str,
        key_terms: List[str],
        business_terms: List[Dict[str, Any]],
        threshold: float
    ) -> str:
        """基于输入和业务术语推断意图

        Args:
            user_input: 用户输入文本
            key_terms: 关键业务术语
            business_terms: 带有相似度分数的详细业务术语
            threshold: 相似度阈值

        Returns:
            意图字符串
        """
        # 基于关键词和业务术语的简单意图分类
        input_lower = user_input.lower()

        # 检查特定意图
        if any(word in input_lower for word in ["help", "assist", "guide", "帮助", "协助", "指导"]):
            return "help_request"
        elif any(word in input_lower for word in ["define", "what is", "meaning", "explain", "定义", "什么是", "含义", "解释"]):
            return "definition_request"
        elif any(word in input_lower for word in ["example", "usage", "how to", "示例", "用法", "如何"]):
            return "example_request"
        elif any(word in input_lower for word in ["problem", "issue", "error", "trouble", "问题", "错误", "麻烦"]):
            return "problem_report"
        elif any(word in input_lower for word in ["report", "summary", "update", "报告", "总结", "更新"]):
            return "report_request"
        elif any(word in input_lower for word in ["policy", "rule", "guideline", "政策", "规则", "指南"]):
            return "policy_inquiry"

        # 基于业务术语类别确定意图
        categories = set()
        for term in business_terms:
            if term.get("similarity", 0) > threshold + 0.1:
                category = term.get("category", "")
                if category:
                    categories.add(category)

        if categories:
            if "product" in categories or "产品" in categories:
                return "product_inquiry"
            elif "process" in categories or "流程" in categories:
                return "process_inquiry"
            elif "service" in categories or "服务" in categories:
                return "service_inquiry"
            elif "policy" in categories or "政策" in categories:
                return "policy_inquiry"

        # 默认意图
        return "general_inquiry"

    def _calculate_confidence(self, business_terms: List[Dict[str, Any]], threshold: float) -> float:
        """基于业务术语匹配计算置信度分数

        Args:
            business_terms: 匹配的业务术语列表
            threshold: 相似度阈值

        Returns:
            0.0 到 1.0 之间的置信度分数
        """
        if not business_terms:
            return 0.0

        # 计算平均相似度分数
        similarities = [term.get("similarity", 0) for term in business_terms]
        avg_similarity = sum(similarities) / len(similarities)

        # 基于匹配数量调整置信度
        match_count = len([s for s in similarities if s > threshold])
        confidence = avg_similarity

        if match_count >= 3:
            confidence = min(1.0, confidence * 1.2)
        elif match_count == 0:
            confidence = max(0.1, confidence * 0.5)

        return round(confidence, 2)

    def enhance_prompt(
        self,
        user_input: str,
        namespace: str = "default"
    ) -> str:
        """使用业务上下文增强提示

        Args:
            user_input: 用户输入
            namespace: 业务数据命名空间

        Returns:
            带有业务上下文的增强提示
        """
        analysis = self.recognize_intent(user_input, namespace)

        # 构建增强提示
        enhanced_prompt = f"用户输入: {user_input}\n"

        if analysis.get("key_business_terms"):
            terms_str = ", ".join(analysis["key_business_terms"])
            enhanced_prompt += f"检测到的业务术语: {terms_str}\n"

        if analysis.get("relevant_terms"):
            enhanced_prompt += "相关业务定义:\n"
            for term in analysis["relevant_terms"]:
                if term.get("similarity", 0) > self._config.get_intent_recognition_config()["threshold"]:
                    enhanced_prompt += f"- {term.get('term')}: {term.get('definition', '')}\n"

        if analysis.get("relevant_documents"):
            enhanced_prompt += "相关业务文档:\n"
            for doc in analysis["relevant_documents"]:
                if doc.get("similarity", 0) > 0.6:
                    enhanced_prompt += f"- {doc.get('title')} (来源: {doc.get('source')})\n"

        enhanced_prompt += f"检测到的意图: {analysis.get('intent', 'general_inquiry')}\n"
        enhanced_prompt += f"置信度: {analysis.get('confidence', 0.0)}\n"

        return enhanced_prompt


class IntentRecognitionTool:
    """意图识别工具 - 用于业务术语感知"""

    def __init__(self, memory_storage: ChromaMemoryStorage):
        """初始化意图识别工具

        Args:
            memory_storage: ChromaMemoryStorage 实例
        """
        self._recognizer = IntentRecognizer(memory_storage)

    def recognize_intent(
        self,
        user_input: str,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """从用户输入识别意图

        Args:
            user_input: 用户输入文本
            namespace: 可选的业务数据命名空间

        Returns:
            意图识别结果
        """
        return self._recognizer.recognize_intent(
            user_input,
            namespace=namespace or "default"
        )

    def enhance_prompt(
        self,
        user_input: str,
        namespace: Optional[str] = None
    ) -> str:
        """使用业务上下文增强提示

        Args:
            user_input: 用户输入文本
            namespace: 可选的业务数据命名空间

        Returns:
            增强提示
        """
        return self._recognizer.enhance_prompt(
            user_input,
            namespace=namespace or "default"
        )

    def store_business_terms(
        self,
        terms: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> bool:
        """存储业务术语用于意图识别

        Args:
            terms: 业务术语列表
            namespace: 可选的命名空间

        Returns:
            成功状态
        """
        return self._recognizer._business_manager.store_business_terms(
            terms,
            namespace=namespace or "default"
        )

    def store_business_documents(
        self,
        documents: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> bool:
        """存储业务文档用于意图识别

        Args:
            documents: 业务文档列表
            namespace: 可选的命名空间

        Returns:
            成功状态
        """
        return self._recognizer._business_manager.store_business_documents(
            documents,
            namespace=namespace or "default"
        )
