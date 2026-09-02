# 阶段 13：桥接层传递 RAG 结果语义

更新时间：2026-08-30

## 目标

把 SuperMew 的检索结果状态传到小智服务端插件，使设备端能够区分“知识库确实命中”、
“知识库没有相关资料”和“检索服务降级/证据不完整”。这样最终回答不会因为上下文缺失而
退化成没有依据的普通模型回答。

## 已完成改动

- `museum-rag/backend/api/routes/museum.py`
  - 在兼容现有响应结构的前提下增加 `trace.retrieval_outcome` 和
    `trace.retrieval_status`。
  - 有有效片段且没有检索降级时返回 `ANSWERABLE / answerable`。
  - 无片段且没有降级时返回 `NO_KNOWLEDGE / no_knowledge`，继续使用“未检索到相关资料”。
  - 发生 embedding、向量库或 Provider 降级且没有可靠片段时返回
    `INSUFFICIENT_EVIDENCE / insufficient_evidence`，并提示当前无法确认知识库是否有答案。
  - `contexts`、旧 trace 字段和 `need_trace=false` 的行为保持兼容。
- `zhibo-guide-platform/main/xiaozhi-server/plugins_func/functions/search_museum_knowledge.py`
  - 消费桥接返回的结果语义。
  - `NO_KNOWLEDGE` 继续引导游客换一种问法，不把空结果交给 LLM 自由发挥。
  - `INSUFFICIENT_EVIDENCE` 时明确要求 LLM 只回答片段支持的内容，并披露资料不足。
  - 将 `coverage_gap_questions` 传入导览上下文，要求缺口部分不要猜测。
- `museum-rag/tests/test_museum_bridge_contract.py`
  - 增加可回答、无知识和检索降级三种桥接结果的契约测试。

## 验证结果

- 桥接定向测试：9 passed、11 个子测试通过。
- RAG 完整测试：39 passed、11 个子测试通过。
- RAG `compileall`：通过。
- 小智插件 `py_compile`：通过。
- 小智插件上下文隔离冒烟验证：通过，覆盖三种结果语义和证据缺口提示。
- 本批暂存内容的敏感值样式扫描：0 条匹配。

## 运行时验证方式

1. 启动 RAG 和小智服务端，确保小智插件的 `base_url` 指向 RAG 服务，桥接密钥只填写在本地配置。
2. 在管理端或设备端询问资料中有明确答案的文物问题，追踪中应看到 `ANSWERABLE`，回答应引用检索片段。
3. 询问资料中没有的问题，追踪中应看到 `NO_KNOWLEDGE`，导览员应说明暂未查到准确资料。
4. 临时停止向量库或制造检索降级后再询问，追踪中应看到 `INSUFFICIENT_EVIDENCE`，回答不得补全缺失细节。

## 安全与边界

- 没有修改 `main`、硬件工程、账号密码、API Key 或本地上传资料。
- 没有把上游 SuperMew 整体覆盖到运行副本；本阶段只改桥接契约和小智插件消费逻辑。
- 小智设备协议和原有 `search_museum_knowledge` 函数名保持不变。

## 提交

代码提交：`1410684 feat(bridge): propagate rag outcomes to xiaozhi`。

## 下一步

在隔离的 `rag/SuperMew-upstream` 分支扩展马王堆人工标注评测集，并建立 Windows 可运行的
兼容性门禁；评测通过后再决定是否迁移上游运行时模块。稳定版继续承担当前设备演示。
