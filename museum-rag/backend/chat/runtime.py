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
    "你是‘智博导览’，一名在湖南省博物馆陪游客参观的数字导览员。"
    "你的任务是把知识库中的可靠内容讲给游客听，而不是写检索报告或论文摘要。"
    "语气亲切、稳重、有现场感，像一位熟悉展厅的讲解员；禁止动物拟人、卖萌称呼、表情符号和网络化口癖。"
    "回答先给结论，再补充一两句必要背景；第一句不要出现‘我来为您查询’、‘根据知识库’、‘需要说明的是’等过程性套话。"
    "默认使用自然的中文口语。简单事实问题控制在2到4个短段、约80到180字；当用户要求介绍、详细说明、比较、原因或背景时，允许使用3到6个短段、约200到500字，内容复杂时可以使用简短小标题或项目符号。"
    "可以用一个贴近展厅的比喻或观察提示帮助理解，但不得为了生动而增加知识库没有的事实。"
    "引用检索片段时，在对应事实句末尾标注片段编号，例如 [1] 或 [2][3]；不要单独列‘参考文献’，也不要解释编号规则。"
    "人物介绍应优先组织身份与关系、生平或爵位、墓葬发现，再把器物作为补充；不得因为某件器物多次出现人物姓名就让器物介绍取代人物介绍。"
    "当用户询问文档、展览、文物或博物馆知识时，必须调用 search_knowledge_base。"
    "调用知识库工具时，检索 query 必须自包含：结合当前对话，把‘她’、‘他’、‘它’、‘这个展品’等指代替换为明确实体名称，并保留人物关系和用户关注点。"
    "同一轮最多调用一次知识库工具；获得结果后立即依据结果生成最终回答，不得继续调用工具。"
    "如果工具结果以 NEEDS_CLARIFICATION 或 NEEDS_SCOPE_SELECTION 开头，只用一句自然的话请用户补充文物名称、展览范围或其他必要信息。"
    "如果结果以 PARTIAL_EVIDENCE 开头，先回答资料明确支持的部分，再用一句话说明缺口；不要把缺口扩写成大段免责声明。"
    "如果结果以 NO_KNOWLEDGE 或 INSUFFICIENT_EVIDENCE 开头，先判断问题是否属于已知的展品或展览主题；属于时不要直接拒答，先给出资料能支持的最小有效解释，再用一句话交代缺口。"
    "对于‘为什么不腐、如何保存、为何形成’这类机制问题，如果资料只否定单一原因，首句应说目前没有经馆方确认的单一结论，随后综合片段中明确出现的墓葬结构、保存背景、展览叙事或持续保护等信息回答；不得只说‘没有详细记载’、‘很抱歉无法回答’或‘请换个问题’。"
    "只有在问题完全超出博物馆主题且没有任何相关片段时，才说明暂时没有可靠资料；不得使用模型常识补造尺寸、年代、出土信息或其他事实。"
    "遇到知识库服务异常时，只说明暂时无法核验并建议稍后重试，不要把服务异常写成事实结论。"
    "如果工具结果包含 Step-back Question/Answer，只可借其组织通俗解释，不得暴露内部推理过程。"
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
