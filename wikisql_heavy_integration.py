#!/usr/bin/env python3
"""
WikiSQL Heavy Integration - 整合Make It Heavy多智能体系统
将Make It Heavy的多智能体分析能力应用于SQL查询生成和验证
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加make-it-heavy到路径
sys.path.append(str(Path(__file__).parent / "make-it-heavy"))

try:
    from orchestrator import TaskOrchestrator
    from agent import OpenRouterAgent
except ImportError as e:
    print(f"❌ 无法导入Make It Heavy模块: {e}")
    print("请确保make-it-heavy项目在正确位置")
    sys.exit(1)

from wikisql_llm_direct import WikiSQLDirectLLM

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikiSQLHeavyAgent:
    """WikiSQL Heavy智能体 - 专门用于SQL查询分析"""
    
    def __init__(self, agent_id: int, config: dict):
        """
        初始化WikiSQL Heavy智能体
        
        Args:
            agent_id: 智能体ID
            config: 配置信息
        """
        self.agent_id = agent_id
        self.config = config
        # 使用Google AI Studio配置
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.agent = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.1,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            request_timeout=60,
            verbose=False
        )
        
        # 定义专门的SQL分析角色
        self.sql_roles = {
            0: "SQL语法专家 - 专注于SQL语法正确性和优化",
            1: "数据分析师 - 专注于查询逻辑和数据理解", 
            2: "性能优化师 - 专注于查询性能和效率",
            3: "结果验证师 - 专注于结果准确性和验证"
        }
        
        self.role = self.sql_roles.get(agent_id, "通用SQL分析师")
        
    def analyze_sql_query(self, question: str, table_info: dict, generated_sql: str) -> dict:
        """
        分析SQL查询
        
        Args:
            question: 自然语言问题
            table_info: 表格信息
            generated_sql: 生成的SQL查询
            
        Returns:
            分析结果
        """
        # 构建专门的SQL分析提示
        analysis_prompt = self._build_sql_analysis_prompt(
            question, table_info, generated_sql
        )
        
        try:
            # 使用智能体进行分析 - 使用ChatOpenAI的invoke方法
            response = self.agent.invoke(analysis_prompt)
            analysis_result = response.content
            
            return {
                "agent_id": self.agent_id,
                "role": self.role,
                "analysis": analysis_result,
                "confidence": self._calculate_confidence(analysis_result),
                "recommendations": self._extract_recommendations(analysis_result)
            }
            
        except Exception as e:
            logger.error(f"智能体 {self.agent_id} 分析失败: {e}")
            return {
                "agent_id": self.agent_id,
                "role": self.role,
                "error": str(e),
                "analysis": None
            }
    
    def _build_sql_analysis_prompt(self, question: str, table_info: dict, sql: str) -> str:
        """构建SQL分析提示词"""
        base_prompt = f"""
作为{self.role}，请分析以下SQL查询：

自然语言问题: {question}

表格信息:
{json.dumps(table_info, indent=2, ensure_ascii=False)}

生成的SQL查询:
{sql}

请从你的专业角度提供详细分析，包括：
"""
        
        # 根据智能体角色添加特定分析要求
        if self.agent_id == 0:  # SQL语法专家
            specific_prompt = """
1. SQL语法正确性检查
2. 语法优化建议
3. 标准SQL兼容性
4. 潜在语法错误识别
"""
        elif self.agent_id == 1:  # 数据分析师
            specific_prompt = """
1. 查询逻辑正确性
2. 数据理解准确性
3. 业务逻辑匹配度
4. 查询结果预期分析
"""
        elif self.agent_id == 2:  # 性能优化师
            specific_prompt = """
1. 查询性能评估
2. 索引使用建议
3. 查询优化方案
4. 执行效率分析
"""
        else:  # 结果验证师
            specific_prompt = """
