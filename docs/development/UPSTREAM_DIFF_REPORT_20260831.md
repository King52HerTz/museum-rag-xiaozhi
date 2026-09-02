# SuperMew 稳定版与最新版差异报告

更新时间：2026-08-31  
对比目的：判断作者最新版是否可以直接替换当前博物馆 RAG 稳定版，以及升级会对小智桥接、知识库资料和管理端造成什么影响。

## 1. 对比范围

本报告把两个“最新版”分开说明：

| 对象 | 本地位置/引用 | 说明 |
| --- | --- | --- |
| 当前稳定版 | `museum-rag` | 根项目中的现有博物馆集成副本，包含智博导览桥接和管理端配套改动 |
| 作者官方最新版 | `rag/SuperMew-upstream` 的 `upstream/main`，`bb02719` | 2026-08-30 从 `icey1287/SuperMew` 读取的最新 `main` |
| 个人升级测试版 | `rag/SuperMew-upstream` 的 `codex/museum-upgrade`，`d6ad05e` | 以作者最新版为基线，叠加本项目的桥接、马王堆评测和隔离运行适配；推送目标是个人 Fork，不是作者仓库 |

统计使用 Git 跟踪文件，不包含模型、虚拟环境、缓存、上传资料和运行日志。

| 目录 | 稳定版 | 作者官方最新版 |
| --- | ---: | ---: |
| 全部跟踪文件 | 107 | 498 |
| `backend/` | 49 | 169 |
| `frontend/` | 36 | 111 |
| `tests/` | 8 | 107 |
| `scripts/` | 3 | 11 |

同名文件 75 个，内容均有差异；稳定版独有 32 个文件，官方最新版新增 423 个文件。数量差异主要来自运行时、数据库迁移、Worker、能力控制、评测和前端工作台的新增，不代表 423 个文件都需要迁移。

## 2. 结论先行

作者最新版功能和工程治理明显更完整，但不能直接覆盖当前稳定版，原因不是单一的代码冲突，而是以下三个边界同时发生变化：

1. **接口边界变化**：官方最新版移除了旧的 `/chat`、`/chat/stream`、`/sessions`，也没有本项目使用的 `/api/museum/query`。
2. **数据边界变化**：从简单的文档表和父块存储升级为 Knowledge Base、Document、Document Version、Index Job、Manifest 和发布/清理队列。
3. **运行边界变化**：最新版的 Skill Registry 要求 Linux 的安全文件访问能力，Windows 进程会在启动阶段被拒绝。

个人升级测试版已经补回了 `/api/museum/query`，但它仍然使用最新版的 Thread/Run、Document Version 和租户/知识库作用域，不能直接读取稳定版已有的文档索引并保证结果一致。

**建议：保留稳定版作为演示版本，把个人升级测试版作为独立升级线；先完成 Linux 隔离验证和资料重建，再逐批迁移。不要整体覆盖 `museum-rag`。**

## 3. 后端架构差异

### 3.1 HTTP 接口和执行模型

稳定版的主要入口位于 `museum-rag/backend/api/routes/`：

- `POST /chat`：非流式聊天；
- `POST /chat/stream`：SSE 流式聊天；
- `/sessions`：会话历史；
- `/documents/upload` 和 `/documents/upload/async`：文档上传；
- `POST /api/museum/query`：给小智服务端返回检索片段的轻量桥接接口。

作者官方最新版的路由聚合位于 `rag/SuperMew-upstream/backend/api/router.py`，主要变为：

- `POST /v1/threads`：创建持久化 Thread；
- `POST /v1/threads/{thread_id}/runs`：创建一次可恢复 Run；
- `/v1/runs/{run_id}/events` 和 `/v1/runs/{run_id}/stream`：读取或订阅持久化 Event；
- `/v1/models`、`/v1/capabilities`：模型和能力控制面；
- `/v1/rag-evaluations/*`：评测 Dataset、Job 和 Case；
- `/documents/upload/async`：只保留异步、持久化索引任务。

官方最新版 README 明确说明旧 `/chat`、`/chat/stream`、`/sessions` 兼容入口已经移除。个人升级分支只额外挂载了 `backend/api/routes/museum.py`，没有恢复旧聊天接口。

### 3.2 Agent、Run 和事件

