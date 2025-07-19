# WikiSQL 直接LLM评估器

一个简洁高效的WikiSQL数据集评估工具，使用直接LLM方案生成和执行SQL查询，支持Gemini 2.5 Flash和Gemma 3 27B模型。

## ✨ 核心特性

- 🤖 **双模型支持**: Gemini 2.5 Flash (快速) 和 Gemma 3 27B IT (高精度)
- 🔧 **直接LLM方案**: 无需复杂Agent框架，直接生成和执行SQL
- 📊 **完整评估流程**: 自动数据加载、预测生成、结果验证
- 🛠️ **解决编码问题**: 自定义验证器完美处理Windows编码问题
- 🎯 **高准确率**: 已验证79%+的准确率表现

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行简单示例
```bash
python simple_example.py
```

### 3. 生成预测文件
```bash
python generate_wikisql_predictions.py
```
支持模型选择：
- Gemini 2.5 Flash (推荐，速度快)
- Gemma 3 27B IT (精度高)

### 4. 验证预测结果
```bash
python run_validation.py
```

## 📁 项目结构

```
WikiSQL项目/
├── 🔧 核心组件
│   ├── wikisql_llm_direct.py          # 主要LLM查询助手
│   ├── wikisql_validator.py           # 自定义验证器
│   ├── wikisql_data_loader.py         # 数据加载器
│   └── wikisql_database_manager.py    # 数据库管理器
│
├── 🚀 执行脚本
│   ├── simple_example.py              # 快速示例
│   ├── generate_wikisql_predictions.py # 预测生成器
│   └── run_validation.py              # 验证器
│
├── 📊 数据
│   └── WikiSQL/                       # WikiSQL原始数据集
│
└── ⚙️ 配置
    └── requirements.txt               # 统一依赖管理
```

## 🎯 使用示例

### 基础用法
```python
from wikisql_llm_direct import WikiSQLDirectLLM

# 初始化助手
assistant = WikiSQLDirectLLM(api_key="your_api_key")

# 加载数据集
assistant.load_wikisql_dataset("dev", limit=10)

# 执行查询
result = assistant.query("What is the position of player number 23?")
print(f"结果: {result}")
```

### 批量评估
```python
# 生成预测文件
predictions_file = assistant.generate_predictions_file("predictions.jsonl", limit=100)

# 批量评估
results = assistant.batch_evaluate(limit=50)
```

## 🔧 配置选项

### 模型选择
- **Gemini 2.5 Flash**: 速度快，成本低，适合大规模处理
- **Gemma 3 27B IT**: 精度高，适合追求最佳准确率

### 数据集配置
```python
assistant.load_wikisql_dataset(
    split="dev",              # train/dev/test
    limit=100,                # 限制问题数量
    force_download=False      # 强制重新下载
)
```

## 📊 性能表现

- **准确率**: 79%+ (Gemini 2.5 Flash)
- **处理速度**: ~100问题/分钟
- **编码兼容**: 完美支持Windows/Linux/Mac
- **内存使用**: 优化的数据加载机制

## ⚠️ 注意事项

1. **API配额**: 注意模型使用限制
2. **网络连接**: 首次运行需下载数据集
3. **编码问题**: 已通过自定义验证器解决
4. **准确率**: 不同模型表现可能有差异

## 🛠️ 故障排除

### 常见问题
```bash
# 依赖问题
pip install --upgrade langchain-openai pandas sqlalchemy

# 编码错误（已解决）
python run_validation.py  # 使用自定义验证器

# API连接问题
# 检查API密钥和网络连接
```

## 📈 与官方方案对比

| 特性 | 官方评估器 | 本项目 |
|------|------------|--------|
| 编码支持 | ❌ Windows问题 | ✅ 完美支持 |
| 模型选择 | ❌ 固定 | ✅ 双模型 |
| 易用性 | ❌ 复杂 | ✅ 简单 |
| 准确率 | - | ✅ 79%+ |
| 调试性 | ❌ 困难 | ✅ 透明 |

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License