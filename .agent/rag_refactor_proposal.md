# RAG Agent 重构方案

## 目标

将当前基于 OpenAI GPT Assistant API 的 RAG agents 重构为更灵活、符合通用接口的方案。

## 当前架构

```python
# 当前使用 GPTAssistantAgent
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

class CambAgent(BaseAgent):
    def set_agent(self, **kwargs):
        super().set_gpt_assistant_agent(**kwargs)
```

**限制**：

- 绑定 OpenAI Assistant API
- 依赖 OpenAI 的 Vector Store
- 较高的 API 成本
- 灵活性有限

---

## 推荐方案对比

### 方案 1: **LlamaIndex + AG2** ⭐⭐⭐⭐⭐

#### 优势

- ✅ 与 AG2 原生集成
- ✅ 支持多种 LLM (OpenAI, Anthropic, Google, 本地模型)
- ✅ 灵活的向量存储 (Chroma, FAISS, Qdrant, Weaviate 等)
- ✅ 强大的查询引擎和检索策略
- ✅ 活跃的社区和文档

#### 架构示例

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, ServiceContext
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

class LlamaIndexRAGAgent(BaseAgent):
    def __init__(self, llm_config=None, **kwargs):
        super().__init__(llm_config=llm_config, **kwargs)
        self.index = None
        self.query_engine = None

    def setup_rag(self, data_path, llm_provider="openai", model_name="gpt-4"):
        # 1. 加载文档
        documents = SimpleDirectoryReader(data_path).load_data()

        # 2. 配置 LLM
        if llm_provider == "openai":
            llm = OpenAI(model=model_name)
        elif llm_provider == "anthropic":
            llm = Anthropic(model=model_name)
        # ... 其他 LLM 提供商

        # 3. 配置向量存储 (可选，默认使用内存)
        chroma_client = chromadb.PersistentClient(path=f"./chroma_db/{self.name}")
        chroma_collection = chroma_client.get_or_create_collection(self.name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        # 4. 创建索引
        self.index = VectorStoreIndex.from_documents(
            documents,
            llm=llm,
            embed_model=OpenAIEmbedding(),
            vector_store=vector_store
        )

        # 5. 创建查询引擎
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=5,
            response_mode="tree_summarize"
        )

    def query(self, query_str):
        """执行 RAG 查询"""
        response = self.query_engine.query(query_str)
        return str(response)

    def set_agent(self, **kwargs):
        """集成到 AG2 ConversableAgent"""
        # 创建一个带 RAG 功能的 function
        def rag_search(query: str) -> str:
            """Search documentation using RAG"""
            return self.query(query)

        # 将 RAG 作为 function 注册到 agent
        self.agent = CmbAgentSwarmAgent(
            name=self.name,
            system_message=self.info["instructions"],
            description=self.info["description"],
            llm_config=self.llm_config,
            functions=[rag_search],
            cmbagent_debug=cmbagent_debug,
        )
```

#### 依赖安装

```bash
pip install llama-index llama-index-llms-openai llama-index-llms-anthropic
pip install llama-index-embeddings-openai chromadb
```

---

### 方案 2: **LangChain RAG** ⭐⭐⭐⭐

#### 优势

- ✅ 成熟的 RAG 解决方案
- ✅ 丰富的预构建链和工具
- ✅ 支持多种向量数据库
- ✅ 强大的文档加载器

#### 架构示例

```python
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter

class LangChainRAGAgent(BaseAgent):
    def __init__(self, llm_config=None, **kwargs):
        super().__init__(llm_config=llm_config, **kwargs)
        self.vectorstore = None
        self.qa_chain = None

    def setup_rag(self, data_path, llm_provider="openai", model_name="gpt-4"):
        # 1. 加载文档
        loader = DirectoryLoader(data_path, glob="**/*.py", loader_cls=TextLoader)
        documents = loader.load()

        # 2. 文本分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)

        # 3. 创建向量存储
        embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=f"./chroma_db/{self.name}"
        )

        # 4. 配置 LLM
        if llm_provider == "openai":
            llm = ChatOpenAI(model_name=model_name)
        elif llm_provider == "anthropic":
            llm = ChatAnthropic(model=model_name)

        # 5. 创建 QA 链
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5})
        )

    def query(self, query_str):
        return self.qa_chain.run(query_str)

    def set_agent(self, **kwargs):
        def rag_search(query: str) -> str:
            """Search documentation using RAG"""
            return self.query(query)

        self.agent = CmbAgentSwarmAgent(
            name=self.name,
            system_message=self.info["instructions"],
            description=self.info["description"],
            llm_config=self.llm_config,
            functions=[rag_search],
            cmbagent_debug=cmbagent_debug,
        )
