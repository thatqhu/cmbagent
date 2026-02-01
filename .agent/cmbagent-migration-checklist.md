# CMBAgent 迁移清单

本文档列出了 `aiscientist` 项目中所有使用 `cmbagent` 的位置，以便逐个考虑替换为 `planning_and_control_simple` 方法。

---

## 📍 调用点总览

| #   | 文件             | 行号 | 方法                                     | 优先级 |
| --- | ---------------- | ---- | ---------------------------------------- | ------ |
| 1   | `idea.py`        | 61   | `planning_and_control_context_carryover` | 🔴 高  |
| 2   | `method.py`      | 49   | `planning_and_control_context_carryover` | 🔴 高  |
| 3   | `experiment.py`  | 82   | `planning_and_control_context_carryover` | 🔴 高  |
| 4   | `aiscientist.py` | 258  | `preprocess_task`                        | 🟡 中  |
| 5   | `aiscientist.py` | 804  | `get_keywords`                           | 🟢 低  |
| 6   | `paper_node.py`  | 39   | `get_keywords`                           | 🟢 低  |

---

## 🔴 调用点 1: Idea Generation (idea.py)

### 📄 文件位置

`aiscientist/idea.py` - 第 61-73 行

### 📋 当前实现

```python
def develop_idea(self, data_description: str) -> str:
    """
    Develops an idea based on the data description.

    Args:
        data_description: description of the data and tools to be used.
    """

    results = cmbagent.planning_and_control_context_carryover(data_description,
                          n_plan_reviews = 1,
                          max_plan_steps = 6,
                          idea_maker_model = self.idea_maker_model,
                          idea_hater_model = self.idea_hater_model,
                          plan_instructions=self.planner_append_instructions,
                          planner_model=self.planner_model,
                          plan_reviewer_model=self.plan_reviewer_model,
                          work_dir = self.idea_dir,
                          api_keys = self.api_keys,
                          default_llm_model = self.orchestration_model,
                          default_formatter_model = self.formatter_model
                         )

    chat_history = results['chat_history']

    try:
        task_result = get_task_result(chat_history,'idea_maker_nest')
    except Exception as e:
        raise e

    pattern = r'\*\*Ideas\*\*\s*\n- Idea 1:'
    replacement = "Project Idea:"
    task_result = re.sub(pattern, replacement, task_result)

    return task_result
```

### 🎯 使用的模型参数

- `idea_maker_model` - 创意生成器模型
- `idea_hater_model` - 创意批评者模型
- `planner_model` - 规划器模型
- `plan_reviewer_model` - 规划审查者模型
- `default_llm_model` (orchestration_model) - 默认编排模型
- `default_formatter_model` (formatter_model) - 格式化模型

**总计: 6 个不同的模型参数**

### 💡 替换建议

```python
def develop_idea(self, data_description: str) -> str:
    """
    Develops an idea based on the data description.

    Args:
        data_description: description of the data and tools to be used.
    """

    results = cmbagent.planning_and_control_simple(
        data_description,
        model = self.unified_model,  # 统一模型
        api_key = self.api_keys.get_key(self.unified_model),
        base_url = self.api_keys.get_base_url(self.unified_model),  # 如果需要
        n_plan_reviews = 1,
        max_plan_steps = 6,
        plan_instructions = self.planner_append_instructions,
        work_dir = self.idea_dir,
        skip_rag_agents = True,  # 跳过 RAG agents
    )

    chat_history = results['chat_history']

    try:
        task_result = get_task_result(chat_history,'idea_maker_nest')
    except Exception as e:
        raise e

    pattern = r'\*\*Ideas\*\*\s*\n- Idea 1:'
    replacement = "Project Idea:"
    task_result = re.sub(pattern, replacement, task_result)

    return task_result
```

### ⚠️ 注意事项

- 需要修改 `Idea.__init__()` 接受 `unified_model` 参数
- 确认 `get_task_result` 仍然能找到 `'idea_maker_nest'` 节点
- 测试结果质量是否与多模型版本相当

### ✅ 迁移步骤

