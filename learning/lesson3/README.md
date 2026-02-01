# Lesson 3: Retrieval Augmented Generation (RAG)

In this lesson, we will create a RAG agent that can answer questions based on a specific document.

## Goals
1. Create a `MyRagAgent` that uses OpenAI's Assistant API with `file_search`.
2. Prepare a knowledge base (text file).
3. Create a script to upload the file to OpenAI, create a vector store, and update the agent's configuration.
4. Chat with the agent to verify it uses the knowledge.

## Prerequisites
- **OpenAI API Key**: Required for vector store creation and Assistant API.

## Steps

1. **Create MyRagAgent**:
   Create `my_rag_agent.py`. It inherits from `BaseAgent`.
   Unlike standard agents, RAG agents in `cmbagent` typically use `set_gpt_assistant_agent`.

2. **Create YAML Configuration**:
   Create `my_rag_agent.yaml`. It must include `assistant_config` with `tools: [{"type": "file_search"}]`.

3. **Prepare Data**:
   We created a folder `data/my_rag_agent/` and will put a `knowledge.txt` file there.

4. **Run Script**:
   Create `run_lesson3.py`.
   This script will:
   - Identify the data files.
   - Upload them to OpenAI Vector Store (using a helper or standard OpenAI code).
   - Update the `MyRagAgent` to use this vector store.
   - Run the agent in a chat loop.

## Notes
- In a full `cmbagent` deployment, the `push_vector_stores` utility handles step 4 automatically. Here we will do it explicitly to understand the process.

## Files
- `my_rag_agent.py`
- `my_rag_agent.yaml`
- `data/my_rag_agent/knowledge.txt`
- `run_lesson3.py`