```

---

### 方案 3: **本地 RAG (FAISS + Sentence Transformers)** ⭐⭐⭐

#### 优势

- ✅ 完全本地化，无需 API 调用
- ✅ 低成本
- ✅ 数据隐私保护
- ❌ 检索质量可能不如商用 embeddings

#### 架构示例

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os

class LocalRAGAgent(BaseAgent):
    def __init__(self, llm_config=None, **kwargs):
        super().__init__(llm_config=llm_config, **kwargs)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.documents = []

    def setup_rag(self, data_path):
        # 1. 加载文档
        for filename in os.listdir(data_path):
            if filename.endswith('.py'):
                with open(os.path.join(data_path, filename), 'r') as f:
                    self.documents.append({
                        'filename': filename,
                        'content': f.read()
                    })

        # 2. 创建 embeddings
        texts = [doc['content'] for doc in self.documents]
        embeddings = self.embedder.encode(texts)

        # 3. 创建 FAISS 索引
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))

    def search(self, query, k=5):
        query_embedding = self.embedder.encode([query])
        distances, indices = self.index.search(
            query_embedding.astype('float32'), k
        )
        return [self.documents[i] for i in indices[0]]

    def query(self, query_str):
        results = self.search(query_str)
        context = "\n\n".join([doc['content'] for doc in results])
        return context
```

---

### 方案 4: **Haystack RAG** ⭐⭐⭐

#### 优势

- ✅ 企业级 RAG 框架
- ✅ 灵活的管道架构
- ✅ 支持混合检索

---

## 推荐实施步骤

### 阶段 1: 原型验证（1-2天）

1. 选择 LlamaIndex 方案
2. 为一个 RAG agent (如 `camb_agent`) 创建原型
3. 测试基本的检索和查询功能

### 阶段 2: 重构 BaseAgent（2-3天）

1. 修改 `base_agent.py`
2. 创建新的 `set_rag_agent` 方法
3. 保留 `set_gpt_assistant_agent` 以实现向后兼容

### 阶段 3: 迁移所有 RAG Agents（3-5天）

1. 更新所有 `rag_agents` 目录下的 agents
2. 更新配置文件
3. 数据迁移（从 OpenAI Vector Store 到新的向量存储）

### 阶段 4: 测试和优化（2-3天）

1. 单元测试
2. 集成测试
3. 性能调优

---

## 成本分析

| 方案                    | 初期成本 | 运行成本                          | 灵活性 |
| ----------------------- | -------- | --------------------------------- | ------ |
| 当前 (OpenAI Assistant) | 低       | 高 (Vector Store + Assistant API) | 低     |
| LlamaIndex              | 中       | 中-低 (仅 LLM + Embeddings)       | 高     |
| LangChain               | 中       | 中-低                             | 高     |
| 本地 FAISS              | 高       | 极低 (无 API 成本)                | 中     |

---

## 配置示例

### 更新 `base_agent.py`

```python
class BaseAgent:
    # ... 现有代码 ...

    ## for rag agents with LlamaIndex
    def set_rag_agent(self,
                      instructions=None,
                      description=None,
                      data_path=None,
                      llm_provider="openai",
                      model_name=None,
                      vector_store_type="chroma",
                      **kwargs):
        """
        使用 LlamaIndex 设置 RAG agent

        Args:
            instructions: agent 的指令
            description: agent 的描述
            data_path: 文档数据路径
            llm_provider: LLM 提供商 (openai, anthropic, google等)
            model_name: 模型名称
            vector_store_type: 向量存储类型 (chroma, faiss, qdrant等)
        """
        # 实现如上所示
        pass

    # 保留旧方法以实现向后兼容
    def set_gpt_assistant_agent(self, **kwargs):
        """旧的 GPT Assistant 方法，已弃用"""
        warnings.warn("set_gpt_assistant_agent is deprecated, use set_rag_agent instead",
                      DeprecationWarning)
        # ... 现有实现 ...
```

### 更新配置文件 (YAML)

```yaml
# camb.yaml
name: "camb_agent"
rag_config:
  type: "llamaindex" # 或 "langchain", "local", "assistant" (旧版)
  llm_provider: "anthropic" # 支持多个提供商
  llm_model: "claude-3-5-sonnet-20241022"
  vector_store: "chroma"
  embedding_model: "text-embedding-3-small"
  top_k: 5
  response_mode: "tree_summarize"

instructions: |
  You are a RAG agent for CAMB package...

description: "Expert in CAMB cosmology package"
```

---

## 下一步建议

1. **我推荐从 LlamaIndex 方案开始**，因为：
   - 与 AG2 集成最佳
   - 社区活跃且文档完善
   - 支持渐进式迁移

2. **创建一个功能分支**进行实验

3. **先迁移一个 agent** (如 `camb_agent`) 作为概念验证

4. **保持向后兼容**，允许用户选择使用新旧实现

---

## 参考资源

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering/)
- [AG2 + LlamaIndex Integration](https://ag2ai.github.io/ag2/docs/notebooks/agentchat_RetrieveChat)
- [Chroma Vector Database](https://www.trychroma.com/)
