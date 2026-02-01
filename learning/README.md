# CMBAgent Learning Roadmap

This project is a step-by-step guide to learning **cmbagent**, an agentic framework for scientific discovery.

## Curriculum

### 1. [Lesson 1: Creating Your First Agent](./lesson1/)
Learn the fundamental structure of a `cmbagent` agent.
- Inheritance from `BaseAgent`.
- Configuration via YAML (`instructions`, `description`).
- Running a simple conversation.

### 2. [Lesson 2: Adding Function Tools](./lesson2/)
Enhance your agent with capabilities.
- Defining Python functions.
- Registering tools with the agent.
- Function execution flow.

### 3. [Lesson 3: RAG (Retrieval-Augmented Generation)](./lesson3/)
Give your agent access to external knowledge.
- Configuring vector stores in YAML.
- Using `file_search` tool.

### 4. [Lesson 4: Swarm Orchestration](./lesson4/)
Orchestrate multiple agents to solve complex tasks.
- Understanding `CMBAgent` class.
- Configuring a swarm of agents (Planner, Engineer, Executor).
- Running the `solve` loop.

---

## Advanced: Refactoring Guide

The following lessons are designed to help you understand and refactor `cmbagent/functions.py` and `cmbagent/hand_offs.py`.

### 5. [Lesson 5: Understanding Agent Functions](./lesson5/)
Deep dive into `functions.py` patterns.
- `ReplyResult` and `AgentTarget` for agent transitions.
- `ContextVariables` for shared state.
- Creating custom routing functions.
- Identifying refactoring opportunities.

### 6. [Lesson 6: Hand-offs and Agent Transitions](./lesson6/)
Understand workflow connections in `hand_offs.py`.
- `set_after_work()` - fixed transitions.
- `OnCondition` + `StringLLMCondition` - conditional transitions.
- `TerminateTarget` - workflow termination.

### 7. [Lesson 7: Refactoring Functions - Strategy Pattern](./lesson7/) *(Coming Soon)*
Learn to refactor large functions.
- Extract Agent Router abstractions.
- Use Registry pattern.
- Eliminate if-elif chains.

### 8. [Lesson 8: Refactoring Hand-offs - Builder Pattern](./lesson8/) *(Coming Soon)*
Refactor hand-offs with Builder pattern.
- Declarative workflow configuration.
- Separation of rules and implementation.
