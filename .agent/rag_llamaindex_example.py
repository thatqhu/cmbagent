"""
LlamaIndex RAG Agent Implementation Example
这是一个使用 LlamaIndex 重构 RAG agent 的示例实现
"""

import os
import warnings
from typing import Optional, List, Dict, Any
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext,
)
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from cmbagent.base_agent import BaseAgent, CmbAgentSwarmAgent, cmbagent_debug


class LlamaIndexRAGMixin:
    """
    LlamaIndex RAG 功能的 Mixin 类
    可以被任何 BaseAgent 子类使用
    """

    def setup_llamaindex_rag(
        self,
        data_path: str,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4",
        embedding_model: str = "text-embedding-3-small",
        vector_store_type: str = "chroma",
        persist_dir: Optional[str] = None,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
    ):
        """
        使用 LlamaIndex 设置 RAG 系统

        Args:
            data_path: 文档数据的路径
            llm_provider: LLM 提供商 ("openai", "anthropic", "google")
            llm_model: 模型名称
            embedding_model: embedding 模型名称
            vector_store_type: 向量存储类型 ("chroma", "faiss", "memory")
            persist_dir: 向量存储持久化目录
            similarity_top_k: 检索的文档数量
            response_mode: 响应生成模式
            chunk_size: 文档分块大小
            chunk_overlap: 文档分块重叠
        """

        # 1. 配置 LLM
        if llm_provider == "openai":
            llm = OpenAI(
                model=llm_model,
                temperature=self.llm_config.get('temperature', 0.7)
            )
        elif llm_provider == "anthropic":
            llm = Anthropic(
                model=llm_model,
                temperature=self.llm_config.get('temperature', 0.7)
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # 2. 配置 Embeddings
        embed_model = OpenAIEmbedding(model=embedding_model)

        # 3. 设置全局配置
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

        # 4. 加载文档
        if cmbagent_debug:
            print(f"\n[RAG] Loading documents from: {data_path}")

        documents = SimpleDirectoryReader(
            data_path,
            exclude_hidden=True,
            recursive=False
        ).load_data()

        if cmbagent_debug:
            print(f"[RAG] Loaded {len(documents)} documents")

        # 5. 配置向量存储
        storage_context = None
        if vector_store_type == "chroma":
            persist_dir = persist_dir or f"./chroma_db/{self.name}"
            chroma_client = chromadb.PersistentClient(path=persist_dir)
            chroma_collection = chroma_client.get_or_create_collection(
                name=self.name.replace('_agent', '')
            )
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            if cmbagent_debug:
                print(f"[RAG] Using Chroma vector store at: {persist_dir}")

        elif vector_store_type == "memory":
            if cmbagent_debug:
                print("[RAG] Using in-memory vector store")
        # 可以添加更多向量存储类型 (FAISS, Qdrant等)

        # 6. 创建索引
        if storage_context:
            self.index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
            )
        else:
            self.index = VectorStoreIndex.from_documents(documents)

        # 7. 创建查询引擎
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=similarity_top_k,
            response_mode=response_mode,
        )

        if cmbagent_debug:
            print(f"[RAG] Query engine created with top_k={similarity_top_k}")

    def rag_query(self, query: str) -> str:
        """
        执行 RAG 查询

        Args:
            query: 查询字符串

        Returns:
            查询响应
        """
        if not hasattr(self, 'query_engine'):
            raise RuntimeError("RAG not initialized. Call setup_llamaindex_rag first.")

        if cmbagent_debug:
            print(f"\n[RAG Query] {query[:100]}...")

        response = self.query_engine.query(query)
        return str(response)


