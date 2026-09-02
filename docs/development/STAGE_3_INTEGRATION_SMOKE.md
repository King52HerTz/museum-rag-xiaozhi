# 阶段 3：真实服务集成回归

更新时间：2026-08-23

## 目标

在不改动硬件工程和用户原始资料的前提下，验证以下演示链路：

```text
湖南省博物馆资料
    -> SuperMew 上传/分块/向量化
    -> 管理端文档列表与检索
    -> 同步/流式聊天
    -> 小智 search_museum_knowledge 插件
```

## 本次运行环境

- SuperMew 后端：`http://127.0.0.1:8000`
- 管理端网页：`http://127.0.0.1:8001/#/museum-knowledge`
- 管理端 API：`http://127.0.0.1:8003/xiaozhi`
- SuperMew Docker 依赖：PostgreSQL、Redis、Milvus、MinIO、etcd 均已启动并显示 healthy。
- 本地知识库资料：10 份湖南省博物馆 / 长沙马王堆汉墓陈列 `.docx` 文档。

真实密钥、密码、虚拟环境、模型文件和上传资料均未写入本阶段文档或 Git。

## 回归结果

### 1. 服务与鉴权

- `check-museum-dev.ps1`：SuperMew、manager-api、manager-web 和管理端 Redis 均为 `UP`。
- `POST /auth/login`：管理员登录成功；`GET /auth/me` 返回管理员角色。
- `GET /documents`：返回 10 份文档，文档画像包含湖南省博物馆和长沙马王堆汉墓陈列。
- 桥接自检：无认证请求得到 401，带正确桥接认证得到 200，trace id 可回传。

### 2. 上传与桥接检索

使用 `rag_test` 中已有的辛追夫人资料走了一次真实 `POST /documents/upload`，结果如下：

- HTTP `200`；
- 叶子分块 1 个、父级分块 2 个；
- 上传后的文档数量仍为 10 份；
- 联调临时增加的分类字段已恢复，未留下测试会话或临时文档。

调用：

```text
POST /api/museum/query
```

问题为“辛追夫人为什么能够千年不腐？”，返回 HTTP `200`、3 个上下文，检索模式为 `hybrid`，结构化文档过滤命中 13 个候选文件名，结果来自辛追夫人、遗体不腐原因和地质环境等资料。

### 3. 管理端聊天

- 同步 `POST /chat`：HTTP `200`，返回基于知识库证据的中文导览回答，返回 `rag_trace`。
- 流式 `POST /chat/stream`：HTTP `200`，收到 `rag_step`、`content`、`trace`、`session_title` 和 `[DONE]`，没有 `error` 事件。
- 使用“它是什么？”做了真实模糊问题验证：模型进行了自然语言澄清，但本次没有进入 RAG 的 `clarify/scope_select` 路由；该边界已记录，不通过改提示词强行制造 HITL 结果。

### 4. 小智插件直连

在小智服务端运行环境中加载 `plugins_func.functions.search_museum_knowledge`，使用当前 `config.yaml` 的插件配置直接调用 SuperMew 桥接接口：

- 返回动作：`Action.REQLLM`；
- 上下文长度大于 0；
- 上下文包含“湖南省博物馆”“辛追”和“博物馆知识库”等关键内容。

这证明“小智插件 -> `/api/museum/query` -> LLM 上下文”链路可用。完整的小智 WebSocket 语音服务和硬件实机链路不在本次启动脚本中，因此本阶段没有宣称已完成设备端端到端验证。

## 自动化验证

在 `museum-rag` 虚拟环境中执行：

```text
python -m unittest discover -s tests -p "test_*.py" -v
Ran 18 tests ... OK

python -m compileall -q backend tests
```

结果：18 个测试全部通过，后端和测试目录编译检查通过。

## 当前结论

阶段 3 已证明管理端、SuperMew RAG、真实资料上传、检索、同步/流式聊天以及小智知识库插件之间的桥接可运行。本阶段没有发现需要凭猜测修改的代码问题。

## 已知边界与下一阶段

1. 完整小智服务端当前依赖管理端配置接口；启动前需要准备本地 `data/.config.yaml`、管理端服务配置和可用模型配置。
2. 本阶段只验证了小智插件的真实 HTTP 调用，没有连接 ESP32 硬件，也没有把官方小智云服务切换到本地服务端。
3. 下一阶段应先补齐本地小智服务端的可复现启动配置，再用一台设备完成“语音提问 -> 插件检索 -> LLM 导览话术 -> 设备播报”验收；同时保留官方服务作为回退方案。
