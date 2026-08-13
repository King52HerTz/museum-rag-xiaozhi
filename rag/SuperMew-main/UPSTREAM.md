# SuperMew 上游同步基线

本目录是博物馆项目中的 SuperMew 集成副本，不是上游仓库的 Git 子模块。
当前保留本项目的“智博导览管理平台”和博物馆检索桥接改动，因此不能直接用上游目录覆盖。

## 上游来源

- 仓库：[icey1287/SuperMew](https://github.com/icey1287/SuperMew)
- 分支：`main`
- 本次审查快照：`f997821db835c9c080accaf1f78c2c4a602fe4b7`
- 快照获取时间：2026-08-13

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
