# `context_variables` 维护机制详解

## 🎯 核心概念

**`context_variables`** 是AG2多智能体系统的**全局共享状态**，它：

- 📦 **存储所有上下文信息**（计划、状态、执行历史等）
- 🔄 **在智能体间传递**（每次handoff自动携带）
- ✏️ **可被任何智能体/函数修改**（通过ContextVariables类型参数）
- 💾 **持久化整个会话**（从初始化到任务完成）

---

## 🔧 一、完整生命周期

```
1. 初始化 (cmbagent.py:solve())
   ↓
2. 传递给第一个智能体 (AutoPattern)
   ↓
3. 智能体A执行
   ├─ UpdateSystemMessage: 读取context_variables注入prompt
   ├─ LLM生成Tool Call
   └─ 函数执行: 修改context_variables
   ↓
4. AG2自动传递给智能体B
   ↓
5. 智能体B执行（重复步骤3）
   ↓
   ...
   ↓
N. 任务完成，保存final_context
```

---

## 📋 二、初始化阶段

### 2.1 定义默认值

**文件**：`cmbagent/context.py:1-77`

```python
# 全局默认共享上下文
shared_context = {
    # Planning相关
    "plans": [],
    "reviews": [],
    "final_plan": None,
    "number_of_steps_in_plan": None,
    "proposed_plan": None,

    # Control路由相关
    "current_plan_step_number": None,
    "current_sub_task": None,
    "agent_for_sub_task": None,
    "current_status": None,
    "current_instructions": None,

    # 任务相关
    "main_task": None,
    "improved_main_task": None,
    "database_path": "data/",
    "codebase_path": "codebase/",

    # 执行状态
    "previous_steps_execution_summary": "\n",
    "current_codebase": None,
    "displayed_images": [],

    # 重试控制
    "n_attempts": 0,
    "max_n_attempts": 3,

    # RAG上下文
    "camb_context": None,
    "classy_context": None,

    # VLM相关
    "evaluate_plots": False,
    "latest_plot_path": None,
    "vlm_plot_analysis": None,
    "vlm_verdict": None,
    "plot_problems": [],

    # ... 共40+个变量
}
```

**关键点**：

- ✅ 这是**模板字典**，定义所有可能用到的键
- ✅ 初始值大多为 `None`、`[]`、`0` 等
- ✅ 确保所有占位符（如 `{final_plan}`）在字典中都有对应的键

### 2.2 创建ContextVariables实例

**文件**：`cmbagent/cmbagent.py:527-608`

```python
def solve(self, task, initial_agent='task_improver', shared_context=None, ...):
    # 1. 深拷贝默认上下文（避免污染全局默认值）
    this_shared_context = copy.deepcopy(self.shared_context)

    # 2. 如果是one_shot模式，预设简化的上下文
    if mode == "one_shot" or mode == "chat":
        one_shot_shared_context = {
            'final_plan': "Step 1: solve the main task.",
            'current_status': "In progress",
            'current_plan_step_number': 1,
            'current_sub_task': "solve the main task.",
            'current_instructions': "solve the main task.",
            'agent_for_sub_task': initial_agent,  # "engineer", "researcher"等
            'feedback_left': 0,
            'number_of_steps_in_plan': 1,
            # ... 其他简化配置
        }
        this_shared_context.update(one_shot_shared_context)

    # 3. 用户自定义上下文（可选）
    if shared_context is not None:
        this_shared_context.update(shared_context)

    # 4. 设置任务相关字段
    this_shared_context['main_task'] = task
    this_shared_context['improved_main_task'] = task
    this_shared_context['work_dir'] = self.work_dir

    # 5. 🔥 包装成AG2的ContextVariables对象
    context_variables = ContextVariables(data=this_shared_context)

    # 6. 创建AutoPattern（AG2的group chat模式）
    agent_pattern = AutoPattern(
        agents=[agent.agent for agent in self.agents],
        initial_agent=self.get_agent_from_name(initial_agent),
        context_variables=context_variables,  # ⭐ 传递给AG2
        group_manager_args={"llm_config": self.llm_config, ...},
    )

    # 7. 启动group chat
    chat_result, context_variables, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=this_shared_context['main_task'],
        max_rounds=max_rounds,
    )

    # 8. 保存最终上下文（任务完成后）
    self.final_context = copy.deepcopy(context_variables)
```

**关键点**：

- ✅ `ContextVariables(data=dict)` 将普通字典包装成AG2对象
- ✅ `initiate_group_chat` 返回**更新后的** `context_variables`
- ✅ `final_context` 保存任务结束时的完整状态

