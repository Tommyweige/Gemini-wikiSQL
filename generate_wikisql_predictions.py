#!/usr/bin/env python3
"""
生成WikiSQL预测文件的脚本
输出符合WikiSQL官方评估器要求的格式
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 WikiSQL预测文件生成器")
    print("=" * 60)
    
    # 1. 获取API密钥
    api_key = input("请输入你的API密钥: ").strip()
    if not api_key:
        print("❌ 需要提供API密钥")
        return
    
    # 1.5. 选择模型
    print("\n🤖 选择模型:")
    print("1. Gemini 2.5 Flash (默认，速度快)")
    print("2. Gemma 3 27B IT (可能更准确)")
    
    model_choice = input("请选择模型 (1/2, 默认1): ").strip()
    if model_choice == "2":
        selected_model = "gemma-3-27b-it"
        print("✅ 已选择: Gemma 3 27B IT")
    else:
        selected_model = "gemini-2.5-flash"
        print("✅ 已选择: Gemini 2.5 Flash")
    
    # 2. 检测本地WikiSQL路径
    print("\n📁 检测本地WikiSQL数据...")
    wikisql_path = None
    possible_paths = ["WikiSQL", "../WikiSQL", "./WikiSQL"]
    
    for path in possible_paths:
        path_obj = Path(path)
        if (path_obj.exists() and 
            (path_obj / "data").exists() and
            (path_obj / "data" / "dev.jsonl").exists() and
            (path_obj / "evaluate.py").exists()):
            wikisql_path = str(path_obj.resolve())  # 使用绝对路径
            print(f"✅ 找到本地WikiSQL: {wikisql_path}")
            print(f"✅ 确认evaluate.py存在: {Path(wikisql_path) / 'evaluate.py'}")
            break
    
    if not wikisql_path:
        print("⚠️ 未找到本地WikiSQL数据")
        choice = input("是否继续（将从网络下载）？(y/n): ").strip().lower()
        if choice != 'y':
            return
    
    # 3. 设置参数
    split = input("选择数据分割 (dev/test/train, 默认dev): ").strip() or "dev"
    limit_input = input("限制问题数量 (默认5): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else 5
    
    output_file = f"predictions_{split}_{limit}_{selected_model.replace('-', '_')}.jsonl"
    
    try:
        # 4. 导入并初始化WikiSQL直接LLM查询助手
        print(f"\n🔧 初始化WikiSQL直接LLM查询助手 (使用 {selected_model})...")
        from wikisql_llm_direct import WikiSQLDirectLLM
        
        # 初始化助手
        assistant = WikiSQLDirectLLM(api_key, local_wikisql_path=wikisql_path)
        
        # 如果选择了不同的模型，需要重新配置
        if selected_model != "gemini-2.5-flash":
            print(f"🔄 切换到 {selected_model} 模型...")
            from langchain_openai import ChatOpenAI
            
            base_url = "https://okjtgbhgemzb.eu-central-1.clawcloudrun.com"
            assistant.llm = ChatOpenAI(
                model=selected_model,
                temperature=0,
                base_url=f"{base_url}/v1",
                request_timeout=30,
                verbose=True
            )
        
        # 5. 加载数据集
        print(f"📥 加载WikiSQL数据集 ({split}, 限制: {limit})...")
        assistant.load_wikisql_dataset(split, limit)
        
        # 显示数据集信息
        info = assistant.get_dataset_info()
        print(f"\n📊 数据集信息:")
        print(f"  - 问题数量: {info['questions_count']}")
        print(f"  - 表格数量: {info['tables_count']}")
        print(f"  - 数据库表格: {info['db_tables_count']}")
        
        # 6. 生成预测文件
        print(f"\n🎯 生成预测文件: {output_file}")
        result_file = assistant.generate_predictions_file(output_file, limit)
        
        if result_file:
            print(f"✅ 预测文件生成成功: {result_file}")
            
            # 7. 尝试运行官方评估器（如果可用）
            if wikisql_path:
                print(f"\n🔍 尝试运行官方评估器...")
                try:
                    wikisql_path_obj = Path(wikisql_path)
                    source_file = wikisql_path_obj / "data" / f"{split}.jsonl"
                    db_file = wikisql_path_obj / "data" / f"{split}.db"
                    evaluate_script = wikisql_path_obj / "evaluate.py"
                    
                    if all(f.exists() for f in [source_file, db_file, evaluate_script]):
                        cmd = [
                            sys.executable,
                            str(evaluate_script),
                            str(source_file),
                            str(db_file),
                            str(Path(result_file).absolute())
                        ]
                        
                        print(f"运行命令: {' '.join(cmd)}")
                        print(f"工作目录: {wikisql_path_obj}")
                        result = subprocess.run(cmd, capture_output=True, text=True, 
                                              cwd=str(wikisql_path_obj))
                        
                        if result.returncode == 0:
                            print("✅ 评估结果:")
                            print(result.stdout)
                        else:
                            print(f"❌ 评估失败: {result.stderr}")
                    else:
                        print("⚠️ 缺少评估所需文件，跳过官方评估")
                        
                except Exception as e:
                    print(f"⚠️ 运行官方评估器失败: {e}")
            
            # 8. 使用说明
            print(f"\n💡 使用说明:")
            print(f"预测文件: {result_file}")
            print(f"格式: 每行一个JSON对象")
            print(f"成功: {{\"query\": {{\"sel\": 0, \"agg\": 0, \"conds\": []}}}}")
            print(f"失败: {{\"error\": \"错误信息\"}}")
            
            if wikisql_path:
                print(f"\n手动评估命令:")
                print(f"cd {wikisql_path}")
                abs_result_path = Path(result_file).absolute()
                print(f"python evaluate.py data/{split}.jsonl data/{split}.db \"{abs_result_path}\"")
        else:
            print("❌ 预测文件生成失败")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()