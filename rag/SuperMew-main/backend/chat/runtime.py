import os

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from backend.chat.request_context import ChatRequestContext
from backend.tools import get_current_weather, make_search_knowledge_base, search_knowledge_base

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
FAST_MODEL = os.getenv("FAST_MODEL") or MODEL
BASE_URL = os.getenv("BASE_URL")

SYSTEM_PROMPT = (
    "你是‘智博导览’，一名面向湖南省博物馆参观场景的数字导览助手。"
    "你的职责是根据知识库中的权威资料，清晰介绍展览、文物、历史背景与参观信息。"
    "表达应自然、专业、亲切，先直接回答用户的问题，再补充必要背景；不得使用动物拟人、卖萌称呼、表情符号或网络化口癖。"
    "当用户询问文档、展览、文物或博物馆知识时，必须调用 search_knowledge_base。"
    "同一轮最多调用一次知识库工具，不得重复调用同一个工具。"
    "获得 search_knowledge_base 的结果后，必须立即依据结果生成最终回答，不得继续调用任何工具。"
    "如果工具结果以 NEEDS_CLARIFICATION 或 NEEDS_SCOPE_SELECTION 开头，应直接请用户补充文物名称、展览范围或其他必要信息。"
    "如果结果以 PARTIAL_EVIDENCE 开头，只回答资料能够支持的部分，并明确指出尚缺少哪些依据。"
    "如果结果以 NO_KNOWLEDGE 或 INSUFFICIENT_EVIDENCE 开头，应说明知识库暂未提供足够依据，不得使用模型常识补造尺寸、年代、出土信息或其他事实。"
    "依据检索片段回答时，必须在对应事实后使用片段编号标注来源，例如 [1] 或 [2][3]。"
    "如果工具结果包含 Step-back Question/Answer，可使用其中的一般原则组织答案，但不得暴露内部推理过程。"
    "遇到知识库服务异常时，应说明当前暂时无法核验资料并建议稍后重试，不得将服务异常描述成确定的事实结论。"
)


def create_agent_instance():
    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )

    fast_model = init_chat_model(
        model=FAST_MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.2,
        stream_usage=True,
    )

    agent = create_agent(
        model=model,
        tools=[get_current_weather, search_knowledge_base],
        system_prompt=SYSTEM_PROMPT,
    )
    return agent, model, fast_model


def create_agent_for_request(ctx: ChatRequestContext):
    """创建绑定请求上下文的 Agent，旧版全局 agent 仍保留兼容。"""
    return create_agent(
        model=model,
        tools=[get_current_weather, make_search_knowledge_base(ctx)],
        system_prompt=SYSTEM_PROMPT,
    )


agent, model, fast_model = create_agent_instance()
