# `context_variables` 注入Prompt的完整机制详解

## 🎯 核心问题

**问题**：`context_variables` 字典中的值是如何被注入到智能体的prompt中的？

**答案**：通过 **AG2的 `UpdateSystemMessage` 机制 + Python字符串格式化（f-string风格）**

---

## 🔧 一、完整工作流程

```
1. 定义Prompt模板（在YAML文件中）
   ↓
2. 初始化智能体时注册 UpdateSystemMessage
   ↓
3. 智能体被激活前，AG2触发 UpdateSystemMessage
   ↓
4. UpdateSystemMessage 执行字符串替换
   ↓
5. 替换后的Prompt发送给LLM
```

---

## 📝 二、步骤详解

### 步骤1：在YAML中定义Prompt模板

**文件**：`cmbagent/agents/control/control.yaml`

```yaml
name: "control"

instructions: |
  You are the control agent in the team.

  You follow step-by-step the established plan:

  {final_plan}                           # ⭐ 占位符1

  The current status of this workflow is:

  **Current step in plan:**
  {current_plan_step_number}             # ⭐ 占位符2

  **Current status:**
  {current_status}                       # ⭐ 占位符3

  **Current sub-task:**
  {current_sub_task}                     # ⭐ 占位符4

  **Agent in charge:**
  {agent_for_sub_task}                   # ⭐ 占位符5

  **Instructions:**
  {current_instructions}                 # ⭐ 占位符6

  **Context**
  Summary of previous steps execution:
  {previous_steps_execution_summary}     # ⭐ 占位符7
```

**关键点**：

- 使用 `{variable_name}` 语法定义占位符
- 与Python f-string类似，但**不**在变量名前加 `f`
- 这些占位符会在运行时被 `context_variables` 中的对应值替换

### 步骤2：初始化智能体时注册 UpdateSystemMessage

**文件**：`cmbagent/base_agent.py:214`

```python
class BaseAgent:
    def set_assistant_agent(self, instructions=None, description=None):
        # 从YAML加载instructions
        if instructions is not None:
            self.info["instructions"] = instructions

        # 创建智能体，注册UpdateSystemMessage
        self.agent = CmbAgentSwarmAgent(
            name=self.name,
            update_agent_state_before_reply=[
                UpdateSystemMessage(self.info["instructions"]),  # ⭐ 核心
            ],
            description=self.info["description"],
            llm_config=self.llm_config,
        )
```

**关键点**：

- `UpdateSystemMessage(self.info["instructions"])` 接收模板字符串
- 这个模板字符串**包含占位符**（如 `{final_plan}`）
- `update_agent_state_before_reply` 是一个回调列表，在智能体生成回复**之前**触发

### 步骤3：智能体被激活时，AG2触发 UpdateSystemMessage

**时机**：每次智能体收到消息并准备生成回复时

**AG2内部流程**（简化版）：

```python
# AG2框架内部（autogen/agentchat.py，伪代码）
class ConversableAgent:
    def generate_reply(self, messages, sender, ...):
        # 1. 在生成回复之前，触发所有callbacks
        for callback in self.update_agent_state_before_reply:
            callback(self, messages, sender, context_variables)

        # 2. 发送消息给LLM
        response = self.llm_client.create(
            model=self.llm_config["model"],
            messages=[
                {"role": "system", "content": self.system_message},  # ⭐ 已被替换
                *messages
            ]
        )

        return response
```

### 步骤4：UpdateSystemMessage 执行字符串替换

**AG2内部实现**（`autogen/agentchat.py`，简化版）：

```python
class UpdateSystemMessage:
    def __init__(self, content_updater):
        """
        Args:
            content_updater: 可以是字符串模板或可调用函数
        """
        self.content_updater = content_updater

    def __call__(self, agent, messages, sender, context_variables):
        if isinstance(self.content_updater, str):
            # ⭐ 关键：使用 format_map 进行字符串替换
            updated_content = self.content_updater.format_map(context_variables)
        else:
            # 如果是函数，调用函数
            updated_content = self.content_updater(context_variables)

        # 更新agent的system_message
        agent.update_system_message(updated_content)
```

**`format_map` 的工作原理**：

```python
# 示例
template = "Current step: {current_plan_step_number}, Agent: {agent_for_sub_task}"
context_variables = {
    "current_plan_step_number": 1,
    "agent_for_sub_task": "camb_context",
    "other_key": "not_used"
}

result = template.format_map(context_variables)
# result = "Current step: 1, Agent: camb_context"
```

**关键点**：

- `format_map` 是Python内置方法，类似 `format(**kwargs)`
- 它从字典中查找对应的键，替换模板中的占位符
- 如果占位符在字典中不存在，会抛出 `KeyError`

