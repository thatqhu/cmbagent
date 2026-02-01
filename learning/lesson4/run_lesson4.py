import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from cmbagent.cmbagent import CMBAgent
from cmbagent.global_config import config_context

load_dotenv()

def main():
    with config_context(model="gpt-4o-mini",
                api_key="cgpt_Iqv93Be8YiBnAGwrNCoSly3HfYa8EPsf",
                base_url="https://test.comparegpt.io/api",
                api_type="openai" ):

        print("Initializing CMBAgent Swarm...")

        # We will use a standard set of agents for a coding task.
        # Note: 'task_improver' is usually the entry point.
        # 'planner', 'engineer', 'executor', 'control', 'terminator', 'task_recorder' are essential.
        agent_list = [
            'task_improver',
            'task_recorder',
            'planner',
            'plan_recorder',
            'plan_reviewer',
            'plan_setter', # needed for recording constraints
            'engineer',
            'executor',
            'executor_response_formatter',
            'control',
            'terminator',
            'admin'
        ]

        # Initialize the swarm
        swarm = CMBAgent(
            agent_list=agent_list,
            verbose=True,
            clear_work_dir=True,
            # We can specify the model if needed, defaults to config
            # model="gpt-4o"
        )

        task = "Write a Python script that calculates the first 10 Fibonacci numbers and saves them to a file 'fib.txt'."

        print(f"\n Solving Task: {task}\n")

        # Run the swarm
        swarm.solve(
            task=task,
            initial_agent='task_improver', # The first agent to see the task
            max_rounds=20
        )

        print("\nSwarm execution finished. Check 'learning/lesson4/work_dir' for results.")

if __name__ == "__main__":
    main()
