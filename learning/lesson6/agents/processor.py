# filename: agents/processor.py
"""
Processor Agent - 核心处理

演示: OnCondition 条件转移
"""

import os
from cmbagent.base_agent import BaseAgent


class Processor(BaseAgent):
    """
    Processor Agent - 处理任务，可能需要帮助。

    Hand-off:
    - 如果需要帮助 → Helper (条件)
    - 如果完成 → Finisher (条件)
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config_path = os.path.join(os.path.dirname(__file__), "processor.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "")

        self.set_assistant_agent()