- [ ] 修改 `Idea.__init__()` 签名
- [ ] 更新 `develop_idea()` 方法
- [ ] 测试 idea generation 功能
- [ ] 对比多模型和单模型结果质量
- [ ] 更新相关文档

---

## 🔴 调用点 2: Method Generation (method.py)

### 📄 文件位置

`aiscientist/method.py` - 第 49-62 行

### 📋 当前实现

````python
def develop_method(self, data_description: str) -> str:
    """
    Develops the methods based on the data description.

    Args:
        data_description: description of the data and tools to be used.
    """

    results = cmbagent.planning_and_control_context_carryover(data_description,
                          n_plan_reviews = 1,
                          max_n_attempts = 4,
                          max_plan_steps = 4,
                          researcher_model = self.researcher_model,
                          planner_model = self.planner_model,
                          plan_reviewer_model = self.plan_reviewer_model,
                          plan_instructions = self.planner_append_instructions,
                          researcher_instructions = self.researcher_append_instructions,
                          work_dir = self.method_dir,
                          api_keys = self.api_keys,
                          default_llm_model = self.orchestration_model,
                          default_formatter_model = self.formatter_model
                         )

    chat_history = results['chat_history']

    try:
        task_result = get_task_result(chat_history,'researcher_response_formatter')
    except Exception as e:
        raise e

    MD_CODE_BLOCK_PATTERN = r"```[ \t]*(?:markdown)[ \t]*\r?\n(.*)\r?\n[ \t]*```"
    extracted_methodology = re.findall(MD_CODE_BLOCK_PATTERN, task_result, flags=re.DOTALL)[0]
    clean_methodology = re.sub(r'^<!--.*?-->\s*\n', '', extracted_methodology)
    return clean_methodology
````

### 🎯 使用的模型参数

- `researcher_model` - 研究者模型
- `planner_model` - 规划器模型
- `plan_reviewer_model` - 规划审查者模型
- `default_llm_model` (orchestration_model) - 默认编排模型
- `default_formatter_model` (formatter_model) - 格式化模型

**总计: 5 个不同的模型参数**

### 💡 替换建议

````python
def develop_method(self, data_description: str) -> str:
    """
    Develops the methods based on the data description.

    Args:
        data_description: description of the data and tools to be used.
    """

    results = cmbagent.planning_and_control_simple(
        data_description,
        model = self.unified_model,  # 统一模型
        api_key = self.api_keys.get_key(self.unified_model),
        base_url = self.api_keys.get_base_url(self.unified_model),  # 如果需要
        n_plan_reviews = 1,
        max_n_attempts = 4,
        max_plan_steps = 4,
        plan_instructions = self.planner_append_instructions,
        researcher_instructions = self.researcher_append_instructions,
        work_dir = self.method_dir,
        skip_rag_agents = True,
    )

    chat_history = results['chat_history']

    try:
        task_result = get_task_result(chat_history,'researcher_response_formatter')
    except Exception as e:
        raise e

    MD_CODE_BLOCK_PATTERN = r"```[ \t]*(?:markdown)[ \t]*\r?\n(.*)\r?\n[ \t]*```"
    extracted_methodology = re.findall(MD_CODE_BLOCK_PATTERN, task_result, flags=re.DOTALL)[0]
    clean_methodology = re.sub(r'^<!--.*?-->\s*\n', '', extracted_methodology)
    return clean_methodology
````

### ⚠️ 注意事项

- 需要修改 `Method.__init__()` 接受 `unified_model` 参数
- 确认 `get_task_result` 仍然能找到 `'researcher_response_formatter'` 节点
- 保留 `researcher_instructions` 参数传递

### ✅ 迁移步骤

- [ ] 修改 `Method.__init__()` 签名
- [ ] 更新 `develop_method()` 方法
- [ ] 测试 method generation 功能
- [ ] 对比多模型和单模型结果质量
- [ ] 更新相关文档

---

## 🔴 调用点 3: Experiment Execution (experiment.py)

### 📄 文件位置

`aiscientist/experiment.py` - 第 82-100 行

### 📋 当前实现

