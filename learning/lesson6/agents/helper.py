# filename: agents/helper.py
"""
Helper Agent - 辅助处理

演示: 条件转移的目标 Agent
"""

import os
from cmbagent.base_agent import BaseAgent


class Helper(BaseAgent):
    """
    Helper Agent - 提供帮助后返回 Processor。

    Hand-off: Helper → Processor (固定，帮助完成后返回)
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config_path = os.path.join(os.path.dirname(__file__), "helper.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "")

        self.set_assistant_agent()
