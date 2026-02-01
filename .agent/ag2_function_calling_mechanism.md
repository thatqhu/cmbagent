# AG2 框架中函数调用的真实机制详解

## 🎯 核心澄清

**重要提示**：我在之前文档中使用的 `control.call_function(...)` 是**概念性的伪代码**，用于说明逻辑流程。

**真实情况**：AG2框架中，智能体并**不会直接调用**Python函数，而是通过 **LLM推断 + 框架执行** 的机制完成函数调用。

---

## 🔧 一、AG2函数调用的核心机制

### 1.1 Function Calling 的两个角色

在AG2中，函数调用涉及两个角色：

```python
register_function(
    f=record_status,           # Python函数本身
    caller=control,            # ⭐ Caller: 决定何时调用（LLM驱动）
    executor=control,          # ⭐ Executor: 执行函数（Python运行时）
    description="..."          # 给LLM的函数说明
)
```

| 角色         | 智能体类型                      | 职责                                          | 如何工作                                                                        |
| ------------ | ------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------- |
| **Caller**   | `AssistantAgent`<br/>（有LLM）  | 决定**何时**调用函数<br/>决定传递**什么参数** | LLM根据conversation context<br/>+ function description<br/>推断是否调用及参数值 |
| **Executor** | `UserProxyAgent`<br/>（执行者） | **执行**Python函数<br/>返回结果               | 接收tool call消息后<br/>直接运行Python代码                                      |

### 1.2 完整工作流程

```
1. 用户消息 / 前一智能体的消息
   ↓
2. Caller Agent (control) 收到消息
   ↓
3. LLM分析消息 + control的system prompt + 注册的functions
   ↓
4. LLM推断：需要调用 record_status 函数
   ↓
5. LLM生成 Tool Call 消息（JSON格式）:
   {
     "tool_calls": [{
       "function": {
         "name": "record_status",
         "arguments": {
           "current_status": "in progress",
           "current_plan_step_number": 1,
           "current_sub_task": "查询CAMB文档",
           "agent_for_sub_task": "camb_context",
           "current_instructions": "..."
         }
       }
     }]
   }
   ↓
6. AG2框架将Tool Call发送给Executor Agent (control)
   ↓
7. Executor实际执行Python函数:
   result = record_status(
       current_status="in progress",
       current_plan_step_number=1,
       ...
   )
   ↓
8. 函数返回 ReplyResult(target=AgentTarget(camb_context), ...)
   ↓
9. AG2框架根据返回结果路由到下一个智能体
```

---

## 🛠️ 二、CMBAgent 中的实际实现

### 2.1 函数注册（register_function）

**位置**：`cmbagent/functions.py:1192-1212`

```python
# 在 register_functions_to_agents() 中
control = cmbagent_instance.get_agent_from_name('control')

register_function(
    record_status,                    # ⭐ Python函数
    caller=control,                   # ⭐ control智能体作为caller
    executor=control,                 # ⭐ control智能体也作为executor
    description=r"""                  # ⭐ 给LLM的说明
        Updates the context and returns the current progress.
        Must be called **before calling the agent in charge of the next sub-task**.
        Must be called **after** each action taken.

        Args:
            current_status (str): The current status ("in progress", "failed", or "completed").
            current_plan_step_number (int): The current step number in the plan.
            current_sub_task (str): Description of the current sub-task.
            current_instructions (str): Instructions for the sub-task.
            agent_for_sub_task (str): The agent responsible for the sub-task.
            context_variables (dict): context dictionary.

        Returns:
            ReplyResult: Contains a formatted status message and updated context.
        """,
)
```

**核心要点**：

1. `record_status` 是一个普通的Python函数（定义在同文件的第746行）
2. `caller=control` 意味着control的LLM会决定何时调用此函数
3. `executor=control` 意味着control也负责执行（caller和executor可以是同一个agent）
4. `description` 是关键：LLM完全依赖这个描述来理解函数用途

### 2.2 Control 智能体配置

**位置**：`cmbagent/agents/control/control.yaml`

```yaml
name: "control"

instructions: |
  你是control智能体。你只能调用 record_status 工具。  ⭐

  你必须在调用执行智能体**之前**调用 record_status。

  你需要逐步执行以下计划：
  {final_plan}

  当前状态：
  - 当前步骤：{current_plan_step_number}
  - 当前任务：{current_sub_task}
  - 负责智能体：{agent_for_sub_task}
  - 状态：{current_status}
```

**关键设计**：

- Prompt中明确告诉control **只能调用 record_status**
- Prompt中包含当前计划的上下文（`{final_plan}` 等变量会被替换）
- LLM会根据这些信息决定何时调用 `record_status` 以及传递什么参数

---

## 📊 三、参数是如何确定的？

### 3.1 LLM推断参数（核心机制）

**谁决定参数**？**LLM（GPT-4/Claude等）**

**如何决定**？基于以下信息：

1. **System Prompt（control.yaml的instructions）**

   ```yaml
   当前步骤：{current_plan_step_number}    # 会被替换为实际值，如"1"
   当前任务：{current_sub_task}            # 会被替换为"查询CAMB文档"
   负责智能体：{agent_for_sub_task}       # 会被替换为"camb_context"
   ```