````python
def run_experiment(self, data_description: str, **kwargs):
    """
    Run the experiment.
    TODO: improve docstring
    """

    print(f"Engineer model: {self.engineer_model}")
    print(f"Researcher model: {self.researcher_model}")
    print(f"Planner model: {self.planner_model}")
    print(f"Plan reviewer model: {self.plan_reviewer_model}")
    print(f"Max n attempts: {self.max_n_attempts}")
    print(f"Max n steps: {self.max_n_steps}")
    print(f"Restart at step: {self.restart_at_step}")
    print(f"Hardware constraints: {self.hardware_constraints}")

    results = cmbagent.planning_and_control_context_carryover(data_description,
                        n_plan_reviews = 1,
                        max_n_attempts = self.max_n_attempts,
                        max_plan_steps = self.max_n_steps,
                        max_rounds_control = 500,
                        engineer_model = self.engineer_model,
                        researcher_model = self.researcher_model,
                        planner_model = self.planner_model,
                        plan_reviewer_model = self.plan_reviewer_model,
                        plan_instructions=self.planner_append_instructions,
                        researcher_instructions=self.researcher_append_instructions,
                        engineer_instructions=self.engineer_append_instructions,
                        work_dir = self.experiment_dir,
                        api_keys = self.api_keys,
                        restart_at_step = self.restart_at_step,
                        hardware_constraints = self.hardware_constraints,
                        default_llm_model = self.orchestration_model,
                        default_formatter_model = self.formatter_model
                        )
    chat_history = results['chat_history']
    final_context = results['final_context']

    try:
        task_result = get_task_result(chat_history,'researcher_response_formatter')
    except Exception as e:
        raise e

    MD_CODE_BLOCK_PATTERN = r"```[ \t]*(?:markdown)[ \t]*\r?\n(.*)\r?\n[ \t]*```"
    extracted_results = re.findall(MD_CODE_BLOCK_PATTERN, task_result, flags=re.DOTALL)[0]
    clean_results = re.sub(r'^<!--.*?-->\s*\n', '', extracted_results)
    self.results = clean_results
    self.plot_paths = final_context['displayed_images']

    return None
````

### 🎯 使用的模型参数

- `engineer_model` - 工程师模型
- `researcher_model` - 研究者模型
- `planner_model` - 规划器模型
- `plan_reviewer_model` - 规划审查者模型
- `default_llm_model` (orchestration_model) - 默认编排模型
- `default_formatter_model` (formatter_model) - 格式化模型

**总计: 6 个不同的模型参数**

### 💡 替换建议

````python
def run_experiment(self, data_description: str, **kwargs):
    """
    Run the experiment.
    TODO: improve docstring
    """

    print(f"Unified model: {self.unified_model}")
    print(f"Max n attempts: {self.max_n_attempts}")
    print(f"Max n steps: {self.max_n_steps}")
    print(f"Restart at step: {self.restart_at_step}")
    print(f"Hardware constraints: {self.hardware_constraints}")

    results = cmbagent.planning_and_control_simple(
        data_description,
        model = self.unified_model,  # 统一模型
        api_key = self.api_keys.get_key(self.unified_model),
        base_url = self.api_keys.get_base_url(self.unified_model),  # 如果需要
        n_plan_reviews = 1,
        max_n_attempts = self.max_n_attempts,
        max_plan_steps = self.max_n_steps,
        max_rounds_control = 500,
        plan_instructions = self.planner_append_instructions,
        researcher_instructions = self.researcher_append_instructions,
        engineer_instructions = self.engineer_append_instructions,
        work_dir = self.experiment_dir,
        restart_at_step = self.restart_at_step,
        hardware_constraints = self.hardware_constraints,
        skip_rag_agents = True,
    )
    chat_history = results['chat_history']
    final_context = results['final_context']

    try:
        task_result = get_task_result(chat_history,'researcher_response_formatter')
    except Exception as e:
        raise e

    MD_CODE_BLOCK_PATTERN = r"```[ \t]*(?:markdown)[ \t]*\r?\n(.*)\r?\n[ \t]*```"
    extracted_results = re.findall(MD_CODE_BLOCK_PATTERN, task_result, flags=re.DOTALL)[0]
    clean_results = re.sub(r'^<!--.*?-->\s*\n', '', extracted_results)
    self.results = clean_results
    self.plot_paths = final_context['displayed_images']

    return None
