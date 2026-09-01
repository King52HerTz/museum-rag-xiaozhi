from typing import TYPE_CHECKING, Any
import time
import uuid

import requests

from config.logger import setup_logging
from plugins_func.register import Action, ActionResponse, ToolType, register_function

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


SEARCH_MUSEUM_KNOWLEDGE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_museum_knowledge",
        "description": (
            "当用户询问湖南省博物馆、马王堆汉墓、辛追夫人、素纱单衣、T形帛画、"
            "皿方罍、人面纹方鼎、文物年代、展品故事、遗体保存、展厅路线或博物馆导览问题时，"
            "调用博物馆知识库检索资料。调用前不要向游客解释正在查询，拿到结果后直接用导览员口吻回答。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "游客提出的博物馆、展品、文物或导览相关问题",
                },
                "exhibit_id": {
                    "type": "string",
                    "description": "可选展品编号；不知道时不要编造，可以不传",
                },
            },
            "required": ["question"],
        },
    },
}


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _clip_text(text: str, limit: int = 1200) -> str:
    text = _safe_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "……"


def _parse_error_payload(response: requests.Response) -> dict:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _trace_digest(result: dict) -> str:
    trace = result.get("trace") or {}
    if not isinstance(trace, dict):
        return "retrieval_mode=-|retrieval_empty=-|rerank_error=-"
    retrieval_mode = _safe_text(trace.get("retrieval_mode"), "-")
    retrieval_empty = trace.get("retrieval_empty")
    rerank_error = "yes" if _safe_text(trace.get("rerank_error")) else "no"
    return (
        f"retrieval_mode={retrieval_mode}"
        f"|retrieval_empty={retrieval_empty if retrieval_empty is not None else '-'}"
        f"|rerank_error={rerank_error}"
    )


def _build_llm_context(question: str, result: dict) -> str:
    contexts = result.get("contexts") or []
    trace = result.get("trace") or {}
    if not isinstance(trace, dict):
        trace = {}
    outcome = _safe_text(trace.get("retrieval_outcome"))
    if not contexts or outcome == "NO_KNOWLEDGE":
        return (
            "你是“智博导览助手”，一名专业、亲切的博物馆语音导览员。\n"
            f"游客问题：{question}\n"
            "博物馆知识库没有检索到足够相关的资料。请直接、自然地告诉游客：目前没有查到足够准确的馆方资料，"
            "可以换一种问法，或询问其他展品；不要说‘我来为您查询’，也不要编造答案。"
        )

    evidence_notice = ""
    if outcome == "INSUFFICIENT_EVIDENCE":
        evidence_notice = (
            "当前检索服务存在降级或证据覆盖缺口。只能回答下面片段明确支持的内容；"
            "如果问题要求的细节不在片段中，请明确说明资料不足，不要自行补全。\n\n"
        )

    lines = [
        "你是“智博导览助手”，一名专业、亲切的博物馆语音导览员。",
        "请严格根据下面的博物馆知识库资料回答游客问题，调用完成后直接回答，不要复述检索过程。",
        "",
        "回答要求：",
        "1. 适合语音播报，默认控制在80到180字，分成2到4个短段；",
        "2. 第一处先直接回答问题，像现场导览员，不要像论文摘要或检索报告；",
        "3. 不要使用固定小标题、项目符号、Markdown 加粗或表情符号；",
        "4. 不要出现“我来为您查询”“根据知识库”“需要说明的是”等过程性套话；",
        "5. 不要编造知识库之外的事实；资料不足时只用一句话说明缺口；",
        "6. 不要机械朗读文件名，如果需要引用，在相关事实后标注片段编号；",
        "7. 如果资料来自多个片段，请综合成连贯、适合游客听的回答。",
        "",
        f"游客问题：{question}",
        "",
    ]

    if evidence_notice:
        lines.append(evidence_notice.rstrip())

    coverage_gaps = [
        _safe_text(item) for item in (trace.get("coverage_gap_questions") or []) if _safe_text(item)
    ]
    if coverage_gaps:
        lines.append("证据覆盖缺口（不要猜测）：" + "；".join(coverage_gaps))

    lines.append("博物馆知识库检索结果：")

    for i, item in enumerate(contexts[:5], start=1):
        source = _safe_text(item.get("source") or item.get("title"), "未知来源")
        page = item.get("page_number")
        content = _clip_text(item.get("content"), 1200)
        if not content:
            continue
        source_line = f"[{i}] 来源：{source}"
        if page is not None:
            source_line += f"，页码/工作表：{page}"
        lines.append(f"{source_line}\n内容：{content}")

    return "\n\n".join(lines)


