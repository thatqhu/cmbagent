import os
import sys
from autogen import UserProxyAgent
from openai import OpenAI
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from learning.lesson3.my_rag_agent import MyRagAgent
from cmbagent.utils import update_yaml_preserving_format

load_dotenv()

def main():
    with config_context(model="gpt-4o-mini",
                    api_key="cgpt_Iqv93Be8YiBnAGwrNCoSly3HfYa8EPsf",
                    base_url="https://test.comparegpt.io/api",
                    api_type="openai" ):

        client = OpenAI(api_key=api_key)

        # 1. Prepare Vector Store
        vector_store_name = "lesson3_store"
        knowledge_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")

        # Check if files exist
        file_paths = []
        for root, dirs, files in os.walk(knowledge_dir):
            for file in files:
                if file.endswith(".txt"):
                    file_paths.append(os.path.join(root, file))

        if not file_paths:
            print("No knowledge files found!")
            return

        print(f"Creating/Updating vector store '{vector_store_name}' with {len(file_paths)} files...")

        # Create vector store
        vector_store = client.beta.vector_stores.create(name=vector_store_name)

        # Upload files
        file_streams = [open(path, "rb") for path in file_paths]
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_streams
        )

        print(f"Vector Store ID: {vector_store.id}")
        print(f"File batch status: {file_batch.status}")

        # 2. Update Agent Config
        # We manually pass the vector store ID to the agent initialization for this lesson
        # instead of rewriting the YAML permanently, although updating YAML is also good practice.

        print("Initializing MyRagAgent...")
        my_agent = MyRagAgent(work_dir="learning/lesson3/work_dir")

        # Set the agent with the specific vector store ID
        my_agent.set_agent(vector_store_ids=vector_store.id)

        # 3. Start Chat
        user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="ALWAYS",
            code_execution_config=False,
        )

        print("\nStarting conversation...")
        print("Try asking: 'What roles are in the CMBAgent swarm?'")

        user_proxy.initiate_chat(
            my_agent.agent,
            message="What roles are in the CMBAgent swarm according to your knowledge base?"
        )

        # Cleanup (Optional)
        # client.beta.vector_stores.delete(vector_store.id)

if __name__ == "__main__":
    main()
