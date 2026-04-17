"""同步管理器 - 用于字典数据更新"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any

from .sql_server import SQLServerExtractor
from .business_data import BusinessDataManager
from .config import get_config

logger = logging.getLogger(__name__)


class SyncManager:
    """同步管理器 - 用于从 SQL Server 同步字典数据到 ChromaDB"""

    def __init__(self, chroma_client):
        """初始化同步管理器

        Args:
            chroma_client: ChromaDB 客户端实例
        """
        self._chroma_client = chroma_client
        self._business_data_manager = BusinessDataManager(chroma_client)
        self._sql_extractor = SQLServerExtractor()
        self._sync_thread = None
        self._running = False
        self._interval_seconds = 3600  # 默认：1小时
        self._tables_config = []
        self._namespace = "sql_server_dictionary"

    def configure_sync(
        self,
        tables_config: List[Dict[str, Any]],
        connection_string: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """配置同步设置

        Args:
            tables_config: 表配置列表
            connection_string: SQL Server 连接字符串
            interval_seconds: 同步间隔（秒）
            namespace: 存储命名空间

        Returns:
            bool: 配置成功状态
        """
        self._tables_config = tables_config
        
        # 使用配置管理模块的默认值
        config = get_config()
        sync_config = config.get_sync_config()
        
        self._interval_seconds = interval_seconds or sync_config["interval_seconds"]
        self._namespace = namespace or sync_config["namespace"]

        # 连接到 SQL Server
        if connection_string:
            connected = self._sql_extractor.connect(connection_string)
        else:
            # 尝试从配置获取连接字符串
            conn_str = config.get_sql_server_connection_string()
            if conn_str:
                connected = self._sql_extractor.connect(conn_str)
            else:
                connected = self._sql_extractor.connect_from_env()

        if not connected:
            logger.error("同步服务连接 SQL Server 失败")
            return False

        logger.info(f"同步服务配置成功，间隔: {self._interval_seconds}秒，命名空间: {self._namespace}")
        return True

    def start_sync(self) -> bool:
        """启动同步服务

        Returns:
            bool: 启动成功状态
        """
        if self._running:
            logger.warning("同步服务已经在运行")
            return True

        if not self._tables_config:
            logger.error("未配置同步表，启动失败")
            return False

        try:
            self._running = True
            self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self._sync_thread.start()
            logger.info(f"同步服务已启动，间隔: {self._interval_seconds}秒")
            return True
        except Exception as e:
            logger.error("启动同步服务失败: %s", e, exc_info=True)
            self._running = False
            return False

    def stop_sync(self) -> bool:
        """停止同步服务

        Returns:
            bool: 停止成功状态
        """
        if not self._running:
            logger.warning("同步服务未运行")
            return True

        try:
            self._running = False
            if self._sync_thread:
                self._sync_thread.join(timeout=5)
            logger.info("同步服务已停止")
            return True
        except Exception as e:
            logger.error("停止同步服务失败: %s", e, exc_info=True)
            return False

    def sync_now(self) -> bool:
        """手动触发同步

        Returns:
            bool: 同步成功状态
        """
        return self._perform_sync()

    def _sync_loop(self):
        """同步循环"""
        while self._running:
            try:
                self._perform_sync()
            except Exception as e:
                logger.error("同步循环错误: %s", e, exc_info=True)
            
            # 等待下一个间隔
            for _ in range(self._interval_seconds):
                if not self._running:
                    break
                time.sleep(1)

    def _perform_sync(self) -> bool:
        """执行从 SQL Server 到 ChromaDB 的同步

        Returns:
            bool: 同步成功状态
        """
        try:
            logger.info("开始从 SQL Server 同步到 ChromaDB")

            # 从 SQL Server 提取术语
            terms = self._sql_extractor.extract_multiple_tables(self._tables_config)
            
            if not terms:
                logger.warning("未从 SQL Server 提取到术语")
                return False

            # 存储术语到 ChromaDB
            success = self._business_data_manager.store_business_terms(
                terms=terms,
                namespace=self._namespace
            )

            if success:
                logger.info(f"成功同步 {len(terms)} 个术语到 ChromaDB")
            else:
                logger.error("存储术语到 ChromaDB 失败")

            return success

        except Exception as e:
            logger.error("执行同步失败: %s", e, exc_info=True)
            return False

    def is_running(self) -> bool:
        """检查同步服务是否运行

        Returns:
            bool: 运行状态
        """
        return self._running

    def get_sync_interval(self) -> int:
        """获取当前同步间隔（秒）

        Returns:
            int: 同步间隔（秒）
        """
        return self._interval_seconds

    def get_namespace(self) -> str:
        """获取当前存储命名空间

        Returns:
            str: 命名空间
        """
        return self._namespace


def get_sync_manager(chroma_client) -> SyncManager:
    """获取同步管理器实例

    Args:
        chroma_client: ChromaDB 客户端实例

    Returns:
        SyncManager: 同步管理器实例
    """
    return SyncManager(chroma_client)