````

### ⚠️ 注意事项

- 需要修改 `Experiment.__init__()` 接受 `unified_model` 参数
- 这是最复杂的调用，需要保留 `engineer_instructions` 和 `researcher_instructions`
- 确认 `final_context['displayed_images']` 仍然可用
- **关键**: 实验执行涉及代码生成和执行，需要重点测试

### ✅ 迁移步骤

- [ ] 修改 `Experiment.__init__()` 签名
- [ ] 更新 `run_experiment()` 方法
- [ ] 测试完整的实验流程
- [ ] 验证代码生成和执行功能
- [ ] 对比多模型和单模型结果质量
- [ ] 更新相关文档

---

## 🟡 调用点 4: Data Description Enhancement (aiscientist.py)

### 📄 文件位置

`aiscientist/aiscientist.py` - 第 258-262 行

### 📋 当前实现

```python
def enhance_data_description(self,
                             summarizer_model: str,
                             summarizer_response_formatter_model: str) -> None:
    """
    Enhance the data description using the preprocess_task from cmbagent.

    Args:
        summarizer_model: LLM to be used for summarization.
        summarizer_response_formatter_model: LLM to be used for formatting the summarization response.
    """

    # Check if data description exists
    if not hasattr(self.research, 'data_description') or not self.research.data_description:
        # Try to load from file if it exists
        try:
            with open(os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE), 'r') as f:
                self.research.data_description = f.read()
        except FileNotFoundError:
            raise ValueError("No data description found. Please set a data description first before enhancing it.")

    # Get the enhanced text from preprocess_task
    enhanced_text = preprocess_task(self.research.data_description,
                                    work_dir = self.project_dir,
                                    summarizer_model = summarizer_model,
                                    summarizer_response_formatter_model = summarizer_response_formatter_model
                                    )

    # ... (后续处理代码)
```

### 🎯 使用的模型参数

- `summarizer_model` - 摘要生成模型
- `summarizer_response_formatter_model` - 格式化模型

**总计: 2 个不同的模型参数**

### 💡 替换建议

**选项 A: 如果 cmbagent 提供了 `preprocess_task_simple`**

```python
def enhance_data_description(self,
                             model: str = None) -> None:
    """
    Enhance the data description using the preprocess_task from cmbagent.

    Args:
        model: LLM to be used for summarization (optional, uses unified_model if not provided).
    """

    # Check if data description exists
    if not hasattr(self.research, 'data_description') or not self.research.data_description:
        try:
            with open(os.path.join(self.project_dir, INPUT_FILES, DESCRIPTION_FILE), 'r') as f:
                self.research.data_description = f.read()
        except FileNotFoundError:
            raise ValueError("No data description found. Please set a data description first before enhancing it.")

    # Use unified model if not specified
    model = model or self.unified_model

    # Get the enhanced text from preprocess_task_simple
    enhanced_text = preprocess_task_simple(
        self.research.data_description,
        work_dir = self.project_dir,
        model = model,
        api_key = self.keys.get_key(model),
        base_url = self.keys.get_base_url(model),
    )

    # ... (后续处理代码)
```

**选项 B: 保持不变（优先级较低）**

- `preprocess_task` 功能相对独立，可以暂时保留原有的双模型模式
- 等待 cmbagent 提供简化版本后再迁移

### ⚠️ 注意事项

- 需要确认 cmbagent 是否提供了 `preprocess_task_simple` 方法
- 如果没有，可以考虑在此阶段跳过此调用点
- 这是预处理步骤，影响相对较小

### ✅ 迁移步骤

- [ ] 确认 cmbagent 是否有 `preprocess_task_simple`
- [ ] 如果有，修改 `enhance_data_description()` 方法
- [ ] 如果没有，暂时跳过，保留原有实现
- [ ] 测试数据描述增强功能
- [ ] 更新相关文档

---

## 🟢 调用点 5: Get Keywords (aiscientist.py)

### 📄 文件位置

`aiscientist/aiscientist.py` - 第 804 行

### 📋 当前实现