### 步骤5：替换后的Prompt发送给LLM

**实际发送给LLM的消息**：

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "You are the control agent in the team.\n\nYou follow step-by-step the established plan:\n\nStep 1: 查询CAMB文档\n  - 任务：了解如何使用CAMB\n  - 执行者：camb_context\n  - 指令：搜索get_results方法\n\nStep 2: 编写代码\n  - 任务：编写CAMB代码\n  - 执行者：engineer\n  ...\n\nThe current status of this workflow is:\n\n**Current step in plan:**\n1\n\n**Current status:**\nin progress\n\n**Current sub-task:**\n查询CAMB文档\n\n**Agent in charge:**\ncamb_context\n\n**Instructions:**\n搜索get_results方法\n\n**Context**\nSummary of previous steps execution:\n\n"
    },
    {
      "role": "user",
      "content": "Please proceed"
    }
  ]
}
```

**可以看到**：

- ✅ `{final_plan}` 被替换为实际的计划文本
- ✅ `{current_plan_step_number}` 被替换为 `1`
- ✅ `{agent_for_sub_task}` 被替换为 `camb_context`
- ✅ 所有占位符都被替换为 `context_variables` 中的实际值

---

## 📊 三、完整示例（从初始化到执行）

### 示例场景：Control智能体的完整生命周期

#### **1. 系统初始化**

```python
# cmbagent/cmbagent.py (简化)
from cmbagent.context import shared_context

# 初始化context_variables（稍后会被更新）
context_variables = shared_context.copy()
context_variables.update({
    "final_plan": None,
    "current_plan_step_number": None,
    "current_status": None,
    "agent_for_sub_task": None,
    # ... 其他变量
})
```

#### **2. Planning阶段完成**

```python
# planner生成计划后，更新context_variables
context_variables["final_plan"] = """
Step 1: 查询CAMB文档
  - 任务：了解如何使用CAMB计算功率谱
  - 执行者：camb_context
  - 指令：搜索get_results和set_params方法

Step 2: 编写Python代码
  - 任务：编写CAMB计算代码
  - 执行者：engineer
  - 指令：使用H0=67, ombh2=0.022生成TT功率谱
"""
context_variables["number_of_steps_in_plan"] = 2
```

#### **3. Control阶段开始 - Step 1**

```python
# record_status被调用，更新context_variables
record_status(
    current_status="in progress",
    current_plan_step_number=1,
    current_sub_task="查询CAMB文档",
    current_instructions="搜索get_results和set_params方法",
    agent_for_sub_task="camb_context",
    context_variables=context_variables
)

# 函数内部更新context_variables
context_variables["current_plan_step_number"] = 1
context_variables["current_sub_task"] = "查询CAMB文档"
context_variables["agent_for_sub_task"] = "camb_context"
context_variables["current_instructions"] = "搜索get_results和set_params方法"
context_variables["current_status"] = "in progress"
```

#### **4. AG2准备让control生成下一个回复**

```python
# AG2内部流程
# 1. 触发 UpdateSystemMessage
control.update_agent_state_before_reply[0](
    agent=control,
    messages=[...],
    sender=previous_agent,
    context_variables=context_variables  # ⭐ 传递当前上下文
)

# 2. UpdateSystemMessage 内部执行替换
template = control.info["instructions"]  # 从YAML加载的模板
# template包含: "Current step: {current_plan_step_number}..."

updated_prompt = template.format_map(context_variables)
# 替换后:
# "Current step: 1..."
# "Agent in charge: camb_context..."
# "Plan:\nStep 1: 查询CAMB文档\n..."

# 3. 更新control的system_message
control.update_system_message(updated_prompt)

# 4. 发送给LLM
llm_response = llm_client.create(
    messages=[
        {"role": "system", "content": updated_prompt},  # ⭐ 已替换
        {"role": "user", "content": "Please proceed"}
    ]
)
```

#### **5. LLM看到的完整Prompt**

```
You are the control agent in the team. You don't respond. You should only call record_status tool.

You must call record_status **before** calling the agent in charge of the up-coming sub-task.

You follow step-by-step the established plan:

Step 1: 查询CAMB文档
  - 任务：了解如何使用CAMB计算功率谱
  - 执行者：camb_context
  - 指令：搜索get_results和set_params方法

Step 2: 编写Python代码
  - 任务：编写CAMB计算代码
  - 执行者：engineer
  - 指令：使用H0=67, ombh2=0.022生成TT功率谱

The current status of this workflow is:

**Current step in plan:**
1

**Current status:**
in progress

**Current sub-task:**
查询CAMB文档

**Agent in charge:**
camb_context

**Instructions:**
搜索get_results和set_params方法

