# WikiSQL Heavy System - 智能SQL查询分析平台

一个先进的WikiSQL数据集评估系统，集成了多智能体架构和自动验证功能，支持标准LLM查询、Heavy多智能体分析和智能对比测试，为SQL查询生成提供工业级的分析能力和可靠性。

## ✨ 核心特性

- 🎯 **三种查询模式**: 标准LLM查询 / Heavy多智能体分析 / 智能对比测试
- 🤖 **Google AI支持**: 使用Google AI Studio进行智能分析 
- 🧠 **4智能体协作**: SQL专家、数据分析师、性能优化师、结果验证师协同工作
- 🔍 **自动验证系统**: 每个预测都通过WikiSQL官方validator验证
- 📊 **实时监控**: 即时显示处理状态、置信度和分析结果
- 🛠️ **跨平台兼容**: 完美支持Windows/Linux/Mac，解决所有编码问题
- 📈 **性能对比分析**: 标准查询 vs Heavy查询的详细对比报告

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装依赖
pip install -r requirements.txt

# 确保WikiSQL数据集在项目目录中
# 项目会自动检测 WikiSQL/ 目录
```

### 2. 智能查询测试 (推荐)
```bash
# 启动智能测试系统 - 支持三种查询模式
python wikisql_heavy_integration.py
```
**功能特色:**
- 🎯 **模式选择**: 标准LLM / Heavy多智能体 / 对比测试
- 📊 **数据配置**: 自定义数据分割和测试数量
- 🔍 **自动验证**: 每个结果都通过WikiSQL validator验证
- 📈 **实时统计**: 处理状态、置信度、分析结果实时显示

### 3. 批量预测生成
```bash
# 生成大规模预测文件
python generate_wikisql_predictions.py
```
**支持功能:**
- Standard Query (标准查询, 快速响应)
- Heavy Query (4个智能体协同分析)

### 4. 独立验证工具
```bash
# 验证现有预测文件
python run_validation.py
```

## 📁 项目结构

```
WikiSQL-Heavy-System/
├── 🎯 主要入口程序
│   ├── wikisql_heavy_integration.py   # 🌟 智能测试系统 (推荐使用)
│   ├── generate_wikisql_predictions.py # 批量预测生成器
│   └── run_validation.py              # 独立验证工具
│
├── 🔧 核心查询引擎
│   ├── wikisql_llm_direct.py          # 标准LLM查询引擎
│   ├── wikisql_validator.py           # WikiSQL验证器
│   ├── wikisql_data_loader.py         # 智能数据加载器
│   └── wikisql_database_manager.py    # 数据库管理器
│
├── 🧠 多智能体框架 (Heavy模式核心)
│   ├── make-it-heavy/
│   │   ├── orchestrator.py           # 多智能体编排器
│   │   ├── agent.py                  # 智能体核心
│   │   ├── config.yaml               # Heavy配置文件
│   │   └── tools/                    # 智能体工具集
│   │       ├── calculator_tool.py    # 计算工具
│   │       ├── search_tool.py        # 搜索工具
│   │       └── task_done_tool.py     # 任务完成工具
│
├── 📊 数据集和文档
│   ├── WikiSQL/                      # WikiSQL官方数据集
│   │   ├── data/                     # 训练/验证/测试数据
│   │   ├── lib/                      # 官方评估库
│   │   └── evaluate.py               # 官方评估器
│   ├── README.md                     # 项目文档
│   ├── WikiSQL_Heavy_System_Architecture.md # 系统架构
│   └── requirements.txt              # 依赖配置
│
└── 📈 输出文件 (自动生成)
    ├── *_predictions_*.jsonl         # 预测结果文件
    ├── *_batch_results_*.json        # 批量测试结果
    ├── comparison_results_*.json     # 对比测试结果
    └── evaluation_report_*.json      # 验证报告
```

## 🎯 使用示例

### 🌟 智能测试系统 (一键启动)
```bash
python wikisql_heavy_integration.py
```
**交互式选择:**
```
🎯 选择查询模式:
1. 标准LLM查询 (单一LLM生成SQL)
2. Heavy多智能体查询 (4个智能体协作分析)  
3. 对比模式 (标准 vs Heavy 对比测试)

📋 选择数据分割: dev/test/train
📊 选择测试数量: 3/10/50/自定义
🔍 选择测试方式: 单个详细/批量测试
```


### 🔧 编程接口使用
```python
from wikisql_heavy_integration import WikiSQLDirectLLMHeavy

# 初始化Heavy系统
assistant = WikiSQLDirectLLMHeavy(api_key="your_api_key")
assistant.load_wikisql_dataset("dev", limit=10)

# Heavy多智能体查询
heavy_result = assistant.query_with_heavy("How many players are from USA?")

# 查看分析结果
analysis = heavy_result["heavy_analysis"]
print(f"置信度: {analysis['overall_confidence']:.3f}")
print(f"智能体分析: {analysis['synthesis']['valid_analyses']}/4")
print(f"SQL: {heavy_result['basic_sql']}")
```

### 📈 批量预测生成
```python
# 大规模预测生成
python generate_wikisql_predictions.py

