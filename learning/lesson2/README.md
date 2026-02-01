# Lesson 2: Adding Function Tools

In this lesson, we will give our agent the ability to use tools (Python functions).

## Goals
1. Define a Python function (e.g., a calculator).
2. Register this function with the agent and the user proxy.
3. Observe the agent calling the function to solve a problem.

## Steps

1. **Create the Tool Agent**:
   Create `my_tool_agent.py` and `my_tool_agent.yaml`. This is similar to Lesson 1, but we'll change the description and instructions.

2. **Define the Tool**:
   In `run_lesson2.py`, we will define a simple function `multiply(a: int, b: int) -> int`.

3. **Register the Tool**:
   We will use `autogen.register_function` to register `multiply` with:
   - `caller`: The assistant agent (who decides to call the tool).
   - `executor`: The user proxy agent (who executes the code).

4. **Run**:
   Ask the agent "What is 123 * 456?". It should use the tool.

## Key Concepts: Caller vs Executor

You might wonder: **"Is the tool an agent?"**
The answer is **No**, the tool (`multiply`) is just a standard Python function.

However, in the `cmbagent` (and AutoGen) framework, a tool cannot run by itself. It needs **Two Agents** to work:
1. **The Caller**: The AI (LLM) that decides *when* to call the function and *what arguments* to pass. (Here: `MyToolAgent`)
2. **The Executor**: The entity that actually runs the Python code. (Here: `UserProxyAgent`)

### Why this distinction?
Reviewing `run_lesson2.py`, you will see:
```python
register_function(
    multiply,
    caller=my_agent.agent,  # "I want to calculate this..."
    executor=user_proxy,    # "Okay, I will run the code for you."
    ...
)
```
This separation is powerful because it allows the AI to "think" (Caller) without needing to have a Python environment inside its own brain. It delegates the "action" to the Executor.

> **Advanced Note**: In complex Swarms (Lesson 4), we sometimes use tools to **switch** between agents (e.g., a function `transfer_to_planner()`). In that specific case, the tool acts as a bridge *to* an agent. But in this lesson, `multiply` is just a calculation function.

## Files
- `my_tool_agent.py`
- `my_tool_agent.yaml`
- `run_lesson2.py`
