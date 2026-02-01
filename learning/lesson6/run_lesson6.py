# filename: run_lesson6.py
"""
Lesson 6: Running the Hand-offs Demo

这个脚本演示了如何:
1. 创建多个 Agent
2. 配置 Hand-offs (固定转移 + 条件转移)
3. 运行 Swarm 工作流

运行方式:
    python run_lesson6.py
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from autogen.agentchat.group import Swarm, ContextVariables

from cmbagent.global_config import config_context

# 导入自定义 Agent 和 Hand-offs
from agents import Greeter, Processor, Helper, Finisher
from hand_offs import register_hand_offs, print_workflow_diagram

load_dotenv()


def main():
    """
    主函数: 初始化 Agent，配置 Hand-offs，运行 Swarm。
    """

    # 使用 config_context 设置 LLM 配置
    with config_context(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_type="openai"
    ):
        print("=" * 70)
        print("Lesson 6: Hand-offs and Agent Transitions")
        print("=" * 70)

        # 打印工作流图
        print_workflow_diagram()

        # Step 1: 创建 Agent 实例
        print("\n[Step 1] Creating agents...")

        greeter = Greeter(name="greeter")
        processor = Processor(name="processor")
        helper = Helper(name="helper")
        finisher = Finisher(name="finisher")

        agents_dict = {
            "greeter": greeter.agent,
            "processor": processor.agent,
            "helper": helper.agent,
            "finisher": finisher.agent,
        }

        print(f"  Created: {list(agents_dict.keys())}")

        # Step 2: 配置 Hand-offs
        print("\n[Step 2] Configuring hand-offs...")
        register_hand_offs(agents_dict)

        # Step 3: 创建 Swarm
        print("[Step 3] Creating Swarm...")

        context_variables = ContextVariables()
        context_variables["workflow_name"] = "Lesson6 Demo"

        swarm = Swarm(
            agents=[greeter.agent, processor.agent, helper.agent, finisher.agent],
            context_variables=context_variables,
        )

        # Step 4: 运行简单任务 (不需要帮助)
        print("\n" + "=" * 70)
        print("Test 1: Simple Task (no help needed)")
        print("=" * 70)

        task1 = "Calculate 2 + 2"
        print(f"\n📋 Task: {task1}\n")

        result1 = swarm.run(
            agent=greeter.agent,
            messages=[{"role": "user", "content": task1}],
            max_rounds=10,
        )

        # Step 5: 重置并运行需要帮助的任务
        print("\n" + "=" * 70)
        print("Test 2: Complex Task (help needed)")
        print("=" * 70)

        # 重新创建 Swarm (重置状态)
        context_variables = ContextVariables()
        context_variables["workflow_name"] = "Lesson6 Demo"

        swarm = Swarm(
            agents=[greeter.agent, processor.agent, helper.agent, finisher.agent],
            context_variables=context_variables,
        )

        task2 = "I need help understanding quantum computing basics"
        print(f"\n📋 Task: {task2}\n")

        result2 = swarm.run(
            agent=greeter.agent,
            messages=[{"role": "user", "content": task2}],
            max_rounds=15,
        )

        print("\n" + "=" * 70)
        print("Lesson 6 completed!")
        print("=" * 70)


if __name__ == "__main__":
    main()
