# CMBAgent 技术架构分析

## 项目概览

**CMBAgent** 是一个基于 [AG2](https://github.com/ag2ai/ag2)（AutoGen 2.0）构建的多智能体系统，专门用于自主科学研究，特别是宇宙学研究。该项目采用 **Planning & Control** 策略实现无人工干预的自主研究流程。

---

## 一、Function Calling / Tools（函数调用与工具系统）

### 1.1 核心架构

CMBAgent 的 Function Calling 系统通过 `functions.py` 实现，主要包含以下几类工具：

#### **工具注册机制**

```python
# 文件：cmbagent/functions.py
def register_functions_to_agents(cmbagent_instance):
    '''注册函数到各个智能体'''
    # 使用 AG2 的 register_function 或 _add_single_function 方法
    register_function(
        function_name,
        caller=agent_object,
        executor=agent_object,
        description="功能描述"
    )
```

### 1.2 核心工具函数

#### **1. 工作流控制工具**

| 函数名                       | 功能                             | 关键参数                                    |
| ---------------------------- | -------------------------------- | ------------------------------------------- |
| `record_status()`            | 记录执行状态并路由到下一个智能体 | `current_status`, `agent_for_sub_task`      |
| `post_execution_transfer()`  | 代码执行后的路由决策             | `execution_status`, `next_agent_suggestion` |
| `terminate_session()`        | 终止会话                         | -                                           |
| `route_plot_judge_verdict()` | 基于VLM评判结果路由              | `vlm_verdict`, `plot_problems`              |

#### **2. Planning 相关工具**

```python
# 记录计划
def record_plan(plan_suggestion: str,
                number_of_steps_in_plan: int,
                context_variables: ContextVariables) -> ReplyResult:
    """记录建议的计划并更新执行上下文"""
    context_variables["plans"].append(plan_suggestion)
    if context_variables["feedback_left"] == 0:
        return ReplyResult(target=TerminateTarget(), ...)
    else:
        return ReplyResult(target=AgentTarget(plan_reviewer), ...)

# 记录计划约束
def record_plan_constraints(needed_agents: list, ...) -> ReplyResult:
    """记录计划所需的智能体列表，确保只调用允许的智能体"""
```

#### **3. VLM（视觉语言模型）工具**

```python
def call_vlm_judge(context_variables: ContextVariables) -> ReplyResult:
    """使用VLM分析生成的图表质量"""
    # 读取最新的图表
    img_path = context_variables.get("latest_plot_path")
    # 发送到VLM进行分析
    completion = send_image_to_vlm(base_64_img, vlm_prompt, ...)
    # 解析结构化JSON响应
    vlm_verdict = vlm_analysis_data.get("verdict", "continue")
    # 存储判决结果
    context_variables["vlm_verdict"] = vlm_verdict
```

#### **4. 科学研究专用工具**

```python
# AAS关键词提取
def record_aas_keywords(aas_keywords: list[str], ...) -> ReplyResult:
    """从AAS列表中提取相关关键词"""

# 创意记录
def record_ideas(ideas: list) -> str:
    """保存科学研究创意到JSON文件"""
    filepath = os.path.join(work_dir, f'ideas_{timestamp}.json')
```

### 1.3 工具路由策略

**智能路由决策**（基于执行结果）：

```python
# 执行失败时的路由逻辑
if execution_status == "failure":
    if error == "ModuleNotFoundError":
        return ReplyResult(target=AgentTarget(installer), ...)
    elif "camb" in error:
        return ReplyResult(target=AgentTarget(camb_context), ...)
    elif "classy" in error:
        return ReplyResult(target=AgentTarget(classy_context), ...)
    else:
        return ReplyResult(target=AgentTarget(engineer), ...)
```

### 1.4 工具特点

- ✅ **类型安全**：使用 `Literal` 类型限定智能体选择
- ✅ **上下文传递**：通过 `ContextVariables` 在智能体间共享状态
- ✅ **智能重试**：内置重试机制（`n_attempts` / `max_n_attempts`）
- ✅ **结构化输出**：使用 `ReplyResult` 返回目标智能体和消息

---

## 二、Memory & RAG（记忆与检索增强生成）

### 2.1 RAG 架构设计

#### **RAG智能体系统**

```
cmbagent/agents/rag_agents/
├── camb_agent       # CAMB宇宙学代码包专家
├── classy_sz_agent  # CLASS-SZ专家
├── cobaya_agent     # Cobaya参数推断专家
├── planck_agent     # Planck卫星数据专家
└── ...
```

每个RAG agent包含：

- `.py` 文件：智能体类定义
- `.yaml` 文件：配置文件（instructions + vector store配置）

### 2.2 向量存储管理

#### **核心函数** (`rag_utils.py`)

```python
def push_vector_stores(cmbagent_instance,
                       make_vector_stores,
                       chunking_strategy,
                       verbose=False):
    """
    1. 识别RAG智能体
    2. 删除旧的向量存储
    3. 创建新的向量存储并上传文件
    """
    # 创建向量存储
    vector_store = client.vector_stores.create(
        name=vector_store_name,
        chunking_strategy=chunking_strategy
    )

    # 上传文件
    file_batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id,
        files=file_streams
    )

    # 更新智能体配置
    rag_agent.info['assistant_config']['tool_resources']['file_search']['vector_store_ids'] = [vector_store.id]
```

#### **Chunking 策略配置**

```python
# 默认策略
default_chunking_strategy = {
    "type": "static",
    "static": {
        "max_chunk_size_tokens": 800,
        "chunk_overlap_tokens": 400
    }
}
```

### 2.3 RAG智能体实现

#### **CAMB Agent 示例** (`camb.yaml`)

```yaml
name: "camb_agent"
instructions: |
  你是一个RAG智能体，负责执行文件搜索和建议Python代码片段...

  你必须使用工具调用（file_search）搜索camb包的信息...

  <DOCUMENTATION>
  --------------------------
  **可用的camb方法和类：**

  def get_results(params):
      """计算指定参数的结果并返回CAMBdata实例"""

  def set_params(...):
      """一次性设置所有CAMB参数"""
  ...

assistant_config:
  assistant_id: "asst_xxx"
  tools:
    - type: "file_search"
      file_search:
        max_num_results: 20 # 最多返回20个相关文档
  tool_resources:
    file_search:
      vector_store_ids: ["vs_xxx"] # OpenAI向量存储ID
```

### 2.4 上下文记忆系统

#### **共享上下文** (`context.py`)

```python
shared_context = {
    # Planning记忆
    "plans": [],
    "reviews": [],
    "final_plan": None,
    "proposed_plan": None,

    # 执行状态记忆
    "current_plan_step_number": None,
    "current_sub_task": None,
    "agent_for_sub_task": None,
    "current_status": None,

    # 任务上下文
    "improved_main_task": None,
    "database_path": "data/",
    "codebase_path": "codebase/",

    # RAG上下文
    "camb_context": None,
    "classy_context": None,

    # VLM记忆
    "latest_plot_path": None,
    "latest_executed_code": None,
    "vlm_plot_analysis": None,
    "vlm_verdict": None,
    "plot_problems": [],
    "plot_fixes": [],

    # 重试控制
    "n_attempts": 0,
    "max_n_attempts": 3,
    "n_plot_evals": 0,
    "max_n_plot_evals": 1,
}
```

### 2.5 RAG智能体使用流程

```
1. 需要专业知识 → 路由到RAG agent
   ↓
2. RAG agent使用file_search工具查询向量存储
   ↓
3. 检索相关文档片段（最多max_num_results个）
   ↓
4. 生成基于检索内容的回答（包含文件名引用）
   ↓
5. 返回给后续智能体使用
```

### 2.6 记忆特点

- 🧠 **持久化**：向量存储存在OpenAI服务器
- 🔍 **高效检索**：基于embedding的语义搜索
- 📚 **领域专业**：每个RAG agent专注特定科学包
- 🔄 **动态更新**：支持重建向量存储
- 📝 **引用追踪**：返回结果包含源文件名

---

## 三、智能体编排 - Swarm/Hands-off（群体编排与自主交接）

### 3.1 编排架构

#### **核心编排文件** (`hand_offs.py`)

```python
def register_all_hand_offs(cmbagent_instance):
    """注册所有智能体的交接关系"""

    # 1. 获取所有智能体实例
    planner = cmbagent_instance.get_agent_object_from_name('planner')
    engineer = cmbagent_instance.get_agent_object_from_name('engineer')
    control = cmbagent_instance.get_agent_object_from_name('control')
    # ... 更多智能体

    # 2. 设置固定的交接关系（after_work handoffs）
    planner.agent.handoffs.set_after_work(AgentTarget(planner_response_formatter.agent))
    engineer.agent.handoffs.set_after_work(AgentTarget(engineer_nest.agent))

    # 3. 设置条件交接关系（LLM-based routing）
    control.agent.handoffs.add_llm_conditions([
        OnCondition(
            target=AgentTarget(engineer.agent),
            condition=StringLLMCondition(prompt="Engineer needed to write code")
        ),
        OnCondition(
            target=AgentTarget(researcher.agent),
            condition=StringLLMCondition(prompt="Researcher needed to generate reasoning")
        ),
        # ... 更多条件
    ])
```

### 3.2 智能体类型

#### **46个专业智能体**，分为以下类别：

| 类别                    | 智能体                                              | 功能                         |
| ----------------------- | --------------------------------------------------- | ---------------------------- |
| **Planning**            | `planner`, `plan_reviewer`, `plan_recorder`         | 制定和审查研究计划           |
| **Control**             | `control`, `control_starter`, `admin`               | 工作流控制和用户交互         |
| **Execution**           | `engineer`, `executor`, `installer`                 | 代码编写、执行、依赖安装     |
| **Research**            | `researcher`, `idea_maker`, `idea_hater`            | 文献研究、创意生成与评估     |
| **RAG Experts**         | `camb_agent`, `classy_sz_agent`, `cobaya_agent`     | 领域特定知识检索             |
| **Response Formatting** | `*_response_formatter`                              | 格式化输出以供下一智能体使用 |
| **Specialized**         | `plot_judge`, `plot_debugger`, `aas_keyword_finder` | VLM图表评估、关键词提取      |

### 3.3 编排模式

#### **1. 固定链式交接**

```python
# Planning阶段的链式交接
task_improver → task_recorder → planner → planner_response_formatter
→ plan_recorder → plan_reviewer → reviewer_response_formatter
→ review_recorder → (回到planner或terminator)
```

#### **2. 嵌套对话（Nested Chat）**

```python
# 工程师嵌套对话
nested_chats = [{
    "recipient": executor_manager,
    "message": lambda recipient, messages, sender, config: f"{messages[-1]['content']}",
    "max_turns": 1,
    "summary_method": "last_msg",
}]

engineer_nest.agent.register_nested_chats(
    trigger=lambda sender: sender not in other_agents,
    chat_queue=nested_chats
)
```

#### **3. LLM条件路由**

```python
# Control智能体的智能路由
control.agent.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(engineer.agent),
        condition=StringLLMCondition(
            prompt="Code execution failed."
        )
    ),
    OnCondition(
        target=AgentTarget(terminator.agent),
        condition=StringLLMCondition(
            prompt="The task is completed."
        )
    ),
])
```

#### **4. 函数驱动路由**

```python
# 基于执行结果的动态路由
def post_execution_transfer(...) -> ReplyResult:
    if execution_status == "success":
        if evaluate_plots and new_images:
            return ReplyResult(target=AgentTarget(plot_judge), ...)
        else:
            return ReplyResult(target=AgentTarget(control), ...)
    else:  # failure
        if next_agent_suggestion == "engineer":
            return ReplyResult(target=AgentTarget(engineer), ...)
```

### 3.4 Planning & Control 工作流

#### **Planning阶段**

```
1. task_improver: 改进任务描述
   ↓
2. planner ⇄ plan_reviewer: 迭代设计计划（最多feedback_left轮）
   ↓
3. plan_recorder: 记录最终计划
   ↓
4. 切换到Control阶段
```

#### **Control阶段（逐步执行）**

```
对于计划中的每一步：
  1. control: 调用record_status()更新状态
     ↓
  2. 根据agent_for_sub_task路由到对应智能体：
     - engineer: 编写代码
     - researcher: 文献研究
     - camb_agent: 查询CAMB文档
     - ...
     ↓
  3. 智能体完成子任务后返回control
     ↓
  4. control判断是否继续下一步或终止
```

### 3.5 消息历史管理

```python
# 使用TransformMessages限制上下文长度
context_handling = TransformMessages(
    transforms=[
        MessageHistoryLimiter(max_messages=1),
    ]
)
# 应用到特定智能体
context_handling.add_to_agent(executor_response_formatter.agent)
context_handling.add_to_agent(planner_response_formatter.agent)
```

### 3.6 编排特点

- 🔀 **混合路由**：固定交接 + LLM条件判断 + 函数驱动
- 🎯 **专业分工**：46个智能体各司其职
- 🔁 **智能重试**：失败后自动路由到修复智能体
- 📊 **VLM集成**：图表质量自动评估
- 🧩 **嵌套对话**：复杂任务分解为子对话
- 🔧 **灵活扩展**：通过YAML添加新智能体

---

## 四、技术亮点总结

### 4.1 创新设计

1. **Planning & Control分离**
   - Planning阶段：设计执行计划
   - Control阶段：逐步执行并动态调整

2. **VLM增强的质量控制**
   - 自动评估生成的图表
   - 提供针对性修复建议

3. **领域特定RAG**
   - 每个科学包（CAMB, CLASS, Cobaya）独立向量存储
   - 精确的文档引用

4. **智能错误恢复**
   - 自动识别错误类型
   - 路由到专门的修复智能体

### 4.2 技术栈

```
基础框架：AG2 (AutoGen 2.0)
LLM：OpenAI GPT-4/Claude/Gemini
RAG后端：OpenAI Vector Stores + File Search
代码执行：LocalCommandLineCodeExecutor
前端：Next.js + WebSocket
后端API：FastAPI
```

### 4.3 适用场景

✅ 自主科学计算和数据分析
✅ 复杂多步骤研究任务
✅ 需要领域专业知识的编程
✅ 迭代式创意生成和评估

---

## 五、快速上手示例

```python
import cmbagent

# 1. 定义科学研究任务
task = """
使用CAMB计算宇宙学功率谱，
参数：H0=67, ombh2=0.022, omch2=0.1,
生成TT和EE功率谱的对比图
"""

# 2. 一键执行（Planning + Control）
results = cmbagent.one_shot(
    task,
    agent='engineer',
    engineer_model='gpt-4o',
    work_dir='./output'
)

# 3. 系统自动完成：
#    - Planning: planner设计步骤计划
#    - Control: 逐步执行
#      - camb_agent查询CAMB文档
#      - engineer编写代码
#      - executor执行代码
#      - plot_judge评估生成的图表
#      - 如有问题，plot_debugger提供修复建议
#    - 输出结果到work_dir
```

---

## 六、参考资料

- **GitHub**: https://github.com/CMBAgents/cmbagent
- **论文**: arxiv.org/abs/2507.07257
- **AG2框架**: github.com/ag2ai/ag2
- **HuggingFace演示**: huggingface.co/spaces/astropilot-ai/cmbagent

---

_文档生成时间：2026-01-09_