稳定版把 Agent、RAG 工具和 SSE 输出放在 `backend/chat/`，一次请求的状态主要在进程内维护。

最新版新增：

- `backend/threads/`：Thread 生命周期和版本；
- `backend/runs/`：Run 创建、租约、取消、恢复和执行；
- `backend/events/`：Event Journal、Outbox、Redis 投影和 SSE；
- `backend/agent/`：运行时、上下文、记忆和中间件；
- `backend/rag/checkpoint_runner.py`、`checkpointing.py`：可暂停/恢复的 RAG 图。

因此最新版可以处理断线重连、真正取消、HITL 人工补充和事件重放；但小智服务端当前的插件协议是一次请求拿到 `contexts`，要接入最新版需要保留一个稳定的桥接适配层。

### 3.3 鉴权和安全

稳定版主要是 JWT Access Token、管理员角色和本地桥接密钥/单点登录。

最新版新增或拆分了：

- HttpOnly Refresh Token、轮换、撤销和重放检测；
- 登录入口 Origin 检查和请求体限制；
- 入口限流、HMAC 身份和 Redis/内存限流适配器；
- 全局安全响应头、CORS 白名单和上传安全检查；
- Skill/Tool Registry、Guardrail 和 Sandbox 权限边界。

稳定版 `backend/app.py` 还包含 Windows 下的 `os.symlink` 兼容替代逻辑；最新版删除了这类替代，并在 `backend/skills/registry.py` 强制检查 `O_DIRECTORY`/`O_NOFOLLOW`。这就是最新版在 Windows 启动时报错的直接原因。

## 4. 知识库、数据库和向量索引差异

### 4.1 稳定版数据模型

稳定版 `backend/db/models.py` 主要使用：

- `users`；
- `chat_sessions`、`chat_messages`；
- `parent_chunks`；
- `document_profiles`。

数据库初始化使用 `Base.metadata.create_all()`。文档上传后直接写入上传目录、PostgreSQL 父块和 Milvus 集合，覆盖同名文件时清理旧数据。

### 4.2 最新版数据模型

最新版使用 Alembic 迁移，当前官方 `main` 包含 18 个迁移（`0001` 至 `0018`），新增：

- `threads`、`messages`、`runs`、`run_events`、`run_checkpoints`；
- `refresh_tokens`；
- `model_profiles`、`model_assignments`；
- `knowledge_bases`、`documents`、`document_versions`；
- `index_jobs`、`index_manifests`、`document_cleanup_jobs`、`document_retirement_jobs`；
- `worker_heartbeats`、`transaction_outbox`、`tool_audits`；
- RAG Evaluation Dataset/Job/Case 表和能力控制表。

文档入库流程变成：

```text
上传 source object
  → 创建 Document Version / Index Job
  → 在 candidate scope 构建向量和父块
  → 校验 exact manifest
  → PostgreSQL CAS 切换 current_version_id
  → 后台清理旧版本
```

这带来“新版本构建失败不污染当前版本”的能力，但也意味着：

- 稳定版的 `document_profiles` 不会自动变成最新版的文档 Catalog；
- 稳定版已有文件需要重新登记、重新分块和重新向量化；
- 不能让两个版本共用同一个 Milvus collection 或上传目录；
- 不能把稳定版数据库直接指向最新版而不做备份和迁移演练。

### 4.3 检索差异

两版都保留 Dense + Milvus 原生 BM25、RRF、三级分块、Auto-merging 和可选 Rerank，因此核心 RAG 思路是一致的。

最新版在此基础上增加：

- `tenant_id`、`knowledge_base_id`、`document_version_id` 的过滤；
- candidate collection 和版本作用域；
- Provider Runtime、超时、重试和失败分类；
- 运行时模型快照；
- 对部分召回、无知识和 Provider 故障的明确事件和 trace。

稳定版的博物馆接口按 `museum/exhibition/exhibit_id/era/category` 使用 `document_profiles` 做文件过滤；个人升级分支由于最新版 Catalog 尚未持有这套旧画像，改为把业务上下文放进语义查询，并使用租户/知识库作用域。这会影响同名文物过滤的精确性，必须通过重新上传的官方资料和评测验证。

## 5. 小智桥接的直接影响

