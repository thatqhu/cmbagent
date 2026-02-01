# filename: functions.py
"""
Lesson 5: Agent Functions - 优雅的 @dataclass + 自包含元数据模式

这个模块演示最佳实践:
1. @dataclass 自动生成 __init__
2. ClassVar 存储注册元数据 (caller_name, executor_name)
3. __doc__ 自动作为 description
4. 一行注册多个函数

对比 cmbagent/functions.py:
- 原版: 1300+ 行, 大量重复的 register_function 调用
- 本版: 每个函数类自包含所有信息, 注册只需一行
"""

from dataclasses import dataclass
from typing import Literal, Any, ClassVar, Type
from autogen import register_function
from autogen.agentchat.group import (
    ContextVariables,
    ReplyResult,
    AgentTarget,
    TerminateTarget,
)


# ============================================================================
# 函数类定义 - 每个类自包含注册所需的所有信息
# ============================================================================

@dataclass
class RecordTask:
    """
    记录任务并转移到 Processor。

    演示: 最简单的 Agent 转移模式。
    """
    processor_agent: Any

    # 注册元数据 - ClassVar 不会成为 __init__ 参数
    caller_name: ClassVar[str] = "receiver"
    executor_name: ClassVar[str] = "receiver"

    def __call__(
        self,
        task_description: str,
        context_variables: ContextVariables
    ) -> ReplyResult:
        """
        Record the task and transfer to Processor.

        Args:
            task_description: The task to be processed
        """
        context_variables["task"] = task_description
        context_variables["attempts"] = 0
        context_variables["max_attempts"] = 3
        context_variables["status"] = "received"

        print(f"\n📥 [RecordTask] Task received: {task_description}")

        return ReplyResult(
            target=AgentTarget(self.processor_agent),
            message=f"Task to process: {task_description}",
            context_variables=context_variables,
        )


@dataclass
class ProcessTask:
    """
    处理任务结果，决定成功/失败/重试。

    演示: 条件路由 - 根据状态转移到不同 Agent。
    """
    processor_agent: Any  # 重试时转回
    reporter_agent: Any   # 成功/最终失败时转到

    caller_name: ClassVar[str] = "processor"
    executor_name: ClassVar[str] = "processor"

    def __call__(
        self,
        status: Literal["success", "failure"],
        result_message: str,
        context_variables: ContextVariables
    ) -> ReplyResult:
        """
        Process task result and decide next step.

        Args:
            status: "success" or "failure"
            result_message: Description of the result or error
        """
        attempts = context_variables.get("attempts", 0)
        max_attempts = context_variables.get("max_attempts", 3)
        task = context_variables.get("task", "Unknown")

        if status == "success":
            context_variables["status"] = "completed"
            context_variables["result"] = result_message
            print(f"\n✅ [ProcessTask] Success! {result_message}")

            return ReplyResult(
                target=AgentTarget(self.reporter_agent),
                message=f"Task completed: {result_message}",
                context_variables=context_variables,
            )

        # 失败处理
        attempts += 1
        context_variables["attempts"] = attempts

        if attempts >= max_attempts:
            context_variables["status"] = "failed"
            context_variables["result"] = f"Failed after {attempts} attempts"
            print(f"\n❌ [ProcessTask] Max attempts reached.")

            return ReplyResult(
                target=AgentTarget(self.reporter_agent),
                message=f"Task failed after {attempts} attempts: {result_message}",
                context_variables=context_variables,
            )

        # 重试
        context_variables["status"] = "retrying"
        print(f"\n🔄 [ProcessTask] Retry {attempts}/{max_attempts}")

        return ReplyResult(
            target=AgentTarget(self.processor_agent),
            message=f"Retry {attempts + 1}/{max_attempts}. Error: {result_message}. Task: {task}",
            context_variables=context_variables,
        )


@dataclass
class FinalizeReport:
    """
    生成最终报告并终止工作流。

    演示: 使用 TerminateTarget() 结束 Swarm。
    """
    # 无需注入依赖 - 总是终止

    caller_name: ClassVar[str] = "reporter"
    executor_name: ClassVar[str] = "reporter"

    def __call__(
        self,
        summary: str,
        context_variables: ContextVariables
    ) -> ReplyResult:
        """
        Generate final report and terminate workflow.

        Args:
            summary: Brief summary of the task outcome
        """
        task = context_variables.get("task", "Unknown")
        status = context_variables.get("status", "unknown")
        attempts = context_variables.get("attempts", 0)

        print(f"""
╔══════════════════════════════════════════════════════════╗
║                    FINAL REPORT                          ║
╠══════════════════════════════════════════════════════════╣
║ Task: {task[:50]:<50} ║
║ Status: {status:<48} ║
║ Attempts: {attempts:<46} ║
║ Summary: {summary[:47]:<47} ║
╚══════════════════════════════════════════════════════════╝
""")

        return ReplyResult(
            target=TerminateTarget(),
            message=f"Workflow completed. Status: {status}",
            context_variables=context_variables,
        )


# ============================================================================
# 优雅的注册系统
# ============================================================================

def register_all(agents: dict, *function_classes: Type):
    """
    一行注册多个函数类！

    工作原理:
    1. 遍历每个函数类
    2. 自动解析 *_agent 字段作为依赖
    3. 从 ClassVar 获取 caller/executor
    4. 从 __call__.__doc__ 获取 description

    Args:
        agents: {"receiver": agent1, "processor": agent2, ...}
        *function_classes: RecordTask, ProcessTask, FinalizeReport, ...

    用法:
        register_all(agents, RecordTask, ProcessTask, FinalizeReport)
    """
    print("📝 Registering functions...")

    for cls in function_classes:
        # 自动解析依赖: processor_agent -> agents["processor"]
        deps = {}
        for field_name in getattr(cls, '__dataclass_fields__', {}):
            if field_name.endswith("_agent"):
                agent_key = field_name.replace("_agent", "")
                if agent_key in agents:
                    deps[field_name] = agents[agent_key]

        # 创建实例
        instance = cls(**deps)

        # 获取注册元数据
        caller_name = getattr(cls, 'caller_name', None)
        executor_name = getattr(cls, 'executor_name', None)

        if not caller_name or not executor_name:
            raise ValueError(f"{cls.__name__} missing caller_name or executor_name")

        caller = agents.get(caller_name)
        executor = agents.get(executor_name)

        if not caller or not executor:
            raise ValueError(f"Agent '{caller_name}' or '{executor_name}' not found")

        # 从 __call__ 的 docstring 获取 description
        description = instance.__call__.__doc__ or cls.__doc__ or f"{cls.__name__} function"

        # 注册！
        register_function(
            instance,
            caller=caller,
            executor=executor,
            description=description,
        )

        print(f"  ✅ {cls.__name__} -> {caller_name}")

    print(f"📝 Registered {len(function_classes)} functions!\n")


# ============================================================================
# 向后兼容的入口函数
# ============================================================================

def register_all_functions(agents: dict):
    """
    注册所有函数 - 向后兼容的入口。

    Args:
        agents: {"receiver": agent, "processor": agent, "reporter": agent}
    """
    register_all(agents, RecordTask, ProcessTask, FinalizeReport)
