# 修复WikiSQL数据路径
# 将以下代码添加到你的脚本中：

from wikisql_heavy_simple import WikiSQLDirectLLMSimpleHeavy

# 方法1: 在初始化时指定路径
assistant = WikiSQLDirectLLMSimpleHeavy(api_key)
assistant.data_loader.local_wikisql_path = "WikiSQL"

# 方法2: 直接修改WikiSQLDataLoader
from wikisql_data_loader import WikiSQLDataLoader
WikiSQLDataLoader.__init__ = lambda self, data_dir="data", local_wikisql_path="WikiSQL": setattr(self, 'data_dir', Path(data_dir)) or setattr(self, 'local_wikisql_path', Path(local_wikisql_path) if local_wikisql_path else None) or setattr(self, 'url_sources', []) or setattr(self, 'urls', {}) or setattr(self, '_tables_cache', {}) or setattr(self, '_questions_cache', {})