当前小智插件和管理端服务调用的是：

```text
POST /api/museum/query
Authorization: Bearer <桥接密钥>
```

对应代码包括：

- `main/xiaozhi-server/plugins_func/functions/search_museum_knowledge.py`；
- `main/manager-api/.../MuseumRagService.java`；
- 稳定版 `museum-rag/backend/api/routes/museum.py`。

### 官方最新版的影响

官方 `upstream/main` 没有 `museum.py`、没有 `/api/museum/query`，`.env.example` 也不再提供稳定版的 `BRIDGE_API_KEY`/`BRIDGE_SSO_SECRET`。直接替换后：

- 小智插件请求会得到 404 或桥接鉴权配置错误；
- 管理端的“导览问答测试”无法调用 RAG；
- 即使改成 `/v1/threads`，也需要处理 Run 创建、Event 流和最终消息读取，不是改一个 URL 就能解决。

### 个人升级测试版的影响

个人分支新增了最新版兼容的 `backend/api/routes/museum.py`，保留了：

- `/api/museum/query` 路径；
- `question/museum/exhibition/exhibit_id/era/category/top_k/need_trace` 请求字段；
- `contexts`、`trace`、`error_code` 等桥接响应字段；
- 独立的 `BRIDGE_API_KEY` 服务间鉴权。

但它的检索调用已经切换到最新版的 tenant/knowledge-base/version 作用域，且没有恢复稳定版的 `/chat`、`/sessions`。因此它是“桥接适配版”，不是“稳定版的无损替换版”。

## 6. 前端工作台差异

稳定版前端重点是：

- 博物馆品牌和“智博导览”页面；
- 聊天消息、历史会话和 RAG Thinking Trace；
- 文档上传、元数据编辑和桥接测试。

最新版前端增加或重做了：

- Thread/Run/Event 状态管理和断线重连；
- Model Center；
- Capability Center、Skill/Tool 管理；
- Document Version 的上传、发布和清理状态机；
- RAG Evaluation Workbench；
- Artifact、Guardrail、HITL 和执行时间线。

因此不能只把最新版 `frontend/` 复制进稳定版：API 路径、状态模型、登录刷新机制和页面数据结构都已经改变。个人升级分支的前端仍然是最新版工作台风格，博物馆品牌和现有小智页面需要单独适配。

## 7. 配置和部署差异

稳定版 `.env.example` 约 38 个配置项，主要集中在模型、Milvus、PostgreSQL、Redis、JWT 和桥接。

官方最新版 `.env.example` 约 203 个配置项，新增配置可归纳为：

- 默认租户/知识库和文档版本信息；
- Index/Evaluation/Run Worker 的轮询、租约、心跳和重试；
- Answer/Fast/Grader/Evaluator 四类模型；
- Provider 超时、并发和缓存；
- Refresh Token、限流、Origin、CORS 和安全头；
- Skill、Web Research、只读 SQL 和 Sandbox；
- 上传大小、压缩比、页数和文件路径安全限制。

官方最新版默认 API 端口和前端代理也回到了 `8000` 体系；稳定版当前开发代理使用 `8010`，本地桥接和启动脚本还有自己的端口约定。迁移时必须明确端口表，不能直接复用旧启动脚本。

## 8. 评测和质量门禁差异

稳定版目前有 8 个主要 Python 测试文件，重点验证：

- RAG 结果语义和证据；
- Provider 错误脱敏；
- 博物馆桥接响应契约；
- HITL 兼容行为。

官方最新版有 107 个测试文件，覆盖迁移、Run/Event、认证生命周期、限流、上传安全、版本发布、Provider Runtime、Sandbox、能力控制和前端状态。

个人升级分支在官方评测基础上增加：

- 马王堆人工标注集 v1/v2/v3；
- 200 条马王堆问题；
- corpus manifest 和离线兼容门禁；
- DeepSeek 结构化输出兼容检查；
- 独立 Compose、模型预检和 live readiness 检查。

这部分是个人升级线的优势，但目前只完成了隔离环境准备，尚未证明最新版在本机 Windows 稳定运行，也尚未完成真实资料上传后的 live 评测。

## 9. 兼容性矩阵

