#!/usr/bin/env python3
"""
简化版WikiSQL Heavy集成 - 避免复杂的依赖问题
直接使用OpenAI API进行多智能体分析
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

from wikisql_llm_direct import WikiSQLDirectLLM

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionGenerationAgent:
    """问题生成智能体 - 将用户输入拆解成4个专门的研究问题"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        
        # 初始化LLM
        try:
            from langchain_openai import ChatOpenAI
            base_url = "https://okjtgbhgemzb.eu-central-1.clawcloudrun.com"
            self.client = ChatOpenAI(
                model=self.model,
                temperature=0.1,
                base_url=f"{base_url}/v1",
                request_timeout=30,
                verbose=False
            )
            self.available = True
        except Exception as e:
            logger.warning(f"问题生成智能体初始化失败: {e}")
            self.available = False
    
    def generate_specialized_questions(self, user_question: str, table_info: dict, generated_sql: str) -> List[str]:
        """生成4个专门的研究问题 - 圍繞用戶核心需求"""
        if not self.available:
            return []
        
        prompt = f"""
You are a question generation expert. Create 4 natural language questions based on the original question, using a 1+3 structure: 1 original question + 3 transformed questions from different perspectives.

Original Question: {user_question}
Table Information: {json.dumps(table_info, ensure_ascii=False)}

Requirements:
1. First question: Keep the EXACT original question unchanged
2. Questions 2-4: Transform the original question from different angles while maintaining the same core intent
3. All questions must be natural language questions (NO SQL syntax allowed)
4. All questions must be in English
5. Focus on different aspects: specificity, context, verification

Example transformation patterns:
- Original: "What school did player number 21 play for?"
- Angle 1: "Which educational institution was attended by the athlete wearing jersey number 21?"
- Angle 2: "What is the academic background of the player identified as number 21?"
- Angle 3: "Can you identify the college or university associated with player 21?"

Please output in the following format:
ORIGINAL: {user_question}
SPECIFIC: [More specific version focusing on details and context]
ALTERNATIVE: [Alternative phrasing with different terminology]
VERIFICATION: [Verification-focused version asking for confirmation]
"""
        
        try:
            response = self.client.invoke(prompt)
            return self._parse_questions(response.content, user_question)
        except Exception as e:
            logger.error(f"生成专门问题失败: {e}")
            return []
    
    def _parse_questions(self, response: str, user_question: str) -> List[str]:
        """解析生成的4个问题"""
        questions = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('ORIGINAL:'):
                questions.append(line.replace('ORIGINAL:', '').strip())
            elif line.startswith('SPECIFIC:'):
                questions.append(line.replace('SPECIFIC:', '').strip())
            elif line.startswith('ALTERNATIVE:'):
                questions.append(line.replace('ALTERNATIVE:', '').strip())
            elif line.startswith('VERIFICATION:'):
                questions.append(line.replace('VERIFICATION:', '').strip())
        
        # 如果解析失败，返回默认的1+3结构英文问题
        if len(questions) != 4:
            questions = [
                user_question,  # 保持原始问题
                f"Which specific details can help us better understand the question: '{user_question}'?",
                f"How can we rephrase the question '{user_question}' using different terminology?", 
                f"What evidence would confirm that we correctly answered '{user_question}'?"
            ]
        
        return questions

