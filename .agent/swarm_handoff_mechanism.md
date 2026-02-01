# CMBAgent Swarm编排与Hands-off机制详解

## 🎯 核心概念

**CMBAgent** 使用AG2的 **Swarm Pattern**（群体模式）实现多智能体协作，通过三种**Hands-off（交接）**机制控制智能体间的转移：

1. **固定交接（`set_after_work`）**：预定义的确定性路由
2. **条件交接（`add_llm_conditions + OnCondition`）**：LLM智能判断的动态路由
3. **函数驱动交接（`ReplyResult`）**：函数执行后的程序化路由

---

## 🏗️ 一、Swarm Pattern 架构

### 1.1 什么是Swarm？

**Swarm Pattern** 是AG2的一种编排模式，特点：

- 📍 **去中心化决策**：每个智能体本地决定下一步，无需中央协调器
- 🔄 **上下文共享**：所有智能体共享同一个message context和context_variables
- 🎯 **专业分工**：每个智能体专注特定任务（写代码、执行、审查等）
- 🤝 **动态协作**：通过handoff实现智能体间的任务委托

**类比**：类似医院急诊室，不同专家（内科、外科、放射科）根据病情动态协作

### 1.2 CMBAgent的Swarm架构

```
46个专业智能体
    ├── Planning Group (planne r, plan_reviewer, ...)
    ├── Control Group (control, admin, ...)
    ├── Execution Group (engineer, executor, installer, ...)
    ├── Research Group (researcher, idea_maker, idea_hater, ...)
    ├── RAG Group (camb_agent, classy_sz_agent, cobaya_agent, ...)
    └── Support Group (response_formatters, plot_judge, ...)

通过3种Handoff机制协作：
    1. set_after_work (固定路由)
    2. add_llm_conditions (智能路由)
    3. ReplyResult (函数路由)
```

---

## 🔧 二、三种Handoff机制详解

### 2.1 固定交接（set_after_work）

#### **定义**

预定义的确定性路由，智能体完成任务后**总是**转到指定的下一个智能体

#### **语法**

```python
agent_a.agent.handoffs.set_after_work(AgentTarget(agent_b.agent))
# agent_a完成后 → 总是转到agent_b

agent_terminator.agent.handoffs.set_after_work(TerminateTarget())
# 完成后 → 终止会话
```

#### **实际示例**

**Planning阶段的链式交接**：

```python
# hand_offs.py:112-136
# 固定的线性流程：改进任务 → 记录 → 计划 → 格式化 → 记录 → 审查 → ...

task_improver.agent.handoffs.set_after_work(
    AgentTarget(task_recorder.agent)
)
# task_improver完成 → task_recorder

task_recorder.agent.handoffs.set_after_work(
    AgentTarget(planner.agent)
)
# task_recorder完成 → planner

planner.agent.handoffs.set_after_work(
    AgentTarget(planner_response_formatter.agent)
)
# planner完成 → planner_response_formatter

planner_response_formatter.agent.handoffs.set_after_work(
    AgentTarget(plan_recorder.agent)
)
# 格式化完成 → plan_recorder

plan_recorder.agent.handoffs.set_after_work(
    AgentTarget(plan_reviewer.agent)
)
# 记录完成 → plan_reviewer

plan_reviewer.agent.handoffs.set_after_work(
    AgentTarget(reviewer_response_formatter.agent)
)
# 审查完成 → reviewer_response_formatter

reviewer_response_formatter.agent.handoffs.set_after_work(
    AgentTarget(review_recorder.agent)
)
# 格式化完成 → review_recorder

review_recorder.agent.handoffs.set_after_work(
    AgentTarget(planner.agent)
)
# 记录完成 → 回到planner（形成循环，直到record_plan返回terminate）
```

**流程图**：

```
task_improver
    ↓ (set_after_work)
task_recorder
    ↓
planner
    ↓
planner_response_formatter
    ↓
plan_recorder
    ↓
plan_reviewer
    ↓
reviewer_response_formatter
    ↓
review_recorder
    ↓
planner ← (循环)
```

**RAG Agent的固定交接**：

