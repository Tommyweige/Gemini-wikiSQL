"""
WikiSQL数据加载器
负责下载、解析和管理WikiSQL数据集
"""

import os
import json
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WikiSQLTable:
    """WikiSQL表格数据结构"""
    id: str
    header: List[str]
    rows: List[List[str]]
    types: List[str]
    name: str = ""
    
    def __post_init__(self):
        """验证数据完整性"""
        if len(self.header) != len(self.types):
            logger.warning(f"表格 {self.id}: header和types长度不匹配")
        
        for i, row in enumerate(self.rows):
            if len(row) != len(self.header):
                logger.warning(f"表格 {self.id}, 行 {i}: 列数不匹配")

@dataclass 
class WikiSQLQuestion:
    """WikiSQL问题数据结构"""
    id: str
    question: str
    sql: Dict
    table_id: str
    phase: int = 1
    
    def get_sql_string(self) -> str:
        """将SQL字典转换为SQL字符串（简化版）"""
        try:
            # 这是一个简化的SQL重建，实际的WikiSQL SQL结构更复杂
            agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
            cond_ops = ['=', '>', '<', 'OP']
            
            sql_parts = []
            
            # SELECT部分
            if 'agg' in self.sql and 'sel' in self.sql:
                agg_idx = self.sql['agg']
                sel_idx = self.sql['sel']
                if agg_idx == 0:
                    sql_parts.append(f"SELECT col{sel_idx}")
                else:
                    sql_parts.append(f"SELECT {agg_ops[agg_idx]}(col{sel_idx})")
            
            # FROM部分
            sql_parts.append("FROM table")
            
            # WHERE部分
            if 'conds' in self.sql and self.sql['conds']:
                where_parts = []
                for cond in self.sql['conds']:
                    if len(cond) >= 3:
                        col_idx, op_idx, value = cond[0], cond[1], cond[2]
                        op = cond_ops[op_idx] if op_idx < len(cond_ops) else '='
                        where_parts.append(f"col{col_idx} {op} '{value}'")
                
                if where_parts:
                    sql_parts.append("WHERE " + " AND ".join(where_parts))
            
            return " ".join(sql_parts)
            
        except Exception as e:
            logger.error(f"SQL重建失败: {e}")
            return str(self.sql)

