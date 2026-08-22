# 阶段 2C：聊天服务 HITL 会话接入

更新时间：2026-08-23

## 目标

将阶段 2B 生成的 `clarify`、`scope_select` 状态接入现有聊天服务，使博物馆知识库在证据不足或范围不明确时能够暂停、向用户提问，并在下一轮继续原问题。保留现有 PostgreSQL/Redis 会话存储、聊天接口和 SSE 基础事件格式。

## 已完成改动

### 同步聊天 `/api/chat`

- 在会话 metadata 中保存 `pending_hitl`；
- 保存原始问题、澄清提示、选项、恢复快照和已给出的补充答案；
- 首次请求遇到 HITL 时返回澄清文本，并保留标准 `rag_trace`；
- 下一轮检测到 pending 状态后，直接调用 `resume_rag_from_hitl`，不重新创建 Agent；
- 恢复检索有证据时由主模型基于检索片段生成最终答案，完成后清除 pending 状态。

### 流式聊天 `/api/chat/stream`

- 保留原有 `rag_step`、`content`、`trace`、`session_title` 和 `[DONE]` 事件；
- 新增 `hitl_request` SSE 事件，携带提示、选项、路由和原始问题；
- HITL 首次请求不向客户端泄漏中间模型文本，只发送澄清事件；
- 下一轮流式恢复时跳过 Agent，执行定向 RAG，并流式输出基于证据的答案。

### 兼容边界

- 使用现有 `ConversationStorage` 实例，不替换数据库模型和会话路由；
- `PendingHitlState` 与现有兼容 trace schema 共存；
- 不修改管理端文档上传、博物馆 `/api/museum/query` 和硬件代码；
- 普通短对话不再额外调用持久化笔记模型，避免影响当前演示链路。

## 验证结果

项目虚拟环境中通过：

```text
python -m unittest discover -s tests -p "test_*.py" -v
Ran 18 tests ... OK

python -m compileall -q backend tests
git diff --check
```

新增 `tests/test_chat_hitl_resume.py`，覆盖同步/流式 HITL 首次请求、pending 持久化、恢复时跳过 Agent、恢复答案、普通同步回答和流式基础事件。

同时完成管理端应用导入检查；未调用真实模型、Milvus、Redis 或 PostgreSQL，真实联调放到下一阶段执行。

## 下一阶段

下一阶段执行真实服务回归：启动 RAG 服务，上传湖南省博物馆资料，验证管理端检索接口，再验证 `/api/chat` 与 `/api/chat/stream` 的普通问答、无知识和 HITL 场景，最后连接小智服务端进行一次端到端请求。
