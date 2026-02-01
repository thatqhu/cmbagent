# filename: run_lesson5.py
"""
Lesson 5: Running the Custom Agent Functions Demo

这个脚本演示了如何:
1. 创建自定义 Agent
2. 注册自定义函数实现工作流控制
3. 运行一个简单的 Swarm

运行方式:
    python run_lesson5.py
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from autogen.agentchat.group import Swarm, ContextVariables

from cmbagent.global_config import config_context

# 导入自定义 Agent 和函数
from agents import Receiver, Processor, Reporter
from functions import register_all_functions

load_dotenv()


def main():
    """
    主函数: 初始化 Agent 并运行 Swarm。
    """

    # 使用 config_context 设置 LLM 配置
    # 你需要替换为你自己的 API 配置
    with config_context(
        model="gpt-4o-mini",
        api_key="cgpt_Iqv93Be8YiBnAGwrNCoSly3HfYa8EPsf",
        base_url="https://test.comparegpt.io/api",
        api_type="openai"
    ):
        print("=" * 60)
        print("Lesson 5: Understanding Agent Functions")
        print("=" * 60)

        # Step 1: 创建 Agent 实例
        print("\n[Step 1] Creating agents...")

        receiver = Receiver(name="receiver")
        processor = Processor(name="processor")
        reporter = Reporter(name="reporter")

        # 获取底层的 autogen agent 对象
        agents_dict = {
            "receiver": receiver.agent,
            "processor": processor.agent,
            "reporter": reporter.agent,
        }

        print(f"  - Created: {list(agents_dict.keys())}")

        # Step 2: 注册函数
        print("\n[Step 2] Registering functions...")
        register_all_functions(agents_dict)

        # Step 3: 设置 Hand-offs (这里我们简化处理)
        # 在完整的 cmbagent 中，这是由 hand_offs.py 处理的
        # 这里我们依赖函数的 ReplyResult 来控制流程

        # Step 4: 创建 Swarm
        print("\n[Step 3] Creating Swarm...")

        # 初始化共享状态
        context_variables = ContextVariables()
        context_variables["workflow_name"] = "Lesson5 Demo"

        swarm = Swarm(
            agents=[receiver.agent, processor.agent, reporter.agent],
            context_variables=context_variables,
        )

        # Step 5: 运行任务
        print("\n[Step 4] Running the workflow...")
        print("-" * 60)

        # 测试用例 1: 简单任务 (应该成功)
        task1 = "Calculate 2 + 2"
        print(f"\n📋 Task 1: {task1}")

        result1 = swarm.run(
            agent=receiver.agent,
            messages=[{"role": "user", "content": task1}],
            max_rounds=10,
        )

        print("\n" + "=" * 60)

        # 重置状态用于下一个任务
        context_variables = ContextVariables()
        context_variables["workflow_name"] = "Lesson5 Demo"

        swarm = Swarm(
            agents=[receiver.agent, processor.agent, reporter.agent],
            context_variables=context_variables,
        )

        # 测试用例 2: 困难任务 (应该触发重试)
        task2 = "This is a hard task that might fail"
        print(f"\n📋 Task 2: {task2}")

        result2 = swarm.run(
            agent=receiver.agent,
            messages=[{"role": "user", "content": task2}],
            max_rounds=15,
        )

        print("\n" + "=" * 60)
        print("Lesson 5 completed!")
        print("=" * 60)

        # 打印最终状态
        print("\n📊 Final Context Variables:")
        for key, value in context_variables.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