2. **Function Description（register_function的description）**

   ```python
   description=r"""
       Args:
           current_status (str): "in progress", "failed", or "completed"
           current_plan_step_number (int): The current step number
           agent_for_sub_task (str): The agent responsible for the sub-task
           ...
   """
   ```

3. **Conversation History（对话历史）**
   - 前一个智能体的消息
   - 之前的执行结果

4. **Function Signature（Python类型提示）**
   ```python
   def record_status(
       current_status: Literal["in progress", "failed", "completed"],
       current_plan_step_number: int,
       current_sub_task: str,
       agent_for_sub_task: Literal["engineer", "researcher", ...],
       ...
   ):
   ```

### 3.2 实际推断过程示例

#### **场景：Planning阶段完成，Control第一次被激活**

**Step 1: AG2发送给control的消息**

```
（这是control收到的system prompt，变量已被替换）

你是control智能体。你只能调用 record_status 工具。

你需要逐步执行以下计划：

Step 1: 查询CAMB文档
  - 任务：了解如何使用CAMB计算功率谱
  - 执行者：camb_context
  - 指令：搜索get_results方法

Step 2: 编写代码
  - 任务：编写CAMB代码
  - 执行者：engineer
  ...

当前状态：
- 当前步骤：1
- 当前任务：查询CAMB文档
- 负责智能体：camb_context
- 状态：in progress
```

**Step 2: LLM分析**

```
LLM思考过程（内部推理，对用户不可见）：
- 我收到的指令说"只能调用 record_status 工具"
- 我看到当前步骤是1，负责智能体是camb_context
- record_status函数的描述说："Must be called before calling the agent in charge of the next sub-task"
- 所以我应该调用 record_status，并传递当前的上下文信息
```

**Step 3: LLM生成Tool Call**

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "record_status",
        "arguments": "{\"current_status\": \"in progress\", \"current_plan_step_number\": 1, \"current_sub_task\": \"查询CAMB文档\", \"current_instructions\": \"搜索get_results方法\", \"agent_for_sub_task\": \"camb_context\"}"
      }
    }
  ]
}
```

**关键点**：

- ✅ `current_plan_step_number: 1` ← LLM从prompt中读取
- ✅ `agent_for_sub_task: "camb_context"` ← LLM解析Step 1的"执行者"
- ✅ `current_status: "in progress"` ← LLM推断（任务刚开始）
- ✅ `current_sub_task` 和 `current_instructions` ← LLM从计划中提取

**Step 4: AG2框架执行**

```python
# AG2自动执行（用户看不到这个过程）
result = record_status(
    current_status="in progress",
    current_plan_step_number=1,
    current_sub_task="查询CAMB文档",
    current_instructions="搜索get_results方法",
    agent_for_sub_task="camb_context",
    context_variables=shared_context  # AG2自动传递
)
# result = ReplyResult(target=AgentTarget(camb_context), ...)
```

**Step 5: AG2路由到下一个智能体**

```python
# AG2根据返回的ReplyResult自动路由
# target=AgentTarget(camb_context) → 激活camb_context智能体
```

---

## 🔍 四、参数来源详解

### 4.1 显式传递 vs LLM推断

| 参数名                     | 值从哪里来？        | 如何传递？                                                                  |
| -------------------------- | ------------------- | --------------------------------------------------------------------------- |
| `current_status`           | **LLM推断**         | LLM根据当前执行阶段判断<br/>（in progress / completed / failed）            |
| `current_plan_step_number` | **Prompt变量**      | `{current_plan_step_number}` 在control prompt中<br/>被替换为实际值（如"1"） |
| `current_sub_task`         | **LLM解析计划**     | LLM从 `{final_plan}` 中提取Step 1的描述                                     |
| `current_instructions`     | **LLM解析计划**     | LLM从 `{final_plan}` 中提取Step 1的指令                                     |
| `agent_for_sub_task`       | **LLM解析计划**     | LLM从 `{final_plan}` 中提取Step 1的"执行者"                                 |
| `context_variables`        | **AG2框架自动传递** | AG2识别函数签名中的`ContextVariables`类型<br/>自动注入当前的上下文字典      |

### 4.2 Prompt变量替换机制

**问题**：`{final_plan}` 这些变量是如何被替换的？

**答案**：通过AG2的 `UpdateSystemMessage` 机制

**代码位置**：`cmbagent/base_agent.py:214`

```python
self.agent = CmbAgentSwarmAgent(
    name=self.name,
    update_agent_state_before_reply=[
        UpdateSystemMessage(self.info["instructions"]),  # ⭐
    ],
    description=self.info["description"],
    llm_config=self.llm_config,
)
```

**工作原理**：

```python
# control.yaml 原始模板
instructions: |
    当前步骤：{current_plan_step_number}
    负责智能体：{agent_for_sub_task}

# AG2在发送给LLM之前，自动替换
# context_variables = {"current_plan_step_number": 1, "agent_for_sub_task": "camb_context"}