```python
def get_keywords(self, input_text: str, n_keywords: int = 5, kw_type: str = 'unesco') -> None:
    """
    Get keywords from input text using cmbagent.

    Args:
        input_text (str): Text to extract keywords from
        n_keywords (int, optional): Number of keywords to extract. Defaults to 5.
        kw_type (str, optional): Type of keywords to extract. Defaults to 'unesco'.

    Returns:
        dict: Dictionary mapping keywords to their URLs
    """

    keywords = cmbagent.get_keywords(input_text, n_keywords = n_keywords, kw_type = kw_type, api_keys = self.keys)
    self.research.keywords = keywords # type: ignore
    print('keywords: ', self.research.keywords)
```

### 🎯 使用的模型参数

- `api_keys` - 通过 KeyManager 管理，内部可能使用默认模型

**总计: 隐式使用 1 个模型**

### 💡 替换建议

**选项 A: 如果 cmbagent 提供了 `get_keywords_simple`**

```python
def get_keywords(self, input_text: str, n_keywords: int = 5, kw_type: str = 'unesco', model: str = None) -> None:
    """
    Get keywords from input text using cmbagent.

    Args:
        input_text (str): Text to extract keywords from
        n_keywords (int, optional): Number of keywords to extract. Defaults to 5.
        kw_type (str, optional): Type of keywords to extract. Defaults to 'unesco'.
        model (str, optional): LLM model to use. Defaults to unified_model.

    Returns:
        dict: Dictionary mapping keywords to their URLs
    """

    # Use unified model if not specified
    model = model or self.unified_model

    keywords = cmbagent.get_keywords_simple(
        input_text,
        n_keywords = n_keywords,
        kw_type = kw_type,
        model = model,
        api_key = self.keys.get_key(model),
        base_url = self.keys.get_base_url(model),
    )
    self.research.keywords = keywords # type: ignore
    print('keywords: ', self.research.keywords)
```

**选项 B: 保持不变（如果 cmbagent 内部已经简化）**

- 如果 `get_keywords` 本身已经只使用单一模型，可以保持不变
- 只需要确保传入的 `api_keys` 包含正确的模型配置

### ⚠️ 注意事项

- 这是一个辅助功能，优先级较低
- 需要确认 cmbagent 是否提供了 `get_keywords_simple` 方法
- 如果原方法已经很简单，可以不修改

### ✅ 迁移步骤

- [ ] 确认 cmbagent 的 `get_keywords` 方法签名
- [ ] 确认是否需要 `get_keywords_simple`
- [ ] 如果需要，修改调用方式
- [ ] 测试关键词提取功能
- [ ] 更新相关文档

---

## 🟢 调用点 6: Keywords in Paper Node (paper_node.py)

### 📄 文件位置

`aiscientist/paper_agents/paper_node.py` - 第 39 行

### 📋 当前实现

```python
if state['paper']['cmbagent_keywords']:
    ################ CMB Agent keywords ###############
    # Extract keywords
    PROMPT = cmbagent_keywords_prompt(state)
    keywords = cmbagent.get_keywords(PROMPT, n_keywords = 8)

    # Extract keys and join them with a comma.
    keywords = ", ".join(keywords.keys())
    ###################################################
```

### 🎯 使用的模型参数

- 隐式使用内部默认模型

**总计: 隐式使用 1 个模型**

### 💡 替换建议

**选项 A: 传入统一模型（推荐）**

```python
if state['paper']['cmbagent_keywords']:
    ################ CMB Agent keywords ###############
    # Extract keywords
    PROMPT = cmbagent_keywords_prompt(state)

    # 从 state 获取统一模型配置
    model = state.get('unified_model', 'gpt-4o')  # 默认值
    api_key = state['keys'].get_key(model)
    base_url = state['keys'].get_base_url(model)

    keywords = cmbagent.get_keywords_simple(
        PROMPT,
        n_keywords = 8,
        model = model,
        api_key = api_key,
        base_url = base_url,
    )

    # Extract keys and join them with a comma.
    keywords = ", ".join(keywords.keys())
    ###################################################
```

**选项 B: 修改 state 结构**