**Context**
Summary of previous steps execution and codebase:
<PREVIOUS_STEPS_EXECUTION_SUMMARY>

-----------------------------------
</PREVIOUS_STEPS_EXECUTION_SUMMARY>

You must implement the plan step-by-step until the final step and never call the terminator agent unless **ALL** the steps in plan have been fully **successfully** implemented one by one.

If a code execution has failed, it must be fixed before moving to subsequent step in the plan!
```

---

## 🔍 四、`context_variables` 与 Prompt 变量的映射

### 常见的context变量及其在Prompt中的使用

| context_variables 键               | 在Prompt中的占位符                   | 示例值                                     | 哪些智能体使用                                 |
| ---------------------------------- | ------------------------------------ | ------------------------------------------ | ---------------------------------------------- |
| `final_plan`                       | `{final_plan}`                       | `"Step 1: ...\nStep 2: ..."`               | control, engineer, researcher, camb_agent, ... |
| `current_plan_step_number`         | `{current_plan_step_number}`         | `1`, `2`, `3`                              | control, engineer, researcher, ...             |
| `current_status`                   | `{current_status}`                   | `"in progress"`, `"completed"`, `"failed"` | control, engineer, ...                         |
| `current_sub_task`                 | `{current_sub_task}`                 | `"查询CAMB文档"`                           | control, engineer, researcher, ...             |
| `agent_for_sub_task`               | `{agent_for_sub_task}`               | `"camb_context"`, `"engineer"`             | control                                        |
| `current_instructions`             | `{current_instructions}`             | `"搜索get_results方法"`                    | control, engineer, ...                         |
| `improved_main_task`               | `{improved_main_task}`               | `"使用CAMB计算功率谱..."`                  | engineer, researcher, camb_agent, ...          |
| `database_path`                    | `{database_path}`                    | `"data/"`                                  | engineer                                       |
| `previous_steps_execution_summary` | `{previous_steps_execution_summary}` | `"Step 1完成: ..."`                        | control, engineer, researcher, ...             |
| `vlm_plot_structured_feedback`     | `{vlm_plot_structured_feedback}`     | `"Problems:\n- 轴标签缺失\n..."`           | engineer                                       |
| `engineer_append_instructions`     | `{engineer_append_instructions}`     | `"使用dpi>=300保存图片"`                   | engineer                                       |

### 查看所有可用的context变量

**文件**：`cmbagent/context.py:1-77`

```python
shared_context = {
    "plans": [],
    "reviews": [],
    "final_plan": None,
    "current_plan_step_number": None,
    "current_sub_task": None,
    "agent_for_sub_task": None,
    "current_status": None,
    "current_instructions": None,
    "improved_main_task": None,
    "database_path": "data/",
    "codebase_path": "codebase/",
    "previous_steps_execution_summary": "\n",
    "vlm_plot_structured_feedback": None,
    "engineer_append_instructions": None,
    # ... 共78行，约40个变量
}
```

---

## 💡 五、关键设计细节

### 5.1 为什么使用 `format_map` 而不是 f-string？

**f-string（不可行）**：

```python
# ❌ 不能这样做
template = f"Current step: {current_plan_step_number}"
# 问题：f-string在定义时立即求值，此时变量可能未定义
```

**format_map（正确）**：

```python
# ✅ 正确做法
template = "Current step: {current_plan_step_number}"
# 稍后再替换
result = template.format_map(context_variables)
# 此时context_variables已包含所有值
```

### 5.2 为什么每次回复前都要更新？

```python
update_agent_state_before_reply=[UpdateSystemMessage(...)]
#                      ↑ 关键词："before_reply"
```

**原因**：`context_variables` 是**动态变化**的

```python
# Step 1: camb_context执行中
context_variables["current_plan_step_number"] = 1
context_variables["agent_for_sub_task"] = "camb_context"
# control的prompt显示: "Current step: 1, Agent: camb_context"

# Step 1完成，Step 2开始
context_variables["current_plan_step_number"] = 2
context_variables["agent_for_sub_task"] = "engineer"
# control的prompt自动更新: "Current step: 2, Agent: engineer"
```

**如果不每次更新**：

- ❌ Prompt会永远显示Step 1的信息
- ❌ LLM无法知道当前实际处于哪一步

### 5.3 处理缺失的变量

**如果Prompt中使用了 `{variable_name}`，但 `context_variables` 中没有这个键？**

```python
# Prompt模板
template = "Current agent: {agent_for_sub_task}"

# context_variables缺少这个键
context_variables = {"current_plan_step_number": 1}

