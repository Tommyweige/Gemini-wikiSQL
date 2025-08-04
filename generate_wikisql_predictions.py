#!/usr/bin/env python3
"""
WikiSQL智能查询系统主程序
支持基础查询和Heavy多智能体分析
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def main():
    """Main function - WikiSQL complete functionality entry point"""
    print("🚀 WikiSQL Intelligent Query System")
    print("=" * 60)
    print("Supporting basic queries and Heavy multi-agent analysis")
    print("=" * 60)
    
    # Step 1: Get API key
    print("\n📋 Step 1: API Key Configuration")
    api_key = input("Please enter your API key: ").strip()
    if not api_key:
        print("❌ API key is required")
        return
    print("✅ API key configured")
    
    # Step 2: Select model
    print("\n📋 Step 2: Model Selection")
    print("1. Gemini 2.5 Flash (Recommended, fast)")
    print("2. Gemma 3 27B IT (High precision)")
    
    model_choice = input("Please select model (1/2, default 1): ").strip()
    if model_choice == "2":
        selected_model = "gemma-3-27b-it"
        print("✅ Selected: Gemma 3 27B IT")
    else:
        selected_model = "gemini-2.5-flash"
        print("✅ Selected: Gemini 2.5 Flash")
    
    # Step 3: Select data split
    print("\n📋 Step 3: Data Split Selection")
    print("1. dev (validation set, recommended)")
    print("2. test (test set)")
    print("3. train (training set)")
    
    split_choice = input("Please select data split (1/2/3, default 1): ").strip()
    if split_choice == "2":
        split = "test"
    elif split_choice == "3":
        split = "train"
    else:
        split = "dev"
    
    print(f"✅ Selected data split: {split}")
    
    # Step 4: Set question limit
    print(f"\n📋 Step 4: Question Limit Configuration")
    limit_input = input("Please enter number of questions to process (default 100): ").strip()
    try:
        limit = int(limit_input) if limit_input else 100
    except ValueError:
        limit = 100
    
    print(f"✅ Question limit: {limit}")
    
    # Step 5: Select query mode
    print(f"\n📋 Step 5: Query Mode Selection")
    print("1. Standard Query (标准查询, 快速, ~86% 准确率)")
    print("2. Heavy Query (4个并行智能体深度分析, ~84% 准确率)")
    
    query_mode = input("请选择查询模式 (1/2, 默认 1): ").strip()
    use_heavy = query_mode == "2"
    
    if use_heavy:
        print("✅ 已选择: Heavy多智能体查询")
        print("   - 使用4个专门智能体进行深度分析")
        print("   - SQL专家、数据分析师、性能优化师、结果验证师")
    else:
        print("✅ 已选择: 标准查询")
    
    # Detect local WikiSQL data
    print(f"\n🔍 Detecting local WikiSQL data...")
    wikisql_path = None
    possible_paths = ["WikiSQL", "../WikiSQL", "./WikiSQL"]
    
    for path in possible_paths:
        path_obj = Path(path)
        if (path_obj.exists() and 
            (path_obj / "data").exists() and
            (path_obj / "data" / f"{split}.jsonl").exists()):
            wikisql_path = str(path_obj)
            print(f"✅ Found local WikiSQL: {wikisql_path}")
            break
    
    if not wikisql_path:
        print("❌ Local WikiSQL data not found")
        print("Please ensure WikiSQL directory is in current directory")
        return
    
    try:
        # Initialize WikiSQL query assistant
        print(f"\n🔧 初始化WikiSQL查询助手...")
        
        if use_heavy:
            print("🧠 启用Heavy多智能体模式...")
            from wikisql_heavy_simple import WikiSQLDirectLLMSimpleHeavy
            assistant = WikiSQLDirectLLMSimpleHeavy(api_key)
            print("✅ Heavy模式已启用 - 4个专门智能体并行分析")
        else:
            print("⚡ 启用标准查询模式...")
            from wikisql_llm_direct import WikiSQLDirectLLM
            assistant = WikiSQLDirectLLM(api_key)
            print("✅ 标准模式已启用")
        
        # Set local data path
        assistant.data_loader.local_wikisql_path = Path(wikisql_path)
        
        # If different model selected, reconfigure
        if selected_model != "gemini-2.5-flash":
            print(f"🔄 Switching to {selected_model} model...")
            from langchain_openai import ChatOpenAI
            
            base_url = "https://okjtgbhgemzb.eu-central-1.clawcloudrun.com"
            new_llm = ChatOpenAI(
                model=selected_model,
                temperature=0,
                base_url=f"{base_url}/v1",
                request_timeout=30,
                verbose=True
            )
            
            assistant.llm = new_llm
            
            # If Heavy mode, reinitialize Heavy Orchestrator with new model
            if use_heavy and hasattr(assistant, 'heavy_orchestrator'):
                print(f"🔄 重新初始化Heavy智能体使用 {selected_model} 模型...")
                try:
                    from wikisql_heavy_simple import SimpleHeavyOrchestrator
                    assistant.heavy_orchestrator = SimpleHeavyOrchestrator(api_key, selected_model)
                    print(f"✅ Heavy智能体已切换到 {selected_model} 模型")
                except Exception as e:
                    print(f"⚠️ Heavy智能体模型切换失败: {e}")
                    assistant.heavy_enabled = False
        
        # 生成输出文件名
        mode_suffix = "heavy" if use_heavy else "normal"
        output_file = f"predictions_{split}_{limit}_{selected_model.replace('-', '_')}_{mode_suffix}.jsonl"
        
        # 加载数据集
        print(f"\n📥 加载WikiSQL数据集 ({split}, 限制: {limit})...")
        assistant.load_wikisql_dataset(split, limit, force_download=False)
        
        # 显示数据集信息
        info = assistant.get_dataset_info()
        print(f"\n📊 数据集信息:")
        print(f"  - 问题数量: {info['questions_count']}")
        print(f"  - 表格数量: {info['tables_count']}")
        print(f"  - 数据库表格: {info['db_tables_count']}")
        
        # 生成预测
        print(f"\n🎯 开始生成预测...")
        print(f"模式: {'Heavy多智能体分析' if use_heavy else '标准查询'}")
        print(f"输出文件: {output_file}")
        
        predictions = []
        
        for i, question in enumerate(assistant.current_questions):
            print(f"\n处理问题 {i+1}/{len(assistant.current_questions)}:")
            print(f"问题: {question.question[:80]}...")
            
            try:
                if use_heavy:
                    # Heavy mode: Use multi-agent analysis
                    print("🧠 开始Heavy多智能体分析...")
                    
                    heavy_result = assistant.generate_sql_with_heavy_analysis(
                        question.question, 
                        question.table_id
                    )
                    
                    if heavy_result.get("heavy_analysis"):
                        analysis = heavy_result["heavy_analysis"]
                        confidence = analysis.get("overall_confidence", 0.0)
                        print(f"   ✅ Heavy分析完成，置信度: {confidence:.3f}")
                        
                        # 使用Heavy分析改进的SQL，如果没有改进则使用基础SQL
                        improved_sql = analysis.get("improved_sql", "")
                        basic_sql = heavy_result.get("basic_sql", "")
                        final_sql = improved_sql if improved_sql and improved_sql != basic_sql else basic_sql
                        
                        if final_sql:
                            if improved_sql and improved_sql != basic_sql:
                                print(f"   🔧 使用Heavy改进的SQL: {improved_sql[:50]}...")
                            else:
                                print(f"   📝 使用基础SQL: {basic_sql[:50]}...")
                            
                            wikisql_query = assistant._parse_sql_to_wikisql_format(final_sql, question)
                            if wikisql_query:
                                prediction = {
                                    "query": wikisql_query,
                                    "heavy_confidence": confidence,
                                    "heavy_agents": analysis.get("synthesis", {}).get("valid_analyses", 0),
                                    "heavy_improved": improved_sql != basic_sql if improved_sql else False,
                                    "original_sql": basic_sql,
                                    "final_sql": final_sql
                                }
                            else:
                                prediction = {"error": f"SQL parsing failed: {final_sql}"}
                        else:
                            prediction = {"error": "SQL generation failed"}
                    else:
                        prediction = {"error": "Heavy analysis failed"}
                else:
                    # Standard mode: Standard prediction generation
                    prediction = assistant.generate_wikisql_prediction(i)
                    print(f"   ✅ 标准查询完成")
                
                predictions.append(prediction)
                
                # Display progress
                if (i + 1) % 5 == 0:
                    success_count = len([p for p in predictions if "error" not in p])
                    print(f"📊 Progress: {i + 1}/{len(assistant.current_questions)}, Success: {success_count}")
                    
            except Exception as e:
                print(f"   ❌ Processing failed: {e}")
                predictions.append({"error": str(e)})
        
        # Save prediction results
        print(f"\n💾 Saving prediction results to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            for prediction in predictions:
                f.write(json.dumps(prediction, ensure_ascii=False) + '\n')
        
        result_file = output_file
        
        if result_file:
            print(f"✅ Prediction file generated successfully: {result_file}")
            
            # 7. Try running official evaluator
            print(f"\n🔍 Attempting to run official evaluator...")
            
            # Use confirmed existing paths
            evaluate_script = Path("WikiSQL") / "evaluate.py"
            source_file = Path("WikiSQL") / "data" / f"{split}.jsonl"
            db_file = Path("WikiSQL") / "data" / f"{split}.db"
            predictions_file = Path(result_file).absolute()
            
            print(f"📁 Checking files:")
            print(f"  evaluate.py: {'✅' if evaluate_script.exists() else '❌'} {evaluate_script}")
            print(f"  {split}.jsonl: {'✅' if source_file.exists() else '❌'} {source_file}")
            print(f"  {split}.db: {'✅' if db_file.exists() else '❌'} {db_file}")
            print(f"  Prediction file: {'✅' if predictions_file.exists() else '❌'} {predictions_file}")
            
            if evaluate_script.exists() and source_file.exists() and db_file.exists():
                try:
                    cmd = [
                        sys.executable,
                        str(evaluate_script.absolute()),
                        str(source_file.absolute()),
                        str(db_file.absolute()),
                        str(predictions_file)
                    ]
                    
                    print(f"🚀 Running command: {' '.join(cmd)}")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        encoding='utf-8'
                    )
                    
                    if result.returncode == 0:
                        print("✅ Official evaluator ran successfully!")
                        print("📊 Evaluation results:")
                        print(result.stdout)
                    else:
                        print(f"⚠️ Official evaluator failed:")
                        print(f"Error output: {result.stderr}")
                        
                        # Use custom validator as fallback
                        print(f"\n🔄 Using custom validator as fallback...")
                        print(f"Run command: python run_validation.py")
                        
                except subprocess.TimeoutExpired:
                    print("⚠️ Official evaluator timed out")
                    print(f"💡 Can run manually: python run_validation.py")
                except Exception as e:
                    print(f"⚠️ Failed to run official evaluator: {e}")
                    print(f"💡 Can run manually: python run_validation.py")
            else:
                print(f"⚠️ Missing required evaluation files:")
                print(f"💡 Can use custom validator: python run_validation.py")
            
            # 8. Usage instructions
            print(f"\n💡 Usage instructions:")
            print(f"Prediction file: {result_file}")
            print(f"Format: One JSON object per line")
            print(f"Success: {{\"query\": {{\"sel\": 0, \"agg\": 0, \"conds\": []}}}}")
            print(f"Failure: {{\"error\": \"error message\"}}")
            
            if wikisql_path:
                print(f"\nManual evaluation command:")
                print(f"cd {wikisql_path}")
                abs_result_path = Path(result_file).absolute()
                print(f"python evaluate.py data/{split}.jsonl data/{split}.db \"{abs_result_path}\"")
        else:
            print("❌ Prediction file generation failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()