class SimpleHeavyAgent:
    """简化版Heavy智能体 - 回答专门的研究问题"""
    
    def __init__(self, agent_id: int, api_key: str, model: str = "gemini-2.5-flash"):
        """
        初始化简化版智能体
        
        Args:
            agent_id: 智能体ID
            api_key: API密钥
            model: 使用的模型
        """
        self.agent_id = agent_id
        self.api_key = api_key
        self.model = model
        
        # 定义智能体角色
        self.agent_types = {
            0: "Research Agent - 数据研究专家",
            1: "Analysis Agent - SQL分析专家", 
            2: "Alternatives Agent - 替代方案专家",
            3: "Verification Agent - 验证专家"
        }
        
        self.role = self.agent_types.get(agent_id, "通用分析师")
        
        # 初始化LangChain OpenAI客户端（使用自定义base URL）
        try:
            from langchain_openai import ChatOpenAI
            
            base_url = "https://okjtgbhgemzb.eu-central-1.clawcloudrun.com"
            self.client = ChatOpenAI(
                model=self.model,
                temperature=0.1,
                base_url=f"{base_url}/v1",
                request_timeout=30,
                verbose=False
            )
            self.available = True
        except ImportError:
            logger.warning("langchain-openai库未安装，Heavy功能不可用")
            self.available = False
        except Exception as e:
            logger.warning(f"LLM客户端初始化失败: {e}")
            self.available = False
    
    def answer_specialized_question(self, specialized_question: str, user_question: str, table_info: dict, generated_sql: str) -> dict:
        """
        回答专门的研究问题
        
        Args:
            specialized_question: 专门的研究问题
            user_question: 用户原始问题
            table_info: 表格信息
            generated_sql: 生成的SQL查询
            
        Returns:
            回答结果
        """
        if not self.available:
            return {
                "agent_id": self.agent_id,
                "role": self.role,
                "error": "OpenAI客户端不可用",
                "analysis": None
            }
        
        # 构建专门问题的回答提示
        answer_prompt = self._build_answer_prompt(
            specialized_question, user_question, table_info, generated_sql
        )
        
        try:
            # 构建完整提示
            full_prompt = f"系统: 你是一个{self.role}。\n\n用户: {answer_prompt}"
            
            response = self.client.invoke(full_prompt)
            answer_result = response.content
            
            return {
                "agent_id": self.agent_id,
                "role": self.role,
                "specialized_question": specialized_question,
                "answer": answer_result,
                "confidence": self._calculate_confidence(answer_result)
            }
            
        except Exception as e:
            logger.error(f"智能体 {self.agent_id} 分析失败: {e}")
            return {
                "agent_id": self.agent_id,
                "role": self.role,
                "specialized_question": specialized_question,
                "error": str(e),
                "answer": None
            }
    
    def _build_answer_prompt(self, specialized_question: str, user_question: str, table_info: dict, sql: str) -> str:
        """Build specialized question answer prompt - Focus on user core needs with SQL execution"""
        return f"""
Your task is to help better answer the user's question: "{user_question}"

Specialized Research Question: {specialized_question}

Background Information:
- User Original Question: {user_question}
- Current Generated SQL: {sql}

Table Structure:
{json.dumps(table_info, indent=2, ensure_ascii=False)}

As {self.role}, please:

1. **Execute the SQL Query**: Analyze what the SQL query `{sql}` would return
2. **Explain the Query Logic**: Why this SQL approach was chosen for the user's question
3. **Check Multi-Condition Requirements**: Does the user question require multiple WHERE conditions?
4. **Interpret Results**: What the query results mean in context of the user's question
5. **Evaluate Correctness**: Does this SQL correctly answer "{user_question}"?
6. **Suggest Improvements**: If needed, propose better SQL queries or approaches

Please structure your response as:
- **SQL Analysis**: [What the query does step by step]
- **Query Reasoning**: [Why this approach was chosen]
- **Multi-Condition Check**: [Does the question require multiple conditions? Are they all present?]
- **Expected Results**: [What results this query would produce]
- **Correctness Assessment**: [Does it answer the user's question correctly?]
- **Recommendations**: [Any improvements, especially missing conditions or alternative approaches]

Special attention to multi-condition queries:
- Questions like "What player played guard for toronto in 1996-97?" need multiple conditions
- Check if all conditions from the user question are captured in the SQL
- Look for missing AND clauses that might be needed

IMPORTANT: Only suggest SQL improvements if there are CLEAR missing conditions or obvious errors.
- Don't suggest LIKE instead of = unless absolutely necessary
- Don't add LOWER(), UPPER(), or other functions unless required
- Keep suggestions simple and compatible with WikiSQL format
- Focus on missing WHERE conditions, not style improvements

Focus on helping answer "{user_question}" accurately and completely.
"""
    
    def _calculate_confidence(self, analysis: str) -> float:
        """Calculate analysis confidence based on English keywords"""
        if not analysis:
            return 0.0
        
        # English confidence keywords for SQL analysis
        confidence_keywords = [
            "correct", "accurate", "appropriate", "valid", "suitable",
            "recommend", "suggest", "should", "would", "effective",
            "optimal", "proper", "reliable", "consistent", "logical"
        ]
        
        # Convert to lowercase for case-insensitive matching
        analysis_lower = analysis.lower()
        keyword_count = sum(1 for keyword in confidence_keywords if keyword in analysis_lower)
        
        # Base confidence calculation
        base_confidence = min(keyword_count / 10, 0.8)  # Max 0.8 from keywords
        
        # Bonus for structured analysis (our format)
        structure_bonus = 0.0
        if "**SQL Analysis**" in analysis:
            structure_bonus += 0.1
        if "**Query Reasoning**" in analysis:
            structure_bonus += 0.1
        if "**Expected Results**" in analysis:
            structure_bonus += 0.05
        if "**Correctness Assessment**" in analysis:
            structure_bonus += 0.05
        
        return min(base_confidence + structure_bonus, 1.0)
    
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