1. 结果准确性验证
2. 边界条件检查
3. 异常情况处理
4. 结果可靠性评估
"""
        
        return base_prompt + specific_prompt + "\n请提供具体、可操作的分析和建议。"
    
    def _calculate_confidence(self, analysis: str) -> float:
        """计算分析置信度"""
        if not analysis:
            return 0.0
        
        # 简单的置信度计算（可以改进）
        confidence_keywords = [
            "正确", "准确", "优秀", "完美", "符合",
            "建议", "推荐", "应该", "可以", "需要"
        ]
        
        keyword_count = sum(1 for keyword in confidence_keywords if keyword in analysis)
        return min(keyword_count / len(confidence_keywords), 1.0)
    
    def _extract_recommendations(self, analysis: str) -> List[str]:
        """提取建议"""
        if not analysis:
            return []
        
        recommendations = []
        lines = analysis.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ["建议", "推荐", "应该", "需要", "可以"]):
                if len(line) > 10:  # 过滤太短的行
                    recommendations.append(line)
        
        return recommendations[:5]  # 最多返回5个建议

class WikiSQLHeavyOrchestrator:
    """WikiSQL Heavy编排器 - 协调多个智能体进行SQL分析"""
    
    def __init__(self, config_path: str = "make-it-heavy/config.yaml"):
        """
        初始化Heavy编排器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.num_agents = 4  # 使用4个专门的SQL分析智能体
        
        # 初始化智能体
        self.agents = []
        for i in range(self.num_agents):
            agent = WikiSQLHeavyAgent(i, self.config)
            self.agents.append(agent)
        
        logger.info(f"初始化了 {self.num_agents} 个WikiSQL Heavy智能体")
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 返回默认配置 - 使用与WikiSQL相同的端点
            return {
                'openrouter': {
                    'api_key': os.getenv('GOOGLE_API_KEY', ''),
                    'model': 'gemini-2.5-flash',
                    'base_url': 'https://aistudio.google.com/v1'
                }
            }
    
    def heavy_sql_analysis(self, question: str, table_info: dict, generated_sql: str) -> dict:
        """
        执行Heavy SQL分析
        
        Args:
            question: 自然语言问题
            table_info: 表格信息
            generated_sql: 生成的SQL查询
            
        Returns:
            综合分析结果
        """
        logger.info("开始Heavy SQL分析...")
        
        # 并行执行多智能体分析
        agent_results = []
        
        for agent in self.agents:
            logger.info(f"智能体 {agent.agent_id} ({agent.role}) 开始分析...")
            result = agent.analyze_sql_query(question, table_info, generated_sql)
            agent_results.append(result)
        
        # 综合分析结果
        synthesis = self._synthesize_results(agent_results)
        
        return {
            "question": question,
            "generated_sql": generated_sql,
            "agent_analyses": agent_results,
            "synthesis": synthesis,
            "overall_confidence": synthesis.get("confidence", 0.0),
            "final_recommendations": synthesis.get("recommendations", [])
        }
    
    def _synthesize_results(self, agent_results: List[dict]) -> dict:
        """综合多个智能体的分析结果"""
        # 收集所有建议
        all_recommendations = []
        total_confidence = 0.0
        valid_analyses = 0
        
        for result in agent_results:
            if result.get("analysis") and not result.get("error"):
                all_recommendations.extend(result.get("recommendations", []))
                total_confidence += result.get("confidence", 0.0)
                valid_analyses += 1
        
        # 计算平均置信度
        avg_confidence = total_confidence / valid_analyses if valid_analyses > 0 else 0.0
        
        # 去重和排序建议
        unique_recommendations = list(set(all_recommendations))
        
        # 生成综合评估
        synthesis_summary = self._generate_synthesis_summary(agent_results)
        
        return {
            "confidence": avg_confidence,
            "recommendations": unique_recommendations[:10],  # 最多10个建议
            "summary": synthesis_summary,
            "valid_analyses": valid_analyses,
            "total_agents": len(agent_results)
        }
    
    def _generate_synthesis_summary(self, agent_results: List[dict]) -> str:
        """生成综合评估摘要"""
        successful_analyses = [r for r in agent_results if not r.get("error")]
        failed_analyses = [r for r in agent_results if r.get("error")]
        
        summary_parts = []
        
        if successful_analyses:
            summary_parts.append(f"✅ {len(successful_analyses)} 个智能体成功完成分析")
            
            # 按角色总结
            for result in successful_analyses:
                role = result.get("role", "未知角色")
                confidence = result.get("confidence", 0.0)
                summary_parts.append(f"  - {role}: 置信度 {confidence:.2f}")
        
        if failed_analyses:
            summary_parts.append(f"❌ {len(failed_analyses)} 个智能体分析失败")
        
        return "\n".join(summary_parts)

