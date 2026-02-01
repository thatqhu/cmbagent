# RAG Agents 快速参考

## 🎯 当前状态

**RAG Agents: 已禁用** ✅

## 📊 一句话总结

所有 RAG agents（camb_agent、classy_sz_agent等）已被优雅禁用，系统会自动回退到 engineer agent，不会出现错误。

## 🚀 快速启用方法

```python
from cmbagent import planning_and_control_context_carryover

results = planning_and_control_context_carryover(
    task="你的任务",
    skip_rag_agents=False,  # ← 改这里
    make_vector_stores=['camb', 'classy_sz'],
    # ... 其他参数
)
```

## 🔍 RAG Agents 列表

| Agent             | 功能              | 禁用时回退到 |
| ----------------- | ----------------- | ------------ |
| `camb_agent`      | CAMB 文档检索     | `engineer`   |
| `classy_sz_agent` | CLASS-SZ 文档检索 | `engineer`   |
| `cobaya_agent`    | Cobaya 文档检索   | `engineer`   |
| `camb_context`    | CAMB 上下文       | `engineer`   |
| `classy_context`  | CLASS 上下文      | `engineer`   |
| `planck_agent`    | Planck 文档检索   | `engineer`   |

## 📁 修改的关键文件

1. **`cmbagent/functions.py`** (201-318行)
   - 添加了 RAG agents 的条件检查和回退逻辑

2. **`cmbagent/agents/executor_response_formatter/executor_response_formatter.py`** (33-50行)
   - 更新了文档说明

3. **`cmbagent/agents/planner_response_formatter/planner_response_formatter.py`** (9-14行)
   - 添加了注释说明

## 🎓 何时启用 RAG?

**启用 RAG** 👍:

- 需要深度查询特定软件包文档
- 处理复杂的宇宙学计算
- 有充足的 API 预算

**禁用 RAG** 👍:

- 通用数据分析
- 使用本地模型（Ollama）
- 成本敏感场景
- 快速原型开发

## ⚠️ 注意事项

- 禁用时 LLM 仍可能建议使用 RAG agents
- 系统会打印警告: `⚠️ RAG agents disabled: xxx unavailable. Falling back to engineer.`
- 这是正常行为，不是错误

## 📚 完整文档

查看详细配置: `docs/rag-agents-configuration.md`
查看修改总结: `docs/rag-agents-disable-summary.md`

---

**更新时间**: 2026-01-13
