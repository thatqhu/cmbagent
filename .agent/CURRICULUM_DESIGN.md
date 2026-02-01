# CMBAgent Learning Curriculum Design

这是 CMBAgent 学习课程的完整设计文档，包含每个 Lesson 的详细设计和实现规范。

## 课程概览

| Lesson | 主题 | 状态 | 核心模块 |
|--------|------|------|----------|
| 1 | Creating Your First Agent | ✅ 完成 | `BaseAgent` |
| 2 | Adding Function Tools | ✅ 完成 | `register_function` |
| 3 | RAG (Retrieval-Augmented Generation) | ✅ 完成 | `GPTAssistantAgent` |
| 4 | Swarm Orchestration | ✅ 完成 | `CMBAgent.solve()` |
| 5 | Understanding Agent Functions | ✅ 完成 | `functions.py` |
| 6 | Hand-offs and Agent Transitions | ✅ 完成 | `hand_offs.py` |
| 7 | Refactoring Functions - Strategy Pattern | 📋 设计中 | `functions.py` 重构 |
| 8 | Refactoring Hand-offs - Builder Pattern | 📋 设计中 | `hand_offs.py` 重构 |

---

## Lesson 5: Understanding Agent Functions

### 目标
深入理解 `cmbagent/functions.py` 模块的核心设计模式。

### 核心概念
1. **ReplyResult** - Agent 函数返回值，控制转移
2. **AgentTarget / TerminateTarget** - 指定下一个 Agent 或终止
3. **ContextVariables** - Agent 间共享状态
4. **@dataclass + 依赖注入** - 最佳实践模式

### 文件结构
```
lesson5/
├── README.md           # 课程文档
├── functions.py        # @dataclass 函数类
├── run_lesson5.py      # 运行脚本
└── agents/
    ├── __init__.py
    ├── receiver.py/yaml
    ├── processor.py/yaml
    └── reporter.py/yaml
```

### 核心代码模式
```python
from dataclasses import dataclass
from typing import Any, ClassVar

@dataclass
class RecordTask:
    """函数类 - 自包含元数据"""
    processor_agent: Any  # 依赖注入

    caller_name: ClassVar[str] = "receiver"
    executor_name: ClassVar[str] = "receiver"

    def __call__(self, task: str, context_variables) -> ReplyResult:
        """Docstring 作为 description"""
        context_variables["task"] = task
        return ReplyResult(
            target=AgentTarget(self.processor_agent),
            message=f"Task: {task}",
            context_variables=context_variables,
        )

# 一行注册所有
def register_all(agents: dict, *classes):
    for cls in classes:
        # 自动解析依赖、注册
        ...
```

### 实践项目
创建一个任务处理 Swarm:
- Receiver → Processor → Reporter
- 演示状态管理和条件路由

---

## Lesson 6: Hand-offs and Agent Transitions

### 目标
深入理解 `cmbagent/hand_offs.py` 模块的工作流配置。

### 核心概念
1. **set_after_work()** - 固定转移
2. **OnCondition + StringLLMCondition** - 条件转移
3. **TerminateTarget** - 终止工作流
4. **Nested Chats** - 嵌套对话 (高级)

### 文件结构
```
lesson6/
├── README.md           # 课程文档
├── hand_offs.py        # Hand-offs 配置
├── run_lesson6.py      # 运行脚本
└── agents/
    ├── __init__.py
    ├── greeter.py/yaml
    ├── processor.py/yaml
    ├── helper.py/yaml
    └── finisher.py/yaml
```

### 核心代码模式
```python
from autogen.agentchat.group import (
    AgentTarget, TerminateTarget,
    OnCondition, StringLLMCondition,
)

def register_hand_offs(agents: dict):
    greeter = agents["greeter"]
    processor = agents["processor"]
    helper = agents["helper"]
    finisher = agents["finisher"]

    # 1. 固定转移
    greeter.handoffs.set_after_work(AgentTarget(processor))

    # 2. 条件转移
    processor.handoffs.add_llm_conditions([
        OnCondition(
            target=AgentTarget(helper),
            condition=StringLLMCondition("needs help"),
        ),
        OnCondition(
            target=AgentTarget(finisher),
            condition=StringLLMCondition("task done"),
        ),
    ])

    # 3. 终止
    finisher.handoffs.set_after_work(TerminateTarget())
```

### 工作流图
```
Greeter → Processor ──→ Finisher → 终止
              │
              └──→ Helper (条件) ──→ 返回 Processor
```

---

## Lesson 7: Refactoring Functions - Strategy Pattern

### 目标
学习如何重构 `cmbagent/functions.py` 的大函数。

### 核心概念
1. **策略模式** - 消除 if-elif 链
2. **字典映射** - Agent 路由
3. **职责分离** - 状态管理/业务逻辑/路由
4. **Registry 模式** - 函数自动发现

### 文件结构
```
lesson7/
├── README.md
├── before/                    # 重构前 (问题代码)
│   └── monolithic_function.py
├── after/                     # 重构后
│   ├── __init__.py
│   ├── base.py               # 基础类
│   ├── router.py             # Agent 路由映射
│   ├── task_functions.py     # 任务函数类
│   ├── control_functions.py  # 控制函数类
│   └── register.py           # 注册逻辑
└── run_lesson7.py
```

### 重构要点

#### Before (问题代码)
```python
# 1300+ 行的大函数
def register_functions_to_agents(cmbagent_instance):
    def record_status(status, agent_for_sub_task, ...):
        # 大量 if-elif
        if agent_for_sub_task == "engineer":
            context["transfer_to_engineer"] = True
        elif agent_for_sub_task == "researcher":
            context["transfer_to_researcher"] = True
        # ... 10+ 个 elif

        if context["transfer_to_engineer"]:
            next_agent = get_agent("engineer")
        elif context["transfer_to_researcher"]:
            next_agent = get_agent("researcher")
        # ... 又 10+ 个 elif
```