class WikiSQLDirectLLMHeavy(WikiSQLDirectLLM):
    """增强版WikiSQL直接LLM查询助手 - 集成Heavy分析"""
    
    def __init__(self, *args, **kwargs):
        """初始化增强版助手"""
        super().__init__(*args, **kwargs)
        
        # 初始化Heavy编排器
        try:
            self.heavy_orchestrator = WikiSQLHeavyOrchestrator()
            self.heavy_enabled = True
            logger.info("✅ Heavy模式已启用")
        except Exception as e:
            logger.warning(f"⚠️ Heavy模式初始化失败: {e}")
            self.heavy_orchestrator = None
            self.heavy_enabled = False
    
    def generate_sql_with_heavy_analysis(self, question: str, table_id: str) -> dict:
        """
        生成SQL并进行Heavy分析
        
        Args:
            question: 自然语言问题
            table_id: 表格ID
            
        Returns:
            包含Heavy分析的结果
        """
        # 1. 生成基础SQL
        basic_sql = self.generate_sql(question, table_id)
        
        result = {
            "question": question,
            "table_id": table_id,
            "basic_sql": basic_sql,
            "heavy_analysis": None,
            "heavy_enabled": self.heavy_enabled
        }
        
        # 2. 如果Heavy模式可用，进行深度分析
        if self.heavy_enabled and basic_sql:
            try:
                table_info = self._get_table_info_for_heavy(table_id)
                heavy_analysis = self.heavy_orchestrator.heavy_sql_analysis(
                    question, table_info, basic_sql
                )
                result["heavy_analysis"] = heavy_analysis
                
                logger.info(f"✅ Heavy分析完成，置信度: {heavy_analysis.get('overall_confidence', 0.0):.2f}")
                
            except Exception as e:
                logger.error(f"❌ Heavy分析失败: {e}")
                result["heavy_error"] = str(e)
        
        return result
    
    def _get_table_info_for_heavy(self, table_id: str) -> dict:
        """获取表格信息用于Heavy分析"""
        if table_id not in self.current_tables:
            return {}
        
        table = self.current_tables[table_id]
        
        return {
            "table_id": table_id,
            "headers": table.header,
            "types": table.types,
            "sample_rows": table.rows[:3] if table.rows else [],
            "total_rows": len(table.rows),
            "db_table_name": self.current_table_mapping.get(table_id, "unknown")
        }
    
    def query_with_heavy(self, question: str, table_id: Optional[str] = None) -> dict:
        """
        执行带Heavy分析的查询
        
        Args:
            question: 自然语言问题
            table_id: 表格ID
            
        Returns:
            查询结果和Heavy分析
        """
        # 推断table_id（如果未提供）
        if not table_id and self.current_questions:
            for q in self.current_questions:
                if question.lower() in q.question.lower():
                    table_id = q.table_id
                    break
            if not table_id:
                table_id = self.current_questions[0].table_id
        
        if not table_id:
            return {"error": "无法确定表格ID"}
        
        # 生成SQL和Heavy分析
        heavy_result = self.generate_sql_with_heavy_analysis(question, table_id)
        
        # 执行SQL获取结果
        if heavy_result.get("basic_sql"):
            try:
                query_result = self.execute_sql(heavy_result["basic_sql"])
                heavy_result["query_result"] = query_result
            except Exception as e:
                heavy_result["query_error"] = str(e)
        
        return heavy_result

def single_question_test(assistant):
    """单个问题详细测试"""
    if not assistant.current_questions:
        print("❌ 没有可测试的问题")
        return
    
    test_question = assistant.current_questions[0].question
    print(f"\n📝 测试问题: {test_question}")
    print(f"📋 表格ID: {assistant.current_questions[0].table_id}")
    
    # 执行Heavy查询
    print("\n🧠 执行Heavy分析...")
    heavy_result = assistant.query_with_heavy(test_question)
    
    # 显示详细结果
    print("\n" + "=" * 80)
    print("🔍 HEAVY分析详细结果")
    print("=" * 80)
    
    if heavy_result.get("heavy_analysis"):
        analysis = heavy_result["heavy_analysis"]
        synthesis = analysis.get("synthesis", {})
        
        print(f"📊 总体置信度: {analysis.get('overall_confidence', 0.0):.3f}")
        print(f"🤖 有效分析: {synthesis.get('valid_analyses', 0)}/{synthesis.get('total_agents', 0)} 个智能体")
        
        # 显示各智能体分析
        print(f"\n🔍 各智能体分析结果:")
        for i, agent_result in enumerate(analysis.get("agent_analyses", []), 1):
            role = agent_result.get("role", "未知角色")
            confidence = agent_result.get("confidence", 0.0)
            error = agent_result.get("error")
            
            if error:
                print(f"  {i}. ❌ {role}: 分析失败 - {error}")
            else:
                print(f"  {i}. ✅ {role}: 置信度 {confidence:.3f}")
                
                # 显示建议
                recommendations = agent_result.get("recommendations", [])
                if recommendations:
                    print(f"     💡 建议: {recommendations[0][:60]}...")
        
        # 显示最终建议
        final_recommendations = analysis.get('final_recommendations', [])
        if final_recommendations:
            print(f"\n💡 最终建议 (前5个):")
            for i, rec in enumerate(final_recommendations[:5], 1):
                print(f"  {i}. {rec}")
        
        # 显示综合摘要
        summary = synthesis.get("summary", "")
        if summary:
            print(f"\n📋 综合摘要:")
            print(f"  {summary}")
    
    # 显示SQL和查询结果
    basic_sql = heavy_result.get("basic_sql", "")
    if basic_sql:
        print(f"\n💻 生成的SQL: {basic_sql}")
    
    query_result = heavy_result.get("query_result")
    if query_result is not None:
        print(f"📊 查询结果: {query_result}")
    
    query_error = heavy_result.get("query_error")
    if query_error:
        print(f"❌ 查询错误: {query_error}")

