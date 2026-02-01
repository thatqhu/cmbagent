# filename: agents/receiver.py
"""
Receiver Agent - 接收并记录任务

这个 Agent 演示了如何使用 ReplyResult 进行 Agent 转移。
"""

import os
from cmbagent.base_agent import BaseAgent


class Receiver(BaseAgent):
    """
    Receiver Agent 负责接收用户任务，并将其转发给 Processor。

    工作流程:
    1. 接收用户输入的任务
    2. 调用 record_task 函数记录任务到 context_variables
    3. 转移到 Processor Agent
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 读取 YAML 配置
        config_path = os.path.join(os.path.dirname(__file__), "receiver.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "Receives and logs tasks")

        # 使用标准对话 Agent
        self.set_assistant_agent()
