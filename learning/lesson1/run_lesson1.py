import os
import sys
from autogen import UserProxyAgent
from dotenv import load_dotenv

# Add the project root to sys.path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from learning.lesson1.my_first_agent import MyFirstAgent
from cmbagent.global_config import config_context

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

def main():
  with config_context(model="gpt-4o-mini",
                        api_key="cgpt_Iqv93Be8YiBnAGwrNCoSly3HfYa8EPsf",
                        base_url="https://test.comparegpt.io/api",
                        api_type="openai" ):
    print("Initializing MyFirstAgent...")
    my_agent = MyFirstAgent(
        work_dir="learning/lesson1/work_dir"
    )

    # Configure the internal autogen agent
    print("Setting up agent...")
    my_agent.set_agent()

    # Create a UserProxyAgent to drive the conversation
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="ALWAYS", # Allow user to type in the terminal
        code_execution_config=False, # We don't need code execution for this simple demo
    )

    # Start the conversation
    print("\nStarting conversation. Type your message below (type 'exit' to quit).")
    user_proxy.initiate_chat(
        my_agent.agent,
        message="Hello! Who are you and what can you do?"
    )

if __name__ == "__main__":
    main()
