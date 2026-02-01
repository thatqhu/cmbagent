# `agent_for_sub_task` 实现机制详解

## 📌 核心概念

`agent_for_sub_task` 是 CMBAgent 中 **Planning & Control 工作流的核心路由变量**，用于指定当前计划步骤应该由哪个智能体执行。它实现了从计划到执行的精确映射。

---

## 🎯 一、整体工作流程

```
Planning阶段
    ↓
【确定计划】final_plan = "Step 1: 查询CAMB文档 (camb_context)
                           Step 2: 编写代码 (engineer)
                           Step 3: 生成报告 (researcher)"
    ↓
Control阶段（逐步执行）
    ↓
对于每个步骤：
  1. control调用 record_status(agent_for_sub_task="camb_context", ...)
  2. record_status 设置上下文并路由到 camb_context
  3. camb_context 完成任务后返回 control
  4. control 调用 record_status(current_status="completed", ...)
  5. 继续下一步骤
```

---

## 🔍 二、核心数据结构

### 2.1 上下文定义 (`context.py`)

```python
shared_context = {
    # Planning相关
    "final_plan": None,              # 最终确定的计划文本
    "number_of_steps_in_plan": None, # 计划总步数

    # Control路由核心变量
    "current_plan_step_number": None,  # 当前步骤编号 (1, 2, 3, ...)
    "current_sub_task": None,          # 当前子任务描述
    "agent_for_sub_task": None,        # ⭐ 负责执行的智能体名称
    "current_instructions": None,      # 给该智能体的具体指令
    "current_status": None,            # "in progress" | "completed" | "failed"

    # 其他上下文
    "previous_steps_execution_summary": "\n",  # 之前步骤的执行摘要
    "n_attempts": 0,                   # 当前步骤的重试次数
    "max_n_attempts": 3,               # 最大重试次数
}
```

---

## 🛠️ 三、关键函数实现

### 3.1 `record_status()` - 状态记录与路由核心

**位置**：`cmbagent/functions.py:746-1187`

**函数签名**：

```python
def record_status(
    current_status: Literal["in progress", "failed", "completed"],
    current_plan_step_number: int,
    current_sub_task: str,
    current_instructions: str,
    agent_for_sub_task: Literal[
        "engineer",
        "researcher",
        "camb_context",
        "classy_context",
        "aas_keyword_finder",
        # ... 更多允许的智能体
    ],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    核心功能：
    1. 更新上下文变量（current_plan_step_number, agent_for_sub_task等）
    2. 加载当前代码库的docstrings
    3. 显示新生成的图表
    4. 根据 agent_for_sub_task 和 current_status 决定下一个智能体

    调用时机：
    - 必须在调用执行智能体**之前**调用
    - 每次状态变化后调用
    """
```

**核心逻辑**：

```python
# 第1步：更新上下文
context_variables["current_plan_step_number"] = current_plan_step_number
context_variables["current_sub_task"] = current_sub_task
context_variables["agent_for_sub_task"] = agent_for_sub_task  # ⭐ 设置执行智能体
context_variables["current_instructions"] = current_instructions
context_variables["current_status"] = current_status

# 第2步：加载当前代码库（给智能体提供上下文）
codes = os.path.join(work_dir, context_variables['codebase_path'])
docstrings = load_docstrings(codes)
context_variables["current_codebase"] = docstrings_string

# 第3步：显示新生成的图表
data_directory = os.path.join(work_dir, context_variables['database_path'])
image_files = load_plots(data_directory)
new_images = [img for img in image_files if img not in displayed_images]
for img_file in new_images:
    display(IPImage(filename=img_file))
context_variables["displayed_images"] = displayed_images + new_images

# 第4步：根据状态和agent_for_sub_task决定路由
agent_to_transfer_to = None

if current_status == "in progress":
    # 状态是"进行中"，路由到指定的执行智能体
    if agent_for_sub_task == "engineer":
        agent_to_transfer_to = get_agent('engineer')
    elif agent_for_sub_task == "researcher":
        agent_to_transfer_to = get_agent('researcher')
    elif agent_for_sub_task == "camb_context":
        agent_to_transfer_to = get_agent('camb_context')
    # ... 其他智能体

elif current_status == "completed":
    # 任务完成，重置重试计数器
    context_variables["n_attempts"] = 0

    if current_plan_step_number == number_of_steps_in_plan:
        # 所有步骤完成，返回admin
        agent_to_transfer_to = get_agent('admin')
    else:
        # 继续下一步，返回admin（由admin询问用户是否继续）
        agent_to_transfer_to = get_agent('admin')

elif current_status == "failed":
    # 任务失败，根据agent_for_sub_task决定如何修复
    if agent_for_sub_task == "engineer":
        # 代码执行失败，返回engineer重新编写
        agent_to_transfer_to = get_agent('engineer')
    elif agent_for_sub_task == "researcher":
        # 研究任务失败，返回researcher_response_formatter
        agent_to_transfer_to = get_agent('researcher_response_formatter')

# 第5步：返回路由结果
return ReplyResult(
    target=AgentTarget(agent_to_transfer_to),
    message=f"""
    **Step number:** {current_plan_step_number} out of {number_of_steps_in_plan}
    **Sub-task:** {current_sub_task}
    **Agent in charge of sub-task:** `{agent_for_sub_task}`  ⭐
    **Instructions:** {current_instructions}
    **Status:** {current_status}
    """,
    context_variables=context_variables
)
```

