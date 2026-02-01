# Lesson 6: Hand-offs and Agent Transitions

在这一课中，我们将深入理解 `cmbagent/hand_offs.py` 模块，学习如何配置 Agent 之间的工作流转移。

## 目标

1. 理解 `set_after_work()` - 默认转移目标
2. 掌握 `OnCondition` + `StringLLMCondition` - 条件转移
3. 学习 Nested Chats - 嵌套对话
4. 创建一个完整的 Agent 工作流

## 核心概念

### 1. Hand-off 概述

在 Swarm 中，Agent 完成任务后需要"交接"到下一个 Agent。这就是 **Hand-off**。

```
Agent A → (hand-off) → Agent B → (hand-off) → Agent C → 终止
```

有三种方式定义 Hand-off:

| 方式 | 触发条件 | 适用场景 |
|------|----------|----------|
| `set_after_work()` | 无条件，总是执行 | 固定流程 |
| `OnCondition` | LLM 判断条件成立 | 动态分支 |
| `ReplyResult` (函数返回) | 函数内部逻辑 | 复杂路由 |

### 2. set_after_work() - 默认转移

```python
from autogen.agentchat.group import AgentTarget, TerminateTarget

# Agent A 完成后，总是转到 Agent B
agent_a.handoffs.set_after_work(AgentTarget(agent_b))

# Agent B 完成后，终止工作流
agent_b.handoffs.set_after_work(TerminateTarget())
```

这是 `cmbagent/hand_offs.py` 中最常见的模式：

```python
# 示例: Planner → PlannerResponseFormatter → PlanRecorder
planner.agent.handoffs.set_after_work(AgentTarget(planner_response_formatter.agent))
planner_response_formatter.agent.handoffs.set_after_work(AgentTarget(plan_recorder.agent))
```

### 3. OnCondition - 条件转移

```python
from autogen.agentchat.group import OnCondition, StringLLMCondition

# 根据 LLM 判断决定转移目标
control.agent.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(engineer),
        condition=StringLLMCondition(prompt="Code execution failed."),
    ),
    OnCondition(
        target=AgentTarget(researcher),
        condition=StringLLMCondition(prompt="Research is needed."),
    ),
    OnCondition(
        target=AgentTarget(terminator),
        condition=StringLLMCondition(prompt="The task is completed."),
    ),
])
```

LLM 会根据当前对话上下文判断哪个条件成立，然后转移到对应的 Agent。

### 4. Nested Chats - 嵌套对话

有时候需要 Agent 在"主流程"中启动一个"子流程"：

```python
from autogen import GroupChat, GroupChatManager

# 创建子流程
sub_chat = GroupChat(
    agents=[agent_a, agent_b],
    max_round=3,
    speaker_selection_method='round_robin',
)

sub_manager = GroupChatManager(groupchat=sub_chat, llm_config=llm_config)

# 注册嵌套对话
main_agent.register_nested_chats(
    trigger=lambda sender: True,  # 触发条件
    chat_queue=[{
        "recipient": sub_manager,
        "message": lambda r, m, s, c: m[-1]['content'],
        "max_turns": 1,
        "summary_method": "last_msg",
    }]
)
```

## 分析: hand_offs.py 结构

`cmbagent/hand_offs.py` 的 `register_all_hand_offs()` 函数主要做三件事：

### 1️⃣ 设置固定链式流程

```python
# Task 处理流程
task_improver → task_recorder → planner

# Plan 处理流程
planner → planner_response_formatter → plan_recorder → plan_reviewer

# Review 处理流程
plan_reviewer → reviewer_response_formatter → review_recorder → planner
```

### 2️⃣ 设置条件转移

```python
# Control Agent 根据状态选择下一步
control.agent.handoffs.add_llm_conditions([
    OnCondition(target=engineer, condition="Code execution failed."),
    OnCondition(target=researcher, condition="Research is needed."),
    OnCondition(target=terminator, condition="Task is completed."),
])
```

### 3️⃣ 设置嵌套对话

```python
# Engineer 的代码执行通过嵌套对话实现
engineer_nest.register_nested_chats(
    trigger=lambda sender: sender not in other_agents,
    chat_queue=[{
        "recipient": executor_manager,  # 子流程管理器
        ...
    }]
)
```

## 实践项目

在这个 Lesson 中，我们创建一个简化的工作流演示：

```
┌─────────┐     ┌───────────┐     ┌──────────┐
│ Greeter │ ──▶ │ Processor │ ──▶ │ Finisher │ ──▶ 终止
└─────────┘     └───────────┘     └──────────┘
                     │
                     ▼ (如果需要帮助)
               ┌──────────┐
               │  Helper  │
               └──────────┘
```

## 文件结构

```
lesson6/
├── README.md               # 本文件
├── agents/
│   ├── __init__.py
│   ├── greeter.py/yaml     # 入口 Agent
│   ├── processor.py/yaml   # 处理 Agent (有条件分支)
│   ├── helper.py/yaml      # 辅助 Agent
│   └── finisher.py/yaml    # 结束 Agent
├── hand_offs.py            # 演示 hand-off 配置
└── run_lesson6.py          # 运行脚本
```

## 学习要点

完成本课后，你应该能够：

1. ✅ 使用 `set_after_work()` 创建固定流程
2. ✅ 使用 `OnCondition` 创建条件分支
3. ✅ 理解 Nested Chats 的工作原理
4. ✅ 识别 `hand_offs.py` 中的模式并能重构

## 下一步

在 Lesson 7 中，我们将学习如何重构 `functions.py`，使用策略模式消除大量的 if-elif 链。
