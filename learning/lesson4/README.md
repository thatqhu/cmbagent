# Lesson 4: Orchestrating a Swarm

In this lesson, we will use the `CMBAgent` class to orchestrate a swarm of agents (Planner, Engineer, Executor).

## Goals
1. Understand the `CMBAgent` orchestrator class.
2. Configure a swarm with `agent_list`.
3. Solve a multi-step task: "Create a plot of y=x^2".

## Prerequisites
- **Agents**: We will reuse standard agents provided by `cmbagent` library (`planner`, `engineer`, `executor`, etc.) or use the ones we customized if needed. For simplicity, we'll use the builtin ones.

## Steps

1. **Create Run Script**:
   Create `run_lesson4.py`.

   It will:
   - Import `CMBAgent`.
   - Initialize `CMBAgent` with `agent_list=['planner', 'engineer', 'executor']`.
   - Call `cmbagent.solve(task="Plot y=x^2 and save it as plot.png.")`.

2. **Understand the Flow**:
   - `task_improver` (default initial agent) refines the task.
   - `planner` creates a plan.
   - `plan_reviewer` reviews it (optional, depends on config).
   - `control` (the orchestrator loop) assigns tasks to `engineer` and `executor`.
   - `engineer` writes code.
   - `executor` runs code.

## Files
- `run_lesson4.py`
