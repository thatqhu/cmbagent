# filename: hand_offs.py
"""
Lesson 6: Hand-offs Configuration

这个模块演示三种 Hand-off 方式:
1. set_after_work() - 固定转移
2. OnCondition + StringLLMCondition - 条件转移
3. TerminateTarget - 终止工作流

对比 cmbagent/hand_offs.py:
- 原版 register_all_hand_offs() 约 350 行
- 这里我们用更清晰的结构演示核心概念
"""

from autogen.agentchat.group import (
    AgentTarget,
    TerminateTarget,
    OnCondition,
    StringLLMCondition,
)


def register_hand_offs(agents: dict):
    """
    配置所有 Agent 的 Hand-offs。

    工作流:
    ```
    Greeter → Processor ──→ Finisher → 终止
                   │
                   ├──→ Helper (如果需要帮助)
                   │        │
                   ←────────┘ (帮助后返回)
    ```

    Args:
        agents: {"greeter": agent, "processor": agent, ...}
    """
    greeter = agents["greeter"]
    processor = agents["processor"]
    helper = agents["helper"]
    finisher = agents["finisher"]

    print("📋 Registering hand-offs...")

    # =========================================================================
    # 1. 固定转移: set_after_work()
    # =========================================================================

    # Greeter → Processor (总是)
    greeter.handoffs.set_after_work(AgentTarget(processor))
    print("  ✅ Greeter → Processor (fixed)")

    # Helper → Processor (帮助完成后返回)
    helper.handoffs.set_after_work(AgentTarget(processor))
    print("  ✅ Helper → Processor (fixed)")

    # Finisher → Terminate (结束工作流)
    finisher.handoffs.set_after_work(TerminateTarget())
    print("  ✅ Finisher → Terminate (fixed)")

    # =========================================================================
    # 2. 条件转移: OnCondition + StringLLMCondition
    # =========================================================================

    # Processor 默认转到 Finisher
    processor.handoffs.set_after_work(AgentTarget(finisher))
    print("  ✅ Processor → Finisher (default)")

    # Processor 根据条件可能转到 Helper
    processor.handoffs.add_llm_conditions([
        OnCondition(
            target=AgentTarget(helper),
            condition=StringLLMCondition(
                prompt="The processor needs help or assistance with the task."
            ),
        ),
        OnCondition(
            target=AgentTarget(finisher),
            condition=StringLLMCondition(
                prompt="The task is completed or the processor is done."
            ),
        ),
    ])
    print("  ✅ Processor → Helper (conditional: needs help)")
    print("  ✅ Processor → Finisher (conditional: task done)")

    print("📋 All hand-offs registered!\n")


def print_workflow_diagram():
    """打印工作流图"""
    diagram = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                     Lesson 6: Workflow Diagram                    ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                   ║
    ║   ┌──────────┐                                                    ║
    ║   │  Greeter │                                                    ║
    ║   └────┬─────┘                                                    ║
    ║        │ (fixed: set_after_work)                                  ║
    ║        ▼                                                          ║
    ║   ┌───────────┐                                                   ║
    ║   │ Processor │◀────────────────────┐                             ║
    ║   └─────┬─────┘                      │                            ║
    ║         │                            │                            ║
    ║         ├── (condition: needs help) ─┼─▶ ┌────────┐               ║
    ║         │                            │   │ Helper │               ║
    ║         │                            └───┴────────┘               ║
    ║         │                           (fixed: after help)           ║
    ║         │                                                         ║
    ║         └── (condition: task done) ──▶ ┌──────────┐               ║
    ║                                        │ Finisher │               ║
    ║                                        └────┬─────┘               ║
    ║                                             │                     ║
    ║                                             ▼                     ║
    ║                                      TerminateTarget()            ║
    ║                                                                   ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(diagram)
