"""
简化的WikiSQL评估示例 - 方案1: 直接使用LLM + 手动SQL执行
这个脚本展示了如何使用Google Gemini API直接生成和执行SQL查询
"""

import os
import json
from typing import Optional
from pathlib import Path


def detect_local_wikisql() -> Optional[str]:
    """
    自动检测本地WikiSQL路径
    
    Returns:
        WikiSQL路径，如果找不到返回None
    """
    possible_paths = [
        "WikiSQL",           # 当前目录下的WikiSQL文件夹
        "../WikiSQL",        # 上级目录的WikiSQL文件夹
        "./WikiSQL",         # 明确的当前目录路径
        "wikisql",           # 小写版本
        "../wikisql"         # 上级目录小写版本
    ]
    
    for path in possible_paths:
        wikisql_path = Path(path)
        # 检查是否存在data目录和关键文件
        if (wikisql_path.exists() and 
            (wikisql_path / "data").exists() and
            (wikisql_path / "data" / "dev.jsonl").exists()):
            print(f"✅ 找到本地WikiSQL: {wikisql_path.absolute()}")
            return str(wikisql_path)
    
    return None

def quick_test():
    """快速测试示例 - 使用直接LLM方案"""
    
    # 1. 设置API密钥
    api_key = input("请输入你的API密钥 (用于Gemini 2.5 Flash): ").strip()
    if not api_key:
        print("需要提供API密钥")
        return
    
    try:
        # 导入直接LLM查询助手
        from wikisql_llm_direct import WikiSQLDirectLLM
        
        # 2. 检测本地WikiSQL
        print("检测本地WikiSQL数据...")
        local_wikisql_path = detect_local_wikisql()
        
        if local_wikisql_path:
            print(f"使用本地WikiSQL数据: {local_wikisql_path}")
            use_local = True
        else:
            print("未找到本地WikiSQL数据")
            choice = input("是否从网络下载？(y/n，默认y): ").strip().lower()
            if choice in ['n', 'no']:
                print("请将WikiSQL项目下载到当前目录或指定路径")
                return
            use_local = False
            local_wikisql_path = None
        
        # 3. 初始化WikiSQL直接LLM查询助手
        print("初始化WikiSQL直接LLM查询助手...")
        assistant = WikiSQLDirectLLM(api_key, local_wikisql_path=local_wikisql_path)
        
        # 4. 加载WikiSQL数据
        print("加载WikiSQL数据集...")
        if not use_local:
            print("注意：首次运行会下载数据，可能需要一些时间...")
        assistant.load_wikisql_dataset("dev", limit=5)
        
        # 5. 显示数据集信息
        info = assistant.get_dataset_info()
        print(f"\n📊 数据集信息:")
        print(f"  - 问题数量: {info['questions_count']}")
        print(f"  - 表格数量: {info['tables_count']}")
        print(f"  - 数据库表格: {info['db_tables_count']}")
        print(f"  - 示例问题: {info['sample_question']}")
        
        # 6. 测试真实WikiSQL问题
        print("\n🚀 开始测试真实WikiSQL问题...")
        print("="*60)
        
        for i in range(min(3, len(assistant.current_questions))):  # 测试前3个问题
            question_obj = assistant.current_questions[i]
            
            print(f"\n问题 {i+1}: {question_obj.question}")
            print(f"预期SQL: {question_obj.get_sql_string()}")
            print(f"表格ID: {question_obj.table_id}")
            print("-" * 40)
            
            # 生成SQL
            generated_sql = assistant.generate_sql(question_obj.question, question_obj.table_id)
            print(f"生成的SQL: {generated_sql}")
            
            # 执行查询
            if generated_sql:
                result = assistant.execute_sql(generated_sql)
                print(f"查询结果: {result}")
            
            # 评估结果
            print("\n📋 评估结果:")
            eval_result = assistant.evaluate_question(i)
            if "error" not in eval_result:
                print(f"  - 生成的SQL: {eval_result.get('generated_sql', 'N/A')}")
                print(f"  - 生成结果: {eval_result.get('generated_result', 'N/A')}")
                print(f"  - 预期结果: {eval_result.get('expected_result', 'N/A')}")
            else:
                print(f"  - 评估错误: {eval_result['error']}")
            
            print("-" * 60)
        
        print("\n✅ 真实WikiSQL测试完成！")
        
        # 7. 可选：交互式查询
        print("\n💬 现在你可以输入自定义问题来查询数据库")
        print("输入 'quit' 退出")
        
        while True:
            user_question = input("\n你的问题: ").strip()
            if user_question.lower() in ['quit', 'exit', '退出']:
                break
            
            if user_question:
                result = assistant.query(user_question)
                print(f"回答: {result}")
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test()