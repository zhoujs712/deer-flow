"""SQL Server 字典数据同步到 ChromaDB 示例"""

import os
import time
import logging
from deerflow_chromadb import get_sync_manager, get_config
import chromadb

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """SQL Server 同步示例主函数"""
    logger.info("启动 SQL Server 字典数据同步示例")

    # 初始化 ChromaDB 客户端
    # 生产环境中，考虑使用持久化目录
    chroma_client = chromadb.Client()

    # 创建同步管理器
    sync_manager = get_sync_manager(chroma_client)

    # 配置 SQL Server 连接和表
    # 选项 1: 使用环境变量
    # 运行前设置这些环境变量:
    # SQL_SERVER_SERVER, SQL_SERVER_DATABASE, SQL_SERVER_USER, SQL_SERVER_PASSWORD
    # 或
    # SQL_SERVER_CONNECTION_STRING
    
    # 选项 2: 直接使用连接字符串
    # connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=your_db;UID=your_user;PWD=your_password"

    # 定义表配置
    # 示例: 从多个字典表提取数据
    tables_config = [
        {
            "table_name": "dbo.dictionary_terms",  # 字典表名
            "term_column": "term",  # 术语列名
            "definition_column": "definition",  # 定义列名
            "category_column": "category",  # 类别列名
            "example_column": "examples"  # 示例列名
        },
        {
            "table_name": "dbo.product_terms",  # 产品术语表名
            "term_column": "product_name",  # 产品名称列
            "definition_column": "description",  # 描述列
            "category_column": "product_category"  # 产品类别列
        }
    ]

    # 配置同步（使用环境变量连接）
    success = sync_manager.configure_sync(
        tables_config=tables_config,
        interval_seconds=3600,  # 1小时同步间隔
        namespace="sql_server_dictionary"  # 存储命名空间
    )

    if not success:
        logger.error("配置同步失败")
        return

    # 启动同步服务
    success = sync_manager.start_sync()
    if not success:
        logger.error("启动同步服务失败")
        return

    # 获取配置信息
    config = get_config()
    sync_config = config.get_sync_config()
    
    logger.info("同步服务启动成功")
    logger.info(f"同步间隔: {sync_manager.get_sync_interval()}秒")
    logger.info(f"存储命名空间: {sync_manager.get_namespace()}")

    # 手动触发初始同步
    logger.info("执行初始同步...")
    sync_success = sync_manager.sync_now()
    if sync_success:
        logger.info("初始同步完成成功")
    else:
        logger.error("初始同步失败")

    # 保持脚本运行以演示同步服务
    try:
        logger.info("同步服务正在运行。按 Ctrl+C 停止...")
        while True:
            time.sleep(60)  # 每分钟检查一次
            logger.info(f"同步服务状态: {'运行中' if sync_manager.is_running() else '已停止'}")
    except KeyboardInterrupt:
        logger.info("停止同步服务...")
        sync_manager.stop_sync()
        logger.info("同步服务已停止")

if __name__ == "__main__":
    main()
