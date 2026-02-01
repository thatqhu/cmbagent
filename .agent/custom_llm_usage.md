# 统一 LLM 配置 - 使用指南

## ✅ 已完成的修改

我已经修改了 `cmbagent/utils.py`，添加了对自定义 base_url 的 LLM 的支持。

## 🚀 快速开始

### 方法 1: 使用环境变量（推荐）

```bash
# 设置自定义 LLM 配置
export CUSTOM_LLM_BASE_URL="http://localhost:8000/v1"
export CUSTOM_LLM_MODEL="llama-3.1-70b"
export CUSTOM_LLM_API_KEY="your-api-key"  # 可选，某些服务不需要

# 运行 cmbagent
cmbagent run
```

### 方法 2: 在代码中设置

```python
import os

# 在导入 cmbagent 之前设置
os.environ["CUSTOM_LLM_BASE_URL"] = "http://localhost:8000/v1"
os.environ["CUSTOM_LLM_MODEL"] = "llama-3.1-70b"
os.environ["CUSTOM_LLM_API_KEY"] = "your-key"

import cmbagent

result = cmbagent.one_shot("Your task here")
```

### 方法 3: 使用 .env 文件

创建 `.env` 文件在项目根目录：

```bash
# .env
CUSTOM_LLM_BASE_URL=http://localhost:8000/v1
CUSTOM_LLM_MODEL=llama-3.1-70b
CUSTOM_LLM_API_KEY=your-key
```

然后使用 `python-dotenv` 加载：

```python
from dotenv import load_dotenv
load_dotenv()

import cmbagent
```

---

## 📋 常见 LLM 服务配置

### 1. Ollama (本地)

```bash
export CUSTOM_LLM_BASE_URL="http://localhost:11434/v1"
export CUSTOM_LLM_MODEL="llama3.1:70b"
export CUSTOM_LLM_API_KEY="ollama"
```

**启动 Ollama 服务**:

```bash
ollama serve
ollama pull llama3.1:70b
```

**测试**:

```bash
curl http://localhost:11434/v1/models
```

---

### 2. vLLM (本地或远程)

```bash
export CUSTOM_LLM_BASE_URL="http://localhost:8000/v1"
export CUSTOM_LLM_MODEL="meta-llama/Llama-3.1-70B-Instruct"
export CUSTOM_LLM_API_KEY="token-abc123"
```

**启动 vLLM 服务**:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-70B-Instruct \
    --served-model-name llama-3.1-70b \
    --api-key token-abc123
```

**测试**:

```bash
curl http://localhost:8000/v1/models \
    -H "Authorization: Bearer token-abc123"
```

---

### 3. LM Studio (本地)

```bash
export CUSTOM_LLM_BASE_URL="http://localhost:1234/v1"
export CUSTOM_LLM_MODEL="local-model"
export CUSTOM_LLM_API_KEY="lm-studio"
```

在 LM Studio 中：

1. 加载模型
2. 点击 "Start Server"
3. 使用默认端口 1234

**测试**:

```bash
curl http://localhost:1234/v1/models
```

---

### 4. Together AI

```bash
export CUSTOM_LLM_BASE_URL="https://api.together.xyz/v1"
export CUSTOM_LLM_MODEL="meta-llama/Llama-3-70b-chat-hf"
export CUSTOM_LLM_API_KEY="your-together-api-key"
```

**获取 API key**: https://api.together.xyz/settings/api-keys

---

### 5. Anyscale

```bash
export CUSTOM_LLM_BASE_URL="https://api.endpoints.anyscale.com/v1"
export CUSTOM_LLM_MODEL="meta-llama/Llama-3-70b-chat-hf"
export CUSTOM_LLM_API_KEY="your-anyscale-api-key"
```

---

### 6. 自定义 OpenAI 兼容服务

```bash
export CUSTOM_LLM_BASE_URL="https://your-llm-service.com/v1"
export CUSTOM_LLM_MODEL="your-model-name"
export CUSTOM_LLM_API_KEY="your-api-key"
```

---

## 🔍 验证配置

运行以下 Python 代码验证配置:

```python
#!/usr/bin/env python3
import os

# 设置配置
os.environ["CUSTOM_LLM_BASE_URL"] = "http://localhost:8000/v1"
os.environ["CUSTOM_LLM_MODEL"] = "llama-3.1-70b"

# 导入并检查
from cmbagent.utils import (
    default_llm_model,
    default_formatter_model,
    default_llm_config_list,
    CUSTOM_LLM_BASE_URL
)

print("=" * 60)
print("配置验证")
print("=" * 60)

print(f"\n✅ 自定义 LLM Base URL: {CUSTOM_LLM_BASE_URL}")
print(f"✅ 默认模型: {default_llm_model}")
print(f"✅ Formatter 模型: {default_formatter_model}")

print(f"\n默认配置:")
for cfg in default_llm_config_list:
    print(f"  Model: {cfg['model']}")
    print(f"  Base URL: {cfg.get('base_url', 'N/A')}")
    print(f"  API Type: {cfg['api_type']}")

