# Lesson 5: Understanding Agent Functions

在这一课中，我们将深入理解 `cmbagent/functions.py` 模块的核心设计模式，并学习如何使用**最佳实践**重构它。

## 目标

1. 理解 `ReplyResult` 和 `AgentTarget` 如何实现 Agent 转移
2. 掌握 `ContextVariables` 共享状态机制
3. 学习 `@dataclass` + 依赖注入的最佳实践
4. 对比分析 `functions.py` 中的问题

## 核心概念

### 1. ReplyResult - Agent 函数的返回值

在 `cmbagent` 中，Agent 的 function tool 可以返回 `ReplyResult` 来控制下一步行为：

```python
from autogen.agentchat.group import ReplyResult, AgentTarget, TerminateTarget

def my_function(context_variables: ContextVariables) -> ReplyResult:
    return ReplyResult(
        target=AgentTarget(next_agent),   # 转移到哪个 Agent
        message="Task completed",          # 传递给下一个 Agent 的消息
        context_variables=context_variables  # 更新后的状态
    )
```

**关键点**:
- `target`: 可以是 `AgentTarget(agent)` 或 `TerminateTarget()`
- `message`: 下一个 Agent 会看到的消息
- `context_variables`: 在整个 Swarm 中共享的状态

### 2. ContextVariables - 共享状态

`ContextVariables` 是一个类似字典的对象，被所有 Agent 共享：

```python
from autogen.agentchat.group import ContextVariables

# 设置状态
context_variables["current_step"] = 1
context_variables["task_status"] = "in_progress"

# 读取状态
step = context_variables.get("current_step", 0)
```

### 3. @dataclass + 依赖注入 (最佳实践)

**为什么用 `@dataclass`？**
- 自动生成 `__init__`、`__repr__`、`__eq__` 等方法
- 代码简洁，意图清晰
- 易于测试和维护

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class RecordTask:
    """记录任务并转移到 Processor"""
    processor_agent: Any  # 依赖注入

    def __call__(
        self,
        task_description: str,
        context_variables: ContextVariables
    ) -> ReplyResult:
        context_variables["task"] = task_description
        return ReplyResult(
            target=AgentTarget(self.processor_agent),
            message=f"Task: {task_description}",
            context_variables=context_variables,
        )

# 使用
record_task = RecordTask(processor_agent=processor)  # 自动生成的 __init__
result = record_task("Calculate 2+2", ctx)           # 调用 __call__
```

## 对比: functions.py 的问题

查看 `cmbagent/functions.py`，你会发现以下问题：

### 问题 1: 巨型闭包函数

```python
def register_functions_to_agents(cmbagent_instance):
    # 1300+ 行代码
    def post_execution_transfer(...): ...
    def call_vlm_judge(...): ...
    def record_status(...): ...
```

**问题**: 难以维护、难以测试、难以理解

### 问题 2: 大量重复的 if-elif 链

```python
if context_variables["agent_for_sub_task"] == "engineer":
    context_variables["transfer_to_engineer"] = True
elif context_variables["agent_for_sub_task"] == "researcher":
    context_variables["transfer_to_researcher"] = True
# ... 10+ 个 elif
```

### 问题 3: 闭包耦合

函数内部直接访问 `cmbagent_instance`，难以复用和测试。

## 本课的解决方案

我们使用 `@dataclass` + 依赖注入模式重构：

| 原版 (functions.py) | 本课 (dataclass) |
|--------------------|------------------|
| 1300+ 行闭包函数 | 3 个独立类，每个 30-50 行 |
| 隐式依赖 cmbagent_instance | 显式注入 agent 依赖 |
| 难以测试 | 可以独立单元测试 |
| if-elif 链 | 方法分离 (`_handle_success`, `_handle_failure`) |

## 文件结构

```
lesson5/
├── README.md           # 本文件
├── agents/
│   ├── __init__.py
│   ├── receiver.py     # Receiver Agent
│   ├── receiver.yaml
│   ├── processor.py    # Processor Agent
│   ├── processor.yaml
│   ├── reporter.py     # Reporter Agent
│   └── reporter.yaml
├── functions.py        # @dataclass 函数类
└── run_lesson5.py      # 运行脚本
```

## 函数类说明

### RecordTask
- **作用**: 接收用户任务，初始化状态，转移到 Processor
- **注入**: `processor_agent`

### ProcessTask
- **作用**: 处理任务结果，决定成功/失败/重试
- **注入**: `processor_agent`, `reporter_agent`
- **逻辑**:
  - 成功 → 转到 Reporter
  - 失败且未超限 → 重试 (转回 Processor)
  - 失败且超限 → 转到 Reporter 报告失败

### FinalizeReport
- **作用**: 生成报告，终止 Swarm
- **注入**: 无（总是终止）

## 运行

```bash
cd learning/lesson5
python run_lesson5.py
```

## 学习要点

完成本课后，你应该能够：

1. ✅ 理解 `ReplyResult` 如何控制 Agent 流程
2. ✅ 使用 `ContextVariables` 在 Agent 间共享状态
3. ✅ 使用 `@dataclass` + 依赖注入创建可测试的函数
4. ✅ 识别并重构 `functions.py` 中的反模式

## 下一步

在 Lesson 6 中，我们将学习 `hand_offs.py` 中的工作流转移机制。