def batch_test(assistant, limit):
    """批量测试"""
    if not assistant.current_questions:
        print("❌ 没有可测试的问题")
        return
    
    print(f"⚡ 开始批量测试 {len(assistant.current_questions)} 个问题...")
    
    results = []
    success_count = 0
    error_count = 0
    total_confidence = 0.0
    
    for i, question in enumerate(assistant.current_questions):
        print(f"\n处理问题 {i+1}/{len(assistant.current_questions)}: {question.question[:50]}...")
        
        try:
            heavy_result = assistant.query_with_heavy(question.question)
            
            if heavy_result.get("heavy_analysis"):
                analysis = heavy_result["heavy_analysis"]
                confidence = analysis.get('overall_confidence', 0.0)
                total_confidence += confidence
                success_count += 1
                
                result = {
                    "question_id": i,
                    "question": question.question,
                    "confidence": confidence,
                    "sql": heavy_result.get("basic_sql", ""),
                    "result": heavy_result.get("query_result"),
                    "status": "success"
                }
                print(f"  ✅ 成功 - 置信度: {confidence:.3f}")
            else:
                error_count += 1
                result = {
                    "question_id": i,
                    "question": question.question,
                    "error": heavy_result.get("heavy_error", "Unknown error"),
                    "status": "error"
                }
                print(f"  ❌ 失败")
            
            results.append(result)
            
        except Exception as e:
            error_count += 1
            print(f"  ❌ 异常: {e}")
            results.append({
                "question_id": i,
                "question": question.question,
                "error": str(e),
                "status": "exception"
            })
    
    # 显示批量测试统计
    print(f"\n" + "=" * 60)
    print(f"📊 批量测试统计结果")
    print(f"=" * 60)
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {error_count}")
    print(f"📈 成功率: {success_count/(success_count+error_count)*100:.1f}%")
    
    if success_count > 0:
        avg_confidence = total_confidence / success_count
        print(f"🎯 平均置信度: {avg_confidence:.3f}")
    
    # 保存结果到文件
    output_file = f"heavy_batch_test_results_{len(assistant.current_questions)}.json"
    try:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 详细结果已保存到: {output_file}")
    except Exception as e:
        print(f"⚠️ 保存结果失败: {e}")

def comparison_test(assistant, limit):
    """对比测试：标准查询 vs Heavy查询"""
    if not assistant.current_questions:
        print("❌ 没有可测试的问题")
        return
    
    print(f"⚖️ 开始对比测试 {min(limit, len(assistant.current_questions))} 个问题...")
    
    comparison_results = []
    
    for i, question in enumerate(assistant.current_questions[:limit]):
        print(f"\n问题 {i+1}: {question.question[:60]}...")
        
        try:
            # 标准查询
            print("  📝 执行标准查询...")
            standard_sql = assistant.generate_sql(question.question, question.table_id)
            standard_result = assistant.execute_sql(standard_sql) if standard_sql else "SQL生成失败"
            
            # Heavy查询
            print("  🧠 执行Heavy查询...")
            heavy_result = assistant.query_with_heavy(question.question)
            heavy_sql = heavy_result.get("basic_sql", "")
            heavy_query_result = heavy_result.get("query_result", "查询失败")
            heavy_confidence = 0.0
            
            if heavy_result.get("heavy_analysis"):
                heavy_confidence = heavy_result["heavy_analysis"].get('overall_confidence', 0.0)
            
            # 比较结果
            results_match = str(standard_result) == str(heavy_query_result)
            sql_match = standard_sql.strip() == heavy_sql.strip()
            
            comparison = {
                "question_id": i,
                "question": question.question,
                "standard_sql": standard_sql,
                "heavy_sql": heavy_sql,
                "standard_result": standard_result,
                "heavy_result": heavy_query_result,
                "heavy_confidence": heavy_confidence,
                "sql_match": sql_match,
                "results_match": results_match,
                "status": "success"
            }
            
            print(f"    SQL匹配: {'✅' if sql_match else '❌'}")
            print(f"    结果匹配: {'✅' if results_match else '❌'}")
            print(f"    Heavy置信度: {heavy_confidence:.3f}")
            
        except Exception as e:
            print(f"  ❌ 对比测试异常: {e}")
            comparison = {
                "question_id": i,
                "question": question.question,
                "error": str(e),
                "status": "error"
            }
        
        comparison_results.append(comparison)
    
    # 统计对比结果
    successful_comparisons = [r for r in comparison_results if r.get("status") == "success"]
    sql_matches = sum(1 for r in successful_comparisons if r.get("sql_match", False))
    result_matches = sum(1 for r in successful_comparisons if r.get("results_match", False))
    
    print(f"\n" + "=" * 60)
    print(f"⚖️ 对比测试统计")
    print(f"=" * 60)
    print(f"📊 成功对比: {len(successful_comparisons)}/{len(comparison_results)}")
    
    if successful_comparisons:
        print(f"🔍 SQL匹配率: {sql_matches}/{len(successful_comparisons)} ({sql_matches/len(successful_comparisons)*100:.1f}%)")
        print(f"📊 结果匹配率: {result_matches}/{len(successful_comparisons)} ({result_matches/len(successful_comparisons)*100:.1f}%)")
        
        avg_confidence = sum(r.get("heavy_confidence", 0) for r in successful_comparisons) / len(successful_comparisons)
        print(f"🎯 Heavy平均置信度: {avg_confidence:.3f}")
    
    # 保存对比结果
    output_file = f"comparison_test_results_{len(comparison_results)}.json"
    try:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, ensure_ascii=False, indent=2)
        print(f"💾 对比结果已保存到: {output_file}")
    except Exception as e:
        print(f"⚠️ 保存对比结果失败: {e}")

