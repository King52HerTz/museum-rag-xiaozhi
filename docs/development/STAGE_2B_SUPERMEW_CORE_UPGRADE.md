# 阶段 2B：SuperMew RAG 核心升级

更新时间：2026-08-23

## 目标

在独立分支 `codex/stage2b-supermew-core-upgrade` 中迁移 SuperMew 官方快照的 RAG 核心能力，同时不破坏博物馆知识库桥接接口。管理端上传、文档画像和 `/api/museum/query` 不直接覆盖。

## 已完成改动

### `backend/rag/utils.py`

- 增加 `FAST_MODEL` 驱动的一次性结构化查询重写协议，支持 Step-back 或 HyDE 二选一；
- 增加重排开关、模板占位值识别和可配置超时；
- 使用 `RETRIEVAL_TOP_K` 作为统一默认召回数量；
- embedding 失败与 Milvus 检索失败分开记录，dense fallback 复用同一向量；
- 保留本地 `filter_expr`、`trace_context`、`merge_retrieval_trace` 以及旧 Step-back/HyDE 包装函数，保证博物馆桥接和旧调用方可继续工作。

### `backend/rag/pipeline.py`

- 迁移官方证据评分路由：`answer`、`rewrite`、`clarify`、`scope_select`、`no_knowledge`；
- 增加复杂问题子问题分解、并行子 Agent 合成和一次性重写预算；
- 增加 HITL 恢复状态生成与定向恢复检索；
- 通过请求级 `ChatRequestContext` 输出 RAG 步骤；
- `run_rag_graph(question, ctx=None)` 保留旧同步调用兼容，旧工具不传 context 时自动创建并关闭临时 context；
- 处理 `backend.chat` 包初始化带来的循环导入，避免管理端启动时导入失败。

### 请求上下文和知识库工具

- 请求上下文可以暂存标准化 HITL 恢复状态；
- 知识库工具识别澄清/范围选择路由并返回稳定的 `NEEDS_CLARIFICATION`、`NEEDS_SCOPE_SELECTION` 标记；
- 现有 Agent 提示词已经要求收到这些标记后直接向用户提问，不继续重复调用知识库工具。

## 验证门禁

项目虚拟环境中已通过：

```text
python -m unittest discover -s tests -p "test_*.py" -v
Ran 11 tests ... OK

python -m compileall -q backend tests
```

新增 `tests/test_rag_core_compatibility.py`，覆盖：

- 无 context 的旧同步入口自动创建并关闭 context；
- 新证据评分流水线返回可回答结果；
- 空召回短路，不调用证据评分模型；
- Step-back/HyDE 结构化重写只保留选中的策略。

另外完成了 RAG 图导入、管理端应用导入和博物馆桥接测试；未进行真实模型、Milvus、Redis 或 PostgreSQL 调用，避免在代码验证阶段暴露环境凭据。

## 暂不切换的部分

`backend/chat/service.py` 的完整同步/流式 HITL 事件、持久化 pending 状态和恢复回答仍作为下一小批改动处理。当前阶段已经能生成并保存 HITL 恢复信息，但不会把管理端文档上传链路替换成上游实现。

## 回退和下一步

- 回退点：本分支提交前保留阶段 2 提交 `ea40cf1`；
- 下一小批：在不改变现有数据库结构的前提下，将 pending HITL 状态映射到会话 metadata，并补充同步/流式事件测试；
- 完成该小批并通过门禁后，再进行小智服务端实际请求回归和 GitHub 推送。
