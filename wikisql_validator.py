#!/usr/bin/env python3
"""
WikiSQL验证器 - 替代官方评估器
解决编码问题并提供详细的评估结果
"""

import json
import sqlite3
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path
import traceback

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikiSQLValidator:
    """WikiSQL验证器"""
    
    def __init__(self, source_file: str, db_file: str, predictions_file: str):
        """
        初始化验证器
        
        Args:
            source_file: 源问题文件 (dev.jsonl)
            db_file: 数据库文件 (dev.db)
            predictions_file: 预测结果文件
        """
        self.source_file = Path(source_file)
        self.db_file = Path(db_file)
        self.predictions_file = Path(predictions_file)
        
        # 验证文件存在
        if not self.source_file.exists():
            raise FileNotFoundError(f"源文件不存在: {self.source_file}")
        if not self.db_file.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_file}")
        if not self.predictions_file.exists():
            raise FileNotFoundError(f"预测文件不存在: {self.predictions_file}")
        
        logger.info(f"初始化验证器:")
        logger.info(f"  源文件: {self.source_file}")
        logger.info(f"  数据库: {self.db_file}")
        logger.info(f"  预测文件: {self.predictions_file}")
    
    def load_source_data(self) -> List[Dict]:
        """加载源问题数据"""
        logger.info("加载源问题数据...")
        questions = []
        
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        questions.append(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析第{line_num}行失败: {e}")
                        continue
        
        except UnicodeDecodeError:
            # 尝试其他编码
            logger.warning("UTF-8解码失败，尝试其他编码...")
            encodings = ['utf-8', 'gbk', 'cp950', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(self.source_file, 'r', encoding=encoding) as f:
                        questions = []
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                            
                            try:
                                data = json.loads(line)
                                questions.append(data)
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"成功使用编码: {encoding}")
                    break
                    
                except UnicodeDecodeError:
                    continue
            else:
                raise Exception("所有编码都失败了")
        
        logger.info(f"加载了 {len(questions)} 个问题")
        return questions
    
    def load_predictions(self) -> List[Dict]:
        """加载预测结果"""
        logger.info("加载预测结果...")
        predictions = []
        
        try:
            with open(self.predictions_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        predictions.append(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析预测第{line_num}行失败: {e}")
                        # 添加错误占位符
                        predictions.append({"error": f"解析失败: {e}"})
                        continue
        
        except Exception as e:
            logger.error(f"加载预测文件失败: {e}")
            raise
        
        logger.info(f"加载了 {len(predictions)} 个预测结果")
        return predictions
    
    def execute_sql_on_db(self, sql: str, table_id: str) -> Any:
        """在数据库中执行SQL查询"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 执行查询
            cursor.execute(sql)
            result = cursor.fetchall()
            
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"SQL执行失败: {sql}, 错误: {e}")
            return None
    
    def wikisql_to_sql(self, query: Dict, table_id: str) -> str:
        """将WikiSQL格式转换为SQL语句"""
        try:
            # 获取表格信息
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 查找表格名称
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # 找到匹配的表格
            table_name = None
            for (name,) in tables:
                if table_id in name or name.endswith(table_id.replace('-', '_')):
                    table_name = name
                    break
            
            if not table_name:
                # 使用第一个表格作为默认
                if tables:
                    table_name = tables[0][0]
                else:
                    raise Exception("找不到任何表格")
            
            # 获取列信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            conn.close()
            
            if not columns:
                raise Exception(f"表格 {table_name} 没有列信息")
            
            # 构建SQL
            sel_col = query.get('sel', 0)
            agg_op = query.get('agg', 0)
            conditions = query.get('conds', [])
            
            # 聚合操作映射
            agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
            
            # 选择列
            if sel_col < len(columns):
                col_name = columns[sel_col][1]  # 列名
            else:
                col_name = columns[0][1]  # 默认第一列
            
            # 构建SELECT部分
            if agg_op > 0 and agg_op < len(agg_ops):
                select_part = f"{agg_ops[agg_op]}({col_name})"
            else:
                select_part = col_name
            
            # 构建WHERE部分
            where_parts = []
            if conditions:
                for cond in conditions:
                    if len(cond) >= 3:
                        cond_col = cond[0]
                        cond_op = cond[1]
                        cond_val = cond[2]
                        
                        if cond_col < len(columns):
                            cond_col_name = columns[cond_col][1]
                            
                            # 操作符映射
                            ops = ['=', '>', '<']
                            if cond_op < len(ops):
                                op = ops[cond_op]
                                # 处理SQL注入和特殊字符
                                escaped_val = str(cond_val).replace("'", "''")
                                where_parts.append(f"{cond_col_name} {op} '{escaped_val}'")
            
            # 组装SQL
            sql = f"SELECT {select_part} FROM {table_name}"
            if where_parts:
                sql += f" WHERE {' AND '.join(where_parts)}"
            
            return sql
            
        except Exception as e:
            logger.error(f"SQL转换失败: {e}")
            return ""
    
    def evaluate_single(self, question: Dict, prediction: Dict) -> Dict:
        """评估单个问题"""
        result = {
            "question_id": question.get("id", "unknown"),
            "question": question.get("question", ""),
            "table_id": question.get("table_id", ""),
            "correct": False,
            "error": None,
            "expected_sql": "",
            "predicted_sql": "",
            "expected_result": None,
            "predicted_result": None
        }
        
        try:
            # 检查预测是否有错误
            if "error" in prediction:
                result["error"] = prediction["error"]
                return result
            
            # 检查预测格式
            if "query" not in prediction:
                result["error"] = "预测结果缺少query字段"
                return result
            
            predicted_query = prediction["query"]
            expected_query = question.get("sql", {})
            
            # 转换为SQL
            table_id = question.get("table_id", "")
            
            try:
                expected_sql = self.wikisql_to_sql(expected_query, table_id)
                predicted_sql = self.wikisql_to_sql(predicted_query, table_id)
                
                result["expected_sql"] = expected_sql
                result["predicted_sql"] = predicted_sql
                
                # 执行SQL获取结果
                if expected_sql:
                    expected_result = self.execute_sql_on_db(expected_sql, table_id)
                    result["expected_result"] = expected_result
                
                if predicted_sql:
                    predicted_result = self.execute_sql_on_db(predicted_sql, table_id)
                    result["predicted_result"] = predicted_result
                    
                    # 比较结果
                    if expected_result is not None and predicted_result is not None:
                        result["correct"] = expected_result == predicted_result
                    
            except Exception as e:
                result["error"] = f"SQL执行错误: {str(e)}"
            
        except Exception as e:
            result["error"] = f"评估错误: {str(e)}"
        
        return result
    
    def evaluate(self) -> Dict[str, Any]:
        """执行完整评估"""
        logger.info("开始评估...")
        
        # 加载数据
        questions = self.load_source_data()
        predictions = self.load_predictions()
        
        # 确保数量匹配
        min_count = min(len(questions), len(predictions))
        if len(questions) != len(predictions):
            logger.warning(f"问题数量({len(questions)})和预测数量({len(predictions)})不匹配，使用较小值: {min_count}")
            logger.info(f"注意：这是正常的，因为我们只生成了前{len(predictions)}个问题的预测")
        
        # 逐个评估
        results = []
        correct_count = 0
        error_count = 0
        
        logger.info(f"评估 {min_count} 个问题...")
        
        for i in range(min_count):
            if i % 10 == 0:
                logger.info(f"进度: {i}/{min_count}")
            
            question = questions[i]
            prediction = predictions[i]
            
            eval_result = self.evaluate_single(question, prediction)
            results.append(eval_result)
            
            if eval_result["correct"]:
                correct_count += 1
            if eval_result["error"]:
                error_count += 1
        
        # 计算统计信息
        accuracy = correct_count / min_count if min_count > 0 else 0
        error_rate = error_count / min_count if min_count > 0 else 0
        
        summary = {
            "total_questions": min_count,
            "correct_answers": correct_count,
            "errors": error_count,
            "accuracy": accuracy,
            "error_rate": error_rate,
            "results": results
        }
        
        logger.info(f"评估完成!")
        logger.info(f"总问题数: {min_count}")
        logger.info(f"正确答案: {correct_count}")
        logger.info(f"错误数量: {error_count}")
        logger.info(f"准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")
        logger.info(f"错误率: {error_rate:.4f} ({error_rate*100:.2f}%)")
        
        return summary
    
    def save_detailed_report(self, summary: Dict, output_file: str = "evaluation_report.json"):
        """保存详细评估报告"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"详细报告已保存: {output_file}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
    
    def print_sample_results(self, summary: Dict, num_samples: int = 5):
        """打印样本结果"""
        results = summary.get("results", [])
        
        print(f"\n{'='*60}")
        print(f"样本结果 (前{num_samples}个):")
        print(f"{'='*60}")
        
        for i, result in enumerate(results[:num_samples]):
            print(f"\n问题 {i+1}:")
            print(f"  ID: {result['question_id']}")
            print(f"  问题: {result['question'][:100]}...")
            print(f"  正确: {result['correct']}")
            
            if result['error']:
                print(f"  错误: {result['error']}")
            else:
                print(f"  预期SQL: {result['expected_sql']}")
                print(f"  预测SQL: {result['predicted_sql']}")
                print(f"  预期结果: {result['expected_result']}")
                print(f"  预测结果: {result['predicted_result']}")
            
            print(f"  {'-'*50}")

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) != 4:
        print("用法: python wikisql_validator.py <source_file> <db_file> <predictions_file>")
        print("示例: python wikisql_validator.py data/dev.jsonl data/dev.db predictions.jsonl")
        return
    
    source_file = sys.argv[1]
    db_file = sys.argv[2]
    predictions_file = sys.argv[3]
    
    try:
        # 创建验证器
        validator = WikiSQLValidator(source_file, db_file, predictions_file)
        
        # 执行评估
        summary = validator.evaluate()
        
        # 保存详细报告
        validator.save_detailed_report(summary)
        
        # 打印样本结果
        validator.print_sample_results(summary)
        
        # 打印最终结果
        print(f"\n{'='*60}")
        print(f"最终评估结果:")
        print(f"{'='*60}")
        print(f"总问题数: {summary['total_questions']}")
        print(f"正确答案: {summary['correct_answers']}")
        print(f"错误数量: {summary['errors']}")
        print(f"准确率: {summary['accuracy']:.4f} ({summary['accuracy']*100:.2f}%)")
        print(f"错误率: {summary['error_rate']:.4f} ({summary['error_rate']*100:.2f}%)")
        print(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"验证失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()