### 3.2 `control` 智能体配置

**位置**：`cmbagent/agents/control/control.yaml`

```yaml
name: "control"

instructions: |
  你是control智能体。你只能调用 record_status 工具。

  你必须在调用执行智能体**之前**调用 record_status。

  你需要逐步执行以下计划：
  {final_plan}

  当前状态：
  - 当前步骤：{current_plan_step_number}
  - 当前任务：{current_sub_task}
  - 负责智能体：{agent_for_sub_task}  ⭐
  - 状态：{current_status}

  注意事项：
  1. 必须逐步执行计划，直到所有步骤成功完成
  2. 如果代码执行失败，必须修复后才能继续下一步
  3. 绝不能在所有步骤完成前调用terminator
```

**关键点**：

- Control智能体只有一个工具：`record_status`
- Control的prompt中包含 `{agent_for_sub_task}` 变量，会被动态替换
- Control不直接与其他智能体交互，完全通过 `record_status` 路由

---

## 🔄 四、完整执行流程示例

### 示例任务

```
使用CAMB计算宇宙学功率谱并生成图表
```

### 4.1 Planning阶段输出

```
final_plan = """
Step 1: 查询CAMB文档
  - 任务：了解如何使用CAMB计算功率谱
  - 执行者：camb_context
  - 指令：搜索get_results和set_params方法

Step 2: 编写Python代码
  - 任务：编写CAMB计算代码
  - 执行者：engineer
  - 指令：使用H0=67, ombh2=0.022生成TT功率谱

Step 3: 生成报告
  - 任务：解释结果
  - 执行者：researcher
  - 指令：分析功率谱的物理意义
"""

context_variables["number_of_steps_in_plan"] = 3
```

### 4.2 Control阶段执行（详细时序）

#### **Step 1: 查询CAMB文档**

```python
# 1️⃣ control智能体被激活
# control读取final_plan，解析出：
# - current_plan_step_number = 1
# - current_sub_task = "查询CAMB文档"
# - agent_for_sub_task = "camb_context"
# - current_instructions = "搜索get_results和set_params方法"

# 2️⃣ control调用record_status工具
control.call_function(
    record_status,
    current_status="in progress",
    current_plan_step_number=1,
    current_sub_task="查询CAMB文档",
    current_instructions="搜索get_results和set_params方法",
    agent_for_sub_task="camb_context"  # ⭐ 指定执行者
)

# 3️⃣ record_status内部执行
# - 更新context_variables["agent_for_sub_task"] = "camb_context"
# - 判断current_status == "in progress"
# - agent_to_transfer_to = get_agent('camb_context')
# - 返回 ReplyResult(target=AgentTarget(camb_context), ...)

# 4️⃣ AG2框架自动路由到camb_context
# camb_context收到消息：
"""
**Step number:** 1 out of 3
**Sub-task:** 查询CAMB文档
**Agent in charge of sub-task:** `camb_context`
**Instructions:** 搜索get_results和set_params方法
**Status:** in progress ⏳
"""

# 5️⃣ camb_context执行file_search
# 搜索向量存储，找到相关CAMB文档
# 返回结果给control

# 6️⃣ control再次调用record_status
control.call_function(
    record_status,
    current_status="completed",  # ⭐ 状态改为完成
    current_plan_step_number=1,
    current_sub_task="查询CAMB文档",
    current_instructions="搜索get_results和set_params方法",
    agent_for_sub_task="camb_context"
)

# 7️⃣ record_status判断
# - current_status == "completed"
# - current_plan_step_number (1) != number_of_steps_in_plan (3)
# - agent_to_transfer_to = get_agent('admin')
# - 返回给admin，询问用户是否继续
```