```python
# hand_offs.py:60-66
camb_context.agent.handoffs.set_after_work(
    AgentTarget(camb_response_formatter.agent)
)
# camb_context查询文档后 → camb_response_formatter格式化

if mode == "one_shot":
    camb_response_formatter.agent.handoffs.set_after_work(
        AgentTarget(engineer.agent)
    )
    # one_shot模式：格式化后 → 直接给engineer
else:
    camb_response_formatter.agent.handoffs.set_after_work(
        AgentTarget(control.agent)
    )
    # planning_and_control模式：格式化后 → 回control
```

**特点**：

- ✅ **确定性**：总是转到同一个智能体
- ✅ **可预测**：流程固定，易于理解
- ✅ **高效**：无需LLM调用判断下一步
- ❌ **不灵活**：无法根据上下文动态调整

### 2.2 条件交接（add_llm_conditions + OnCondition）

#### **定义**

基于**LLM智能判断**的动态路由，LLM根据对话上下文决定转到哪个智能体

#### **语法**

```python
agent.agent.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(agent_b.agent),
        condition=StringLLMCondition(prompt="条件描述")
    ),
    OnCondition(
        target=AgentTarget(agent_c.agent),
        condition=StringLLMCondition(prompt="另一个条件")
    ),
])
```

#### **工作原理**

```
1. agent完成任务
   ↓
2. AG2检查：是否有OnCondition handoffs？
   ↓ 有
3. AG2将所有OnCondition的prompt发送给agent的LLM
   ↓
4. LLM分析当前对话上下文 + 各个condition的prompt
   ↓
5. LLM选择最匹配的condition，生成tool call
   ↓
6. AG2根据tool call结果，转到对应的target agent
   ↓
7. 如果没有condition匹配，fallback到set_after_work的default handoff
```

#### **实际示例：Control智能体的智能路由**

```python
# hand_offs.py:307-344
# Control智能体使用LLM动态决定下一个智能体

# 默认fallback：如果所有condition都不匹配，终止
control.agent.handoffs.set_after_work(AgentTarget(terminator.agent))

# 添加LLM条件判断
control.agent.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(engineer.agent),
        condition=StringLLMCondition(prompt="Code execution failed.")
    ),
    # LLM理解：代码执行失败了 → 转给engineer修复

    OnCondition(
        target=AgentTarget(researcher.agent),
        condition=StringLLMCondition(prompt="Researcher needed to generate reasoning, write report, or interpret results")
    ),
    # LLM理解：需要生成推理或写报告 → 转给researcher

    OnCondition(
        target=AgentTarget(engineer.agent),
        condition=StringLLMCondition(prompt="Engineer needed to write code, make plots, do calculations.")
    ),
    # LLM理解：需要写代码或做计算 → 转给engineer

    OnCondition(
        target=AgentTarget(idea_maker.agent),
        condition=StringLLMCondition(prompt="idea_maker needed to make new ideas")
    ),
    # LLM理解：需要生成新创意 → 转给idea_maker

    OnCondition(
        target=AgentTarget(idea_hater.agent),
        condition=StringLLMCondition(prompt="idea_hater needed to critique ideas")
    ),
    # LLM理解：需要批评创意 → 转给idea_hater

    OnCondition(
        target=AgentTarget(terminator.agent),
        condition=StringLLMCondition(prompt="The task is completed.")
    ),
    # LLM理解：任务完成了 → 终止
])
```

#### **LLM的内部推理过程**（简化）

```
Situation: Step 2执行完成，control被激活

Control的system message:
- Current step: 2
- Status: completed
- Next step: Step 3 (需要生成报告)

AG2发送给LLM的tool schemas:
1. handoff_to_engineer (condition: "Code execution failed")
2. handoff_to_researcher (condition: "Researcher needed to write report")
3. handoff_to_engineer (condition: "Engineer needed to write code")
4. handoff_to_idea_maker (condition: "idea_maker needed to make ideas")
5. handoff_to_terminator (condition: "Task is completed")

LLM思考：
- Step 2已完成 ✓
- Step 3需要生成报告 ✓
- Condition 2匹配："Researcher needed to write report" ✓

LLM生成tool call:
{
  "function": "handoff_to_researcher",
  "arguments": {}
}

AG2执行：
→ 激活researcher智能体
```

#### **特点**：