```python
# 在调用 paper generation 时，确保 state 包含统一模型配置
input_state = {
    "files": {"Folder": self.project_dir},
    "llm": {
        "model": llm.name,
        "temperature": llm.temperature,
        "max_output_tokens": llm.max_output_tokens
    },
    "unified_model": llm.name,  # 添加统一模型配置
    "paper": {
        "journal": journal,
        "add_citations": add_citations,
        "cmbagent_keywords": cmbagent_keywords
    },
    "keys": self.keys,
    "writer": writer,
}
```

### ⚠️ 注意事项

- 需要修改 `GraphState` 类型定义，添加 `unified_model` 字段
- 或者直接从 `state['llm']['model']` 获取模型名称
- 这是论文生成流程的一部分，需要保持一致性

### ✅ 迁移步骤

- [ ] 确认 `GraphState` 类型定义位置
- [ ] 添加 `unified_model` 字段到 state
- [ ] 修改 `keywords_node` 函数
- [ ] 测试论文关键词生成功能
- [ ] 更新相关文档

---

## 📊 迁移优先级和依赖关系

### 优先级顺序

1. **🔴 高优先级** (核心功能)
   - 调用点 1: Idea Generation
   - 调用点 2: Method Generation
   - 调用点 3: Experiment Execution

2. **🟡 中优先级** (辅助功能)
   - 调用点 4: Data Description Enhancement

3. **🟢 低优先级** (可选功能)
   - 调用点 5: Get Keywords (aiscientist.py)
   - 调用点 6: Keywords in Paper Node

### 依赖关系

```
调用点 1 (Idea) → 调用点 2 (Method) → 调用点 3 (Experiment) → 调用点 6 (Paper Keywords)
                                                                   ↑
                                                     调用点 5 (Get Keywords)
                                                                   ↑
调用点 4 (Enhance) ────────────────────────────────────────────────┘
```

### 建议迁移顺序

1. 先迁移 **调用点 1** (Idea)，验证基本功能
2. 迁移 **调用点 2** (Method)，确保流程连贯
3. 迁移 **调用点 3** (Experiment)，完成核心功能迁移
4. 迁移 **调用点 6** (Paper Keywords)，与调用点 3 一起测试
5. 迁移 **调用点 5** (Get Keywords)，确保 API 一致性
6. 最后迁移 **调用点 4** (Enhance)，如果 cmbagent 提供了简化版本

---

## 🛠️ 所需的 cmbagent 方法

为了完成迁移，需要 `cmbagent` 提供以下方法：

### 1. `planning_and_control_simple` ✅ (已提供)

```python
def planning_and_control_simple(
    data_description: str,
    model: str,
    api_key: str | dict,
    base_url: str | None = None,
    n_plan_reviews: int = 1,
    max_plan_steps: int = 6,
    max_n_attempts: int = 10,
    max_rounds_control: int = 500,
    plan_instructions: str | None = None,
    researcher_instructions: str | None = None,
    engineer_instructions: str | None = None,
    work_dir: str | Path,
    restart_at_step: int = -1,
    hardware_constraints: str | None = None,
    skip_rag_agents: bool = True,
    **kwargs
) -> dict
```

### 2. `get_keywords_simple` ❓ (需要确认)

```python
def get_keywords_simple(
    prompt: str,
    n_keywords: int = 8,
    model: str = "gpt-4o",
    api_key: str | dict = None,
    base_url: str | None = None,
    kw_type: str = 'aas',
) -> dict
```

### 3. `preprocess_task_simple` ❓ (需要确认)

```python
def preprocess_task_simple(
    data_description: str,
    work_dir: str | Path,
    model: str,
    api_key: str | dict,
    base_url: str | None = None,
) -> str
```

---

## 📝 通用修改模式

### 类构造函数修改模式

```python
# Before
class SomeClass:
    def __init__(self,
                 model_a: str,
                 model_b: str,
                 model_c: str,
                 ...):
        self.model_a = model_a
        self.model_b = model_b
        self.model_c = model_c

# After
class SomeClass:
    def __init__(self,
                 unified_model: str = "gpt-4o",
                 # 保留旧参数以实现向后兼容
                 model_a: str = None,
                 model_b: str = None,
                 model_c: str = None,
                 use_simple_mode: bool = True,
                 ...):
        if use_simple_mode:
            self.unified_model = unified_model
        else:
            # 向后兼容模式
            self.model_a = model_a or unified_model
            self.model_b = model_b or unified_model
            self.model_c = model_c or unified_model
```

