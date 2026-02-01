# filename: agents/greeter.py
"""
Greeter Agent - 工作流入口

演示: set_after_work() 固定转移
"""

import os
from cmbagent.base_agent import BaseAgent


class Greeter(BaseAgent):
    """
    Greeter Agent - 迎接用户并转发任务。

    Hand-off: Greeter → Processor (固定)
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config_path = os.path.join(os.path.dirname(__file__), "greeter.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "")

        self.set_assistant_agent()