class ModernRAGAgent(BaseAgent, LlamaIndexRAGMixin):
    """
    使用 LlamaIndex 的现代 RAG Agent
    这是一个示例实现，展示如何使用新的 RAG 系统
    """

    def __init__(self, llm_config=None, **kwargs):
        super().__init__(llm_config=llm_config, **kwargs)
        self.index = None
        self.query_engine = None

    def set_rag_agent(
        self,
        instructions: Optional[str] = None,
        description: Optional[str] = None,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4",
        vector_store_type: str = "chroma",
        **kwargs
    ):
        """
        设置使用 LlamaIndex 的 RAG agent

        这个方法会：
        1. 初始化 LlamaIndex RAG 系统
        2. 创建一个 AG2 ConversableAgent
        3. 将 RAG 查询注册为一个 function tool
        """

        # 更新 instructions 和 description
        if instructions is not None:
            self.info["instructions"] = instructions
        if description is not None:
            self.info["description"] = description

        # 获取数据路径
        dir_path = os.getenv('CMBAGENT_DATA')
        data_path = os.path.join(dir_path, 'data', self.name.replace('_agent', ''))

        # 初始化 RAG 系统
        self.setup_llamaindex_rag(
            data_path=data_path,
            llm_provider=llm_provider,
            llm_model=llm_model,
            vector_store_type=vector_store_type,
            **kwargs
        )

        # 创建 RAG 搜索函数
        def file_search(query: str) -> str:
            """
            Search documentation using RAG (Retrieval-Augmented Generation).

            Args:
                query: The search query string

            Returns:
                Relevant documentation content
            """
            return self.rag_query(query)

        # 更新 instructions 以包含文件列表
        files = [f for f in os.listdir(data_path)
                if not (f.startswith('.') or f.endswith('.ipynb') or
                       f.endswith('.yaml') or f.endswith('.txt') or
                       os.path.isdir(os.path.join(data_path, f)))]

        self.info["instructions"] += f'\n\nYou have access to the following files: {files}.\n'
        self.info["instructions"] += '\nUse the file_search function to retrieve relevant information from these files.\n'

        # 创建 AG2 agent
        self.agent = CmbAgentSwarmAgent(
            name=self.name,
            update_agent_state_before_reply=[
                # UpdateSystemMessage 需要从 autogen.agentchat 导入
                # UpdateSystemMessage(self.info["instructions"]),
            ],
            system_message=self.info["instructions"],
            description=self.info["description"],
            llm_config=self.llm_config,
            functions=[file_search],
            cmbagent_debug=cmbagent_debug,
        )

        if cmbagent_debug:
            print(f"[RAG Agent] {self.name} initialized with LlamaIndex")


# 示例：更新现有的 CAMB agent
class CambAgentV2(ModernRAGAgent):
    """
    使用新 RAG 系统的 CAMB agent
    """

    def __init__(self, llm_config=None, **kwargs):
        agent_id = os.path.join(
            os.path.dirname(__file__),
            'agents/rag_agents/camb'
        )
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        # 默认使用 Anthropic Claude
        llm_provider = kwargs.pop('llm_provider', 'anthropic')
        llm_model = kwargs.pop('llm_model', 'claude-3-5-sonnet-20241022')

        self.set_rag_agent(
            llm_provider=llm_provider,
            llm_model=llm_model,
            **kwargs
        )


# 向后兼容：在 BaseAgent 中添加新方法
def add_rag_support_to_base_agent():
    """
    这个函数可以动态地将 RAG 支持添加到 BaseAgent
    在实际实现中，应该直接修改 base_agent.py
    """

    def set_rag_agent(
        self,
        instructions: Optional[str] = None,
        description: Optional[str] = None,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        vector_store_type: str = "chroma",
        **kwargs
    ):
        """
        使用 LlamaIndex 设置 RAG agent（新方法）

        替代 set_gpt_assistant_agent 以支持更多 LLM 提供商
        """
        # 创建临时的 ModernRAGAgent 实例来利用其功能
        rag_mixin = LlamaIndexRAGMixin()

        # ... 实现细节 ...

        if cmbagent_debug:
            print(f"\n[BaseAgent] Setting up RAG agent: {self.name}")
            print(f"  - LLM Provider: {llm_provider}")
            print(f"  - Model: {llm_model}")
            print(f"  - Vector Store: {vector_store_type}")

    # 将方法添加到 BaseAgent
    # BaseAgent.set_rag_agent = set_rag_agent

    print("RAG support added to BaseAgent")


if __name__ == "__main__":
    """
    测试示例
    """
    print("LlamaIndex RAG Agent Implementation Example")
    print("=" * 60)
    print("\nTo use this implementation:")
    print("1. Install dependencies:")
    print("   pip install llama-index llama-index-llms-openai llama-index-llms-anthropic")
    print("   pip install llama-index-embeddings-openai chromadb")
    print("\n2. Set environment variables:")
    print("   export OPENAI_API_KEY='your-key'")
    print("   export ANTHROPIC_API_KEY='your-key'")
    print("   export CMBAGENT_DATA='/path/to/cmbagent/data'")
    print("\n3. Usage example:")
    print("""
    from cmbagent.rag_llamaindex import CambAgentV2

    # 配置
    llm_config = {
        'config_list': [
            {'model': 'claude-3-5-sonnet-20241022', 'api_key': os.getenv('ANTHROPIC_API_KEY')}
        ],
        'temperature': 0.7
    }

    # 创建 agent
    agent = CambAgentV2(llm_config=llm_config)
    agent.set_agent(llm_provider='anthropic')

    # 使用 agent
    response = agent.rag_query("How do I calculate CMB power spectra with CAMB?")
    print(response)
    """)
