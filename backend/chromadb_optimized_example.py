"""优化后的 ChromaDB 集成综合示例"""

import os
import logging
from deerflow_chromadb import (
    ChromaMemoryStorage, 
    BusinessDataManager, 
    IntentRecognitionTool, 
    get_sync_manager, 
    get_config
)
import chromadb

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """优化后的 ChromaDB 集成示例主函数"""
    logger.info("启动优化后的 ChromaDB 集成示例")

    # 1. 初始化 ChromaMemoryStorage
    logger.info("初始化 ChromaMemoryStorage...")
    storage = ChromaMemoryStorage()
    logger.info("ChromaMemoryStorage 初始化成功")

    # 2. 使用配置管理模块
    logger.info("获取配置信息...")
    config = get_config()
    logger.info(f"ChromaDB 配置: {config.get_chromadb_config()}")
    logger.info(f"同步配置: {config.get_sync_config()}")
    logger.info(f"意图识别配置: {config.get_intent_recognition_config()}")

    # 3. 存储业务数据
    logger.info("存储示例业务术语...")
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
        },
        {
            "term": "客户生命周期价值",
            "definition": "客户在与企业关系期间产生的总价值",
            "examples": ["我们的客户生命周期价值为 1000 元", "提高客户生命周期价值是长期增长的关键"],
            "category": "metrics"
        }
    ]

    # 获取 ChromaDB 客户端
    chroma_client = storage._client
    
    # 初始化业务数据管理器
    business_manager = BusinessDataManager(chroma_client)
    
    # 存储业务术语
    success = business_manager.store_business_terms(
        terms=business_terms,
        namespace="marketing"
    )
    if success:
        logger.info("业务术语存储成功")
    else:
        logger.error("业务术语存储失败")

    # 4. 测试意图识别
    logger.info("测试意图识别...")
    intent_tool = IntentRecognitionTool(storage)
    
    # 测试查询
    test_queries = [
        "如何提高用户留存率？",
        "什么是转化率？",
        "如何计算客户生命周期价值？"
    ]
    
    for query in test_queries:
        logger.info(f"\n测试查询: {query}")
        
        # 识别意图
        result = intent_tool.recognize_intent(
            query,
            namespace="marketing"
        )
        logger.info(f"意图: {result['intent']}")
        logger.info(f"置信度: {result['confidence']}")
        logger.info(f"关键业务术语: {result['key_business_terms']}")
        
        # 增强提示
        enhanced_prompt = intent_tool.enhance_prompt(
            query,
            namespace="marketing"
        )
        logger.info("增强提示:")
        logger.info(enhanced_prompt)

    # 5. 配置 SQL Server 同步（如果需要）
    logger.info("\n配置 SQL Server 同步...")
    
    # 检查 SQL Server 连接配置
    sql_conn_str = config.get_sql_server_connection_string()
    if sql_conn_str:
        logger.info("SQL Server 连接字符串配置已找到")
        
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
        
        # 配置同步
        sync_configured = sync_manager.configure_sync(
            tables_config=tables_config,
            interval_seconds=3600
        )
        
        if sync_configured:
            logger.info("SQL Server 同步配置成功")
            # 启动同步服务
            sync_started = sync_manager.start_sync()
            if sync_started:
                logger.info("SQL Server 同步服务已启动")
                # 手动触发初始同步
                sync_success = sync_manager.sync_now()
                if sync_success:
                    logger.info("初始同步完成")
                else:
                    logger.error("初始同步失败")
            else:
                logger.error("启动同步服务失败")
        else:
            logger.error("配置同步失败")
    else:
        logger.info("未找到 SQL Server 连接配置，跳过同步设置")

    logger.info("\n优化后的 ChromaDB 集成示例完成")

if __name__ == "__main__":
    main()