@register_function(
    "search_museum_knowledge",
    SEARCH_MUSEUM_KNOWLEDGE_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def search_museum_knowledge(
    conn: "ConnectionHandler",
    question=None,
    exhibit_id=None,
):
    question = _safe_text(question)
    exhibit_id = _safe_text(exhibit_id)
    if not question:
        return ActionResponse(Action.RESPONSE, None, "请告诉我你想了解哪件展品或哪个展厅。")

    plugin_config = conn.config.get("plugins", {}).get("search_museum_knowledge", {})
    base_url = _safe_text(plugin_config.get("base_url"), "http://127.0.0.1:8000").rstrip("/")
    api_key = _safe_text(plugin_config.get("api_key"))
    museum = _safe_text(plugin_config.get("museum"), "湖南省博物馆")
    exhibition = _safe_text(plugin_config.get("exhibition"), "")
    top_k = plugin_config.get("top_k", 5)
    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 5
    timeout = plugin_config.get("timeout", 8)
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        timeout = 8.0
    need_trace = bool(plugin_config.get("need_trace", True))
    request_id = uuid.uuid4().hex[:16]
    started_at = time.perf_counter()

    url = f"{base_url}/api/museum/query"
    headers = {
        "Content-Type": "application/json",
        "X-Bridge-Trace-Id": request_id,
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "question": question,
        "museum": museum,
        "scene": "museum_guide",
        "top_k": top_k,
        "need_trace": need_trace,
    }
    if exhibition:
        payload["exhibition"] = exhibition
    if exhibit_id:
        payload["exhibit_id"] = exhibit_id

    logger.bind(tag=TAG).info(
        f"博物馆知识库请求开始：trace_id={request_id}, base_url={base_url}, top_k={top_k}, "
        f"need_trace={need_trace}, museum={museum}, exhibition={exhibition or '-'}, "
        f"exhibit_id={exhibit_id or '-'}, question_len={len(question)}"
    )

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.encoding = "utf-8"
        result = response.json()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        server_trace_id = _safe_text(response.headers.get("X-Bridge-Trace-Id"), request_id)

        if response.status_code >= 400:
            error_code = _safe_text(result.get("error_code"))
            message = _safe_text(result.get("message"), "博物馆知识库请求失败")
            logger.bind(tag=TAG).error(
                f"博物馆知识库桥接异常：trace_id={server_trace_id}, status={response.status_code}, "
                f"elapsed_ms={elapsed_ms}, error_code={error_code or '-'}, "
                f"details_count={len(result.get('details') or [])}, payload={result}"
            )

            if error_code in {"BRIDGE_AUTH_MISSING", "BRIDGE_AUTH_INVALID", "BRIDGE_API_KEY_NOT_CONFIGURED"}:
                return ActionResponse(
                    Action.RESPONSE,
                    None,
                    "博物馆知识库桥接认证失败，请检查 SuperMew 与小智插件的 api_key 配置。",
                )

            if error_code == "MUSEUM_QUERY_VALIDATION_FAILED":
                return ActionResponse(
                    Action.RESPONSE,
                    None,
                    f"博物馆知识库请求参数异常：{message}",
                )

            return ActionResponse(
                Action.RESPONSE,
                None,
                f"博物馆知识库暂时不可用：{message}",
            )

        if result.get("code", 0) != 0:
            logger.bind(tag=TAG).error(
                f"博物馆知识库返回业务异常：trace_id={server_trace_id}, elapsed_ms={elapsed_ms}, "
                f"code={result.get('code')}, error_code={_safe_text(result.get('error_code'), '-')}, "
                f"payload={result}"
            )
            return ActionResponse(
                Action.RESPONSE,
                None,
                "我刚才查询博物馆知识库时遇到异常，请稍后再试。",
            )

        logger.bind(tag=TAG).info(
            f"博物馆知识库请求成功：trace_id={server_trace_id}, elapsed_ms={elapsed_ms}, "
            f"contexts={len(result.get('contexts') or [])}, {_trace_digest(result)}"
        )
        llm_context = _build_llm_context(question, result)
        return ActionResponse(Action.REQLLM, llm_context, None)

    except requests.exceptions.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        response = getattr(exc, "response", None)
        error_payload = _parse_error_payload(response) if response is not None else {}
        server_trace_id = _safe_text(getattr(response, "headers", {}).get("X-Bridge-Trace-Id") if response is not None else "", request_id)
        if error_payload:
            error_code = _safe_text(error_payload.get("error_code"))
            message = _safe_text(error_payload.get("message"), "博物馆知识库请求失败")
            logger.bind(tag=TAG).error(
                f"博物馆知识库请求失败：trace_id={server_trace_id}, exception={type(exc).__name__}, "
                f"status={getattr(response, 'status_code', 'unknown')}, elapsed_ms={elapsed_ms}, "
                f"error_code={error_code or '-'}, payload={error_payload}"
            )
            if error_code in {"BRIDGE_AUTH_MISSING", "BRIDGE_AUTH_INVALID", "BRIDGE_API_KEY_NOT_CONFIGURED"}:
                return ActionResponse(
                    Action.RESPONSE,
                    None,
                    "博物馆知识库桥接认证失败，请检查 SuperMew 与小智插件的 api_key 配置。",
                )
            return ActionResponse(
                Action.RESPONSE,
                None,
                f"博物馆知识库请求失败：{message}",
            )

        logger.bind(tag=TAG).error(
            f"博物馆知识库请求失败：trace_id={request_id}, exception={type(exc).__name__}, "
            f"elapsed_ms={elapsed_ms}, message={exc}"
        )
        return ActionResponse(
            Action.RESPONSE,
            None,
            "我现在无法连接博物馆知识库，请检查 RAG 服务是否已经启动，或稍后再试。",
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.bind(tag=TAG).error(
            f"博物馆知识库插件处理异常：trace_id={request_id}, exception={type(exc).__name__}, "
            f"elapsed_ms={elapsed_ms}, message={exc}"
        )
        return ActionResponse(
            Action.RESPONSE,
            None,
            f"博物馆知识库插件处理异常：{type(exc).__name__}",
        )
