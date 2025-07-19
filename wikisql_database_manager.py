"""
WikiSQL数据库管理器
负责根据WikiSQL数据动态创建和管理SQLite数据库表格
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, Float, Boolean
from sqlalchemy.engine import Engine
from langchain_community.utilities import SQLDatabase

from wikisql_data_loader import WikiSQLTable, WikiSQLQuestion

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikiSQLDatabaseManager:
    """WikiSQL数据库管理器"""
    
    def __init__(self, db_path: str = ":memory:"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库路径，默认使用内存数据库
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.metadata = MetaData()
        self.created_tables: Dict[str, str] = {}  # table_id -> table_name mapping
        
        # 创建LangChain SQL数据库对象
        self.sql_db = SQLDatabase(self.engine)
        
        logger.info(f"数据库管理器初始化完成: {db_path}")
    
    def _map_wikisql_type_to_sql(self, wikisql_type: str) -> str:
        """
        将WikiSQL数据类型映射到SQL数据类型
        
        Args:
            wikisql_type: WikiSQL数据类型
            
        Returns:
            SQL数据类型
        """
        type_mapping = {
            'text': 'TEXT',
            'real': 'REAL', 
            'number': 'INTEGER',
            'integer': 'INTEGER'
        }
        return type_mapping.get(wikisql_type.lower(), 'TEXT')
    
    def _infer_column_type(self, values: List[str], declared_type: str = "text") -> str:
        """
        推断列的数据类型
        
        Args:
            values: 列的所有值
            declared_type: 声明的类型
            
        Returns:
            SQLite数据类型
        """
        if not values:
            return "TEXT"
        
        # 如果声明类型是real，直接返回REAL
        if declared_type.lower() == "real":
            return "REAL"
        
        # 统计不同类型的值
        int_count = 0
        float_count = 0
        total_count = len(values)
        
        for value in values:
            if value is None or value == "":
                continue
                
            str_value = str(value).strip()
            if not str_value:
                continue
            
            # 尝试转换为整数
            try:
                int(str_value)
                int_count += 1
                continue
            except ValueError:
                pass
            
            # 尝试转换为浮点数
            try:
                float(str_value)
                float_count += 1
                continue
            except ValueError:
                pass
        
        # 根据统计结果决定类型
        numeric_count = int_count + float_count
        if numeric_count > total_count * 0.8:  # 80%以上是数字
            if float_count > 0:
                return "REAL"
            else:
                return "INTEGER"
        
        return "TEXT"
    
    def _sanitize_table_name(self, table_id: str) -> str:
        """
        清理表格名称，确保符合SQL标准
        
        Args:
            table_id: 原始表格ID
            
        Returns:
            清理后的表格名称
        """
        # 移除特殊字符，只保留字母、数字和下划线
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(table_id))
        
        # 确保以字母开头
        if clean_name and clean_name[0].isdigit():
            clean_name = f"table_{clean_name}"
        
        # 确保不为空
        if not clean_name:
            clean_name = "table_unknown"
        
        return clean_name
    
    def _sanitize_column_name(self, column_name: str) -> str:
        """
        清理列名，确保符合SQL标准
        
        Args:
            column_name: 原始列名
            
        Returns:
            清理后的列名
        """
        import re
        # 移除特殊字符，只保留字母、数字和下划线
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(column_name))
        
        # 移除连续的下划线
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # 移除开头和结尾的下划线
        clean_name = clean_name.strip('_')
        
        # 确保以字母开头
        if clean_name and clean_name[0].isdigit():
            clean_name = f"col_{clean_name}"
        
        # 确保不为空
        if not clean_name:
            clean_name = "col_unknown"
        
        # 避免SQL关键字
        sql_keywords = {'select', 'from', 'where', 'order', 'group', 'by', 'having', 'limit'}
        if clean_name.lower() in sql_keywords:
            clean_name = f"{clean_name}_col"
        
        return clean_name
    
    def create_table_from_wikisql(self, wikisql_table: WikiSQLTable, use_col_format: bool = True) -> str:
        """
        根据WikiSQL表格创建数据库表格
        
        Args:
            wikisql_table: WikiSQL表格对象
            
        Returns:
            创建的表格名称
        """
        table_name = self._sanitize_table_name(wikisql_table.id)
        
        # 如果表格已存在，先删除
        if table_name in self.created_tables.values():
            self.drop_table(table_name)
        
        logger.info(f"正在创建表格: {table_name} (原ID: {wikisql_table.id})")
        
        try:
            # 根据参数决定使用哪种列名格式
            if use_col_format:
                # 使用col0, col1, col2...格式，与官方WikiSQL保持一致
                clean_headers = [f"col{i}" for i in range(len(wikisql_table.header))]
                logger.info(f"使用col格式列名: {clean_headers}")
            else:
                # 使用清理后的原始列名
                clean_headers = [self._sanitize_column_name(header) for header in wikisql_table.header]
            
            # 检查重复列名
            seen_headers = set()
            for i, header in enumerate(clean_headers):
                original_header = header
                counter = 1
                while header in seen_headers:
                    header = f"{original_header}_{counter}"
                    counter += 1
                clean_headers[i] = header
                seen_headers.add(header)
            
            # 推断列类型
            column_types = []
            for i, header in enumerate(clean_headers):
                # 获取该列的所有值
                column_values = [row[i] if i < len(row) else None for row in wikisql_table.rows]
                declared_type = wikisql_table.types[i] if i < len(wikisql_table.types) else "text"
                column_type = self._infer_column_type(column_values, declared_type)
                column_types.append(column_type)
            
            # 构建CREATE TABLE语句
            column_definitions = []
            for header, col_type in zip(clean_headers, column_types):
                column_definitions.append(f'"{header}" {col_type}')
            
            create_sql = f'''
                CREATE TABLE "{table_name}" (
                    {', '.join(column_definitions)}
                )
            '''
            
            # 执行创建表格
            with self.engine.connect() as conn:
                conn.execute(text(create_sql))
                conn.commit()
            
            # 插入数据
            self._insert_table_data(table_name, clean_headers, wikisql_table.rows)
            
            # 记录创建的表格
            self.created_tables[wikisql_table.id] = table_name
            
            logger.info(f"表格创建成功: {table_name} ({len(wikisql_table.rows)} 行)")
            return table_name
            
        except Exception as e:
            logger.error(f"创建表格失败: {e}")
            raise
    
    def _insert_table_data(self, table_name: str, headers: List[str], rows: List[List[Any]]):
        """
        插入表格数据
        
        Args:
            table_name: 表格名称
            headers: 列名列表
            rows: 数据行列表
        """
        if not rows:
            logger.info(f"表格 {table_name} 没有数据需要插入")
            return
        
        # 构建INSERT语句
        placeholders = ', '.join([f':{header}' for header in headers])
        column_names = ', '.join([f'"{h}"' for h in headers])
        insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
        
        try:
            with self.engine.connect() as conn:
                for row_idx, row in enumerate(rows):
                    try:
                        # 准备数据，确保长度匹配
                        row_data = {}
                        for i, header in enumerate(headers):
                            value = row[i] if i < len(row) else None
                            # 处理空值
                            if value == '' or value is None:
                                row_data[header] = None
                            else:
                                row_data[header] = value
                        
                        conn.execute(text(insert_sql), row_data)
                        
                    except Exception as e:
                        logger.warning(f"插入第 {row_idx + 1} 行数据失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"数据插入失败: {e}")
            raise
    
    def drop_table(self, table_name: str):
        """
        删除表格
        
        Args:
            table_name: 表格名称
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                conn.commit()
            
            # 从记录中移除
            for table_id, name in list(self.created_tables.items()):
                if name == table_name:
                    del self.created_tables[table_id]
                    break
            
            logger.info(f"表格已删除: {table_name}")
            
        except Exception as e:
            logger.error(f"删除表格失败: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> str:
        """
        获取表格信息
        
        Args:
            table_name: 表格名称
            
        Returns:
            表格结构信息
        """
        try:
            with self.engine.connect() as conn:
                # 获取表格结构
                result = conn.execute(text(f'PRAGMA table_info("{table_name}")'))
                columns = result.fetchall()
                
                # 获取行数
                count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                row_count = count_result.fetchone()[0]
                
                info = f"表格: {table_name}\n"
                info += f"行数: {row_count}\n"
                info += "列信息:\n"
                
                for col in columns:
                    info += f"  - {col[1]} ({col[2]})\n"
                
                return info
                
        except Exception as e:
            logger.error(f"获取表格信息失败: {e}")
            return f"错误: {e}"
    
    def list_tables(self) -> List[str]:
        """
        列出所有表格
        
        Returns:
            表格名称列表
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result.fetchall()]
                return tables
                
        except Exception as e:
            logger.error(f"列出表格失败: {e}")
            return []
    
    def _init_langchain_db(self):
        """重新初始化LangChain数据库连接"""
        try:
            self.sql_db = SQLDatabase.from_uri(
                f"sqlite:///{self.db_path}",
                include_tables=None,  # 包含所有表格
                sample_rows_in_table_info=3
            )
            logger.info("LangChain数据库连接已重新初始化")
        except Exception as e:
            logger.error(f"重新初始化LangChain数据库失败: {e}")
            raise
    
    def get_langchain_db(self) -> SQLDatabase:
        """
        获取LangChain SQL数据库对象
        
        Returns:
            SQLDatabase对象
        """
        return self.sql_db
    
    def execute_query(self, query: str) -> List[Tuple]:
        """
        执行SQL查询
        
        Args:
            query: SQL查询语句
            
        Returns:
            查询结果
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                return result.fetchall()
                
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise
    
    def create_multiple_tables(self, wikisql_tables: Dict[str, WikiSQLTable]) -> Dict[str, str]:
        """
        批量创建表格
        
        Args:
            wikisql_tables: WikiSQL表格字典
            
        Returns:
            table_id -> table_name 映射
        """
        created_mapping = {}
        
        for table_id, wikisql_table in wikisql_tables.items():
            try:
                table_name = self.create_table_from_wikisql(wikisql_table)
                created_mapping[table_id] = table_name
            except Exception as e:
                logger.error(f"创建表格 {table_id} 失败: {e}")
                continue
        
        logger.info(f"批量创建完成: {len(created_mapping)}/{len(wikisql_tables)} 个表格")
        return created_mapping

def main():
    """测试数据库管理器"""
    print("=== WikiSQL数据库管理器测试 ===")
    
    # 创建管理器
    db_manager = WikiSQLDatabaseManager()
    
    # 创建测试数据
    from wikisql_data_loader import WikiSQLTable
    
    test_table = WikiSQLTable(
        id="test_table_1",
        header=["Name", "Age", "City", "Salary"],
        rows=[
            ["Alice", "25", "New York", "50000"],
            ["Bob", "30", "Los Angeles", "60000"],
            ["Charlie", "35", "Chicago", "70000"],
            ["Diana", "28", "Houston", "55000"]
        ],
        types=["text", "real", "text", "real"],
        name="Test Employee Table"
    )
    
    # 创建表格
    print("创建测试表格...")
    table_name = db_manager.create_table_from_wikisql(test_table)
    print(f"表格创建成功: {table_name}")
    
    # 显示表格信息
    print("\n表格信息:")
    print(db_manager.get_table_info(table_name))
    
    # 执行测试查询
    print("\n执行测试查询:")
    try:
        results = db_manager.execute_query(f'SELECT * FROM "{table_name}" LIMIT 3')
        print("查询结果:")
        for row in results:
            print(f"  {row}")
    except Exception as e:
        print(f"查询失败: {e}")
    
    # 列出所有表格
    print(f"\n所有表格: {db_manager.list_tables()}")

if __name__ == "__main__":
    main()