### API 调用修改模式

```python
# Before
results = cmbagent.planning_and_control_context_carryover(
    data_description,
    model_a = self.model_a,
    model_b = self.model_b,
    model_c = self.model_c,
    api_keys = self.api_keys,
    ...
)

# After
results = cmbagent.planning_and_control_simple(
    data_description,
    model = self.unified_model,
    api_key = self.api_keys.get_key(self.unified_model),
    base_url = self.api_keys.get_base_url(self.unified_model),
    skip_rag_agents = True,
    ...
)
```

---

## ✅ 迁移检查清单

### 准备阶段

- [ ] 阅读本迁移清单
- [ ] 理解 `planning_and_control_simple` 的接口和行为
- [ ] 确认 cmbagent 版本更新到包含 `planning_and_control_simple` 的版本
- [ ] 创建测试分支进行迁移工作
- [ ] 备份当前工作代码

### 核心迁移

- [ ] 迁移调用点 1: Idea Generation
- [ ] 测试 idea generation 功能
- [ ] 迁移调用点 2: Method Generation
- [ ] 测试 method generation 功能
- [ ] 迁移调用点 3: Experiment Execution
- [ ] 测试完整的研究流程 (idea → method → experiment)

### 辅助功能迁移

- [ ] 迁移调用点 6: Keywords in Paper Node
- [ ] 测试论文生成功能
- [ ] 迁移调用点 5: Get Keywords (aiscientist.py)
- [ ] 测试关键词提取功能
- [ ] 迁移调用点 4: Data Description Enhancement (如果可用)

### 质量保证

- [ ] 运行完整的集成测试
- [ ] 对比单模型和多模型版本的输出质量
- [ ] 性能基准测试
- [ ] 成本分析 (API 调用次数和 tokens 使用)
- [ ] 代码审查

### 文档和清理

- [ ] 更新 README.md
- [ ] 更新 API 文档
- [ ] 更新示例代码
- [ ] 添加迁移指南
- [ ] 清理已弃用的代码 (如果决定不保留向后兼容)

---

## 📈 预期收益

### 成本降低

- **减少 API 调用**: 从 6 个不同的模型调用减少到 1 个
- **减少 Token 使用**: 避免在不同模型间切换的额外开销
- **估算节省**: 约 40-60% 的 API 成本（取决于具体使用场景）

### 代码简化

- **减少参数**: 每个类的构造函数参数从 6-7 个减少到 1-2 个
- **更易维护**: 统一的模型配置更容易管理和调试
- **更少错误**: 减少配置错误的可能性

### 性能改进

- **更快执行**: 减少模型切换和初始化开销
- **更简单的错误处理**: 单一模型的错误处理更直接

---

## ⚠️ 潜在风险

### 功能降级风险

- **质量影响**: 单一模型可能不如专门优化的多模型组合
- **缓解措施**:
  - 进行充分的 A/B 测试
  - 保留向后兼容选项
  - 在关键路径上使用更强大的模型（如 gpt-4o）

### 技术债务

- **向后兼容**: 如果保留旧代码会增加维护负担
- **缓解措施**:
  - 计划在 6 个月后完全移除旧代码
  - 明确标记弃用的参数和方法

### 依赖风险

- **cmbagent 更新**: 依赖外部模块的新功能
- **缓解措施**:
  - 锁定 cmbagent 版本
  - 与 cmbagent 团队保持沟通
  - 为关键功能准备备用方案

---

## 📞 支持和反馈

如果在迁移过程中遇到问题：

1. 检查 cmbagent 的文档和更新日志
2. 参考本清单中的示例代码
3. 与团队讨论特定的技术细节
4. 记录遇到的问题和解决方案，更新本文档

---

**最后更新**: 2026-01-14
**文档版本**: 1.0.0
**作者**: AI Assistant