def validate_prediction(prediction, question_idx, source_file, db_file, temp_predictions_file):
    """验证单个预测结果"""
    try:
        # 写入临时预测文件
        with open(temp_predictions_file, 'w', encoding='utf-8') as f:
            import json
            f.write(json.dumps(prediction, ensure_ascii=False) + '\n')
        
        # 创建验证器
        from wikisql_validator import WikiSQLValidator
        validator = WikiSQLValidator(source_file, db_file, temp_predictions_file)
        
        # 执行验证
        summary = validator.evaluate()
        
        # 返回验证结果
        is_correct = summary['correct_answers'] > 0
        return {
            "is_correct": is_correct,
            "accuracy": summary['accuracy'],
            "error_info": summary.get('error_info', ''),
            "total_questions": summary['total_questions']
        }
        
    except Exception as e:
        return {
            "is_correct": False,
            "accuracy": 0.0,
            "error_info": f"验证失败: {str(e)}",
            "total_questions": 1
        }

def single_question_test_with_validation(assistant, source_file, db_file, temp_predictions_file, use_heavy=True):
    """带验证的单个问题详细测试"""
    if not assistant.current_questions:
        print("❌ 没有可测试的问题")
        return
    
    question = assistant.current_questions[0]
    print(f"\n📝 测试问题: {question.question}")
    print(f"📋 表格ID: {question.table_id}")
    
    try:
        if use_heavy:
            # Heavy查询
            print("\n🧠 执行Heavy分析...")
            heavy_result = assistant.query_with_heavy(question.question)
            
            # 生成WikiSQL格式预测
            if heavy_result.get("basic_sql"):
                wikisql_prediction = assistant._parse_sql_to_wikisql_format(
                    heavy_result["basic_sql"], question
                )
                if wikisql_prediction:
                    prediction = {"query": wikisql_prediction}
                else:
                    prediction = {"error": "SQL解析失败"}
            else:
                prediction = {"error": "SQL生成失败"}
            
            # 显示Heavy分析结果
            if heavy_result.get("heavy_analysis"):
                analysis = heavy_result["heavy_analysis"]
                print(f"📊 Heavy置信度: {analysis.get('overall_confidence', 0.0):.3f}")
                print(f"🤖 有效智能体: {analysis.get('synthesis', {}).get('valid_analyses', 0)}/4")
        else:
            # 标准查询
            print("\n📝 执行标准查询...")
            prediction = assistant.generate_wikisql_prediction(0)
        
        # 验证结果
        print("\n🔍 验证预测结果...")
        validation_result = validate_prediction(prediction, 0, source_file, db_file, temp_predictions_file)
        
        # 显示验证结果
        print("\n" + "=" * 60)
        print("🎯 验证结果")
        print("=" * 60)
        print(f"✅ 正确性: {'正确' if validation_result['is_correct'] else '错误'}")
        print(f"📊 准确率: {validation_result['accuracy']:.3f}")
        
        if not validation_result['is_correct']:
            print(f"❌ 错误信息: {validation_result['error_info']}")
        
        # 显示预测内容
        print(f"\n💻 预测结果:")
        if "query" in prediction:
            query = prediction["query"]
            print(f"  SELECT: col{query.get('sel', 0)}")
            print(f"  AGG: {query.get('agg', 0)}")
            print(f"  CONDITIONS: {query.get('conds', [])}")
        else:
            print(f"  错误: {prediction.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def batch_test_with_validation(assistant, limit, source_file, db_file, temp_predictions_file, use_heavy=True):
    """带验证的批量测试"""
    if not assistant.current_questions:
        print("❌ 没有可测试的问题")
        return
    
    mode_name = "Heavy" if use_heavy else "标准"
    print(f"⚡ 开始{mode_name}批量测试 {len(assistant.current_questions)} 个问题...")
    
    predictions = []
    results = []
    correct_count = 0
    error_count = 0
    
    for i, question in enumerate(assistant.current_questions):
        print(f"\n处理问题 {i+1}/{len(assistant.current_questions)}: {question.question[:50]}...")
        
        try:
            if use_heavy:
                # Heavy查询
                heavy_result = assistant.query_with_heavy(question.question)
                if heavy_result.get("basic_sql"):
                    wikisql_prediction = assistant._parse_sql_to_wikisql_format(
                        heavy_result["basic_sql"], question
                    )
                    if wikisql_prediction:
                        prediction = {"query": wikisql_prediction}
                        confidence = heavy_result.get("heavy_analysis", {}).get('overall_confidence', 0.0)
                    else:
                        prediction = {"error": "SQL解析失败"}
                        confidence = 0.0
                else:
                    prediction = {"error": "SQL生成失败"}
                    confidence = 0.0
            else:
                # 标准查询
                prediction = assistant.generate_wikisql_prediction(i)
                confidence = 1.0  # 标准查询没有置信度
            
            predictions.append(prediction)
            
            # 验证结果
            validation_result = validate_prediction(prediction, i, source_file, db_file, temp_predictions_file)
            
            if validation_result['is_correct']:
                correct_count += 1
                print(f"  ✅ 正确")
            else:
                error_count += 1
                print(f"  ❌ 错误")
            
            result = {
                "question_id": i,
                "question": question.question,
                "prediction": prediction,
                "is_correct": validation_result['is_correct'],
                "confidence": confidence if use_heavy else None,
                "validation_accuracy": validation_result['accuracy']
            }
            results.append(result)
            
        except Exception as e:
            error_count += 1
            print(f"  ❌ 异常: {e}")
            predictions.append({"error": str(e)})
            results.append({
                "question_id": i,
                "question": question.question,
                "error": str(e),
                "is_correct": False
            })
    
    # 保存所有预测到文件进行最终验证
    final_predictions_file = f"{mode_name.lower()}_predictions_{len(assistant.current_questions)}.jsonl"
    with open(final_predictions_file, 'w', encoding='utf-8') as f:
        for prediction in predictions:
            import json
            f.write(json.dumps(prediction, ensure_ascii=False) + '\n')
    
    # 最终验证
    print(f"\n🔍 执行最终批量验证...")
    try:
        from wikisql_validator import WikiSQLValidator
        validator = WikiSQLValidator(source_file, db_file, final_predictions_file)
        final_summary = validator.evaluate()
        
        print(f"\n" + "=" * 60)
        print(f"📊 {mode_name}批量测试最终结果")
        print(f"=" * 60)
        print(f"✅ 正确答案: {final_summary['correct_answers']}")
        print(f"❌ 错误答案: {final_summary['errors']}")
        print(f"📈 最终准确率: {final_summary['accuracy']:.3f} ({final_summary['accuracy']*100:.1f}%)")
        print(f"📊 总问题数: {final_summary['total_questions']}")
        
        if use_heavy and results:
            # 计算Heavy模式的平均置信度
            heavy_results = [r for r in results if r.get('confidence') is not None]
            if heavy_results:
                avg_confidence = sum(r['confidence'] for r in heavy_results) / len(heavy_results)
                print(f"🎯 平均Heavy置信度: {avg_confidence:.3f}")
        
    except Exception as e:
        print(f"❌ 最终验证失败: {e}")
    
    # 保存详细结果
    output_file = f"{mode_name.lower()}_batch_results_{len(assistant.current_questions)}.json"
    try:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 详细结果已保存到: {output_file}")
        print(f"💾 预测文件已保存到: {final_predictions_file}")
    except Exception as e:
        print(f"⚠️ 保存结果失败: {e}")

def comparison_test_with_validation(assistant, limit, source_file, db_file, temp_predictions_file):
    """带验证的对比测试"""
    if not assistant.current_questions:
        print("❌ 没有可测试的问题")
        return
    
    print(f"⚖️ 开始对比测试 {min(limit, len(assistant.current_questions))} 个问题...")
    
    standard_predictions = []
    heavy_predictions = []
    comparison_results = []
    
    for i, question in enumerate(assistant.current_questions[:limit]):
        print(f"\n问题 {i+1}: {question.question[:60]}...")
        
        try:
            # 标准查询
            print("  📝 执行标准查询...")
            standard_prediction = assistant.generate_wikisql_prediction(i)
            standard_predictions.append(standard_prediction)
            
            # 验证标准查询
            standard_validation = validate_prediction(standard_prediction, i, source_file, db_file, temp_predictions_file)
            
            # Heavy查询
            print("  🧠 执行Heavy查询...")
            heavy_result = assistant.query_with_heavy(question.question)
            
            if heavy_result.get("basic_sql"):
                wikisql_prediction = assistant._parse_sql_to_wikisql_format(
                    heavy_result["basic_sql"], question
                )
                if wikisql_prediction:
                    heavy_prediction = {"query": wikisql_prediction}
                else:
                    heavy_prediction = {"error": "SQL解析失败"}
            else:
                heavy_prediction = {"error": "SQL生成失败"}
            
            heavy_predictions.append(heavy_prediction)
            
            # 验证Heavy查询
            heavy_validation = validate_prediction(heavy_prediction, i, source_file, db_file, temp_predictions_file)
            
            # 获取Heavy置信度
            heavy_confidence = 0.0
            if heavy_result.get("heavy_analysis"):
                heavy_confidence = heavy_result["heavy_analysis"].get('overall_confidence', 0.0)
            
            comparison = {
                "question_id": i,
                "question": question.question,
                "standard_prediction": standard_prediction,
                "heavy_prediction": heavy_prediction,
                "standard_correct": standard_validation['is_correct'],
                "heavy_correct": heavy_validation['is_correct'],
                "heavy_confidence": heavy_confidence,
                "standard_accuracy": standard_validation['accuracy'],
                "heavy_accuracy": heavy_validation['accuracy']
            }
            
            print(f"    标准查询: {'✅' if standard_validation['is_correct'] else '❌'}")
            print(f"    Heavy查询: {'✅' if heavy_validation['is_correct'] else '❌'} (置信度: {heavy_confidence:.3f})")
            
        except Exception as e:
            print(f"  ❌ 对比测试异常: {e}")
            comparison = {
                "question_id": i,
                "question": question.question,
                "error": str(e)
            }
        
        comparison_results.append(comparison)
    
    # 保存预测文件并进行最终验证
    standard_file = f"standard_predictions_comparison_{limit}.jsonl"
    heavy_file = f"heavy_predictions_comparison_{limit}.jsonl"
    
    with open(standard_file, 'w', encoding='utf-8') as f:
        for pred in standard_predictions:
            import json
            f.write(json.dumps(pred, ensure_ascii=False) + '\n')
    
    with open(heavy_file, 'w', encoding='utf-8') as f:
        for pred in heavy_predictions:
            import json
            f.write(json.dumps(pred, ensure_ascii=False) + '\n')
    
    # 最终验证
    print(f"\n🔍 执行最终对比验证...")
    try:
        from wikisql_validator import WikiSQLValidator
        
        # 验证标准查询
        standard_validator = WikiSQLValidator(source_file, db_file, standard_file)
        standard_summary = standard_validator.evaluate()
        
        # 验证Heavy查询
        heavy_validator = WikiSQLValidator(source_file, db_file, heavy_file)
        heavy_summary = heavy_validator.evaluate()
        
        print(f"\n" + "=" * 60)
        print(f"⚖️ 对比测试最终结果")
        print(f"=" * 60)
        print(f"📝 标准查询准确率: {standard_summary['accuracy']:.3f} ({standard_summary['accuracy']*100:.1f}%)")
        print(f"🧠 Heavy查询准确率: {heavy_summary['accuracy']:.3f} ({heavy_summary['accuracy']*100:.1f}%)")
        
        improvement = heavy_summary['accuracy'] - standard_summary['accuracy']
        print(f"📈 Heavy改进: {improvement:+.3f} ({improvement*100:+.1f}%)")
        
        # Heavy置信度统计
        successful_comparisons = [r for r in comparison_results if 'error' not in r]
        if successful_comparisons:
            avg_confidence = sum(r.get('heavy_confidence', 0) for r in successful_comparisons) / len(successful_comparisons)
            print(f"🎯 Heavy平均置信度: {avg_confidence:.3f}")
        
    except Exception as e:
        print(f"❌ 最终验证失败: {e}")
    
    # 保存对比结果
    output_file = f"comparison_results_validated_{limit}.json"
    try:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, ensure_ascii=False, indent=2)
        print(f"💾 对比结果已保存到: {output_file}")
        print(f"💾 标准预测文件: {standard_file}")
        print(f"💾 Heavy预测文件: {heavy_file}")
    except Exception as e:
        print(f"⚠️ 保存对比结果失败: {e}")

