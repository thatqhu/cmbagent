# filename: agents/processor.py
"""
Processor Agent - 处理任务

这个 Agent 演示了如何使用 ContextVariables 跟踪状态和重试逻辑。
"""

import os
from cmbagent.base_agent import BaseAgent


class Processor(BaseAgent):
    """
    Processor Agent 负责处理任务。

    工作流程:
    1. 从 context_variables 读取任务信息
    2. 模拟处理任务 (可能成功或失败)
    3. 如果失败且未超过最大重试次数，则重试
    4. 如果成功，转移到 Reporter
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config_path = os.path.join(os.path.dirname(__file__), "processor.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "Processes tasks")

        self.set_assistant_agent()