- ✅ **智能**：LLM根据上下文动态判断
- ✅ **灵活**：可以适应多种情况
- ✅ **自然**：用自然语言描述条件
- ❌ **成本高**：每次handoff都需要LLM调用
- ❌ **不稳定**：LLM可能误判

### 2.3 函数驱动交接（ReplyResult）

#### **定义**

通过函数执行结果**程序化决定**下一个智能体，结合了确定性和灵活性

#### **语法**

```python
def some_function(..., context_variables: ContextVariables) -> ReplyResult:
    # 根据逻辑判断
    if condition_a:
        next_agent = agent_a
    elif condition_b:
        next_agent = agent_b
    else:
        next_agent = default_agent

    return ReplyResult(
        target=AgentTarget(next_agent),  # ⭐ 程序化决定
        message="...",
        context_variables=context_variables
    )
```

#### **实际示例1：record_status的路由逻辑**

```python
# functions.py:746-1187
def record_status(
    current_status: Literal["in progress", "failed", "completed"],
    agent_for_sub_task: Literal["engineer", "researcher", ...],
    context_variables: ContextVariables
) -> ReplyResult:

    agent_to_transfer_to = None

    # 1. 状态是"in progress" → 转到执行智能体
    if current_status == "in progress":
        if agent_for_sub_task == "engineer":
            agent_to_transfer_to = get_agent('engineer')
        elif agent_for_sub_task == "researcher":
            agent_to_transfer_to = get_agent('researcher')
        elif agent_for_sub_task == "camb_context":
            agent_to_transfer_to = get_agent('camb_context')
        # ... 其他智能体

    # 2. 状态是"completed" → 判断是否所有步骤完成
    elif current_status == "completed":
        context_variables["n_attempts"] = 0  # 重置重试计数

        if current_plan_step_number == number_of_steps_in_plan:
            # 所有步骤完成 → admin
            agent_to_transfer_to = get_agent('admin')
        else:
            # 还有步骤 → 回control继续
            agent_to_transfer_to = get_agent('control')

    # 3. 状态是"failed" → 根据agent_for_sub_task决定如何修复
    elif current_status == "failed":
        if agent_for_sub_task == "engineer":
            # 工程师任务失败 → 转回engineer重试
            agent_to_transfer_to = get_agent('engineer')
        elif agent_for_sub_task == "researcher":
            # 研究员任务失败 → 转到格式化器
            agent_to_transfer_to = get_agent('researcher_response_formatter')

    return ReplyResult(
        target=AgentTarget(agent_to_transfer_to),
        context_variables=context_variables
    )
```

#### **实际示例2：post_execution_transfer的错误恢复**

```python
# functions.py:110-270
def post_execution_transfer(
    execution_status: Literal["success", "failure"],
    next_agent_suggestion: Literal["engineer", "installer", ...],
    fix_suggestion: Optional[str],
    context_variables: ContextVariables
) -> ReplyResult:

    # 1. 检查重试次数
    if context_variables["n_attempts"] >= context_variables["max_n_attempts"]:
        return ReplyResult(
            target=AgentTarget(terminator),
            message="Max attempts reached.",
            context_variables=context_variables
        )

    # 2. 执行成功
    if execution_status == "success":
        # 检查是否需要VLM评估图表
        if context_variables.get("evaluate_plots") and new_images:
            context_variables["latest_plot_path"] = most_recent_image
            return ReplyResult(
                target=AgentTarget(plot_judge),  # → plot_judge
                context_variables=context_variables
            )
        else:
            # 没有图表或不需要评估 → control
            context_variables["n_attempts"] = 0
            return ReplyResult(
                target=AgentTarget(control),  # → control
                context_variables=context_variables
            )

    # 3. 执行失败 - 智能错误恢复
    else:  # failure
        context_variables["n_attempts"] += 1

        # 根据错误类型路由
        if "ModuleNotFoundError" in fix_suggestion:
            # 缺少依赖 → installer
            return ReplyResult(
                target=AgentTarget(installer),
                context_variables=context_variables
            )

        elif "camb" in fix_suggestion.lower():
            # CAMB相关错误 → camb_context查询文档
            return ReplyResult(
                target=AgentTarget(camb_context),
                context_variables=context_variables
            )

        elif "classy" in fix_suggestion.lower():
            # CLASS相关错误 → classy_context
            return ReplyResult(
                target=AgentTarget(classy_context),
                context_variables=context_variables
            )

        elif next_agent_suggestion == "plot_debugger":
            # 图表问题 → plot_debugger
            return ReplyResult(
                target=AgentTarget(plot_debugger),
                context_variables=context_variables
            )

        else:
            # 一般错误 → engineer重新编写
            return ReplyResult(
                target=AgentTarget(engineer),
                context_variables=context_variables
            )
```