def main():
    """测试WikiSQL Heavy集成"""
    print("🚀 WikiSQL Heavy Integration 测试")
    print("=" * 60)
    
    # 获取API密钥
    api_key = input("请输入你的Google AI Studio API密钥: ").strip()
    if not api_key:
        print("❌ 需要提供API密钥")
        return
    
    # 首先选择查询模式
    print("\n🎯 选择查询模式:")
    print("1. 标准LLM查询 (单一LLM生成SQL)")
    print("2. Heavy多智能体查询 (4个智能体协作分析)")
    print("3. 对比模式 (标准 vs Heavy 对比测试)")
    
    query_mode = input("请选择查询模式 (1/2/3, 默认 1): ").strip()
    
    if query_mode == "2":
        mode_type = "heavy"
        print("✅ 已选择: Heavy多智能体查询")
    elif query_mode == "3":
        mode_type = "comparison"
        print("✅ 已选择: 对比模式")
    else:
        mode_type = "standard"
        print("✅ 已选择: 标准LLM查询")
    
    # 选择数据分割
    print("\n📋 选择数据分割:")
    print("1. dev (验证集, 推荐)")
    print("2. test (测试集)")
    print("3. train (训练集)")
    
    split_choice = input("请选择数据分割 (1/2/3, 默认 1): ").strip()
    if split_choice == "2":
        split = "test"
    elif split_choice == "3":
        split = "train"
    else:
        split = "dev"
    
    print(f"✅ 已选择数据分割: {split}")
    
    # 选择测试数据量
    print(f"\n📋 选择测试数据量:")
    print("1. 小规模测试 (3 个问题)")
    print("2. 中等测试 (10 个问题)")
    print("3. 大规模测试 (50 个问题)")
    print("4. 自定义数量")
    
    limit_choice = input("请选择测试规模 (1/2/3/4, 默认 1): ").strip()
    
    if limit_choice == "2":
        limit = 10
    elif limit_choice == "3":
        limit = 50
    elif limit_choice == "4":
        custom_limit = input("请输入自定义数量: ").strip()
        try:
            limit = int(custom_limit)
            if limit <= 0:
                print("❌ 数量必须大于0，使用默认值3")
                limit = 3
        except ValueError:
            print("❌ 输入无效，使用默认值3")
            limit = 3
    else:
        limit = 3
    
    print(f"✅ 已选择测试数量: {limit} 个问题")
    
    # 根据查询模式选择测试方式
    if mode_type == "comparison":
        test_mode = "comparison"
        print(f"\n📋 对比模式将同时测试标准查询和Heavy查询")
    else:
        print(f"\n📋 选择测试方式:")
        print("1. 单个问题详细测试 (显示完整分析过程)")
        print("2. 批量测试 (快速处理多个问题)")
        
        test_choice = input("请选择测试方式 (1/2, 默认 1): ").strip()
        test_mode = "batch" if test_choice == "2" else "single"
    
    try:
        # 根据模式初始化助手
        if mode_type == "heavy" or mode_type == "comparison":
            print(f"\n🔧 初始化WikiSQL Heavy助手...")
            assistant = WikiSQLDirectLLMHeavy(api_key)
        else:
            print(f"\n🔧 初始化标准WikiSQL助手...")
            from wikisql_llm_direct import WikiSQLDirectLLM
            assistant = WikiSQLDirectLLM(api_key)
        
        # 加载数据集
        print(f"📥 加载WikiSQL数据集 ({split}, 限制: {limit})...")
        assistant.load_wikisql_dataset(split, limit)
        
        # 初始化WikiSQL验证器
        print(f"🔧 初始化WikiSQL验证器...")
        from wikisql_validator import WikiSQLValidator
        
        # 构建验证器所需的文件路径
        wikisql_data_path = assistant.data_loader.local_wikisql_path or "WikiSQL"
        source_file = f"{wikisql_data_path}/data/{split}.jsonl"
        db_file = f"{wikisql_data_path}/data/{split}.db"
        
        # 创建临时预测文件用于验证
        temp_predictions_file = f"temp_predictions_{split}.jsonl"
        
        # 显示数据集信息
        info = assistant.get_dataset_info()
        print(f"\n📊 数据集信息:")
        print(f"  - 问题数量: {info['questions_count']}")
        print(f"  - 表格数量: {info['tables_count']}")
        print(f"  - 数据库表格: {info['db_tables_count']}")
        
        # 根据选择的模式和测试方式执行测试
        if mode_type == "comparison":
            # 对比模式
            print(f"\n⚖️ 执行对比测试...")
            comparison_test_with_validation(assistant, min(10, limit), source_file, db_file, temp_predictions_file)
            
        elif test_mode == "batch":
            # 批量测试
            print(f"\n⚡ 执行批量测试...")
            if mode_type == "heavy":
                batch_test_with_validation(assistant, limit, source_file, db_file, temp_predictions_file, use_heavy=True)
            else:
                batch_test_with_validation(assistant, limit, source_file, db_file, temp_predictions_file, use_heavy=False)
                
        else:
            # 单个问题详细测试
            print(f"\n🔍 执行单个问题详细测试...")
            if mode_type == "heavy":
                single_question_test_with_validation(assistant, source_file, db_file, temp_predictions_file, use_heavy=True)
            else:
                single_question_test_with_validation(assistant, source_file, db_file, temp_predictions_file, use_heavy=False)
        
        print("\n✅ Heavy集成测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()