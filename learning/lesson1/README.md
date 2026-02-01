# Lesson 1: Creating Your First Agent

In this lesson, we will create a simple agent using the `cmbagent` framework.

## Goals
1. Understand the folder structure for an agent.
2. Create an agent class inheriting from `BaseAgent`.
3. Create a YAML configuration file for the agent.
4. Run the agent to see it in action.

## Steps

1. **Define the Agent Class**:
   We will create a file `my_first_agent.py`. This class will inherit from `cmbagent.base_agent.BaseAgent`.
   It needs to implement `__init__` to call the super constructor with `agent_id` (which links to the YAML file).
   It also needs a `set_agent` method which typically calls `super().set_assistant_agent(**kwargs)`.

2. **Define the Agent Configuration**:
   We will create `my_first_agent.yaml`. This file contains the `name`, `description`, and `instructions` (system prompt) for the agent.

3. **Run the Agent**:
   We will create `run_lesson1.py` to instantiate `my_first_agent` and interaction with it.
   Since `cmbagent` relies on `autogen`, we will use `UserProxyAgent` to initiate a chat with our new agent.

## Prerequisites
- Make sure you have the `cmbagent` package installed (or are running from the source root).
- You need an `OPENAI_API_KEY` set in your environment variables.

## Files
- `my_first_agent.py`: The agent logic.
- `my_first_agent.yaml`: The agent configuration.
- `run_lesson1.py`: The script to run the lesson.