print("\n✅ 配置成功!")
```

---

## 🧪 测试

### 简单测试

```python
import os
os.environ["CUSTOM_LLM_BASE_URL"] = "http://localhost:8000/v1"
os.environ["CUSTOM_LLM_MODEL"] = "llama-3.1-70b"

import cmbagent

result = cmbagent.one_shot(
    task="Calculate 2 + 2 and explain your answer.",
    agent='engineer'
)

print(result)
```

### 测试所有 agents 使用相同配置

当设置 `CUSTOM_LLM_BASE_URL` 后，所有 agents 会自动使用同一个 LLM：

```python
from cmbagent.utils import default_agent_llm_configs

# 检查前几个 agents
for agent_name in list(default_agent_llm_configs.keys())[:5]:
    config = default_agent_llm_configs[agent_name]
    print(f"{agent_name}:")
    print(f"  Model: {config['model']}")
    print(f"  Base URL: {config.get('base_url', 'N/A')}")
    print()
```

---

## ⚙️ 工作原理

### 修改说明

`cmbagent/utils.py` 中的修改：

1. **新增环境变量读取**:

   ```python
   CUSTOM_LLM_BASE_URL = os.getenv("CUSTOM_LLM_BASE_URL")
   CUSTOM_LLM_MODEL = os.getenv("CUSTOM_LLM_MODEL", "llama-3.1-70b")
   CUSTOM_LLM_API_KEY = os.getenv("CUSTOM_LLM_API_KEY", "sk-dummy")
   ```

2. **修改 `get_model_config` 函数**:
   - 添加 `base_url` 参数
   - 优先使用自定义配置
   - 保持向后兼容

3. **修改默认模型配置**:
   - 如果设置了 `CUSTOM_LLM_BASE_URL`，所有模型使用自定义配置
   - 否则使用原有的多模型配置

4. **统一所有 agents**:
   - 所有 agents 的 `llm_config` 自动指向自定义 LLM
   - 简化配置管理

---

## 🔄 回退到原有配置

如果需要回退，只需**不设置**环境变量：

```bash
unset CUSTOM_LLM_BASE_URL
unset CUSTOM_LLM_MODEL
unset CUSTOM_LLM_API_KEY
```

或者在代码中：

```python
import os
os.environ.pop("CUSTOM_LLM_BASE_URL", None)
```

系统会自动使用原有的多 LLM 配置。

---

## 📝 完整示例

### 使用 Ollama 本地运行 cmbagent

```bash
#!/bin/bash

# 1. 启动 Ollama
ollama serve &

# 2. 下载模型
ollama pull llama3.1:70b

# 3. 设置环境变量
export CUSTOM_LLM_BASE_URL="http://localhost:11434/v1"
export CUSTOM_LLM_MODEL="llama3.1:70b"
export CUSTOM_LLM_API_KEY="ollama"

# 4. 运行 cmbagent
python3 << EOF
import cmbagent

result = cmbagent.one_shot(
    task="Explain what a Large Language Model is in simple terms.",
    agent='engineer'
)

print("Result:")
print(result)
EOF
```

---

## 🐛 故障排除

### 问题 1: 连接失败

```
ConnectionError: HTTPConnectionPool(host='localhost', port=8000)
```

**解决**:

- 确认 LLM 服务正在运行
- 检查端口是否正确
- 测试连接: `curl http://localhost:8000/v1/models`

### 问题 2: 认证失败

```
AuthenticationError: Invalid API key
```

**解决**:

- 确认 API key 正确
- 某些本地服务不需要真实 API key，使用占位符如 `"sk-dummy"`

### 问题 3: 模型名称不匹配

```
Model 'llama-3.1-70b' not found
```

**解决**:

- 列出可用模型: `curl http://localhost:8000/v1/models`
- 使用服务中实际的模型名称

### 问题 4: 配置未生效

**解决**:

- 确保在导入 cmbagent **之前**设置环境变量
- 重新启动 Python 解释器
- 检查拼写: `CUSTOM_LLM_BASE_URL` (注意下划线)

---

## ✅ 优势总结

- ✅ **简化配置**: 统一使用一个 LLM，无需管理多个 API keys
- ✅ **降低成本**: 可使用本地或更便宜的服务
- ✅ **提高灵活性**: 随时切换 LLM 服务
- ✅ **保持兼容**: 不影响原有功能，可随时切回
- ✅ **便于测试**: 快速测试不同的 LLM
- ✅ **支持本地化**: 完全离线运行

---

## 📚 参考资源

- [Ollama 文档](https://ollama.ai/)
- [vLLM 文档](https://docs.vllm.ai/)
- [LM Studio](https://lmstudio.ai/)
- [Together AI](https://www.together.ai/)
- [OpenAI API 兼容性](https://platform.openai.com/docs/api-reference)

---

## 💡 下一步

1. 选择你的 LLM 服务
2. 设置环境变量
3. 运行简单测试
4. 享受统一配置的便利！

如果遇到问题，请检查 [故障排除](#故障排除) 部分。