#### **特点**：

- ✅ **确定性**：程序化逻辑，可预测
- ✅ **灵活性**：可以实现复杂的条件判断
- ✅ **高效**：不需要额外的LLM调用
- ✅ **可调试**：可以打印日志追踪路由逻辑
- ❌ **需要编码**：需要在函数中实现路由逻辑

---

## 🔄 三、三种Handoff的优先级

### 3.1 执行顺序

```
智能体完成任务后：

1. 检查：是否有函数返回ReplyResult？
   ↓ 有
   使用ReplyResult.target指定的智能体 ✓（优先级最高）

2. 检查：是否有OnCondition handoffs？
   ↓ 有
   LLM评估所有condition，选择匹配的
   ↓ 有匹配
   使用OnCondition.target指定的智能体 ✓

3. 检查：是否有set_after_work？
   ↓ 有
   使用set_after_work指定的智能体 ✓（fallback）

4. 都没有？
   ↓
   终止会话或返回用户 ✓（默认行为）
```

### 3.2 实际示例：Control智能体的完整handoff逻辑

```python
# Step 1: Control有set_after_work（fallback）
control.agent.handoffs.set_after_work(AgentTarget(terminator.agent))

# Step 2: Control有add_llm_conditions（智能路由）
control.agent.handoffs.add_llm_conditions([
    OnCondition(target=AgentTarget(engineer.agent), ...),
    OnCondition(target=AgentTarget(researcher.agent), ...),
    # ...
])

# Step 3: Control调用record_status函数（函数路由）
# record_status返回ReplyResult(target=AgentTarget(camb_context), ...)

# 执行优先级：
# 1. record_status的ReplyResult → camb_context ✓ (最高)
# 2. add_llm_conditions → engineer/researcher/... (LLM判断)
# 3. set_after_work → terminator (fallback)
```

**流程图**：

```
control被激活
    ↓
调用record_status函数
    ↓
record_status返回ReplyResult(target=camb_context)
    ↓
AG2检测到ReplyResult ← 优先级1
    ↓
忽略OnCondition (优先级2)
忽略set_after_work (优先级3)
    ↓
直接激活camb_context ✓
```

---

## 🎯 四、Nested Chat（嵌套对话）

### 4.1 什么是Nested Chat？

**Nested Chat** 是一种特殊的handoff模式，允许智能体内部启动一个**子对话**，完成后再返回主流程

**类比**：主线任务中召开小组会议讨论子问题，会议结束后继续主任务

### 4.2 Engineer的Nested Chat

```python
# hand_offs.py:187-228
# Engineer需要执行代码，但自己不能执行
# 使用nested chat：engineer → engineer_nest → executor → engineer_response_formatter

# 1. 创建嵌套对话的GroupChat
executor_chat = GroupChat(
    agents=[
        engineer_response_formatter.agent,  # 格式化engineer的代码
        executor.agent,                     # 执行代码
    ],
    messages=[],
    max_round=3,
    speaker_selection_method='round_robin',  # 轮流发言
)

# 2. 创建GroupChatManager管理嵌套对话
executor_manager = GroupChatManager(
    groupchat=executor_chat,
    llm_config=cmbagent_instance.llm_config,
    name="engineer_nested_chat",
)

# 3. 定义嵌套对话配置
nested_chats = [{
    "recipient": executor_manager,  # 接收者：嵌套对话的管理器
    "message": lambda recipient, messages, sender, config:
        f"{messages[-1]['content']}" if messages else "",  # 转发最后一条消息
    "max_turns": 1,  # 只运行1轮
    "summary_method": "last_msg",  # 用最后一条消息作为摘要
}]

# 4. 注册到engineer_nest
engineer_nest.agent.register_nested_chats(
    trigger=lambda sender: sender not in other_agents,  # 触发条件
    chat_queue=nested_chats
)

# 5. 设置handoff链
engineer.agent.handoffs.set_after_work(
    AgentTarget(engineer_nest.agent)
)
# engineer完成 → engineer_nest

engineer_nest.agent.handoffs.set_after_work(
    AgentTarget(executor_response_formatter.agent)
)
# 嵌套对话完成 → executor_response_formatter
```