class SimpleHeavyOrchestrator:
    """真正的Make It Heavy编排器 - 按照正确流程实现"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        初始化Make It Heavy编排器
        
        Args:
            api_key: API密钥（与WikiSQL相同）
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.model = model
        
        # 初始化Question Generation Agent
        self.question_generator = SimpleHeavyAgent(-1, api_key, model)
        
        # 初始化4个专门智能体
        self.agents = []
        agent_roles = [
            "SQL Research Agent - Deep SQL query analysis and data exploration",
            "SQL Logic Agent - Query logic validation and reasoning analysis", 
            "SQL Alternatives Agent - Alternative query approaches and optimization",
            "SQL Verification Agent - Query result verification and accuracy assessment"
        ]
        
        for i, role in enumerate(agent_roles):
            agent = SimpleHeavyAgent(i, api_key, model)
            agent.role = role
            self.agents.append(agent)
        
        # 初始化Synthesis Agent
        self.synthesis_agent = SimpleHeavyAgent(99, api_key, model)
        self.synthesis_agent.role = "Synthesis Agent - 综合分析和最终答案生成"
        
        logger.info(f"初始化了Make It Heavy系统 - Question Generator + 4个专门智能体 + Synthesis Agent (模型: {model})")
    
    def heavy_sql_analysis(self, question: str, table_info: dict, generated_sql: str) -> dict:
        """
        执行真正的Make It Heavy分析流程
        
        流程:
        1. Question Generation Agent - 生成4个专门问题
        2. 4个智能体并行回答专门问题
        3. Synthesis Agent - 综合所有答案
        
        Args:
            question: 自然语言问题
            table_info: 表格信息
            generated_sql: 生成的SQL查询
            
        Returns:
            综合分析结果
        """
        logger.info("开始Make It Heavy分析流程...")
        
        # 第一步：Question Generation Agent - 生成4个专门问题
        print("🧠 第一步：Question Generation Agent 生成专门问题...")
        specialized_questions = self._generate_specialized_questions(question, table_info, generated_sql)
        
        if not specialized_questions:
            return {"error": "无法生成专门问题"}
        
        print("✅ 生成了4个专门问题:")
        for i, q in enumerate(specialized_questions, 1):
            print(f"  {i}. {q[:100]}...")
        
        # 第二步：4个智能体并行执行
        print("\n🚀 第二步：4个智能体并行分析...")
        agent_results = self._parallel_agent_execution(specialized_questions, question, table_info, generated_sql)
        
        # 第三步：Synthesis Agent综合分析
        print("\n🎯 第三步：Synthesis Agent 综合分析...")
        final_synthesis = self._synthesis_analysis(question, agent_results, generated_sql)
        
        # 檢查是否需要改進SQL
        improved_sql = self._extract_improved_sql(final_synthesis, generated_sql)
        
        return {
            "question": question,
            "generated_sql": generated_sql,
            "improved_sql": improved_sql,  # Heavy分析改進的SQL
            "specialized_questions": specialized_questions,
            "agent_analyses": agent_results,
            "synthesis": final_synthesis,
            "overall_confidence": final_synthesis.get("confidence", 0.0),
            "final_answer": final_synthesis.get("final_answer", ""),
            "make_it_heavy_flow": True
        }
    
    def _generate_specialized_questions(self, question: str, table_info: dict, generated_sql: str) -> list:
        """
        第一步：Question Generation Agent 生成4個專門問題
        
        Args:
            question: 自然語言問題
            table_info: 表格信息
            generated_sql: 生成的SQL查詢
            
        Returns:
            4個專門問題的列表
        """
        # 使用Question Generation Agent生成專門問題
        question_generator = QuestionGenerationAgent(self.api_key)
        specialized_questions = question_generator.generate_specialized_questions(
            question, table_info, generated_sql
        )
        
        if not specialized_questions:
            # 如果生成失败，使用默认的1+3结构英文问题
            specialized_questions = [
                question,  # 保持原始问题
                f"Which specific details and conditions are most important when answering: '{question}'?",
                f"How can we rephrase this inquiry using different terminology: '{question}'?",
                f"What evidence would confirm we have correctly answered: '{question}'?"
            ]
        
        return specialized_questions
    
    def _parallel_agent_execution(self, specialized_questions: list, original_question: str, table_info: dict, generated_sql: str) -> list:
        """
        第二步：4個專業智能體並行執行分析
        
        Args:
            specialized_questions: 4個專門問題
            original_question: 原始問題
            table_info: 表格信息
            generated_sql: 生成的SQL
            
        Returns:
            智能體分析結果列表
        """
        import concurrent.futures
        import time
        
        agent_results = []
        
        def execute_agent_analysis(agent, specialized_question, agent_id):
            """單個智能體執行分析"""
            try:
                if not agent.available:
                    return {
                        "agent_id": agent_id,
                        "role": agent.role,
                        "specialized_question": specialized_question,
                        "error": "智能體不可用",
                        "answer": None,
                        "confidence": 0.0
                    }
                
                # 執行專門問題分析
                result = agent.answer_specialized_question(
                    specialized_question, original_question, table_info, generated_sql
                )
                return result
                
            except Exception as e:
                return {
                    "agent_id": agent_id,
                    "role": agent.role,
                    "specialized_question": specialized_question,
                    "error": str(e),
                    "answer": None,
                    "confidence": 0.0
                }
        
        # 並行執行4個智能體
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 提交任務
            future_to_agent = {}
            for i, (agent, spec_question) in enumerate(zip(self.agents, specialized_questions)):
                future = executor.submit(execute_agent_analysis, agent, spec_question, i)
                future_to_agent[future] = (agent, i)
            
            # 收集結果
            for future in concurrent.futures.as_completed(future_to_agent, timeout=120):
                try:
                    result = future.result()
                    agent_results.append(result)
                except Exception as e:
                    agent, agent_id = future_to_agent[future]
                    agent_results.append({
                        "agent_id": agent_id,
                        "role": agent.role,
                        "error": f"執行超時或失敗: {str(e)}",
                        "answer": None,
                        "confidence": 0.0
                    })
        
        # 按agent_id排序
        agent_results.sort(key=lambda x: x.get("agent_id", 0))
        return agent_results
    
    def _synthesis_analysis(self, original_question: str, agent_results: list, generated_sql: str) -> dict:
        """
        第三步：Synthesis Agent 綜合所有智能體的分析結果
        
        Args:
            original_question: 原始問題
            agent_results: 智能體分析結果
            generated_sql: 生成的SQL
            
        Returns:
            綜合分析結果
        """
        # 收集所有成功的分析
        successful_results = [r for r in agent_results if not r.get("error")]
        
        if not successful_results:
            return {
                "error": "没有成功的智能体分析", 
                "confidence": 0.0,
                "successful_agents": 0,
                "total_agents": len(agent_results),
                "valid_analyses": 0,
                "final_answer": "所有智能体分析都失败了"
            }
        
        # Build synthesis analysis prompt - Focus on user core question
        synthesis_prompt = f"""
