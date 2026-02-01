import os
import sys
from autogen import UserProxyAgent, register_function
from dotenv import load_dotenv
from typing import Annotated
from cmbagent.global_config import config_context

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from learning.lesson2.my_tool_agent import MyToolAgent

load_dotenv()

def main():
    with config_context(model="gpt-4o-mini",
                        api_key="cgpt_Iqv93Be8YiBnAGwrNCoSly3HfYa8EPsf",
                        base_url="https://test.comparegpt.io/api",
                        api_type="openai" ):

        # 1. Initialize the agent
        print("Initializing MyToolAgent...")
        my_agent = MyToolAgent(work_dir="learning/lesson2/work_dir")
        my_agent.set_agent()

        # 2. Create User Proxy (Executor)
        user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="ALWAYS",
            code_execution_config=False, # We use function calling mechanism, not code execution for this demo
        )

        # 3. Define the tool
        def multiply(
            a: Annotated[int, "The first integer"],
            b: Annotated[int, "The second integer"]
        ) -> int:
            print(f"Executing multiply({a}, {b})")
            return a * b

        # 4. Register the tool
        print("Registering tool 'multiply'...")
        register_function(
            multiply,
            caller=my_agent.agent,  # The assistant suggests the call
            executor=user_proxy,    # The user proxy executes the call
            name="multiply",
            description="Multiplies two integers."
        )

        # 5. Start Chat
        print("\nStarting conversation...")
        chat_result = user_proxy.initiate_chat(
            my_agent.agent,
            message="What is 1234 * 5678?"
        )

        print("\n[Debug] Conversation Result:")
        print(f"Summary: {chat_result.summary}")
        print(f"Chat History: {chat_result.chat_history}")

if __name__ == "__main__":
    main()
