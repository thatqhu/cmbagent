# filename: agents/reporter.py
"""
Reporter Agent - 报告结果

这个 Agent 演示了如何使用 TerminateTarget 结束 Swarm。
"""

import os
from cmbagent.base_agent import BaseAgent


class Reporter(BaseAgent):
    """
    Reporter Agent 负责报告最终结果。

    工作流程:
    1. 从 context_variables 读取处理结果
    2. 生成报告
    3. 调用 finalize_report 函数结束 Swarm
    """

    agent_type = "assistant"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config_path = os.path.join(os.path.dirname(__file__), "reporter.yaml")
        config = self.load_config(config_path)

        self.config = config
        self.instructions = config.get("instructions", "")
        self.description = config.get("description", "Reports final results")

        self.set_assistant_agent()
