# WikiSQL Heavy集成使用指南

## 🎯 概述

WikiSQL Heavy集成将"Make It Heavy"的多智能体分析系统整合到WikiSQL项目中，提供深度SQL查询分析和验证功能。

## ✨ 核心特性

### 🧠 多智能体SQL分析
- **SQL语法专家**: 专注语法正确性和优化
- **数据分析师**: 专注查询逻辑和数据理解  
- **性能优化师**: 专注查询性能和效率
- **结果验证师**: 专注结果准确性和验证

### 🔍 深度分析功能
- **并行分析**: 4个专门智能体同时分析
- **置信度评估**: 量化分析可靠性
- **综合建议**: 整合多角度建议
- **错误检测**: 多层验证机制

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

#### WikiSQL API密钥
用于基础LLM功能（Gemini 2.5 Flash）

#### OpenRouter API密钥
用于Heavy多智能体分析，需要在以下位置配置：

**方法1: 环境变量**
```bash
export OPENROUTER_API_KEY="your_openrouter_key"
```

**方法2: 修改配置文件**
编辑 `make-it-heavy/config.yaml`:
```yaml
openrouter:
  api_key: "your_openrouter_key"
  model: "google/gemini-2.5-flash-preview-05-20"
```

### 3. 测试集成
```bash
python test_heavy_integration.py
```

## 📖 使用方法

### 基础使用
```python
from wikisql_heavy_integration import WikiSQLDirectLLMHeavy

# 初始化Heavy助手
assistant = WikiSQLDirectLLMHeavy(api_key="your_wikisql_key")

# 加载数据集
assistant.load_wikisql_dataset("dev", limit=10)

# 检查Heavy模式状态
if assistant.heavy_enabled:
    print("✅ Heavy模式可用")
else:
    print("⚠️ Heavy模式不可用，使用基础模式")
```

### Heavy查询
```python
# 执行Heavy分析查询
heavy_result = assistant.query_with_heavy(
    "What is the position of player number 23?"
)

# 查看分析结果
if heavy_result.get("heavy_analysis"):
    analysis = heavy_result["heavy_analysis"]
    
    print(f"置信度: {analysis['overall_confidence']:.2f}")
    print(f"建议数量: {len(analysis['final_recommendations'])}")
    
    # 查看智能体分析
    for agent_result in analysis["agent_analyses"]:
        print(f"智能体 {agent_result['agent_id']}: {agent_result['role']}")
        print(f"置信度: {agent_result.get('confidence', 0.0):.2f}")
```

### 仅SQL生成和分析
```python
# 只进行SQL生成和Heavy分析，不执行查询
sql_analysis = assistant.generate_sql_with_heavy_analysis(
    question="How many players are there?",
    table_id="table_123"
)

print(f"生成的SQL: {sql_analysis['basic_sql']}")

if sql_analysis.get("heavy_analysis"):
    analysis = sql_analysis["heavy_analysis"]
    print(f"Heavy分析置信度: {analysis['overall_confidence']:.2f}")
```

## 🔧 配置选项

### Heavy模式配置
在 `make-it-heavy/config.yaml` 中配置：

```yaml
# 智能体设置
agent:
  max_iterations: 10

# 编排器设置  
orchestrator:
  parallel_agents: 4      # 并行智能体数量
  task_timeout: 300       # 每个智能体超时时间(秒)
  aggregation_strategy: "consensus"

# 模型设置
openrouter:
  model: "google/gemini-2.5-flash-preview-05-20"  # 推荐高上下文模型
```

### 智能体角色
系统自动分配4个专门角色：
- **智能体0**: SQL语法专家
- **智能体1**: 数据分析师  
- **智能体2**: 性能优化师
- **智能体3**: 结果验证师

## 📊 输出格式