### 4.3 Nested Chat流程

```
主流程：
    control
      ↓
    engineer (生成代码)
      ↓
    engineer_nest (触发嵌套对话)
      ↓
    ┌─────────────────────────────────┐
    │   嵌套对话（executor_manager）   │
    │                                 │
    │   engineer_response_formatter   │
    │   (提取代码)                     │
    │         ↓                       │
    │   executor                      │
    │   (执行代码)                     │
    │         ↓                       │
    │   执行结果                       │
    │         ↓                       │
    │   返回给executor_manager        │
    └─────────────────────────────────┘
      ↓
    executor_response_formatter (格式化结果)
      ↓
    调用post_execution_transfer函数
      ↓
    根据执行结果路由到下一个智能体
```

**优势**：

- ✅ 隔离子任务的复杂度
- ✅ 可重用的对话模式
- ✅ 主流程更清晰

---

## 💡 五、实际工作流示例

### 示例：Planning & Control完整流程

```
═══════════════════════════════════════════════════════════════
                      PLANNING阶段
═══════════════════════════════════════════════════════════════

task_improver (改进任务描述)
    ↓ (set_after_work - 固定)
task_recorder (调用record_improved_task函数)
    ↓ (set_after_work - 固定)
planner (生成执行计划)
    ↓ (set_after_work - 固定)
planner_response_formatter (格式化计划)
    ↓ (set_after_work - 固定)
plan_recorder (调用record_plan函数)
    ├─ feedback_left > 0?
    │   ↓ Yes (函数驱动)
    │   plan_reviewer (审查计划)
    │       ↓ (set_after_work - 固定)
    │   reviewer_response_formatter (格式化审查意见)
    │       ↓ (set_after_work - 固定)
    │   review_recorder (调用record_review函数)
    │       ↓ (函数驱动)
    │   planner ← (循环，根据审查意见修改计划)
    │
    └─ feedback_left == 0?
        ↓ Yes (函数驱动)
        TerminateTarget() ← Planning阶段结束

═══════════════════════════════════════════════════════════════
                      CONTROL阶段
═══════════════════════════════════════════════════════════════

control_starter (初始化)
    ↓ (调用record_status_starter函数 - 函数驱动)
    读取final_plan Step 1: agent_for_sub_task="camb_context"
    ↓
camb_context (查询CAMB文档)
    ↓ (set_after_work - 固定)
camb_response_formatter (格式化RAG结果)
    ↓ (set_after_work - 固定，根据mode)
control (调用record_status函数)
    ↓ (函数驱动)
    读取final_plan Step 2: agent_for_sub_task="engineer"
    ↓
engineer (编写代码)
    ↓ (set_after_work - 固定)
engineer_nest (触发嵌套对话)
    ├─ 嵌套对话开始
    │   engineer_response_formatter (提取代码)
    │       ↓
    │   executor (执行代码)
    │       ↓
    │   返回执行结果
    └─ 嵌套对话结束
    ↓ (set_after_work - 固定)
executor_response_formatter (格式化执行结果)
    ↓ (调用post_execution_transfer函数 - 函数驱动)
    ├─ execution_status == "success"?
    │   ↓ Yes
    │   ├─ evaluate_plots && new_images?
    │   │   ↓ Yes
    │   │   plot_judge (VLM评估图表)
    │   │       ↓ (调用call_vlm_judge和route_plot_judge_verdict)
    │   │       ├─ verdict == "retry"?
    │   │       │   ↓ Yes
    │   │       │   plot_debugger (提供修复建议)
    │   │       │       ↓
    │   │       │   engineer ← (重新生成代码)
    │   │       │
    │   │       └─ verdict == "continue"?
    │   │           ↓ Yes
    │   │           control
    │   │
    │   └─ No
    │       control (继续下一步)
    │
    └─ execution_status == "failure"?
        ↓ Yes
        n_attempts++
        ├─ "ModuleNotFoundError"?
        │   ↓ Yes
        │   installer (安装依赖)
        │       ↓ (set_after_work - 固定)
        │   executor_bash (执行bash命令)
        │       ↓ (set_after_work - 固定)
        │   executor_response_formatter
        │       ↓
        │   control
        │       ↓
        │   engineer ← (重新执行代码)
        │
        ├─ "camb" in error?
        │   ↓ Yes
        │   camb_context (查询CAMB文档)
        │       ↓
        │   engineer ← (根据文档修复)
        │
        └─ 其他错误?
            ↓ Yes
            engineer ← (重新编写代码)

control (所有步骤完成后)
    ├─ LLM条件判断 (add_llm_conditions)
    │   ├─ "Task is completed"? → terminator ✓
    │   ├─ "Engineer needed"? → engineer
    │   ├─ "Researcher needed"? → researcher
    │   └─ ...
    │
    └─ fallback (set_after_work)
        → terminator

═══════════════════════════════════════════════════════════════
                      任务结束
═══════════════════════════════════════════════════════════════
```