#### After (重构后)
```python
# router.py - 字典映射替代 if-elif
AGENT_ROUTING = {
    "engineer": "engineer",
    "researcher": "researcher",
    "camb_agent": "camb_agent",
    # ...
}

def get_next_agent(agent_name: str, getter) -> Any:
    return getter(AGENT_ROUTING.get(agent_name))

# control_functions.py - 独立类
@dataclass
class RecordStatus:
    agents_getter: Callable

    def __call__(self, status, agent_for_sub_task, context):
        next_agent = get_next_agent(agent_for_sub_task, self.agents_getter)
        return ReplyResult(target=AgentTarget(next_agent), ...)
```

### 关键对比
| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 单文件行数 | 1478 | ~100-200 |
| if-elif 链 | 10+ 处 | 0 |
| 可测试性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 代码重复 | 高 | 低 |

---

## Lesson 8: Refactoring Hand-offs - Builder Pattern

### 目标
学习如何重构 `cmbagent/hand_offs.py` 使用 Builder 模式。

### 核心概念
1. **Builder 模式** - 链式配置
2. **声明式配置** - 配置驱动的工作流
3. **规则与实现分离** - 易于维护

### 文件结构
```
lesson8/
├── README.md
├── before/
│   └── procedural_handoffs.py
├── after/
│   ├── builder.py            # HandoffBuilder 类
│   ├── workflow.py           # 工作流定义
│   └── register.py           # 注册逻辑
└── run_lesson8.py
```

### 重构要点

#### Before (问题代码)
```python
# 大量重复的过程式代码
planner.handoffs.set_after_work(AgentTarget(formatter))
formatter.handoffs.set_after_work(AgentTarget(recorder))
recorder.handoffs.set_after_work(AgentTarget(reviewer))
# ... 几十行类似代码
```

#### After (重构后)
```python
# builder.py - 链式 Builder
class WorkflowBuilder:
    def __init__(self, agents: dict):
        self.agents = agents
        self.chains = []

    def chain(self, *agent_names) -> 'WorkflowBuilder':
        """创建线性链"""
        agents = [self.agents[name] for name in agent_names]
        for i in range(len(agents) - 1):
            agents[i].handoffs.set_after_work(AgentTarget(agents[i+1]))
        return self

    def branch(self, from_agent: str, conditions: dict) -> 'WorkflowBuilder':
        """创建条件分支"""
        agent = self.agents[from_agent]
        for condition, target in conditions.items():
            agent.handoffs.add_llm_conditions([
                OnCondition(
                    target=AgentTarget(self.agents[target]),
                    condition=StringLLMCondition(condition),
                )
            ])
        return self

    def terminate(self, agent_name: str) -> 'WorkflowBuilder':
        """设置终止"""
        self.agents[agent_name].handoffs.set_after_work(TerminateTarget())
        return self

# 使用 - 声明式配置
workflow = (
    WorkflowBuilder(agents)
    .chain("task_improver", "task_recorder", "planner")
    .chain("planner", "formatter", "plan_recorder", "reviewer")
    .branch("control", {
        "needs coding": "engineer",
        "needs research": "researcher",
        "task completed": "terminator",
    })
    .terminate("terminator")
)
```

### 关键优势
| 优势 | 说明 |
|------|------|
| **可读性** | 工作流一目了然 |
| **可维护** | 修改一处，影响可控 |
| **可复用** | Builder 可用于不同项目 |
| **易测试** | 可以测试工作流配置 |

---

## 生成 Lesson 命令

使用以下提示词让 AI 生成相应的 Lesson:

### 生成 Lesson 7
```
请根据 learning/CURRICULUM_DESIGN.md 中 Lesson 7 的设计，
创建完整的 lesson7 目录和所有文件，包括:
- README.md
- before/ 目录 (问题代码示例)
- after/ 目录 (重构后代码)
- run_lesson7.py

重点演示:
1. 如何用字典映射替换 if-elif 链
2. 如何将大函数拆分为独立的 @dataclass 类
3. 如何使用 Registry 模式自动注册函数
```

### 生成 Lesson 8
```
请根据 learning/CURRICULUM_DESIGN.md 中 Lesson 8 的设计，
创建完整的 lesson8 目录和所有文件，包括:
- README.md
- before/ 目录 (问题代码示例)
- after/ 目录 (重构后代码)
- run_lesson8.py

重点演示:
1. 如何创建 WorkflowBuilder 类
2. 如何用链式调用配置工作流
3. 如何实现声明式的 Hand-off 配置
```

---

## 附录: 关键 API 参考

### autogen.agentchat.group
```python
from autogen.agentchat.group import (
    Swarm,              # Swarm 运行器
    ContextVariables,   # 共享状态
    ReplyResult,        # 函数返回值
    AgentTarget,        # 转移到 Agent
    TerminateTarget,    # 终止工作流
    OnCondition,        # 条件转移
    StringLLMCondition, # LLM 判断条件
)
```

### autogen.register_function
```python
from autogen import register_function

register_function(
    f,                  # 函数或可调用对象
    caller,             # 谁可以调用 (LLM)
    executor,           # 谁来执行
    name=None,          # 函数名
    description=None,   # 描述 (给 LLM 看)
)
```

### Agent Handoffs
```python
# 固定转移
agent.handoffs.set_after_work(AgentTarget(next_agent))

# 条件转移
agent.handoffs.add_llm_conditions([
    OnCondition(target=AgentTarget(a), condition=StringLLMCondition("...")),
])

# 终止
agent.handoffs.set_after_work(TerminateTarget())
```
