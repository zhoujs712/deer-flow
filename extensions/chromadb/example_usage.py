"""Example usage of ChromaDB business data and intent recognition."""

from chromadb import ChromaMemoryStorage, IntentRecognitionTool


def example_business_data():
    """Example of storing business data and using intent recognition."""
    # Initialize ChromaMemoryStorage
    storage = ChromaMemoryStorage()
    
    # Initialize intent recognition tool
    intent_tool = IntentRecognitionTool(storage)
    
    # Step 1: Store business terms
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
            "term": "客单价",
            "definition": "每个客户平均购买金额",
            "examples": ["我们的客单价为 299 元", "提高客单价是增加收入的重要方式"],
            "category": "metrics"
        },
        {
            "term": "A/B 测试",
            "definition": "比较两个版本以确定哪个表现更好的实验方法",
            "examples": ["我们进行了 A/B 测试来优化按钮颜色", "A/B 测试结果显示版本 B 表现更好"],
            "category": "process"
        },
        {
            "term": "用户画像",
            "definition": "基于用户数据构建的用户特征描述",
            "examples": ["根据用户画像我们调整了营销策略", "用户画像是精准营销的基础"],
            "category": "marketing"
        }
    ]
    
    # Store business terms
    success = intent_tool.store_business_terms(business_terms, namespace="marketing")
    print(f"Stored business terms: {success}")
    
    # Step 2: Store business documents
    business_documents = [
        {
            "title": "2024 年营销战略",
            "content": "我们的 2024 年营销战略将聚焦于提高用户留存率和转化率。通过 A/B 测试优化用户体验，基于用户画像进行精准营销。目标是将客单价提高 15%。",
            "tags": ["marketing", "strategy", "2024"],
            "source": "营销部门"
        },
        {
            "title": "产品优化指南",
            "content": "产品优化应关注用户留存率。通过分析用户行为数据，识别流失原因，针对性地改进产品功能。A/B 测试是验证优化效果的有效方法。",
            "tags": ["product", "optimization"],
            "source": "产品部门"
        }
    ]
    
    # Store business documents
    success = intent_tool.store_business_documents(business_documents, namespace="marketing")
    print(f"Stored business documents: {success}")
    
    # Step 3: Test intent recognition
    test_queries = [
        "如何提高用户留存率？",
        "什么是 A/B 测试？",
        "我们的客单价目标是多少？",
        "如何基于用户画像进行营销？",
        "2024 年的营销战略是什么？"
    ]
    
    print("\n=== Intent Recognition Results ===")
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = intent_tool.recognize_intent(query, namespace="marketing")
        print(f"Intent: {result['intent']}")
        print(f"Confidence: {result['confidence']}")
        if result['key_business_terms']:
            print(f"Business terms: {', '.join(result['key_business_terms'])}")
        
        # Show enhanced prompt
        print("\nEnhanced prompt:")
        enhanced = intent_tool.enhance_prompt(query, namespace="marketing")
        print(enhanced)


if __name__ == "__main__":
    example_business_data()