---

## 📊 六、Handoff策略总结

### 6.1 各阶段使用的Handoff类型

| 阶段            | 主要使用的Handoff类型        | 原因                           |
| --------------- | ---------------------------- | ------------------------------ |
| **Planning**    | 固定交接（`set_after_work`） | 流程固定，线性执行             |
| **Control**     | 混合（函数驱动 + LLM条件）   | 需要根据计划和执行结果动态路由 |
| **Execution**   | 函数驱动（`ReplyResult`）    | 根据执行结果智能恢复错误       |
| **Nested Chat** | 固定交接                     | 子对话流程固定                 |

### 6.2 选择Handoff类型的指导原则

#### **使用set_after_work（固定交接）**

- ✅ 流程固定，总是同一个下一步
- ✅ 需要高效，避免LLM调用
- ✅ RAG agent完成后返回formatter
- ✅ Planning阶段的线性流程

**示例**：

```python
camb_context.agent.handoffs.set_after_work(
    AgentTarget(camb_response_formatter.agent))
```

#### **使用add_llm_conditions（LLM条件）**

- ✅ 下一步不确定，需要根据上下文判断
- ✅ 有多个可能的路径
- ✅ 条件难以用代码表达
- ✅ Control智能体的多路由

**示例**：

```python
control.agent.handoffs.add_llm_conditions([
    OnCondition(target=engineer, condition="需要写代码"),
    OnCondition(target=researcher, condition="需要写报告"),
])
```

#### **使用ReplyResult（函数驱动）**

- ✅ 需要根据函数执行结果路由
- ✅ 条件可以用代码清晰表达
- ✅ 需要精确控制路由逻辑
- ✅ 错误恢复场景

**示例**：

```python
if execution_status == "success":
    return ReplyResult(target=AgentTarget(control), ...)
else:
    return ReplyResult(target=AgentTarget(engineer), ...)
```

---

## 🎓 七、总结

### 核心要点

1. ✅ **Swarm Pattern**：46个专业智能体通过handoff协作
2. ✅ **3种Handoff机制**：
   - `set_after_work`：确定性，高效
   - `add_llm_conditions + OnCondition`：智能判断，灵活
   - `ReplyResult`：程序化控制，精确
3. ✅ **优先级**：函数驱动 > LLM条件 > 固定交接
4. ✅ **Nested Chat**：处理复杂子任务（如代码执行）
5. ✅ **混合策略**：Planning用固定，Control用混合，Execution用函数

### Hands-off的本质

**Hands-off** 不是"放手不管"，而是**智能委托**：

- 🤖 每个智能体专注自己的专业领域
- 🔄 通过handoff将任务传递给最合适的智能体
- 🧠 结合确定性路由和智能判断
- 🎯 实现复杂任务的自主分解和执行

**类比**：像一个高效的团队，每个成员知道何时完成自己的工作，何时将任务交给下一个专家

---

_文档生成时间：2026-01-09_
_基于AG2 (AutoGen 2.0) Swarm Pattern_