| 能力 | 当前稳定版 | 作者官方最新版 | 个人升级测试版 | 判断 |
| --- | --- | --- | --- | --- |
| Windows 直接启动 | 可用 | 启动阶段被安全检查阻断 | 同样需要 Linux/WSL | 高风险 |
| 小智 `search_museum_knowledge` | 可用 | 无 `/api/museum/query` | 已补回接口，待 Linux 验证 | 可迁移但不能直接替换 |
| 管理端导览问答测试 | 调用旧桥接接口 | 接口缺失 | 保留桥接接口，待验证 | 需要回归测试 |
| 旧 `/chat`、`/sessions` 页面 | 可用 | 已移除 | 未恢复 | 前端需适配 |
| 现有上传资料和 Milvus 数据 | 可用 | 需要 Catalog/Version 重建 | 需要重新上传/重建 | 不可直接共用 |
| Dense/BM25/RRF/Auto-merging | 可用 | 保留并加强作用域 | 保留并适配桥接 | 适合选择性迁移 |
| Thread/Run/Event 可恢复执行 | 无 | 有 | 有 | 新能力 |
| 四角色模型控制面 | 无 | 有 | 有 | 需要新配置和管理流程 |
| RAG 评测工作台 | 基础/外部脚本 | 完整 | 完整并增加马王堆集 | 新能力 |
| 稳定版博物馆元数据过滤 | 有 | 无旧画像机制 | 当前改为语义上下文 | 需要重新设计 |

## 10. 风险分级

### 红色：不能直接做

- 整体复制作者最新版覆盖 `museum-rag`；
- 让稳定版和最新版共用 PostgreSQL、Milvus collection 或上传目录；
- 只修改小智插件 URL，不改 Run/Event 和鉴权适配；
- 为了在 Windows 启动而删除最新版的安全文件检查。

### 黄色：需要迁移和验证

- 稳定版资料重新登记为 Document Version 并重建向量；
- 博物馆字段从旧 `document_profiles` 迁移到知识库/文档元数据；
- 保持 `/api/museum/query` 的响应兼容；
- 管理端登录、模型配置、知识库页面和前端代理适配新版接口；
- 重新执行 200 条马王堆评测和小智设备回归。

### 绿色：适合优先吸收

- Provider 错误分类和脱敏；
- RAG 证据缺口、部分证据和引用追踪；
- 简单属性问题快速路径；
- 版本化评测集、离线门禁和运行就绪检查；
- 不依赖新版数据库的文档加载、检索质量改进。

## 11. 建议的升级顺序

1. **冻结稳定演示线**：继续使用 `museum-rag` 和当前小智桥接，暂不替换。
2. **验证个人升级线**：在 WSL/Linux 中启动 `codex/museum-upgrade`，只使用隔离端口、隔离数据库、隔离 Milvus collection 和隔离上传目录。
3. **重建官方资料**：把马王堆 26 份官方优先 Markdown 资料重新上传到最新版 Catalog，等待 Index Job 发布成功。
4. **完成真实评测**：记录 `index_id`/manifest 身份，执行 200 条问题评测，并人工检查黑地彩绘棺、素纱单衣、T 形帛画等关键文物证据。
5. **做桥接契约回归**：验证小智插件、管理端问答和 RAG 工作台都能收到同一份 `contexts/trace` 语义。
6. **逐批迁移**：先迁移 RAG 结果语义和 Provider 安全，再迁移文档版本和 Run/Event；每批都保留可回退的稳定版本。
7. **最后再考虑合并**：只有在 Linux 运行、资料发布、评测门禁、管理端和硬件回归全部通过后，才考虑把升级线合并到主分支。

## 12. 本次审查后的决定

当前不合并、不覆盖、不推送新的业务代码。稳定版继续作为可演示版本；`SuperMew-upstream/codex/museum-upgrade` 只作为升级候选和实验分支。

作者最新版值得继续研究，但应当把它当作“新一代运行时”来适配，而不是当作稳定版的普通更新。对本项目最重要的工作不是把所有新文件搬过来，而是先确保三件事不被破坏：

1. 小智设备仍能通过 `/api/museum/query` 得到可靠证据；
2. 已审核的湖南省博物馆资料能在新 Catalog 中可追溯、可重建；
3. 任何升级失败都可以回到当前稳定演示线。