# 替换后发送给LLM的实际prompt：
instructions: |
    当前步骤：1
    负责智能体：camb_context
```

---

## 💡 五、常见误解澄清

### ❌ 误解1：Control智能体直接调用record_status

```python
# ❌ 错误理解（这不是真实发生的）
control.call_function(record_status, ...)
```

### ✅ 真相：LLM决定调用，AG2执行

```python
# ✅ 真实流程
1. control的LLM收到消息
2. LLM分析：需要调用record_status
3. LLM生成Tool Call JSON
4. AG2框架解析JSON
5. AG2执行Python函数 record_status(...)
6. AG2处理返回的ReplyResult
7. AG2路由到下一个智能体
```

### ❌ 误解2：参数是硬编码的

```python
# ❌ 错误理解
agent_for_sub_task = "camb_context"  # 某处硬编码
record_status(..., agent_for_sub_task=agent_for_sub_task)
```

### ✅ 真相：参数由LLM从上下文推断

```python
# ✅ 真实流程
1. planner生成计划文本："Step 1的执行者是camb_context"
2. 计划存入context_variables["final_plan"]
3. control的prompt包含 {final_plan}
4. AG2替换变量，发送给LLM
5. LLM读取计划文本，提取"camb_context"
6. LLM生成Tool Call: {"agent_for_sub_task": "camb_context"}
```

### ❌ 误解3：context_variables需要手动传递

```python
# ❌ 错误理解
record_status(..., context_variables=shared_context)
```

### ✅ 真相：AG2自动注入

```python
# ✅ AG2识别函数签名
def record_status(..., context_variables: ContextVariables):
    # AG2看到类型提示 ContextVariables
    # 自动从当前swarm状态中获取并注入
```

---

## 🎓 六、为什么这样设计？

### 6.1 优势

1. **灵活性**
   - LLM可以根据**实时对话上下文**动态调整参数
   - 不需要硬编码复杂的if-else逻辑

2. **自然语言驱动**
   - 只需用自然语言描述函数用途（description）
   - LLM自动理解何时调用、如何传参

3. **容错性**
   - LLM可以处理计划文本的各种格式
   - 不需要严格的JSON schema

4. **可扩展性**
   - 添加新函数只需注册，无需修改agent代码
   - LLM自动学习使用新工具

### 6.2 代价

1. **不可预测性**
   - LLM可能推断错误的参数
   - 需要良好的prompt engineering

2. **成本**
   - 每次函数调用都需要LLM推理
   - 消耗额外的API调用

3. **调试困难**
   - 参数值由LLM"黑盒"推断
   - 需要查看完整的conversation history才能理解

---

## 📚 七、实际调试示例

### 如果你想知道control到底传了什么参数，怎么办？

#### 方法1：查看AG2的debug日志

```python
# 在CMBAgent初始化时
cmbagent_debug = True  # 启用调试模式

# 会打印类似这样的信息：
"""
[control] Tool call: record_status
Arguments: {
  "current_status": "in progress",
  "current_plan_step_number": 1,
  "agent_for_sub_task": "camb_context",
  ...
}
"""
```

#### 方法2：在函数内部打印

```python
def record_status(
    current_status,
    current_plan_step_number,
    agent_for_sub_task,
    ...,
    context_variables
):
    # 在函数开头添加调试日志
    print(f"🔍 record_status called with:")
    print(f"  - current_status: {current_status}")
    print(f"  - step_number: {current_plan_step_number}")
    print(f"  - agent_for_sub_task: {agent_for_sub_task}")

    # 继续执行...
```

#### 方法3：查看LLM的原始响应

```python
# AG2会记录所有LLM的响应
# 包括Tool Call的完整JSON
# 可以通过conversation history查看
```

---

## 🎯 八、总结

### 核心机制

```
Planning阶段生成计划
    ↓
计划存入 context_variables["final_plan"]
    ↓
Control阶段开始
    ↓
AG2替换control prompt中的 {final_plan} 等变量
    ↓
发送完整prompt给control的LLM
    ↓
LLM分析prompt + 注册的functions
    ↓
LLM推断：需要调用record_status
    ↓
LLM从prompt中提取参数值（current_plan_step_number, agent_for_sub_task等）
    ↓
LLM生成Tool Call JSON
    ↓
AG2框架解析JSON，执行Python函数
    ↓
函数返回ReplyResult(target=AgentTarget(camb_context), ...)
    ↓
AG2路由到camb_context智能体
```

### 关键要点

1. ✅ **没有直接调用**：control智能体不会执行 `control.call_function(...)`
2. ✅ **LLM是决策者**：所有参数值都是LLM从上下文中推断出来的
3. ✅ **Prompt是关键**：control的prompt包含了LLM推断参数所需的所有信息
4. ✅ **AG2是执行者**：框架负责解析Tool Call并执行Python函数
5. ✅ **类型提示很重要**：`Literal["engineer", ...]` 限制了LLM的选择范围

---

_文档生成时间：2026-01-09_
_基于AG2 (AutoGen 2.0) 框架_
