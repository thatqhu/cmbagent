# RAG Agents 配置指南

本文档说明如何在 CMBAgent 项目中启用或禁用 RAG (Retrieval-Augmented Generation) agents。

## 📋 RAG Agents 列表

项目中包含以下 RAG agents（基于 OpenAI Assistant API 和 Vector Stores）：

1. **`camb_agent`** - CAMB 宇宙学软件包的专业文档检索代理
2. **`classy_sz_agent`** - CLASS-SZ 软件包的专业文档检索代理
3. **`cobaya_agent`** - Cobaya 软件包的专业文档检索代理
4. **`planck_agent`** - Planck 卫星数据相关的专业文档检索代理
5. **`camb_context`** - CAMB 上下文代理（可使用 RAG 或静态文档）
6. **`classy_context`** - CLASS 上下文代理（可使用 RAG 或静态文档）

## 🔧 当前状态

**默认配置：RAG agents 已禁用** (`skip_rag_agents=True`)

这意味着：

- ✅ **降低成本** - 无需创建和维护 OpenAI Vector Stores
- ✅ **加快初始化** - 跳过 RAG agents 的创建过程
- ✅ **更灵活** - 可使用任何兼容 OpenAI API 的模型（Ollama、vLLM 等）
- ⚠️ **功能受限** - 无法查询特定软件包的深度文档

## 🚀 如何启用 RAG Agents

### 方法 1: 使用 `planning_and_control_context_carryover`

```python
from cmbagent import planning_and_control_context_carryover

results = planning_and_control_context_carryover(
    task="分析宇宙微波背景辐射数据",
    # ... 其他参数 ...
    skip_rag_agents=False,  # 🔑 关键：设置为 False
    make_vector_stores=['camb', 'classy_sz', 'cobaya', 'planck']  # 指定要创建的 vector stores
)
```

### 方法 2: 直接使用 `CMBAgent` 类

```python
from cmbagent import CMBAgent

cmbagent = CMBAgent(
    work_dir="./my_work_dir",
    skip_rag_agents=False,  # 🔑 启用 RAG agents
    make_vector_stores=['camb', 'classy_sz'],  # 只创建需要的 vector stores
    api_keys=your_api_keys
)
```

### 方法 3: 选择性启用部分 RAG agents

```python
# 只启用特定的 RAG agents
cmbagent = CMBAgent(
    work_dir="./my_work_dir",
    skip_rag_agents=False,
    make_vector_stores=['camb'],  # 只创建 camb_agent 的 vector store
    api_keys=your_api_keys
)
```

## ⚠️ 禁用时的自动回退机制

当 RAG agents 被禁用时，系统会自动处理对这些 agents 的请求：

```python
# 在 functions.py 中的自动回退逻辑
elif next_agent_suggestion == "camb_agent":
    if not cmbagent_instance.skip_rag_agents:
        # RAG 启用：使用专业的 camb_agent
        camb = cmbagent_instance.get_agent_from_name('camb_agent')
        return ReplyResult(target=AgentTarget(camb), ...)
    else:
        # RAG 禁用：自动回退到通用的 engineer
        print("⚠️  RAG agents disabled: camb_agent requested but unavailable. Falling back to engineer.")
        return ReplyResult(target=AgentTarget(engineer), ...)
```

**回退规则：**

- `camb_agent` → `engineer`
- `classy_sz_agent` → `engineer`
- `cobaya_agent` → `engineer`
- `camb_context` → `engineer`
- `classy_context` → `engineer`

## 📝 使用注意事项

### 启用 RAG Agents 时需要：

1. **有效的 OpenAI API Key**

   ```python
   api_keys = {
       'openai': 'sk-your-openai-key-here'
   }
   ```

2. **足够的 API 配额**
   - Vector Store 创建需要一次性上传大量文档
   - 检索查询会产生额外的 API 调用费用

3. **更长的初始化时间**
   - 首次创建 Vector Stores 需要几分钟
   - 后续运行会复用已创建的 Vector Stores

### 禁用 RAG Agents 时的优势：

1. **成本优化**
   - 无 Vector Store 存储费用
   - 无额外的检索 API 调用

2. **兼容性更好**
   - 可使用 Ollama 本地模型
   - 可使用 vLLM 自托管服务
   - 可使用 Together AI、Groq 等替代服务

3. **调试更简单**
   - 更少的组件依赖
   - 更清晰的错误信息

## 🔍 验证 RAG Agents 状态

在运行时检查 RAG agents 是否已启用：

```python
# 方法 1: 检查 CMBAgent 实例
print(f"RAG agents enabled: {not cmbagent.skip_rag_agents}")

# 方法 2: 尝试获取 RAG agent
try:
    camb_agent = cmbagent.get_agent_from_name('camb_agent')
    print("✅ camb_agent is available")
except Exception as e:
    print(f"❌ camb_agent not available: {e}")
```

## 📚 相关文件

以下文件包含 RAG agents 的配置和逻辑：

- **`cmbagent/cmbagent.py`** - CMBAgent 类初始化，`skip_rag_agents` 参数
- **`cmbagent/functions.py`** - RAG agents 的回退逻辑和条件检查
- **`cmbagent/hand_offs.py`** - RAG agents 的 handoff 配置
- **`cmbagent/agents/executor_response_formatter/executor_response_formatter.py`** - 执行器响应格式化器
- **`cmbagent/agents/planner_response_formatter/planner_response_formatter.py`** - 计划器响应格式化器
- **`cmbagent/agents/rag_agents/`** - RAG agents 的配置文件（YAML）

## 🎯 最佳实践建议

### 推荐使用场景

**启用 RAG Agents：**

- 需要深度查询 CAMB/CLASS/Cobaya 等软件包的文档
- 处理复杂的宇宙学计算问题
- 需要准确的软件包 API 使用指南
- 有充足的 API 预算

**禁用 RAG Agents：**

- 通用的数据分析任务
- 使用本地模型（Ollama）或非 OpenAI 服务
- 成本敏感的应用场景
- 快速原型开发和测试

### 性能优化

如果只需要部分 RAG agents，可以选择性启用：

```python
# 示例：只启用 CAMB 相关的 RAG agent
cmbagent = CMBAgent(
    skip_rag_agents=False,
    make_vector_stores=['camb'],  # 只创建 CAMB 的 vector store
    # 其他配置...
)
```

## 🔄 未来集成准备

代码已经设计为支持灵活切换 RAG agents：

1. **保留所有接口** - 所有 RAG agents 选项都保留在类型定义中
2. **条件检查** - 运行时动态检查 `skip_rag_agents` 状态
3. **优雅回退** - 自动回退机制不会中断工作流程
4. **清晰注释** - 代码中标注了 RAG 相关的所有位置

要重新启用 RAG agents，只需：

1. 设置 `skip_rag_agents=False`
2. 提供 `make_vector_stores` 参数
3. 确保有效的 OpenAI API Key

无需修改任何代码！

---

**最后更新时间**: 2026-01-13
**维护者**: CMBAgent Team