As Synthesis Agent, your task is to synthesize the analysis from 4 professional agents, with the ultimate goal of ensuring we correctly answer the user's question.

User Question: {original_question}
Current SQL Solution: {generated_sql}

Analysis Results from 4 Professional Agents:
"""
        
        for result in successful_results:
            role = result.get("role", "Unknown Role")
            question = result.get("specialized_question", "")
            answer = result.get("answer", "")
            synthesis_prompt += f"""
{role}:
Specialized Question: {question}
Analysis Answer: {answer}

---
"""
        
        synthesis_prompt += f"""
As Synthesis Agent, analyze the SQL query results and recommendations from all 4 agents to provide a comprehensive answer to: "{original_question}"

Please synthesize their findings by:

1. **SQL Query Evaluation**: Compare how each agent analyzed the SQL query `{generated_sql}`
2. **Results Analysis**: Synthesize what each agent found about the query results and their correctness
3. **Consensus Assessment**: Where do the agents agree/disagree about the SQL approach?
4. **Improved SQL**: If agents suggest improvements, provide the corrected SQL query
5. **Final Answer**: Based on all agent analyses, what is the best answer to "{original_question}"?
6. **Confidence Score**: Overall confidence in the final answer (0-1)

Structure your response as:
- **Query Assessment**: [Combined evaluation of the SQL query]
- **Agent Consensus**: [Where agents agree and disagree]
- **Improved SQL**: [If needed, provide corrected SQL query in format: ```sql\nSELECT ... \n```]
- **Final Answer**: [Definitive answer to the user's question]
- **Confidence**: [Number between 0-1]

IMPORTANT: If the agents identified missing conditions or SQL errors, provide the corrected SQL query in a code block like this:
```sql
SELECT col0 FROM table_name WHERE col1='condition1' AND col2='condition2';
```

CRITICAL GUIDELINES for SQL improvements:
1. Keep SQL simple and compatible with WikiSQL format
2. Use exact matches (=) instead of LIKE unless absolutely necessary
3. Don't add unnecessary functions like LOWER(), UPPER(), etc.
4. Stick to basic SELECT, FROM, WHERE, AND structure
5. Only suggest improvements if there are clear missing conditions or obvious errors

Focus on providing the most accurate answer to "{original_question}" based on all agent insights.
"""
        
        try:
            response = self.synthesis_agent.client.invoke(synthesis_prompt)
            synthesis_content = response.content
            
            # 从synthesis内容中提取置信度
            confidence = self._extract_confidence_from_synthesis(synthesis_content, successful_results)
            
            return {
                "synthesis_content": synthesis_content,
                "confidence": confidence,
                "successful_agents": len(successful_results),
                "total_agents": len(agent_results),
                "final_answer": synthesis_content,
                "valid_analyses": len(successful_results)
            }
            
        except Exception as e:
            logger.error(f"Synthesis Agent分析失败: {e}")
            return {
                "error": f"综合分析失败: {e}",
                "confidence": 0.0,
                "successful_agents": len(successful_results),
                "total_agents": len(agent_results),
                "valid_analyses": len(successful_results),
                "final_answer": f"Synthesis Agent失败，但{len(successful_results)}个智能体成功完成分析"
            }
    
    def _extract_confidence_from_synthesis(self, synthesis_content: str, successful_results: list) -> float:
        """从synthesis内容和智能体结果中提取真实的置信度"""
        import re
        
        # 1. 尝试从synthesis内容中提取明确的置信度
        confidence_patterns = [
            r'\*\*Confidence\*\*[：:]\s*([0-9.]+)',
            r'置信度[：:]\s*([0-9.]+)',
            r'confidence[：:]\s*([0-9.]+)',
            r'Confidence Score[：:]\s*([0-9.]+)',
            r'Overall confidence[：:]\s*([0-9.]+)',
            r'([0-9.]+)\s*(?:out of|/)\s*1',
            r'([0-9.]+)\s*(?:%|percent)',
        ]
        
        for pattern in confidence_patterns:
            matches = re.findall(pattern, synthesis_content, re.IGNORECASE)
            if matches:
                try:
                    conf_value = float(matches[0])
                    # 如果是百分比，转换为0-1范围
                    if conf_value > 1:
                        conf_value = conf_value / 100
                    if 0 <= conf_value <= 1:
                        return conf_value
                except ValueError:
                    continue
        
        # 2. 基于智能体结果计算置信度
        if successful_results:
            agent_confidences = [r.get("confidence", 0.0) for r in successful_results]
            avg_agent_confidence = sum(agent_confidences) / len(agent_confidences)
            
            # 3. 基于synthesis内容质量调整置信度
            quality_indicators = [
                "correct", "accurate", "appropriate", "valid", "suitable",
                "recommend", "improved", "better", "optimal", "effective"
            ]
            
            negative_indicators = [
                "error", "incorrect", "wrong", "missing", "failed",
                "unclear", "ambiguous", "problematic", "insufficient"
            ]
            
            content_lower = synthesis_content.lower()
            positive_count = sum(1 for indicator in quality_indicators if indicator in content_lower)
            negative_count = sum(1 for indicator in negative_indicators if indicator in content_lower)
            
            # 质量调整因子
            quality_factor = (positive_count - negative_count * 0.5) / 10
            quality_factor = max(-0.3, min(0.3, quality_factor))  # 限制在-0.3到0.3之间
            
            # 成功智能体比例调整
            success_ratio = len(successful_results) / 4  # 总共4个智能体
            
            # 综合计算置信度
            final_confidence = avg_agent_confidence * success_ratio + quality_factor
            final_confidence = max(0.0, min(1.0, final_confidence))  # 确保在0-1范围内
            
            return final_confidence
        
        # 4. 默认置信度（如果所有方法都失败）
        return 0.5
    
    def _extract_improved_sql(self, synthesis_result: dict, original_sql: str) -> str:
        """從Synthesis結果中提取改進的SQL查詢"""
        if synthesis_result.get("error"):
            return original_sql
        
        final_answer = synthesis_result.get("final_answer", "")
        
        # 尋找SQL查詢建議
        import re
        
        # 更全面的SQL代碼塊模式
        sql_patterns = [
            # 標準代碼塊
            r'```sql\s*\n(.*?)\n```',
            r'```\s*\n(SELECT.*?;)\s*\n```',
            # Improved SQL 部分
            r'\*\*Improved SQL\*\*.*?```sql\s*\n(.*?)\n```',
            r'\*\*Improved SQL\*\*.*?[:：]\s*(SELECT.*?;)',
            # 一般SQL建議
            r'建議.*?SQL.*?[:：]\s*(SELECT.*?;)',
            r'改進.*?SQL.*?[:：]\s*(SELECT.*?;)',
            r'正確.*?SQL.*?[:：]\s*(SELECT.*?;)',
            r'corrected.*?SQL.*?[:：]\s*(SELECT.*?;)',
            r'improved.*?SQL.*?[:：]\s*(SELECT.*?;)',
            # 直接的SELECT語句
            r'(SELECT\s+col\d+.*?WHERE.*?;)',
            r'(SELECT\s+.*?FROM\s+.*?WHERE.*?AND.*?;)',
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, final_answer, re.DOTALL | re.IGNORECASE)
            if matches:
                improved_sql = matches[0].strip()
                # 清理SQL
                improved_sql = improved_sql.replace('\n', ' ').replace('\r', ' ')
                improved_sql = ' '.join(improved_sql.split())  # 規範化空格
                
                # 確保SQL以分號結尾
                if not improved_sql.endswith(';'):
                    improved_sql += ';'
                
                # 檢查是否真的是改進的SQL - 更嚴格的驗證
                if (improved_sql and 
                    improved_sql != original_sql and 
                    'SELECT' in improved_sql.upper() and
                    len(improved_sql) > 10 and
                    self._is_valid_improvement(improved_sql, original_sql)):
                    logger.info(f"Heavy分析提取到改進SQL: {improved_sql}")
                    return improved_sql
        
        # 如果沒有找到改進的SQL，返回原始SQL
        logger.info(f"未找到改進SQL，使用原始SQL: {original_sql}")
        return original_sql
    
    def _is_valid_improvement(self, improved_sql: str, original_sql: str) -> bool:
        """驗證改進的SQL是否真的比原始SQL更好"""
        import re
        
        # 提取WHERE條件數量
        def count_conditions(sql):
            where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER|\s+GROUP|\s+LIMIT|;|$)', sql, re.IGNORECASE)
            if not where_match:
                return 0
            where_clause = where_match.group(1)
            return len(re.findall(r'\bAND\b', where_clause, re.IGNORECASE)) + 1
        
        original_conditions = count_conditions(original_sql)
        improved_conditions = count_conditions(improved_sql)
        
        # 檢查是否添加了有意義的條件
        if improved_conditions > original_conditions:
            logger.info(f"SQL改進：添加了 {improved_conditions - original_conditions} 個條件")
            return True
        
        # 檢查是否修復了明顯的錯誤（如錯誤的列選擇）
        original_select = re.search(r'SELECT\s+(.*?)\s+FROM', original_sql, re.IGNORECASE)
        improved_select = re.search(r'SELECT\s+(.*?)\s+FROM', improved_sql, re.IGNORECASE)
        
        if original_select and improved_select:
            orig_cols = original_select.group(1).strip()
            impr_cols = improved_select.group(1).strip()
            
            # 如果只是改變了選擇的列，需要謹慎
            if orig_cols != impr_cols:
                logger.warning(f"SQL改進改變了選擇列：{orig_cols} -> {impr_cols}")
                # 只有在原始SQL明顯錯誤時才接受列的改變
                return False
        
        # 檢查是否添加了不必要的複雜性
        complexity_indicators = ['LIKE', 'LOWER', 'UPPER', 'CROSS APPLY', 'STRING_SPLIT', '%']
        improved_complexity = sum(1 for indicator in complexity_indicators if indicator in improved_sql.upper())
        original_complexity = sum(1 for indicator in complexity_indicators if indicator in original_sql.upper())
        
        if improved_complexity > original_complexity:
            logger.warning(f"SQL改進增加了複雜性，可能不適合WikiSQL格式")
            return False
        
        # 如果沒有明顯改進，保持原始SQL
        logger.info("SQL改進沒有明顯優勢，保持原始SQL")
        return False
    
    def _synthesize_results_old(self, agent_results: List[dict]) -> dict:
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

class WikiSQLDirectLLMSimpleHeavy(WikiSQLDirectLLM):
    """简化版Heavy增强WikiSQL助手"""
    
    def __init__(self, api_key: str, enable_heavy: bool = True, **kwargs):
        """初始化简化版Heavy助手"""
        super().__init__(api_key, **kwargs)
        
        # 初始化简化版Heavy编排器（使用相同的API密钥和模型）
        if enable_heavy:
            try:
                # 获取当前使用的模型名称
                current_model = getattr(self.llm, 'model_name', 'gemini-2.5-flash')
                self.heavy_orchestrator = SimpleHeavyOrchestrator(api_key, current_model)
                self.heavy_enabled = True
                logger.info(f"✅ 简化版Heavy模式已启用（模型: {current_model}）")
            except Exception as e:
                logger.warning(f"⚠️ 简化版Heavy模式初始化失败: {e}")
                self.heavy_orchestrator = None
                self.heavy_enabled = False
        else:
            logger.info("Heavy模式已禁用")
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
                
                logger.info(f"✅ 简化版Heavy分析完成，置信度: {heavy_analysis.get('overall_confidence', 0.0):.2f}")
                
            except Exception as e:
                logger.error(f"❌ 简化版Heavy分析失败: {e}")
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
    """测试简化版WikiSQL Heavy集成"""
    print("🚀 WikiSQL 简化版Heavy Integration 测试")
    print("=" * 60)
    
    # 获取API密钥
    wikisql_api_key = input("请输入你的WikiSQL API密钥: ").strip()
    if not wikisql_api_key:
        print("❌ 需要提供WikiSQL API密钥")
        return
    
    openai_api_key = input("请输入你的OpenAI API密钥 (用于Heavy分析，可选): ").strip()
    
    try:
        # 初始化简化版Heavy助手
        print("初始化简化版WikiSQL Heavy助手...")
        assistant = WikiSQLDirectLLMSimpleHeavy(
            wikisql_api_key, 
            openai_api_key=openai_api_key
        )
        
        if assistant.heavy_enabled:
            print("✅ 简化版Heavy模式已启用")
        else:
            print("⚠️ Heavy模式未启用，将使用基础模式")
        
        # 加载数据集
        print("加载WikiSQL数据集...")
        assistant.load_wikisql_dataset("dev", limit=2)
        
        # 测试查询
        if assistant.current_questions:
            test_question = assistant.current_questions[0].question
            print(f"\n测试问题: {test_question}")
            
            if assistant.heavy_enabled:
                # 执行Heavy查询
                print("执行简化版Heavy分析...")
                heavy_result = assistant.query_with_heavy(test_question)
                
                # 显示结果
                print("\n" + "=" * 60)
                print("简化版Heavy分析结果:")
                print("=" * 60)
                
                if heavy_result.get("heavy_analysis"):
                    analysis = heavy_result["heavy_analysis"]
                    print(f"置信度: {analysis.get('overall_confidence', 0.0):.2f}")
                    print(f"有效分析: {analysis['synthesis']['valid_analyses']}/{analysis['synthesis']['total_agents']}")
                    
                    recommendations = analysis.get('final_recommendations', [])
                    if recommendations:
                        print(f"\n主要建议 (前3个):")
                        for i, rec in enumerate(recommendations[:3], 1):
                            print(f"  {i}. {rec}")
                
                if heavy_result.get("query_result"):
                    print(f"\n查询结果: {heavy_result['query_result']}")
            else:
                # 基础查询
                result = assistant.query(test_question)
                print(f"基础查询结果: {result}")
        
        print("\n✅ 简化版Heavy集成测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()