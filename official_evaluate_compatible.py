#!/usr/bin/env python3
"""
兼容版WikiSQL官方评估器
解决SQLAlchemy版本兼容性问题，使用纯SQLite替代records库
"""

import json
import sqlite3
import sys
from argparse import ArgumentParser
from tqdm import tqdm
from pathlib import Path

def count_lines(filename):
    """计算文件行数"""
    with open(filename, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

class CompatibleDBEngine:
    """兼容版数据库引擎，使用纯SQLite替代records库"""
    
    def __init__(self, db_file):
        """初始化数据库连接"""
        self.db_file = db_file
        print(f"Connecting to database: {db_file}")
        
        # 测试连接
        try:
            conn = sqlite3.connect(db_file)
            conn.close()
            print("Database connection successful")
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise
    
    def execute_query(self, table_id, query, lower=True):
        """执行查询"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 构建SQL查询
            sql = self._build_sql(table_id, query)
            
            # 执行查询
            cursor.execute(sql)
            result = cursor.fetchall()
            
            conn.close()
            
            # 处理结果
            if lower:
                # 将字符串结果转为小写
                processed_result = []
                for row in result:
                    processed_row = []
                    for cell in row:
                        if isinstance(cell, str):
                            processed_row.append(cell.lower())
                        else:
                            processed_row.append(cell)
                    processed_result.append(tuple(processed_row))
                return processed_result
            else:
                return result
                
        except Exception as e:
            print(f"Query execution failed: {sql}, error: {e}")
            return None
    
    def _build_sql(self, table_id, query):
        """构建SQL查询"""
        # 获取表名
        table_name = self._get_table_name(table_id)
        
        # 获取列信息
        columns = self._get_columns(table_name)
        
        # 解析查询
        sel = query.get('sel', 0)
        agg = query.get('agg', 0)
        conds = query.get('conds', [])
        
        # 聚合函数映射
        agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
        
        # 构建SELECT部分
        if sel < len(columns):
            col_name = columns[sel][1]
        else:
            col_name = columns[0][1]
        
        if agg > 0 and agg < len(agg_ops):
            select_part = f"{agg_ops[agg]}({col_name})"
        else:
            select_part = col_name
        
        # 构建WHERE部分
        where_parts = []
        if conds:
            for cond in conds:
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
                            # 处理SQL注入
                            escaped_val = str(cond_val).replace("'", "''")
                            where_parts.append(f"{cond_col_name} {op} '{escaped_val}'")
        
        # 组装SQL
        sql = f"SELECT {select_part} FROM {table_name}"
        if where_parts:
            sql += f" WHERE {' AND '.join(where_parts)}"
        
        return sql
    
    def _get_table_name(self, table_id):
        """获取表名"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 查找匹配的表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        table_name = None
        for (name,) in tables:
            if table_id in name or name.endswith(table_id.replace('-', '_')):
                table_name = name
                break
        
        if not table_name and tables:
            table_name = tables[0][0]  # 使用第一个表作为默认
        
        conn.close()
        
        if not table_name:
            raise Exception(f"Table not found: {table_id}")
        
        return table_name
    
    def _get_columns(self, table_name):
        """获取列信息"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        conn.close()
        
        if not columns:
            raise Exception(f"Table {table_name} has no column info")
        
        return columns

class CompatibleQuery:
    """兼容版查询类"""
    
    def __init__(self, sel, agg, conds, ordered=False):
        self.sel = sel
        self.agg = agg
        self.conds = conds if conds else []
        self.ordered = ordered
    
    @classmethod
    def from_dict(cls, query_dict, ordered=False):
        """从字典创建查询对象"""
        return cls(
            sel=query_dict.get('sel', 0),
            agg=query_dict.get('agg', 0),
            conds=query_dict.get('conds', []),
            ordered=ordered
        )
    
    def __eq__(self, other):
        """比较两个查询是否相等"""
        if not isinstance(other, CompatibleQuery):
            return False
        
        # 比较基本字段
        if self.sel != other.sel or self.agg != other.agg:
            return False
        
        # 比较条件
        if self.ordered:
            return self.conds == other.conds
        else:
            # 无序比较
            return sorted(self.conds) == sorted(other.conds)

def main():
    """主函数"""
    parser = ArgumentParser()
    parser.add_argument('source_file', help='source file for the prediction')
    parser.add_argument('db_file', help='source database for the prediction')
    parser.add_argument('pred_file', help='predictions by the model')
    parser.add_argument('--ordered', action='store_true', help='whether the exact match should consider the order of conditions')
    args = parser.parse_args()

    print("=" * 60)
    print("Compatible WikiSQL Official Evaluator")
    print("=" * 60)
    print(f"Source file: {args.source_file}")
    print(f"Database: {args.db_file}")
    print(f"Predictions: {args.pred_file}")
    print(f"Ordered: {args.ordered}")
    print("=" * 60)

    # 初始化数据库引擎
    engine = CompatibleDBEngine(args.db_file)
    
    exact_match = []
    execution_accuracy = []
    
    print("Starting evaluation...")
    
    with open(args.source_file, encoding='utf-8') as fs, open(args.pred_file, encoding='utf-8') as fp:
        total_lines = count_lines(args.source_file)
        
        for ls, lp in tqdm(zip(fs, fp), total=total_lines, desc="Progress"):
            try:
                eg = json.loads(ls)
                ep = json.loads(lp)
                
                # 构建期望查询
                qg = CompatibleQuery.from_dict(eg['sql'], ordered=args.ordered)
                
                # 执行期望查询
                gold = engine.execute_query(eg['table_id'], eg['sql'], lower=True)
                
                # 处理预测
                pred = ep.get('error', None)
                qp = None
                
                if not ep.get('error', None):
                    try:
                        qp = CompatibleQuery.from_dict(ep['query'], ordered=args.ordered)
                        pred = engine.execute_query(eg['table_id'], ep['query'], lower=True)
                    except Exception as e:
                        pred = repr(e)
                
                # 计算准确率
                correct = pred == gold
                match = qp == qg if qp is not None else False
                
                execution_accuracy.append(correct)
                exact_match.append(match)
                
            except Exception as e:
                print(f"Error processing line: {e}")
                execution_accuracy.append(False)
                exact_match.append(False)
                continue
    
    # 计算最终结果
    ex_acc = sum(execution_accuracy) / len(execution_accuracy) if execution_accuracy else 0
    lf_acc = sum(exact_match) / len(exact_match) if exact_match else 0
    
    result = {
        'ex_accuracy': ex_acc,
        'lf_accuracy': lf_acc,
    }
    
    print("\n" + "=" * 60)
    print("Evaluation Results:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)
    print(f"Execution Accuracy: {ex_acc:.4f} ({ex_acc*100:.2f}%)")
    print(f"Logical Form Accuracy: {lf_acc:.4f} ({lf_acc*100:.2f}%)")
    print(f"Total samples: {len(execution_accuracy)}")
    print("=" * 60)

if __name__ == '__main__':
    main()