---

## 🔄 三、传递机制

### 3.1 AG2自动传递

**AG2框架的核心特性**：`context_variables` 在智能体转移时**自动携带**

```python
# AG2内部机制（简化伪代码）
class GroupChat:
    def __init__(self, pattern):
        self.context_variables = pattern.context_variables  # 初始化

    def send_message_to_agent(self, agent, message):
        # 每次激活智能体时，都携带当前的context_variables
        # 1. 调用UpdateSystemMessage（注入prompt）
        for callback in agent.update_agent_state_before_reply:
            callback(agent, message, self.context_variables)  # ⭐ 传递

        # 2. 调用智能体的函数时，自动注入context_variables
        if function_has_context_param(tool):
            result = tool(
                arg1=value1,
                context_variables=self.context_variables  # ⭐ 自动注入
            )

            # 3. 函数可能返回更新后的context_variables
            if isinstance(result, ReplyResult):
                self.context_variables = result.context_variables  # ⭐ 更新
```

**关键点**：

- ✅ **不需要手动传递**：AG2自动在智能体间传递
- ✅ **引用传递**：所有智能体共享同一个ContextVariables对象
- ✅ **函数自动注入**：函数签名中包含 `context_variables: ContextVariables` 时自动注入

### 3.2 实际传递流程示例

```python
# Step 1: control被激活
# AG2调用UpdateSystemMessage
UpdateSystemMessage(control.instructions).format_map(context_variables)
# → control的prompt中 {final_plan} 被替换

# Step 2: control的LLM调用record_status函数
# AG2识别函数签名: def record_status(..., context_variables: ContextVariables)
# AG2自动注入当前的context_variables

# Step 3: record_status函数修改context_variables
def record_status(..., context_variables):
    context_variables["current_plan_step_number"] = 1
    context_variables["agent_for_sub_task"] = "camb_context"
    return ReplyResult(
        target=AgentTarget(camb_context),
        context_variables=context_variables  # ⭐ 返回修改后的上下文
    )

# Step 4: AG2接收ReplyResult，更新全局context_variables
self.context_variables = result.context_variables

# Step 5: AG2激活camb_context
# 自动携带更新后的context_variables
# UpdateSystemMessage看到 current_plan_step_number=1
```

---

## ✏️ 四、修改机制

### 4.1 函数修改context_variables

**规则**：任何注册给智能体的函数，只要签名中包含 `context_variables: ContextVariables`，就能修改它

**示例1：record_status**

```python
# cmbagent/functions.py:746-1187
def record_status(
    current_status: Literal["in progress", "failed", "completed"],
    current_plan_step_number: int,
    current_sub_task: str,
    current_instructions: str,
    agent_for_sub_task: Literal["engineer", "researcher", ...],
    context_variables: ContextVariables  # ⭐ AG2自动注入
) -> ReplyResult:
    # 1. 直接修改（字典操作）
    context_variables["current_plan_step_number"] = current_plan_step_number
    context_variables["current_sub_task"] = current_sub_task
    context_variables["agent_for_sub_task"] = agent_for_sub_task
    context_variables["current_instructions"] = current_instructions
    context_variables["current_status"] = current_status

    # 2. 加载并更新复杂数据
    codes = os.path.join(work_dir, context_variables['codebase_path'])
    docstrings = load_docstrings(codes)
    context_variables["current_codebase"] = docstrings  # 更新代码库信息

    # 3. 处理图片
    image_files = load_plots(data_directory)
    displayed_images = context_variables.get("displayed_images", [])
    new_images = [img for img in image_files if img not in displayed_images]
    context_variables["displayed_images"] = displayed_images + new_images

    # 4. 返回（必须包含context_variables）
    return ReplyResult(
        target=AgentTarget(next_agent),
        message="...",
        context_variables=context_variables  # ⭐必须返回
    )
```

**示例2：post_execution_transfer**

```python
# cmbagent/functions.py:110-270
def post_execution_transfer(
    next_agent_suggestion: Literal["engineer", "installer", ...],
    context_variables: ContextVariables,
    execution_status: Literal["success", "failure"],
    fix_suggestion: Optional[str] = None
) -> ReplyResult:
    # 1. 从全局变量转移到context_variables
    context_variables["latest_executed_code"] = cmbagent.vlm_utils._last_executed_code

    # 2. VLM情况：更新plot相关字段
    if evaluate_plots and new_images:
        context_variables["latest_plot_path"] = most_recent_image
        context_variables["displayed_images"].append(most_recent_image)
        return ReplyResult(
            target=AgentTarget(plot_judge),
            context_variables=context_variables  # ⭐
        )

    # 3. 错误处理：增加重试计数
    if execution_status == "failure":
        context_variables["n_attempts"] += 1

        # 根据错误类型路由
        if "ModuleNotFoundError" in fix_suggestion:
            return ReplyResult(
                target=AgentTarget(installer),
                context_variables=context_variables  # ⭐
            )

    # 4. 成功：重置重试计数
    if execution_status == "success":
        context_variables["n_attempts"] = 0
        return ReplyResult(
            target=AgentTarget(control),
            context_variables=context_variables  # ⭐
        )
```