class WikiSQLDataLoader:
    """WikiSQL数据加载器"""
    
    def __init__(self, data_dir: str = "data", local_wikisql_path: str = None):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据存储目录
            local_wikisql_path: 本地WikiSQL项目路径（如果提供，将直接读取本地文件）
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 本地WikiSQL路径
        self.local_wikisql_path = Path(local_wikisql_path) if local_wikisql_path else None
        
        # WikiSQL数据集URL - 多个备用源
        self.url_sources = [
            # 尝试main分支
            {
                "train": "https://github.com/salesforce/WikiSQL/raw/main/data/train.jsonl",
                "dev": "https://github.com/salesforce/WikiSQL/raw/main/data/dev.jsonl", 
                "test": "https://github.com/salesforce/WikiSQL/raw/main/data/test.jsonl",
                "train_tables": "https://github.com/salesforce/WikiSQL/raw/main/data/train.tables.jsonl",
                "dev_tables": "https://github.com/salesforce/WikiSQL/raw/main/data/dev.tables.jsonl",
                "test_tables": "https://github.com/salesforce/WikiSQL/raw/main/data/test.tables.jsonl"
            },
            # 尝试master分支
            {
                "train": "https://github.com/salesforce/WikiSQL/raw/master/data/train.jsonl",
                "dev": "https://github.com/salesforce/WikiSQL/raw/master/data/dev.jsonl", 
                "test": "https://github.com/salesforce/WikiSQL/raw/master/data/test.jsonl",
                "train_tables": "https://github.com/salesforce/WikiSQL/raw/master/data/train.tables.jsonl",
                "dev_tables": "https://github.com/salesforce/WikiSQL/raw/master/data/dev.tables.jsonl",
                "test_tables": "https://github.com/salesforce/WikiSQL/raw/master/data/test.tables.jsonl"
            }
        ]
        
        # 当前使用的URL集合
        self.urls = self.url_sources[0]
        
        # 缓存
        self._tables_cache: Dict[str, WikiSQLTable] = {}
        self._questions_cache: Dict[str, List[WikiSQLQuestion]] = {}
    
    def _get_local_file_path(self, split: str, file_type: str) -> Optional[Path]:
        """
        获取本地WikiSQL文件路径
        
        Args:
            split: 数据分割 ("train", "dev", "test")
            file_type: 文件类型 ("questions" 或 "tables")
            
        Returns:
            本地文件路径，如果不存在返回None
        """
        if not self.local_wikisql_path:
            return None
        
        # 构建文件名
        if file_type == "questions":
            filename = f"{split}.jsonl"
        elif file_type == "tables":
            filename = f"{split}.tables.jsonl"
        else:
            return None
        
        # 检查可能的路径
        possible_paths = [
            self.local_wikisql_path / "data" / filename,  # WikiSQL/data/dev.jsonl
            self.local_wikisql_path / filename,           # WikiSQL/dev.jsonl
            Path(filename)                                # 当前目录下的文件
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"找到本地文件: {path}")
                return path
        
        return None
    
    def _use_local_files(self, split: str) -> bool:
        """
        检查是否可以使用本地文件
        
        Args:
            split: 数据分割
            
        Returns:
            是否可以使用本地文件
        """
        questions_file = self._get_local_file_path(split, "questions")
        tables_file = self._get_local_file_path(split, "tables")
        
        return questions_file is not None and tables_file is not None
    
    def download_file(self, url: str, filename: str, force_download: bool = False) -> Path:
        """
        下载文件，支持多个备用源
        
        Args:
            url: 下载URL
            filename: 本地文件名
            force_download: 是否强制重新下载
            
        Returns:
            下载文件的路径
        """
        file_path = self.data_dir / filename
        
        if file_path.exists() and not force_download:
            logger.info(f"文件已存在: {file_path}")
            return file_path
        
        # 尝试所有URL源
        last_error = None
        for source_idx, url_source in enumerate(self.url_sources):
            # 找到对应的URL
            actual_url = url
            for key, source_url in url_source.items():
                if url.endswith(key + ".jsonl") or key in url:
                    actual_url = source_url
                    break
            
            logger.info(f"正在下载 (源 {source_idx + 1}/{len(self.url_sources)}): {actual_url}")
            
            try:
                response = requests.get(actual_url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 简单的进度显示
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\r下载进度: {progress:.1f}%", end="", flush=True)
                
                print()  # 换行
                logger.info(f"下载完成: {file_path}")
                
                # 更新当前使用的URL源
                self.urls = url_source
                return file_path
                
            except Exception as e:
                last_error = e
                logger.warning(f"源 {source_idx + 1} 下载失败: {e}")
                continue
        
        # 所有源都失败了
        logger.error(f"所有下载源都失败了，最后错误: {last_error}")
        raise last_error or Exception("所有下载源都不可用")
    
    def download_dataset(self, split: str = "dev", force_download: bool = False) -> Tuple[Path, Path]:
        """
        获取指定分割的数据集（优先使用本地文件）
        
        Args:
            split: 数据分割 ("train", "dev", "test")
            force_download: 是否强制重新下载
            
        Returns:
            (问题文件路径, 表格文件路径)
        """
        if split not in ["train", "dev", "test"]:
            raise ValueError(f"无效的split: {split}")
        
        # 优先检查本地文件
        if not force_download and self._use_local_files(split):
            logger.info(f"使用本地WikiSQL文件: {split}")
            questions_file = self._get_local_file_path(split, "questions")
            tables_file = self._get_local_file_path(split, "tables")
            return questions_file, tables_file
        
        # 如果没有本地文件或强制下载，则从网络下载
        logger.info(f"从网络下载WikiSQL数据: {split}")
        
        # 下载问题文件
        questions_url = self.urls[split]
        questions_file = self.download_file(
            questions_url, 
            f"{split}.jsonl", 
            force_download
        )
        
        # 下载表格文件
        tables_url = self.urls[f"{split}_tables"]
        tables_file = self.download_file(
            tables_url, 
            f"{split}.tables.jsonl", 
            force_download
        )
        
        return questions_file, tables_file
    
    def load_tables(self, tables_file: Path) -> Dict[str, WikiSQLTable]:
        """
        加载表格数据
        
        Args:
            tables_file: 表格文件路径
            
        Returns:
            表格ID到WikiSQLTable的映射
        """
        logger.info(f"正在加载表格: {tables_file}")
        tables = {}
        
        try:
            with open(tables_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        
                        table = WikiSQLTable(
                            id=data['id'],
                            header=data['header'],
                            rows=data['rows'],
                            types=data.get('types', ['text'] * len(data['header'])),
                            name=data.get('name', f"table_{data['id']}")
                        )
                        
                        tables[table.id] = table
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析错误 (行 {line_num}): {e}")
                    except Exception as e:
                        logger.error(f"表格加载错误 (行 {line_num}): {e}")
            
            logger.info(f"成功加载 {len(tables)} 个表格")
            return tables
            
        except Exception as e:
            logger.error(f"文件读取错误: {e}")
            raise
    
    def load_questions(self, questions_file: Path) -> List[WikiSQLQuestion]:
        """
        加载问题数据
        
        Args:
            questions_file: 问题文件路径
            
        Returns:
            WikiSQLQuestion列表
        """
        logger.info(f"正在加载问题: {questions_file}")
        questions = []
        
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        
                        question = WikiSQLQuestion(
                            id=str(line_num),  # 使用行号作为ID
                            question=data['question'],
                            sql=data['sql'],
                            table_id=data['table_id'],
                            phase=data.get('phase', 1)
                        )
                        
                        questions.append(question)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析错误 (行 {line_num}): {e}")
                    except Exception as e:
                        logger.error(f"问题加载错误 (行 {line_num}): {e}")
            
            logger.info(f"成功加载 {len(questions)} 个问题")
            return questions
            
        except Exception as e:
            logger.error(f"文件读取错误: {e}")
            raise
    
    def load_dataset(self, split: str = "dev", limit: Optional[int] = None, force_download: bool = False) -> Tuple[List[WikiSQLQuestion], Dict[str, WikiSQLTable]]:
        """
        加载完整数据集
        
        Args:
            split: 数据分割
            limit: 限制加载的问题数量
            force_download: 是否强制重新下载
            
        Returns:
            (问题列表, 表格字典)
        """
        # 检查缓存
        cache_key = f"{split}_{limit}"
        if cache_key in self._questions_cache and not force_download:
            logger.info("使用缓存数据")
            return self._questions_cache[cache_key], self._tables_cache
        
        # 下载数据
        questions_file, tables_file = self.download_dataset(split, force_download)
        
        # 加载数据
        tables = self.load_tables(tables_file)
        questions = self.load_questions(questions_file)
        
        # 应用限制
        if limit and limit > 0:
            questions = questions[:limit]
            logger.info(f"限制问题数量为: {limit}")
        
        # 缓存结果
        self._questions_cache[cache_key] = questions
        self._tables_cache.update(tables)
        
        return questions, tables
    
    def get_question_table_pair(self, question: WikiSQLQuestion, tables: Dict[str, WikiSQLTable]) -> Tuple[WikiSQLQuestion, Optional[WikiSQLTable]]:
        """
        获取问题对应的表格
        
        Args:
            question: WikiSQL问题
            tables: 表格字典
            
        Returns:
            (问题, 对应的表格或None)
        """
        table = tables.get(question.table_id)
        if not table:
            logger.warning(f"找不到表格: {question.table_id}")
        
        return question, table
    
    def validate_dataset(self, questions: List[WikiSQLQuestion], tables: Dict[str, WikiSQLTable]) -> Dict[str, int]:
        """
        验证数据集完整性
        
        Args:
            questions: 问题列表
            tables: 表格字典
            
        Returns:
            验证统计信息
        """
        stats = {
            "total_questions": len(questions),
            "total_tables": len(tables),
            "missing_tables": 0,
            "valid_pairs": 0
        }
        
        for question in questions:
            if question.table_id in tables:
                stats["valid_pairs"] += 1
            else:
                stats["missing_tables"] += 1
        
        logger.info(f"数据集验证结果: {stats}")
        return stats
    

def main():
    """测试数据加载器"""
    print("=== WikiSQL数据加载器测试 ===")
    
    # 创建加载器
    loader = WikiSQLDataLoader()
    
    # 加载小量数据进行测试
    print("加载dev数据集 (限制10个问题)...")
    questions, tables = loader.load_dataset("dev", limit=10)
    
    # 验证数据
    stats = loader.validate_dataset(questions, tables)
    print(f"验证结果: {stats}")
    
    # 显示示例
    if questions and tables:
        question = questions[0]
        _, table = loader.get_question_table_pair(question, tables)
        
        print(f"\n=== 示例问题 ===")
        print(f"问题: {question.question}")
        print(f"SQL: {question.get_sql_string()}")
        
        if table:
            print(f"\n=== 对应表格 ===")
            print(f"表格ID: {table.id}")
            print(f"列名: {table.header}")
            print(f"数据类型: {table.types}")
            print(f"行数: {len(table.rows)}")
            if table.rows:
                print(f"示例行: {table.rows[0]}")

if __name__ == "__main__":
    main()