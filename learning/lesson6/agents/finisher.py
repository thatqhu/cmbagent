# filename: agents/finisher.py
"""
Finisher Agent - 工作流结束

演示: TerminateTarget() 终止工作流
"""

import os
from cmbagent.base_agent import BaseAgent


class Finisher(BaseAgent):
    """
    Finisher Agent - 总结任务并终止工作流。

    Hand-off: Finisher → TerminateTarget() (终止)
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config_path = os.path.join(os.path.dirname(__file__), "finisher.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "")

        self.set_assistant_agent()