# 尝试替换
template.format_map(context_variables)
# ❌ 抛出 KeyError: 'agent_for_sub_task'
```

**CMBAgent的解决方案**：在 `context.py` 中**预定义所有变量**

```python
shared_context = {
    "agent_for_sub_task": None,  # ⭐ 即使初始为None，键也存在
    "final_plan": None,
    # ... 所有可能用到的变量
}
```

**替换时的行为**：

```python
template = "Agent: {agent_for_sub_task}"
context_variables = {"agent_for_sub_task": None}

result = template.format_map(context_variables)
# result = "Agent: None"  # ✅ 不会报错，显示"None"
```

---

## 🎓 六、实战示例：添加新的context变量

### 场景：想在engineer的prompt中显示当前重试次数

#### **步骤1：在 `context.py` 添加变量**

```python
# cmbagent/context.py
shared_context = {
    # ... 现有变量
    "n_attempts": 0,          # ✅ 已存在
    "max_n_attempts": 3,      # ✅ 已存在
    "retry_info": None,       # ⭐ 新增：格式化的重试信息
}
```

#### **步骤2：在某个函数中更新这个变量**

```python
# cmbagent/functions.py - record_status函数中
def record_status(..., context_variables):
    # 格式化重试信息
    context_variables["retry_info"] = f"Attempt {context_variables['n_attempts'] + 1}/{context_variables['max_n_attempts']}"

    # ... 其他逻辑
```

#### **步骤3：在engineer.yaml中使用这个变量**

```yaml
# cmbagent/agents/engineer/engineer.yaml
instructions: |
  You are the engineer agent.

  Current retry status: {retry_info}    # ⭐ 新增占位符

  ... (其他指令)
```

#### **步骤4：自动生效**

```python
# 无需修改任何其他代码！
# AG2会自动：
# 1. 读取engineer.yaml的instructions
# 2. 注册UpdateSystemMessage
# 3. 每次engineer被激活时，自动替换 {retry_info}
```

#### **Engineer看到的Prompt**

```
You are the engineer agent.

Current retry status: Attempt 2/3    # ⭐ 自动替换

... (其他指令)
```

---

## 🔍 七、调试技巧

### 如何查看实际发送给LLM的Prompt？

#### **方法1：启用AG2调试模式**

```python
# 在CMBAgent初始化时
import autogen
autogen.cmbagent_debug = True

# 会打印类似：
"""
[control] System message:
You are the control agent...
Current step: 1
Agent: camb_context
...
"""
```

#### **方法2：在UpdateSystemMessage中添加日志**

```python
# 修改base_agent.py (仅用于调试)
class BaseAgent:
    def set_assistant_agent(self, ...):
        original_instructions = self.info["instructions"]

        def debug_updater(context_variables):
            updated = original_instructions.format_map(context_variables)
            print(f"🔍 [{self.name}] Updated prompt:")
            print(updated[:500])  # 打印前500字符
            return updated

        self.agent = CmbAgentSwarmAgent(
            update_agent_state_before_reply=[
                UpdateSystemMessage(debug_updater),  # 使用函数而非字符串
            ],
            ...
        )
```

#### **方法3：在函数中打印context_variables**

```python
# 在record_status等函数中
def record_status(..., context_variables):
    print(f"🔍 context_variables state:")
    print(f"  - current_plan_step_number: {context_variables['current_plan_step_number']}")
    print(f"  - agent_for_sub_task: {context_variables['agent_for_sub_task']}")
    print(f"  - current_status: {context_variables['current_status']}")
```

---

## 📚 八、总结

### 核心机制

```
YAML模板（包含{占位符}）
    ↓
BaseAgent.set_assistant_agent()
    ↓
注册 UpdateSystemMessage(template)
    ↓
每次智能体被激活前
    ↓
AG2触发 UpdateSystemMessage
    ↓
执行 template.format_map(context_variables)
    ↓
替换所有占位符
    ↓
更新agent.system_message
    ↓
发送给LLM
```

### 关键要点

1. ✅ **模板在YAML中定义**：使用 `{variable_name}` 占位符
2. ✅ **变量在 `context.py` 预定义**：确保所有键都存在
3. ✅ **值在运行时更新**：通过函数调用更新 `context_variables`
4. ✅ **替换在激活前触发**：`UpdateSystemMessage` 自动执行
5. ✅ **使用 `format_map`**：不是f-string，不是 `format(**kwargs)`
6. ✅ **每次都重新替换**：适应动态变化的上下文

### 优势

- 🎯 **解耦Prompt定义和值更新**：YAML定义结构，Python更新值
- 🔄 **动态适应上下文**：同一个模板，不同时刻显示不同内容
- 📝 **易于维护**：修改Prompt只需编辑YAML，无需改代码
- 🔧 **灵活扩展**：添加新变量只需3步（定义 → 更新 → 使用）

---

_文档生成时间：2026-01-09_
_基于AG2 (AutoGen 2.0) 框架_
