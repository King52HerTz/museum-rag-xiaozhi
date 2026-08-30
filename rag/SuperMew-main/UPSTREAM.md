# SuperMew 上游同步基线

本目录是博物馆项目中的 SuperMew 集成副本，不是上游仓库的 Git 子模块。
当前保留本项目的“智博导览管理平台”和博物馆检索桥接改动，因此不能直接用上游目录覆盖。

## 上游来源

- 仓库：[icey1287/SuperMew](https://github.com/icey1287/SuperMew)
- 分支：`main`
- 本次审查快照：`f997821db835c9c080accaf1f78c2c4a602fe4b7`
- 快照获取时间：2026-08-13

## 2026-08-30 同步审计

- 已从当前可运行版本创建独立同步分支：`codex/sync-supermew-upstream-20260830`。
- 已在独立 clone 中建立纯官方基线分支：`codex/supermew-upstream-20260830`；此前的
  `codex/museum-upgrade` 本地实验提交继续单独保留。
- 本次已成功更新 `rag/SuperMew-upstream` 的远程引用；`upstream/main` 当前为
  `23f8f14970954d50ab5c3f7af97919935cccde4d`（提交时间 2026-08-28）。
- 此前的连接重置已恢复，但仍以本次成功 fetch 的提交作为迁移基线，不把未验证的远程状态写入运行副本。
- 当前运行副本 `SuperMew-main` 与纯官方基线的核心 `pipeline.py`、`utils.py` 存在较大差异，
  两者目前不能视为已同步。
- 在获取最新上游并完成差异审查、回归测试前，不将同步分支合并到主分支。

### 本次差异与测试结果

- 过滤环境目录、缓存、模型和运行数据后，当前副本有 100 个受控文件，官方基线有 485 个；
  71 个同名文件内容不同，当前副本独有 29 个文件，官方基线新增 414 个文件。
- 上游完整测试套件在 Windows 上无法收集：其技能注册表要求 Linux 的
  `O_DIRECTORY`/`O_NOFOLLOW`，沙箱测试还依赖 Unix `resource` 模块。
- 可在本机运行的 RAG、桥接、文档加载、Provider 和结构化输出测试结果为：53 passed、10 个子测试通过。
- 因此下一批迁移必须按模块边界进行，不能把上游目录整体复制到 `SuperMew-main`。
- 第一批结果语义迁移已完成：新增 `RetrievalOutcome` 及缺口提示工具，并将结果写入兼容的
  `rag_trace.retrieval_outcome` 字段；未替换检索流程、桥接响应或小智插件协议。该批次提交为
  `e59cde2 feat(rag): expose stable retrieval outcomes`，当前稳定副本测试为 21 passed、11 个子测试通过。
- 第二批证据上下文预算迁移已完成：评分器使用独立的紧凑证据包，回答 Agent 使用有上限且
  引用编号稳定的证据包；发生省略或截断时记录计数并提示回答仅使用已展示片段。该批次提交为
  `aeb5bd8 feat(rag): bound evidence context`，没有改变上传、`/api/museum/query` 或设备协议，
  当前稳定副本测试为 24 passed、11 个子测试通过。
- 第三批结果消费语义迁移已完成：知识库工具现在明确区分 `NO_KNOWLEDGE`、
  `INSUFFICIENT_EVIDENCE` 和 `PARTIAL_EVIDENCE`，并在系统提示中要求 Agent 只回答已有证据；
  兼容追踪保留 coverage gap 字段。该批次提交为 `d8aeb14 feat(rag): surface retrieval evidence outcomes`，
  当前稳定副本测试为 27 passed、11 个子测试通过。
- 第四批复杂问题覆盖度迁移已完成：合成阶段会把未回答的子问题记录为
  `coverage_gap_questions`，同时保留已召回片段并标记 `INSUFFICIENT_EVIDENCE`；完整测试为
  28 passed、11 个子测试通过。该批次提交为 `478726c feat(rag): track synthesis coverage gaps`。
- 第五批检索降级语义迁移已完成：embedding 不可用、向量库不可用和混合检索降级会写入安全
  错误码；无证据时标记 `INSUFFICIENT_EVIDENCE`，不再误报为知识库没有答案。该批次提交为
  `dbf9008 feat(rag): classify retrieval degradation`，完整测试为 31 passed、11 个子测试通过。

## 本地必须保留的功能

以下内容属于博物馆项目的本地集成，不应在同步时被上游版本覆盖：

- `backend/api/routes/museum.py`：智博导览检索型接口；
- `backend/infra/auth.py`、`backend/api/routes/auth.py`：桥接鉴权与单点登录；
- `backend/app.py`、`backend/api/router.py`：博物馆品牌、桥接错误处理和路由挂载；
- `backend/indexing/document_profile_store.py` 及文档路由/模型/Schema 中的博物馆元数据；
- 前端的智博导览品牌、文档元数据筛选和批量编辑页面；
- 与上述功能配套的 `.env.example` 配置项。

## 同步策略

1. 先在主仓库创建备份标签，再在仓库外获取上游快照；
2. 先生成新增、删除和同名文件差异清单；
3. 只引入经过兼容性检查的新增文件或小范围改动；
4. `backend/chat/service.py`、`backend/chat/runtime.py`、`backend/rag/pipeline.py`、
   `backend/rag/utils.py`、`backend/schemas/chat.py` 等上游耦合模块必须作为一个迁移批次处理，
   不允许单文件覆盖；
5. 每个批次完成后运行后端语法检查和前端构建，再提交并由 GitHub Desktop 推送。

## 当前状态

本次已在保留现有桥接代码的前提下迁移上游的请求级上下文基础：

- 每次同步/流式问答使用独立的 `ChatRequestContext`；
- RAG 追踪、步骤事件和知识工具调用次数按请求隔离；
- 保留旧版全局工具作为兼容入口，博物馆检索接口不变。

HITL、请求级 Agent 全量重构以及新版 RAG 流程仍需作为后续完整迁移批次处理。

第三阶段已增加兼容 Schema 和规范化函数：新旧 RAG trace 字段可以共存，历史数据中的未知字段会被忽略，
追踪写入会过滤无效片段；HITL 状态只完成数据结构兼容，尚未改变现有对话交互。
