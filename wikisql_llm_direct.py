"""
WikiSQL直接LLM查询助手 - 方案1实现
不使用SQL Agent，直接使用LLM生成SQL并手动执行
"""

import os
import json
import logging
import sqlite3
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from wikisql_data_loader import WikiSQLDataLoader, WikiSQLQuestion, WikiSQLTable
from wikisql_database_manager import WikiSQLDatabaseManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikiSQLDirectLLM:
    """WikiSQL直接LLM查询助手 - 方案1实现"""
    
    def __init__(self, api_key: Optional[str] = None, data_dir: str = "data", local_wikisql_path: str = None):
        """
        初始化WikiSQL直接LLM查询助手
        
        Args:
            api_key: API密钥 (用于Gemini 2.5 Flash模型)
            data_dir: 数据存储目录
            local_wikisql_path: 本地WikiSQL项目路径
        """
        # 设置API密钥
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        elif not os.getenv("GOOGLE_API_KEY"):
            logger.warning("警告：请设置GOOGLE_API_KEY环境变量或提供API密钥")
        
        # 初始化组件
        self.data_loader = WikiSQLDataLoader(data_dir, local_wikisql_path)
        self.db_manager = WikiSQLDatabaseManager()
        
        # 初始化LLM (使用Google AI Studio)
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            request_timeout=30
        )
        
        # 数据存储
        self.current_questions: List[WikiSQLQuestion] = []
        self.current_tables: Dict[str, WikiSQLTable] = {}
        self.current_table_mapping: Dict[str, str] = {}  # wikisql_table_id -> db_table_name
        self.column_mapping: Dict[str, Dict] = {}  # 存储列名映射关系
        
        logger.info("WikiSQL直接LLM查询助手初始化完成")
    
    def load_wikisql_dataset(self, split: str = "dev", limit: Optional[int] = 10, force_download: bool = False):
        """
        加载WikiSQL数据集
        
        Args:
            split: 数据分割 ("train", "dev", "test")
            limit: 限制加载的问题数量
            force_download: 是否强制重新下载
        """
        logger.info(f"正在加载WikiSQL数据集: {split} (限制: {limit})")
        
        # 加载真实数据
        questions, tables = self.data_loader.load_dataset(split, limit, force_download)
        
        # 验证数据
        stats = self.data_loader.validate_dataset(questions, tables)
        logger.info(f"数据验证结果: {stats}")
        
        # 存储数据
        self.current_questions = questions
        self.current_tables = tables
        
        # 创建数据库表格
        self._create_database_tables()
        
        logger.info(f"✅ 数据集加载完成: {len(questions)} 个问题, {len(tables)} 个表格")
    
    def _create_database_tables(self):
        """创建数据库表格，使用col0, col1, col2...格式"""
        logger.info("正在创建数据库表格...")
        
        # 只为当前问题相关的表格创建数据库表
        relevant_table_ids = set(q.table_id for q in self.current_questions)
        relevant_tables = {tid: table for tid, table in self.current_tables.items() 
                          if tid in relevant_table_ids}
        
        logger.info(f"需要创建 {len(relevant_tables)} 个相关表格")
        
        # 为每个表格创建数据库表，使用col格式
        for table_id, table in relevant_tables.items():
            try:
                # 使用数据库管理器创建表格
                db_table_name = self.db_manager.create_table_from_wikisql(table, use_col_format=True)
                
                # 存储映射关系
                self.current_table_mapping[table_id] = db_table_name
                
                # 存储列名映射关系
                column_names = [f"col{i}" for i in range(len(table.header))]
                self.column_mapping[table_id] = {
                    'original_headers': table.header,
                    'db_columns': column_names,
                    'mapping': dict(zip(table.header, column_names))
                }
                
                logger.info(f"✅ 表格 {table_id} -> {db_table_name}")
                
            except Exception as e:
                logger.error(f"创建表格 {table_id} 失败: {e}")
        
        logger.info(f"✅ 数据库表格创建完成: {len(self.current_table_mapping)} 个表格")
    
    def _build_table_context(self, table_id: str) -> str:
        """构建表格上下文信息"""
        if table_id not in self.current_tables:
            return "表格信息不可用"
        
        table = self.current_tables[table_id]
        db_table_name = self.current_table_mapping.get(table_id, "unknown")
        
        context_parts = []
        context_parts.append(f"表格名称: {db_table_name}")
        context_parts.append(f"表格描述: {getattr(table, 'name', '无描述')}")
        
        # 列信息
        context_parts.append("列信息:")
        for i, header in enumerate(table.header):
            col_name = f"col{i}"
            data_type = table.types[i] if i < len(table.types) else "text"
            context_parts.append(f"  {col_name}: {header} ({data_type})")
        
        # 数据样本
        max_rows = min(5, len(table.rows))
        if max_rows > 0:
            context_parts.append(f"\n数据样本 (前{max_rows}行):")
            for i, row in enumerate(table.rows[:max_rows]):
                row_data = [str(cell) for cell in row]
                context_parts.append(f"  行{i+1}: {row_data}")
        
        return "\n".join(context_parts)
    
    def _generate_sql_prompt(self, question: str, table_id: str) -> str:
        """生成SQL查询的提示词"""
        table_context = self._build_table_context(table_id)
        
        prompt = f"""
你是一个SQL查询专家。请根据自然语言问题生成对应的SQL查询。

表格信息:
{table_context}

重要规则:
1. 列名必须使用 col0, col1, col2... 格式
2. 表格名称使用提供的确切名称
3. 只返回SQL查询语句，不要包含其他解释
4. 使用标准的SQLite语法
5. 仔细分析问题，只在明确需要时使用聚合函数
6. 只添加问题中明确提到的WHERE条件

聚合函数指南:
- "how many" / "count" → COUNT()
- "minimum" / "smallest" → MIN()  
- "maximum" / "largest" → MAX()
- "sum" / "total" (求和) → SUM()
- "average" → AVG()

注意: "total amount" 可能指数量(COUNT)或最大值(MAX)，需要根据上下文判断

问题: {question}

请仔细分析问题类型和所有条件，生成完整准确的SQL查询:
"""
        return prompt
    
    def generate_sql(self, question: str, table_id: str) -> str:
        """
        使用LLM生成SQL查询
        
        Args:
            question: 自然语言问题
            table_id: 表格ID
            
        Returns:
            生成的SQL查询
        """
        try:
            prompt = self._generate_sql_prompt(question, table_id)
            
            logger.info(f"正在为问题生成SQL: {question}")
            logger.info(f"使用表格: {table_id}")
            
            # 调用LLM API
            response = self.llm.invoke(prompt)
            
            if response.content:
                sql = response.content.strip()
                # 清理SQL（移除markdown标记等）
                sql = self._clean_sql(sql)
                logger.info(f"生成的SQL: {sql}")
                return sql
            else:
                logger.error("LLM没有返回有效响应")
                return ""
                
        except Exception as e:
            logger.error(f"生成SQL失败: {e}")
            return ""
    
    def _clean_sql(self, sql: str) -> str:
        """清理SQL查询字符串"""
        # 移除markdown代码块标记
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        
        # 移除多余的空白字符
        sql = sql.strip()
        
        # 确保SQL以分号结尾
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    def execute_sql(self, sql: str) -> Any:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            
        Returns:
            查询结果
        """
        try:
            logger.info(f"执行SQL: {sql}")
            result = self.db_manager.execute_query(sql)
            logger.info(f"查询结果: {result}")
            return result
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return f"SQL执行错误: {str(e)}"
    
    def query(self, question: str, table_id: Optional[str] = None) -> str:
        """
        执行自然语言查询
        
        Args:
            question: 自然语言问题
            table_id: 表格ID（如果不提供，尝试从当前问题中推断）
            
        Returns:
            查询结果
        """
        # 如果没有提供table_id，尝试从当前问题中找到
        if not table_id and self.current_questions:
            # 简单匹配：找到第一个包含相似问题的表格
            for q in self.current_questions:
                if question.lower() in q.question.lower() or q.question.lower() in question.lower():
                    table_id = q.table_id
                    break
            
            # 如果还是没找到，使用第一个表格
            if not table_id:
                table_id = self.current_questions[0].table_id
        
        if not table_id:
            return "错误：无法确定要查询的表格"
        
        # 生成SQL
        sql = self.generate_sql(question, table_id)
        if not sql:
            return "错误：无法生成SQL查询"
        
        # 执行SQL
        result = self.execute_sql(sql)
        
        # 格式化结果
        if isinstance(result, list) and result:
            if len(result) == 1 and len(result[0]) == 1:
                # 单个值结果
                return str(result[0][0])
            else:
                # 多行或多列结果
                return str(result)
        elif result is None or (isinstance(result, list) and not result):
            return "查询无结果"
        else:
            return str(result)
    
    def generate_wikisql_prediction(self, question_idx: int) -> Dict[str, Any]:
        """
        为指定问题生成WikiSQL格式的预测
        
        Args:
            question_idx: 问题索引
            
        Returns:
            WikiSQL格式的预测结果
        """
        if question_idx >= len(self.current_questions):
            return {"error": "问题索引超出范围"}
        
        question = self.current_questions[question_idx]
        
        try:
            # 生成SQL
            sql = self.generate_sql(question.question, question.table_id)
            if not sql:
                return {"error": "无法生成SQL查询"}
            
            # 解析SQL为WikiSQL格式
            parsed_query = self._parse_sql_to_wikisql_format(sql, question)
            
            if parsed_query:
                return {"query": parsed_query}
            else:
                return {"error": f"无法解析SQL为WikiSQL格式: {sql}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_sql_to_wikisql_format(self, sql: str, question) -> Optional[Dict]:
        """
        将SQL解析为WikiSQL格式
        
        Args:
            sql: SQL查询语句
            question: 问题对象
            
        Returns:
            WikiSQL格式的查询字典
        """
        try:
            table = self.current_tables.get(question.table_id)
            if not table:
                logger.error(f"找不到表格: {question.table_id}")
                return None
            
            logger.info(f"解析SQL: {sql}")
            
            # 初始化默认值
            sel_index = 0
            agg_index = 0
            conditions = []
            
            sql_upper = sql.upper().strip()
            
            # 解析SELECT部分
            select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_upper)
            if select_match:
                select_part = select_match.group(1).strip()
                
                # 解析聚合函数
                if 'COUNT(' in select_part:
                    agg_index = 3
                elif 'MAX(' in select_part:
                    agg_index = 1
                elif 'MIN(' in select_part:
                    agg_index = 2
                elif 'SUM(' in select_part:
                    agg_index = 4
                elif 'AVG(' in select_part:
                    agg_index = 5
                else:
                    agg_index = 0
                
                # 解析选择的列
                col_match = re.search(r'COL(\d+)', select_part)
                if col_match:
                    sel_index = int(col_match.group(1))
            
            # 解析WHERE条件 - 支持多条件
            where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|$)', sql_upper)
            if where_match:
                where_part = where_match.group(1).strip()
                
                # 分割AND条件
                and_conditions = re.split(r'\s+AND\s+', where_part)
                
                for condition in and_conditions:
                    condition = condition.strip()
                    
                    # 条件解析模式
                    condition_patterns = [
                        (r'COL(\d+)\s*=\s*[\'"]([^\'"]+)[\'"]', 0),  # 等于字符串
                        (r'COL(\d+)\s*=\s*([^\s\'";]+)', 0),        # 等于数字
                        (r'COL(\d+)\s*>\s*([^\s\'";]+)', 1),        # 大于
                        (r'COL(\d+)\s*<\s*([^\s\'";]+)', 2),        # 小于
                        (r'COL(\d+)\s+LIKE\s+[\'"]([^\'"]+)[\'"]', 0),  # LIKE (当作等于处理)
                    ]
                    
                    matched = False
                    for pattern, op_index in condition_patterns:
                        match = re.search(pattern, condition)
                        if match:
                            col_idx = int(match.group(1))
                            value = match.group(2).strip()
                            # 移除引号
                            value = value.strip('\'"')
                            conditions.append([col_idx, op_index, value])
                            matched = True
                            break
                    
                    if not matched:
                        logger.warning(f"无法解析条件: {condition}")
            
            result = {
                'sel': sel_index,
                'agg': agg_index,
                'conds': conditions
            }
            
            logger.info(f"解析结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"解析SQL失败: {e}")
            return None
    
    def evaluate_question(self, question_idx: int) -> Dict[str, Any]:
        """
        评估特定问题
        
        Args:
            question_idx: 问题索引
            
        Returns:
            评估结果
        """
        if question_idx >= len(self.current_questions):
            return {"error": "问题索引超出范围"}
        
        question = self.current_questions[question_idx]
        
        try:
            # 生成SQL并执行
            generated_sql = self.generate_sql(question.question, question.table_id)
            if generated_sql:
                generated_result = self.execute_sql(generated_sql)
            else:
                generated_result = "SQL生成失败"
            
            # 获取预期SQL并执行
            expected_sql = question.get_sql_string()
            try:
                converted_sql = self._convert_wikisql_to_db_sql(expected_sql, question.table_id)
                expected_result = self.execute_sql(converted_sql)
            except Exception as e:
                expected_result = f"预期SQL执行失败: {e}"
                converted_sql = f"转换失败: {e}"
            
            return {
                "question_id": question.id,
                "question": question.question,
                "generated_sql": generated_sql,
                "generated_result": generated_result,
                "expected_sql": expected_sql,
                "converted_sql": converted_sql,
                "expected_result": expected_result,
                "table_id": question.table_id
            }
            
        except Exception as e:
            return {
                "question_id": question.id,
                "question": question.question,
                "error": str(e)
            }
    
    def _convert_wikisql_to_db_sql(self, wikisql: str, table_id: str) -> str:
        """
        将WikiSQL格式的SQL转换为数据库可执行的SQL
        
        Args:
            wikisql: WikiSQL格式的SQL
            table_id: 表格ID
            
        Returns:
            转换后的SQL
        """
        if table_id not in self.current_table_mapping:
            raise ValueError(f"找不到表格: {table_id}")
        
        db_table_name = self.current_table_mapping[table_id]
        
        # 替换表名
        converted_sql = wikisql.replace("FROM table", f'FROM "{db_table_name}"')
        
        return converted_sql
    
    def generate_predictions_file(self, output_file: str = "predictions.jsonl", limit: Optional[int] = None) -> str:
        """
        生成符合WikiSQL官方评估器格式的预测文件
        
        Args:
            output_file: 输出文件路径
            limit: 限制处理的问题数量
            
        Returns:
            输出文件路径
        """
        if not self.current_questions:
            logger.error("没有加载问题数据")
            return ""
        
        questions_to_process = self.current_questions[:limit] if limit else self.current_questions
        
        logger.info(f"开始生成预测文件: {output_file}")
        logger.info(f"处理 {len(questions_to_process)} 个问题")
        
        predictions = []
        
        for i, question in enumerate(questions_to_process):
            logger.info(f"处理问题 {i+1}/{len(questions_to_process)}: {question.question}")
            
            try:
                # 生成WikiSQL格式的预测
                prediction = self.generate_wikisql_prediction(i)
                predictions.append(prediction)
                
                # 显示进度
                if (i + 1) % 5 == 0:
                    logger.info(f"已处理 {i + 1} 个问题")
                    
            except Exception as e:
                logger.error(f"处理问题 {i+1} 失败: {e}")
                predictions.append({"error": str(e)})
        
        # 保存预测结果
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for prediction in predictions:
                    f.write(json.dumps(prediction, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 预测文件已保存: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"保存预测文件失败: {e}")
            return ""
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """获取当前数据集信息"""
        return {
            "questions_count": len(self.current_questions),
            "tables_count": len(self.current_tables),
            "db_tables_count": len(self.current_table_mapping),
            "db_tables": self.db_manager.list_tables(),
            "sample_question": self.current_questions[0].question if self.current_questions else None
        }

def main():
    """测试WikiSQL直接LLM查询助手"""
    print("=== WikiSQL直接LLM查询助手测试 ===")
    
    # 获取API密钥
    api_key = input("请输入你的Google AI Studio API密钥 (或按Enter跳过): ").strip()
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ 需要提供API密钥")
            return
    
    try:
        # 创建助手
        print("初始化WikiSQL直接LLM查询助手...")
        assistant = WikiSQLDirectLLM(api_key)
        
        # 加载数据集
        print("加载WikiSQL数据集...")
        assistant.load_wikisql_dataset("dev", limit=3)  # 只加载3个问题进行测试
        
        # 显示数据集信息
        info = assistant.get_dataset_info()
        print(f"\n数据集信息: {info}")
        
        # 测试查询
        if assistant.current_questions:
            test_question = assistant.current_questions[0].question
            print(f"\n测试问题: {test_question}")
            
            result = assistant.query(test_question)
            print(f"查询结果: {result}")
        
        # 评估第一个问题
        print("\n评估第一个问题...")
        eval_result = assistant.evaluate_question(0)
        print(f"评估结果: {eval_result}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()