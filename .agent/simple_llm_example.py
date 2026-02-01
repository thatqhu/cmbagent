"""
简化 LLM 配置使用示例

演示如何使用 planning_and_control_simple() 方法
"""

from cmbagent import planning_and_control_simple

# ============================================================
# 示例 1: 使用 OpenAI GPT-4
# ============================================================
def example_openai():
    """使用 OpenAI API 的示例"""
    print("=" * 60)
    print("示例 1: 使用 OpenAI GPT-4")
    print("=" * 60)

    results = planning_and_control_simple(
        task="分析宇宙微波背景辐射数据并生成功率谱图",
        api_key="sk-your-openai-api-key-here",  # 替换为你的 API key
        model="gpt-4o",
        max_plan_steps=5
    )

    print("✅ 执行完成!")
    return results


# ============================================================
# 示例 2: 使用 Ollama 本地模型
# ============================================================
def example_ollama():
    """使用 Ollama 本地模型的示例

    前提条件:
    1. 安装 Ollama: https://ollama.ai/
    2. 启动 Ollama 服务: ollama serve
    3. 下载模型: ollama pull llama3.1:70b
    """
    print("=" * 60)
    print("示例 2: 使用 Ollama 本地模型")
    print("=" * 60)

    results = planning_and_control_simple(
        task="分析宇宙微波背景辐射数据并生成功率谱图",
        api_key="ollama",  # Ollama 不需要真实的 API key
        model="llama3.1:70b",
        base_url="http://localhost:11434/v1",
        max_plan_steps=3
    )

    print("✅ 执行完成!")
    return results


# ============================================================
# 示例 3: 使用 Together AI
# ============================================================
def example_together_ai():
    """使用 Together AI 的示例

    前提条件:
    1. 注册 Together AI 账号: https://together.ai/
    2. 获取 API key
    """
    print("=" * 60)
    print("示例 3: 使用 Together AI")
    print("=" * 60)

    results = planning_and_control_simple(
        task="分析宇宙微波背景辐射数据并生成功率谱图",
        api_key="your-together-api-key-here",  # 替换为你的 API key
        model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        base_url="https://api.together.xyz/v1",
        max_plan_steps=4
    )

    print("✅ 执行完成!")
    return results


# ============================================================
# 示例 4: 使用 vLLM 自托管服务
# ============================================================
def example_vllm():
    """使用 vLLM 自托管服务的示例

    前提条件:
    1. 安装 vLLM: pip install vllm
    2. 启动 vLLM 服务:
       python -m vllm.entrypoints.openai.api_server \
           --model microsoft/Phi-3-medium-128k-instruct \
           --port 8000
    """
    print("=" * 60)
    print("示例 4: 使用 vLLM 自托管服务")
    print("=" * 60)

    results = planning_and_control_simple(
        task="分析宇宙微波背景辐射数据并生成功率谱图",
        api_key="dummy",  # vLLM 不需要真实的 API key
        model="microsoft/Phi-3-medium-128k-instruct",
        base_url="http://localhost:8000/v1",
        max_plan_steps=3
    )

    print("✅ 执行完成!")
    return results


# ============================================================
# 示例 5: 高级用法 - 自定义配置
# ============================================================
def example_advanced():
    """高级用法示例"""
    print("=" * 60)
    print("示例 5: 高级用法 - 自定义配置")
    print("=" * 60)

    results = planning_and_control_simple(
        task="分析宇宙微波背景辐射数据并生成功率谱图",
        api_key="sk-your-api-key",
        model="gpt-4o",
        max_plan_steps=5,
        # 自定义工作目录
        work_dir="./custom_output",
        clear_work_dir=True,
        # 添加自定义指令
        plan_instructions="确保计划中包含数据验证步骤",
        engineer_instructions="使用 matplotlib 和 seaborn 生成图表",
        researcher_instructions="优先使用 arXiv.org 上最新的文献",
        # 硬件约束
        hardware_constraints="使用 CPU 进行计算，避免使用 GPU",
        # 控制轮次
        max_rounds_planning=30,
        max_rounds_control=50,
        max_n_attempts=5
    )

    print("✅ 执行完成!")
    return results


# ============================================================
# 主函数
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CMBAgent - 简化 LLM 配置使用示例")
    print("=" * 60 + "\n")

    # 选择要运行的示例
    example_choice = input("""
请选择要运行的示例:
1. OpenAI GPT-4
2. Ollama 本地模型
3. Together AI
4. vLLM 自托管服务
5. 高级用法

请输入数字 (1-5): """).strip()

    examples = {
        "1": example_openai,
        "2": example_ollama,
        "3": example_together_ai,
        "4": example_vllm,
        "5": example_advanced
    }

    if example_choice in examples:
        try:
            results = examples[example_choice]()
            print("\n" + "=" * 60)
            print("执行结果概览")
            print("=" * 60)
            print(f"最终上下文键: {list(results['final_context'].keys())}")
            print(f"聊天记录条数: {len(results['chat_history'])}")
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ 无效的选择!")