# 支持选择:
# - 模型: Gemini 2.5 Flash / Gemma 3 27B IT
# - 模式: Standard / Heavy
# - 数据: dev/test/train
# - 数量: 自定义
```

## 🔧 配置选项

### 🎯 查询模式详解

#### 1. 标准LLM查询
- **特点**: 单个LLM直接生成SQL
- **速度**: 快速 (~100问题/分钟)
- **特点**: 快速响应
- **适用**: 大规模批量处理、快速原型验证

#### 2. Heavy多智能体查询
- **特点**: 4个专门智能体协作分析
  - 🔧 **SQL语法专家**: 语法正确性和优化
  - 📊 **数据分析师**: 查询逻辑和数据理解
  - ⚡ **性能优化师**: 查询性能和效率
  - ✅ **结果验证师**: 结果准确性验证
- **速度**: 中等 (~25问题/分钟)
- **特点**: 深度分析 (多智能体协作)
- **适用**: 复杂查询分析、深度分析场景

#### 3. 对比测试模式
- **功能**: 同时运行标准和Heavy查询
- **输出**: 详细对比报告和改进分析
- **适用**: 性能评估、方法验证

### 🤖 模型配置

#### Gemini 2.5 Flash
#### Gemma 3 27B IT

## ⚠️ 使用注意事项

### 🔑 API配置
- **API密钥**: 确保有效的gemini兼容API密钥
- **配额管理**: Heavy模式消耗更多API调用，注意配额限制
- **网络连接**: 首次运行需要下载WikiSQL数据集

### 📊 数据要求
- **WikiSQL数据集**: 确保`WikiSQL/`目录存在于项目根目录
- **磁盘空间**: 至少需要500MB用于数据集和输出文件
- **内存要求**: 建议8GB+内存用于大规模测试

### ⚡ 性能考虑
- **Heavy模式**: 处理时间较长，适合小到中等规模测试
- **批量处理**: 大规模测试建议使用标准模式
- **并发限制**: 避免同时运行多个Heavy测试实例

## 🛠️ 故障排除

### 🔧 常见问题解决

#### 1. 依赖安装问题
```bash
# 升级核心依赖
pip install --upgrade langchain-openai pandas sqlalchemy

# 如果遇到版本冲突
pip install -r requirements.txt --force-reinstall
```

#### 2. WikiSQL数据集问题
```bash
# 检查数据集结构
ls WikiSQL/data/
# 应该包含: dev.jsonl, dev.db, test.jsonl, test.db 等

# 如果数据集缺失，重新下载
git clone https://github.com/salesforce/WikiSQL.git
```

#### 3. API连接问题
```bash
# 测试API连接
python -c "
import os
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', google_api_key='your_google_api_key')
print('API连接正常')
"
```

#### 4. 编码问题 (已解决)
- ✅ 项目已完美解决Windows编码问题
- ✅ 自定义验证器支持所有平台
- ✅ UTF-8编码处理所有文件操作

### 🚨 错误代码对照

| 错误类型 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `API key not found` | Google API密钥未设置 | 设置GOOGLE_API_KEY环境变量 |
| `WikiSQL data not found` | 数据集路径错误 | 确保WikiSQL目录在项目根目录 |
| `Heavy analysis failed` | 智能体初始化失败 | 检查make-it-heavy配置文件 |
| `Validation error` | 预测格式错误 | 检查SQL解析和WikiSQL格式转换 |

### 🎯 优势总结
- **分析深度领先**: Heavy模式多智能体协作，超越传统单模型方案
- **智能化程度**: 唯一提供置信度评估和智能建议的方案
- **用户体验**: 一键启动，交互式配置，实时反馈
- **可靠性**: 每个预测都经过验证，确保结果可信

## 🤖 Heavy多智能体架构

### 🧠 智能体协作机制
本项目的Heavy模式采用4个专门智能体协同协作：

```
🔧 SQL语法专家     📊 数据分析师
     ↓                ↓
   语法检查          逻辑分析
   优化建议          数据理解
     ↓                ↓
     🤝 ← 协作分析 → 🤝
     ↓                ↓
⚡ 性能优化师     ✅ 结果验证师
     ↓                ↓
   性能评估          准确性验证
   效率优化          可靠性检查
```

### 🔄 分析流程
1. **协同分析**: 4个智能体从不同角度分工分析问题
2. **置信度评估**: 每个智能体提供0.0-1.0的置信度评分
3. **结果合成**: 智能合成多个分析结果
4. **最终验证**: 通过WikiSQL validator验证准确性

### 🎯 技术优势
- **多角度覆盖**: 语法、逻辑、性能、验证四个维度全覆盖
- **智能评分**: 基于多智能体一致性的置信度评估
- **自适应优化**: 根据分析结果动态调整SQL生成策略
- **实时反馈**: 每个步骤都有详细的分析报告

## 🔧 系统架构

### 📊 技术栈
```
🎯 用户界面层
├── wikisql_heavy_integration.py    # 交互式测试系统
├── generate_wikisql_predictions.py # 批量预测生成
└── run_validation.py               # 独立验证工具

🧠 智能分析层  
├── WikiSQLDirectLLM                # 标准LLM引擎
├── WikiSQLDirectLLMHeavy           # Heavy多智能体引擎
└── WikiSQLHeavyOrchestrator        # 智能体编排器

🔍 验证评估层
├── WikiSQLValidator                # 自定义验证器
├── 实时状态监控                     # 即时反馈系统
└── 对比分析报告                     # 性能对比工具

📊 数据管理层
├── WikiSQLDataLoader               # 智能数据加载
├── WikiSQLDatabaseManager          # 数据库管理
└── 跨平台编码处理                   # UTF-8兼容
```

### 🚀 核心创新
- **智能体专业化**: 每个智能体都有明确的专业领域
- **协作机制**: 智能体间的信息共享和结果合成
- **自动验证**: 每个预测都经过严格验证
- **性能监控**: 实时追踪处理状态和分析效率

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License