#### **Step 2: 编写代码**

```python
# 1️⃣ 用户确认继续，control被再次激活
# control解析final_plan的Step 2

# 2️⃣ control调用record_status
control.call_function(
    record_status,
    current_status="in progress",
    current_plan_step_number=2,
    current_sub_task="编写Python代码",
    current_instructions="使用H0=67, ombh2=0.022生成TT功率谱",
    agent_for_sub_task="engineer"  # ⭐ 切换到engineer
)

# 3️⃣ record_status路由到engineer
# - context_variables["agent_for_sub_task"] = "engineer"
# - agent_to_transfer_to = get_agent('engineer')

# 4️⃣ engineer执行
# engineer嵌套对话：engineer → engineer_nest → executor
# executor执行代码

# 5️⃣ 如果执行成功
executor_response_formatter.call_function(
    post_execution_transfer,
    execution_status="success",
    next_agent_suggestion="control"
)
# → 返回control

# 6️⃣ control调用record_status标记完成
control.call_function(
    record_status,
    current_status="completed",
    current_plan_step_number=2,
    # ... 其他参数
)

# 🔴 如果执行失败
executor_response_formatter.call_function(
    post_execution_transfer,
    execution_status="failure",
    next_agent_suggestion="engineer",  # 建议返回engineer修复
    fix_suggestion="ModuleNotFoundError: No module named 'camb'"
)
# → 根据错误类型路由到installer或engineer

# installer安装依赖后，返回control
# control再次调用record_status(status="in progress", agent_for_sub_task="engineer")
# 重新执行Step 2
```

#### **Step 3: 生成报告**

```python
# 类似Step 1/2的流程
# agent_for_sub_task = "researcher"
# researcher生成markdown报告
```

---

## ⚙️ 五、`agent_for_sub_task` 的关键设计

### 5.1 类型安全

```python
agent_for_sub_task: Literal[
    "engineer",
    "researcher",
    "camb_context",
    "classy_context",
    "aas_keyword_finder",
]
```

- 使用 `Literal` 类型限定只能使用允许的智能体
- 编译时检查，避免拼写错误
- IDE自动补全支持

### 5.2 与 `post_execution_transfer` 的区别

| 对比项       | `agent_for_sub_task`     | `post_execution_transfer` 的 `next_agent_suggestion` |
| ------------ | ------------------------ | ---------------------------------------------------- |
| **作用范围** | 计划层面的智能体分配     | 执行层面的错误恢复路由                               |
| **设置位置** | `record_status()` 参数   | `post_execution_transfer()` 参数                     |
| **决策者**   | planner（Planning阶段）  | executor_response_formatter（执行实时判断）          |
| **生命周期** | 整个计划步骤期间保持不变 | 仅在执行失败时提供建议                               |
| **示例**     | `"engineer"`             | `"installer"`, `"camb_context"`, `"engineer"`        |

**协同工作**：

```python
# Control阶段：Step 2正在执行
context_variables["agent_for_sub_task"] = "engineer"  # 计划指定

# 代码执行失败
post_execution_transfer(
    execution_status="failure",
    next_agent_suggestion="installer"  # ⭐ 建议先安装依赖
)
# → 路由到installer

# installer完成后返回control
# control再次调用record_status，agent_for_sub_task仍然是"engineer"
# → 继续让engineer重试
```

### 5.3 状态机模型

```
                   record_status(status="in progress", agent="engineer")
                                    ↓
┌─────────────────────────────────────────────────────────────┐
│                        Engineer任务                          │
│  context_variables["agent_for_sub_task"] = "engineer"       │
└─────────────────────────────────────────────────────────────┘
                                    ↓
              ┌─────────────────────┴─────────────────────┐
              ↓                                           ↓
     post_execution_transfer                    post_execution_transfer
     (status="success")                        (status="failure")
              ↓                                           ↓
      返回control                              根据错误类型路由：
              ↓                                - installer (缺依赖)
    record_status                             - camb_context (CAMB错误)
    (status="completed")                      - engineer (一般错误)
              ↓                                           ↓
       继续下一步                              修复后返回control
                                                        ↓
                                              record_status
                                              (status="in progress",
                                               agent="engineer")
                                               重新执行→
```