### Heavy分析结果结构
```python
{
    "question": "原始问题",
    "generated_sql": "生成的SQL",
    "agent_analyses": [
        {
            "agent_id": 0,
            "role": "SQL语法专家",
            "analysis": "详细分析内容",
            "confidence": 0.85,
            "recommendations": ["建议1", "建议2"]
        }
        # ... 其他智能体结果
    ],
    "synthesis": {
        "confidence": 0.82,
        "recommendations": ["综合建议1", "综合建议2"],
        "summary": "综合评估摘要",
        "valid_analyses": 4,
        "total_agents": 4
    },
    "overall_confidence": 0.82,
    "final_recommendations": ["最终建议列表"]
}
```

## 🎯 使用场景

### 适合Heavy分析的情况
- ✅ **复杂查询**: 多表连接、复杂条件
- ✅ **关键业务**: 需要高准确率的查询
- ✅ **调试分析**: 查询结果异常需要深度分析
- ✅ **学习研究**: 了解SQL查询的多角度分析

### 适合基础模式的情况
- ✅ **简单查询**: 单表查询、基础条件
- ✅ **批量处理**: 大量查询需要快速处理
- ✅ **资源受限**: API配额或时间限制
- ✅ **原型开发**: 快速验证想法

## ⚡ 性能对比

| 特性 | 基础模式 | Heavy模式 |
|------|----------|-----------|
| **速度** | 快 (~5秒) | 慢 (~30-60秒) |
| **准确率** | 79%+ | 预期85%+ |
| **分析深度** | 基础 | 深度多角度 |
| **API消耗** | 低 | 高 (4倍) |
| **适用场景** | 日常使用 | 重要查询 |

## 🛠️ 故障排除

### 常见问题

#### 1. Heavy模式不可用
```
⚠️ Heavy模式初始化失败
```
**解决方案**:
- 检查OpenRouter API密钥是否正确
- 确认make-it-heavy目录存在
- 验证config.yaml配置文件

#### 2. 智能体分析失败
```
❌ 智能体 X 分析失败
```
**解决方案**:
- 检查网络连接
- 验证API配额
- 查看错误日志详情

#### 3. 配置文件错误
```
❌ 加载配置文件失败
```
**解决方案**:
- 确认config.yaml文件存在
- 检查YAML语法正确性
- 验证文件权限

### 调试技巧

#### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 检查Heavy状态
```python
if not assistant.heavy_enabled:
    print("Heavy模式未启用原因:")
    # 检查配置和依赖
```

#### 单独测试智能体
```python
# 测试单个智能体
from wikisql_heavy_integration import WikiSQLHeavyAgent

agent = WikiSQLHeavyAgent(0, config)
result = agent.analyze_sql_query(question, table_info, sql)
```

## 📈 最佳实践

### 1. 合理使用Heavy模式
- 对重要查询使用Heavy分析
- 批量处理时使用基础模式
- 根据时间和资源限制选择

### 2. 优化配置
- 选择高上下文窗口模型
- 调整超时时间适应网络环境
- 根据需要调整智能体数量

### 3. 结果解读
- 关注综合置信度
- 重视多智能体一致性建议
- 结合业务逻辑判断

## 🔮 未来扩展

### 计划功能
- **自定义智能体角色**: 支持特定领域专家
- **学习优化**: 基于历史分析改进
- **可视化分析**: 图形化展示分析结果
- **批量Heavy分析**: 支持批量深度分析

### 集成可能性
- **与验证器集成**: Heavy分析结果用于验证
- **与预测生成集成**: Heavy模式生成预测文件
- **与评估系统集成**: Heavy分析改进评估准确率

## 🎉 总结

WikiSQL Heavy集成为SQL查询分析提供了强大的多智能体支持，在保持原有简洁性的同时，为需要深度分析的场景提供了专业级的分析能力。

**选择建议**:
- **日常使用**: 基础模式 (快速、经济)
- **重要查询**: Heavy模式 (深度、准确)
- **混合使用**: 根据具体需求灵活选择