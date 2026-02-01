import os
from cmbagent.base_agent import BaseAgent

class MyFirstAgent(BaseAgent):
    """
    A simple agent for Lesson 1.
    """
    def __init__(self, llm_config=None, **kwargs):
        # We determine the agent_id based on this file's location.
        # This assumes my_first_agent.yaml is in the same directory.
        agent_id = os.path.splitext(os.path.abspath(__file__))[0]

        # Initialize the base class
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        # This method is called to configure the internal autogen agent.
        # For a standard assistant (non-RAG), we use set_assistant_agent.
        super().set_assistant_agent(**kwargs)