**示例3：record_plan**

```python
# cmbagent/functions.py:591-656
def record_plan(
    plan_suggestion: str,
    number_of_steps_in_plan: int,
    context_variables: ContextVariables
) -> ReplyResult:
    # 1. 追加到历史列表
    context_variables["plans"].append(plan_suggestion)

    # 2. 设置提议的计划
    context_variables["proposed_plan"] = plan_suggestion
    context_variables["number_of_steps_in_plan"] = number_of_steps_in_plan

    # 3. 决定下一步
    if context_variables["feedback_left"] == 0:
        # 没有更多审查轮次，直接接受计划
        context_variables["final_plan"] = plan_suggestion  # ⭐ 设置最终计划
        return ReplyResult(
            target=TerminateTarget(),  # Planning阶段结束
            message="...",
            context_variables=context_variables
        )
    else:
        # 还有审查轮次，发送给plan_reviewer
        return ReplyResult(
            target=AgentTarget(plan_reviewer),
            message="...",
            context_variables=context_variables
        )
```

### 4.2 修改操作总结

| 操作类型     | 代码示例                                         | 说明           |
| ------------ | ------------------------------------------------ | -------------- |
| **读取**     | `value = context_variables["key"]`               | 字典式访问     |
| **写入**     | `context_variables["key"] = new_value`           | 直接赋值       |
| **追加列表** | `context_variables["plans"].append(plan)`        | 修改可变对象   |
| **条件读取** | `context_variables.get("key", default)`          | 带默认值       |
| **删除**     | `del context_variables["key"]`                   | 删除键（少用） |
| **更新多个** | `context_variables.update({"k1": v1, "k2": v2})` | 批量更新       |

**关键规则**：

1. ✅ **必须返回**：函数返回的 `ReplyResult` 必须包含 `context_variables`
2. ✅ **直接修改**：ContextVariables是引用传递，修改会影响全局状态
3. ✅ **类型无限制**：值可以是str, int, list, dict, None等任意Python对象

---

## 💾 五、持久化机制

### 5.1 会话期间的持久化

```python
# AG2框架确保context_variables在整个group chat期间持久存在
class GroupChat:
    def __init__(self, pattern):
        self.context_variables = pattern.context_variables  # ⭐ 存储为实例变量

    def run_conversation(self):
        current_agent = self.initial_agent
        for round in range(self.max_rounds):
            # 每一轮都使用同一个context_variables
            result = current_agent.generate_reply(
                messages=...,
                context_variables=self.context_variables  # ⭐ 始终传递同一个对象
            )

            # 更新（如果函数返回了新的context_variables）
            if result.context_variables:
                self.context_variables = result.context_variables

            current_agent = result.target_agent

        return self.context_variables  # ⭐ 返回最终状态
```

### 5.2 任务完成后的保存

```python
# cmbagent/cmbagent.py:619-626
chat_result, context_variables, last_agent = initiate_group_chat(
    pattern=agent_pattern,
    messages=task,
    max_rounds=max_rounds,
)

# ⭐ 保存最终上下文（深拷贝，避免后续修改）
self.final_context = copy.deepcopy(context_variables)

# 访问最终状态
print(self.final_context["final_plan"])
print(self.final_context["n_attempts"])
print(self.final_context["previous_steps_execution_summary"])
```

### 5.3 跨会话持久化（可选）

```python
# 保存到文件
import pickle

def save_context(context_variables, filepath):
    with open(filepath, 'wb') as f:
        pickle.dump(dict(context_variables), f)

def load_context(filepath):
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return ContextVariables(data=data)

# 使用
save_context(context_variables, "session_state.pkl")
# ... 重启应用
restored_context = load_context("session_state.pkl")
```

---

## 🔍 六、调试ContextVariables

### 6.1 打印当前状态