---

## 💡 六、实际使用场景

### 场景1：线性任务执行

```python
# Planning阶段生成的计划
plan = """
Step 1: 提取AAS关键词 (aas_keyword_finder)
Step 2: 文献检索 (researcher)
Step 3: 编写代码 (engineer)
"""

# Control执行
# Step 1
record_status(agent_for_sub_task="aas_keyword_finder", status="in progress")
# → aas_keyword_finder提取关键词
record_status(agent_for_sub_task="aas_keyword_finder", status="completed")

# Step 2
record_status(agent_for_sub_task="researcher", status="in progress")
# → researcher生成文献综述
record_status(agent_for_sub_task="researcher", status="completed")

# Step 3
record_status(agent_for_sub_task="engineer", status="in progress")
# → engineer编写代码
```

### 场景2：错误恢复

```python
# Step 2: 使用CAMB编写代码
record_status(agent_for_sub_task="engineer", status="in progress")
# → engineer编写代码
# → executor执行代码
# → 💥 出现CAMB内部错误

# post_execution_transfer智能判断
post_execution_transfer(
    execution_status="failure",
    next_agent_suggestion="camb_context",  # 建议查询CAMB文档
    fix_suggestion="AttributeError: 'CAMBparams' has no attribute 'set_cosmology'"
)
# → 路由到camb_context
# → camb_context查询正确用法
# → 返回control

# control再次调用engineer（agent_for_sub_task未变）
record_status(agent_for_sub_task="engineer", status="in progress")
# → engineer根据camb_context的建议修复代码
# → 成功执行
record_status(agent_for_sub_task="engineer", status="completed")
```

### 场景3：VLM图表评估

```python
# Step 3: 生成图表
record_status(agent_for_sub_task="engineer", status="in progress")
# → engineer生成图表代码
# → executor执行
# 💡 post_execution_transfer检测到新图表
if evaluate_plots and new_images:
    return ReplyResult(target=AgentTarget(plot_judge), ...)
# → plot_judge调用VLM评估
# → VLM判决：verdict="retry"（图表有问题）
# → plot_debugger生成修复建议
# → 返回engineer修复

# ⭐ agent_for_sub_task始终保持"engineer"，确保步骤一致性
```

---

## 🎓 七、设计优势

### 7.1 关注点分离

- **Planning层**：关注"做什么"（agent_for_sub_task）
- **Execution层**：关注"怎么做"（post_execution_transfer）

### 7.2 可追溯性

```python
# 任何时刻都能知道：
print(f"当前步骤 {context_variables['current_plan_step_number']}")
print(f"负责智能体 {context_variables['agent_for_sub_task']}")
print(f"执行状态 {context_variables['current_status']}")
```

### 7.3 灵活的错误恢复

```python
# agent_for_sub_task保持不变，但允许临时调用其他智能体修复问题
# 修复完成后自动返回原计划的智能体
```

### 7.4 幂等性

```python
# 相同的agent_for_sub_task可以被重复调用
# 直到current_status变为"completed"
while context_variables["current_status"] != "completed":
    if context_variables["n_attempts"] >= context_variables["max_n_attempts"]:
        break  # 超过最大重试次数
    record_status(agent_for_sub_task="engineer", status="in progress")
```

---

## 📚 八、总结

`agent_for_sub_task` 是CMBAgent实现 **Planning与Control分离** 的关键机制：

1. **Planning阶段**：planner决定每一步由哪个智能体执行（设置agent_for_sub_task）
2. **Control阶段**：control通过record_status严格按计划路由
3. **Execution阶段**：post_execution_transfer提供智能错误恢复
4. **整体流程**：计划驱动 + 实时调整 = 自主完成复杂任务

这种设计使得系统能够：

- ✅ 按预定计划有序执行
- ✅ 自动处理执行错误
- ✅ 在失败时智能重试
- ✅ 保持执行过程可追溯
- ✅ 支持VLM、RAG等高级功能的无缝集成

---

_文档生成时间：2026-01-09_
