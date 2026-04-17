"""配置管理模块"""

import os
from typing import Dict, Optional, Any


class ChromaDBConfig:
    """ChromaDB 配置管理类"""

    def __init__(self):
        """初始化配置"""
        # ChromaDB 配置
        self.chromadb_persist_dir = os.environ.get("CHROMADB_PERSIST_DIR", ".chromadb")
        self.chromadb_host = os.environ.get("CHROMADB_HOST")
        self.chromadb_port = os.environ.get("CHROMADB_PORT")
        
        # SQL Server 配置
        self.sql_server_connection_string = os.environ.get("SQL_SERVER_CONNECTION_STRING")
        self.sql_server_server = os.environ.get("SQL_SERVER_SERVER")
        self.sql_server_database = os.environ.get("SQL_SERVER_DATABASE")
        self.sql_server_user = os.environ.get("SQL_SERVER_USER")
        self.sql_server_password = os.environ.get("SQL_SERVER_PASSWORD")
        
        # 同步配置
        self.sync_interval_seconds = int(os.environ.get("SYNC_INTERVAL_SECONDS", "3600"))
        self.sync_namespace = os.environ.get("SYNC_NAMESPACE", "sql_server_dictionary")
        
        # 意图识别配置
        self.intent_recognition_top_k = int(os.environ.get("INTENT_RECOGNITION_TOP_K", "5"))
        self.intent_recognition_threshold = float(os.environ.get("INTENT_RECOGNITION_THRESHOLD", "0.7"))

    def get_chromadb_config(self) -> Dict[str, Any]:
        """获取 ChromaDB 配置

        Returns:
            Dict: ChromaDB 配置
        """
        config = {
            "persist_dir": self.chromadb_persist_dir
        }
        
        if self.chromadb_host and self.chromadb_port:
            config["host"] = self.chromadb_host
            config["port"] = self.chromadb_port
        
        return config

    def get_sql_server_connection_string(self) -> Optional[str]:
        """获取 SQL Server 连接字符串

        Returns:
            Optional[str]: 连接字符串
        """
        if self.sql_server_connection_string:
            return self.sql_server_connection_string
        
        if all([self.sql_server_server, self.sql_server_database, self.sql_server_user, self.sql_server_password]):
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.sql_server_server};"
                f"DATABASE={self.sql_server_database};"
                f"UID={self.sql_server_user};"
                f"PWD={self.sql_server_password}"
            )
        
        return None

    def get_sync_config(self) -> Dict[str, Any]:
        """获取同步配置

        Returns:
            Dict: 同步配置
        """
        return {
            "interval_seconds": self.sync_interval_seconds,
            "namespace": self.sync_namespace
        }

    def get_intent_recognition_config(self) -> Dict[str, Any]:
        """获取意图识别配置

        Returns:
            Dict: 意图识别配置
        """
        return {
            "top_k": self.intent_recognition_top_k,
            "threshold": self.intent_recognition_threshold
        }


# 全局配置实例
config = ChromaDBConfig()

def get_config() -> ChromaDBConfig:
    """获取配置实例

    Returns:
        ChromaDBConfig: 配置实例
    """
    return config