```python
# 方法1：在函数内部打印
def record_status(..., context_variables):
    print("🔍 context_variables 快照:")
    print(f"  - current_plan_step_number: {context_variables['current_plan_step_number']}")
    print(f"  - agent_for_sub_task: {context_variables['agent_for_sub_task']}")
    print(f"  - current_status: {context_variables['current_status']}")
    print(f"  - n_attempts: {context_variables['n_attempts']}")
```

### 6.2 追踪修改历史

```python
# 创建包装器记录所有修改
class TrackedContextVariables(ContextVariables):
    def __setitem__(self, key, value):
        print(f"🔧 修改: {key} = {value}")
        super().__setitem__(key, value)

# 使用
context_variables = TrackedContextVariables(data=shared_context)

# 输出:
# 🔧 修改: current_plan_step_number = 1
# 🔧 修改: agent_for_sub_task = camb_context
# ...
```

### 6.3 查看特定时刻的完整状态

```python
# 在关键节点保存快照
def record_plan(..., context_variables):
    # 保存快照
    snapshot = copy.deepcopy(dict(context_variables))
    print("📸 Planning完成时的context_variables:")
    import pprint
    pprint.pprint(snapshot)

    # 继续执行...
```

---

## 🎓 七、最佳实践

### 7.1 命名约定

```python
# ✅ 好的命名
context_variables["current_plan_step_number"]    # 清晰，类型明确
context_variables["vlm_plot_structured_feedback"] # 描述性强

# ❌ 避免的命名
context_variables["data"]    # 太泛泛
context_variables["temp"]    # 不清楚用途
```

### 7.2 初始化所有可能的键

```python
# ✅ 在context.py中预定义
shared_context = {
    "new_feature_flag": False,  # 即使是新功能，也预定义
}

# ❌ 避免在函数中临时创建键
def some_function(context_variables):
    if "undefined_key" not in context_variables:  # 不好的做法
        context_variables["undefined_key"] = default_value
```

### 7.3 避免过度嵌套

```python
# ✅ 扁平结构
context_variables["vlm_verdict"] = "retry"
context_variables["plot_problems"] = ["missing labels"]

# ❌ 过度嵌套（难以在YAML模板中访问）
context_variables["vlm_analysis"] = {
    "verdict": "retry",
    "problems": ["missing labels"]
}
# YAML中无法使用 {vlm_analysis.verdict}
```

### 7.4 使用类型提示

```python
# ✅ 清晰的类型提示
def record_status(
    current_status: Literal["in progress", "failed", "completed"],
    context_variables: ContextVariables  # ⭐ 必须
) -> ReplyResult:
    ...
```

---

## 📚 八、总结

### 核心特点

1. ✅ **全局共享**：所有智能体共享同一个 `context_variables` 对象
2. ✅ **自动传递**：AG2在智能体handoff时自动携带
3. ✅ **函数注入**：函数签名包含 `context_variables: ContextVariables` 时自动注入
4. ✅ **引用修改**：直接修改会影响全局状态
5. ✅ **持久存在**：从初始化到任务完成，始终存在
6. ✅ **字典接口**：像普通dict一样使用（`[]`, `.get()`, `.update()` 等）

### 生命周期总结

```
初始化
  ↓ (copy.deepcopy(shared_context_default))
创建ContextVariables实例
  ↓ (传递给AutoPattern)
AG2 Group Chat开始
  ↓
  ┌─→ 智能体A
  │     ├─ UpdateSystemMessage(读取)
  │     ├─ 函数调用(读取+修改)
  │     └─ 返回ReplyResult(包含更新后的context_variables)
  │
  ├─→ AG2接收并更新全局context_variables
  │
  ├─→ 智能体B (自动携带更新后的context_variables)
  │     ├─ UpdateSystemMessage(读取)
  │     ├─ 函数调用(读取+修改)
  │     └─ ...
  │
  └─→ ... (循环直到任务完成)
  ↓
任务完成，保存final_context
  ↓
返回给用户
```

### 关键API

| 操作         | 代码                                                                                   |
| ------------ | -------------------------------------------------------------------------------------- |
| **初始化**   | `ContextVariables(data=dict)`                                                          |
| **读取**     | `value = context_variables["key"]`<br/>`value = context_variables.get("key", default)` |
| **写入**     | `context_variables["key"] = value`                                                     |
| **更新**     | `context_variables.update({"k1": v1})`                                                 |
| **函数接收** | `def func(..., context_variables: ContextVariables)`                                   |
| **函数返回** | `ReplyResult(..., context_variables=context_variables)`                                |
| **最终保存** | `self.final_context = copy.deepcopy(context_variables)`                                |

---

_文档生成时间：202 6-01-09_
_基于AG2 (AutoGen 2.0) 框架_
