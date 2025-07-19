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
        self.agent = OpenRouterAgent("make-it-heavy/config.yaml", silent=True)
        
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
            # 使用智能体进行分析
            analysis_result = self.agent.run(analysis_prompt)
            
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
            # 返回默认配置
            return {
                'openrouter': {
                    'api_key': os.getenv('OPENROUTER_API_KEY', ''),
                    'model': 'google/gemini-2.5-flash-preview-05-20'
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

def main():
    """测试WikiSQL Heavy集成"""
    print("🚀 WikiSQL Heavy Integration 测试")
    print("=" * 60)
    
    # 获取API密钥
    api_key = input("请输入你的API密钥: ").strip()
    if not api_key:
        print("❌ 需要提供API密钥")
        return
    
    try:
        # 初始化Heavy助手
        print("初始化WikiSQL Heavy助手...")
        assistant = WikiSQLDirectLLMHeavy(api_key)
        
        # 加载数据集
        print("加载WikiSQL数据集...")
        assistant.load_wikisql_dataset("dev", limit=3)
        
        # 测试Heavy查询
        if assistant.current_questions:
            test_question = assistant.current_questions[0].question
            print(f"\n测试问题: {test_question}")
            
            # 执行Heavy查询
            print("执行Heavy分析...")
            heavy_result = assistant.query_with_heavy(test_question)
            
            # 显示结果
            print("\n" + "=" * 60)
            print("Heavy分析结果:")
            print("=" * 60)
            
            if heavy_result.get("heavy_analysis"):
                analysis = heavy_result["heavy_analysis"]
                print(f"置信度: {analysis.get('overall_confidence', 0.0):.2f}")
                print(f"建议数量: {len(analysis.get('final_recommendations', []))}")
                
                print("\n主要建议:")
                for i, rec in enumerate(analysis.get('final_recommendations', [])[:3], 1):
                    print(f"  {i}. {rec}")
            
            if heavy_result.get("query_result"):
                print(f"\n查询结果: {heavy_result['query_result']}")
        
        print("\n✅ Heavy集成测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()