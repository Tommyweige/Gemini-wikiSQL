# WikiSQL Heavy System Architecture Flow

## 🏗️ 系统整体架构

```mermaid
graph TB
    A[用户启动] --> B[generate_wikisql_predictions.py]
    B --> C{选择查询模式}
    C -->|选项1| D[Standard Query 标准查询]
    C -->|选项2| E[Heavy Query 4个并行智能体]
    
    D --> F[WikiSQLDirectLLM]
    F --> G[单个LLM生成SQL]
    G --> H[执行SQL]
    H --> I[返回结果]
    
    E --> J[WikiSQLDirectLLMHeavy]
    J --> K[Heavy分析流程]
    K --> L[最终结果]
```

## 🔄 Heavy模式详细流程

```mermaid
graph TD
    A[Heavy Query开始] --> B[WikiSQLDirectLLMHeavy]
    B --> C[生成基础SQL]
    C --> D[SimpleHeavyOrchestrator]
    
    D --> E[阶段1: Question Generation Agent]
    E --> F[生成4个专门问题 1+3结构]
    F --> G[问题1: 原始问题]
    F --> H[问题2: 具体化版本]
    F --> I[问题3: 替代表述]
    F --> J[问题4: 验证导向]
    
    G --> K[智能体0: Research Agent]
    H --> L[智能体1: Analysis Agent]
    I --> M[智能体2: Alternatives Agent]
    J --> N[智能体3: Verification Agent]
    
    K --> O[阶段2: 并行分析]
    L --> O
    M --> O
    N --> O
    
    O --> P[阶段3: Synthesis Agent]
    P --> Q[综合所有分析结果]
    Q --> R[生成最终答案]
    R --> S[检查是否有改进SQL]
    S --> T[返回Heavy分析结果]
```

## 🧠 4个并行智能体详细分工

```mermaid
graph LR
    A[4个专门问题] --> B[智能体并行处理]
    
    B --> C[智能体0<br/>Research Agent<br/>数据研究专家]
    B --> D[智能体1<br/>Analysis Agent<br/>SQL分析专家]
    B --> E[智能体2<br/>Alternatives Agent<br/>替代方案专家]
    B --> F[智能体3<br/>Verification Agent<br/>验证专家]
    
    C --> G[分析问题1<br/>原始问题]
    D --> H[分析问题2<br/>具体化版本]
    E --> I[分析问题3<br/>替代表述]
    F --> J[分析问题4<br/>验证导向]
    
    G --> K[Synthesis Agent]
    H --> K
    I --> K
    J --> K
    
    K --> L[综合分析结果]
```

## 📊 问题生成结构 (1+3)

```mermaid
graph TD
    A[原始问题<br/>What school did player number 21 play for?] --> B[Question Generation Agent]
    
    B --> C[问题1: ORIGINAL<br/>What school did player number 21 play for?<br/>保持原始问题不变]
    
    B --> D[问题2: SPECIFIC<br/>Which educational institution was attended<br/>by the athlete wearing jersey number 21?<br/>更具体的版本]
    
    B --> E[问题3: ALTERNATIVE<br/>What is the academic background<br/>of the player identified as number 21?<br/>替代表述]
    
    B --> F[问题4: VERIFICATION<br/>Can you identify the college or university<br/>associated with player 21?<br/>验证导向]
    
    C --> G[智能体0处理]
    D --> H[智能体1处理]
    E --> I[智能体2处理]
    F --> J[智能体3处理]
```

## 🔧 技术架构层次

```mermaid
graph TB
    subgraph "用户界面层"
        A[generate_wikisql_predictions.py]
    end
    
    subgraph "核心处理层"
        B[WikiSQLDirectLLM<br/>标准模式]
        C[WikiSQLDirectLLMHeavy<br/>Heavy模式]
    end
    
    subgraph "Heavy分析层"
        D[SimpleHeavyOrchestrator<br/>编排器]
        E[QuestionGenerationAgent<br/>问题生成]
        F[SimpleHeavyAgent x4<br/>4个并行智能体]
        G[Synthesis Agent<br/>综合分析]
    end
    
    subgraph "数据处理层"
        H[WikiSQLDataLoader<br/>数据加载]
        I[WikiSQLDatabaseManager<br/>数据库管理]
    end
    
    subgraph "LLM服务层"
        J[ChatOpenAI<br/>LangChain接口]
        K[AI Studio API端点<br/>aistudio.google.com]
    end
    
    A --> B
    A --> C
    C --> D
    D --> E
    D --> F
    D --> G
    B --> H
    C --> H
    B --> I
    C --> I
    E --> J
    F --> J
    G --> J
    J --> K
```

## 🎯 数据流向

```mermaid
sequenceDiagram
    participant U as 用户
    participant M as Main程序
    participant H as Heavy模式
    participant Q as 问题生成器
    participant A as 4个智能体
    participant S as 综合分析器
    
    U->>M: 选择Heavy查询模式
    M->>H: 初始化Heavy助手
    H->>H: 生成基础SQL
    H->>Q: 请求生成4个专门问题
    Q->>Q: 生成1+3结构问题
    Q->>H: 返回4个英文问题
    H->>A: 并行分配问题给4个智能体
    
    par 并行处理
        A->>A: 智能体0分析问题1
    and
        A->>A: 智能体1分析问题2
    and
        A->>A: 智能体2分析问题3
    and
        A->>A: 智能体3分析问题4
    end
    
    A->>S: 收集所有分析结果
    S->>S: 综合分析并生成最终答案
    S->>H: 返回综合结果
    H->>H: 检查是否有改进SQL
    H->>M: 返回Heavy分析结果
    M->>U: 显示最终结果
```

## 📁 文件结构

```
WikiSQL Heavy System/
├── generate_wikisql_predictions.py     # 主程序入口
├── wikisql_llm_direct.py              # 标准LLM查询
├── wikisql_heavy_integration.py       # Heavy集成（原始版本）
├── wikisql_heavy_simple.py            # 简化版Heavy实现 ⭐
├── wikisql_data_loader.py             # 数据加载器
├── wikisql_database_manager.py        # 数据库管理
├── wikisql_validator.py               # 结果验证
└── make-it-heavy/                     # Make It Heavy框架
    ├── agent.py                       # 基础智能体
    ├── orchestrator.py                # 编排器
    └── config.yaml                    # 配置文件
```

## 🚀 系统特点

### ✅ 优势
- **4个并行智能体**: 从不同角度深度分析
- **1+3问题结构**: 保持原始问题 + 3个变换角度
- **纯自然语言**: 不包含SQL语法的问题
- **全英文输出**: 统一的语言标准
- **综合分析**: Synthesis Agent整合所有结果

### 🎯 工作流程
1. **问题生成**: 1个原始 + 3个变换问题
2. **并行分析**: 4个智能体同时处理
3. **综合评估**: 整合所有分析结果
4. **SQL改进**: 如果需要，提供改进的SQL
5. **最终答案**: 返回完整的分析结果

这就是你当前的WikiSQL Heavy系统架构！🎉