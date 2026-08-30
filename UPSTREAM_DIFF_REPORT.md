# 阶段 1：上游来源与本地差异审计

更新时间：2026-08-30

## 2026-08-30 复核结果

本次已成功获取作者仓库 `main` 的最新本地引用：
`23f8f14970954d50ab5c3f7af97919935cccde4d`（提交时间 2026-08-28）。
与上游工作副本对比时排除了虚拟环境、缓存、模型、数据库卷、运行数据和本地密钥文件。

当前运行副本 `rag/SuperMew-main` 与 `rag/SuperMew-upstream` 的纯官方基线分支
`codex/supermew-upstream-20260830` 的过滤后文件统计如下：

- 当前副本受 Git 控制的文件：100 个；官方基线：485 个；
- 同路径文件：71 个，内容全部不同；
- 当前副本独有：29 个；官方基线新增：414 个。

这说明两者不是同一代码版本，不能通过整体复制完成同步。可在 Windows 上运行的 RAG、桥接、
文档加载、Provider 和结构化输出测试为 53 passed、10 个子测试通过；上游完整测试仍需要
Linux 的 `O_DIRECTORY`、`O_NOFOLLOW` 和 `resource` 支持。

当前同步分支已完成两批兼容迁移：稳定检索结果语义和证据上下文预算。运行副本的完整测试为
24 passed、11 个子测试通过；管理端上传、博物馆检索桥接和小智设备协议均未被替换。

随后完成第三批结果消费语义迁移：知识库工具会向 Agent 标记无知识、证据不足或部分证据，
并保留 coverage gap 追踪字段；完整测试更新为 27 passed、11 个子测试通过。

第四批补充复杂问题的子问题覆盖度追踪：合成结果会列出未覆盖的子问题并保留已命中的证据，
完整测试更新为 28 passed、11 个子测试通过。

第五批补充检索降级分类：embedding、向量库和混合检索回退都会留下可审计的安全错误码，
完整测试更新为 31 passed、11 个子测试通过。

## 初次审计记录（2026-08-13）

以下内容保留首次 ZIP/快照审计时的来源和边界，作为历史记录；本文件顶部的
2026-08-30 复核结果才是当前同步分支使用的基线。

## 审计范围

本报告只比较可追溯的代码文件和配置模板，不把虚拟环境、模型、数据库卷、缓存、上传资料和日志当成源码差异。

当前仓库仍然是一个总仓库，`rag/SuperMew-main` 和 `xiaozhi-esp32-server-main` 目录本身没有独立的 `.git` 历史。因此本报告的“本地改动”指：当前总仓库中相对保存的上游快照或用户 ZIP 的文件差异，不等同于某个独立 fork 的 commit 差异。

## 来源记录

| 组件 | 来源 | 本次可验证版本 | 备注 |
| --- | --- | --- | --- |
| SuperMew | `https://github.com/icey1287/SuperMew.git` | `f997821db835c9c080accaf1f78c2c4a602fe4b7` | 已保存官方快照并用于代码级比较 |
| 小智服务端 | `https://github.com/xinnan-tech/xiaozhi-esp32-server.git` | `17560a7d295a0a7f3e46add30bb584d486b651c3` | 远端 HEAD 记录已验证；当前环境未能完成 Git Clone |
| 小智本地 ZIP | 用户提供的 `xiaozhi-esp32-server-main.zip` | ZIP 内部版本未建立 Git commit | 只能作为旧快照参考，不能作为最新上游 |
| 硬件 | `yingjian/SmartRing-Plus-main` | 固定版本 | 本次审计和后续软件升级均排除 |

## SuperMew 审计结果

当前总仓库中有 95 个被 Git 跟踪的 SuperMew 文件。与已经保存的官方快照比较：

- 57 个同路径文件内容不同；
- 12 个文件只存在于本地集成副本；
- 官方快照包含 1 个当前本地没有的新增文件：`docker-compose.prod.yml`；
- 差异不能全部视为博物馆修改，其中一部分来自当前 ZIP 快照与官方 commit 的版本差异。

### 明确属于本地博物馆适配层的文件

- `backend/api/routes/museum.py`
- `backend/indexing/document_profile_store.py`
- `backend/infra/auth.py` 中的桥接鉴权扩展
- `backend/app.py` 中的品牌、桥接异常处理和 trace 处理
- `backend/api/router.py` 中的博物馆路由挂载
- 前端文档元数据筛选和批量编辑相关组件
- `scripts/document_profile_overrides.*`
- `UPSTREAM.md`

### 与上游高耦合、必须成批迁移的文件

以下文件不是普通的“复制覆盖”范围，后续升级时必须先阅读上游变化，再逐项迁移：

- `backend/chat/request_context.py`
- `backend/chat/runtime.py`
- `backend/chat/service.py`
- `backend/chat/storage.py`
- `backend/chat/streaming.py`
- `backend/rag/pipeline.py`
- `backend/rag/utils.py`
- `backend/schemas/chat.py`
- `backend/tools/knowledge.py`

当前工作区对其中 3 个文件还有未提交的 HITL 实验改动。它们不属于阶段 1 审计提交，也不应在上游升级前继续扩展。

## 小智审计结果

当前总仓库中有 830 个被 Git 跟踪的小智文件。与用户保存的旧 ZIP 快照比较：

- 8 个同路径文件内容不同；
- 11 个文件只存在于当前本地项目；
- 这 11 个本地文件主要是博物馆桥接功能和配置，不是上游缺失造成的异常；
- 用户 ZIP 没有 Git commit 信息，因此不能用它判断当前官方最新版本。

### 明确属于本地博物馆适配层的文件

- `main/manager-api/src/main/java/xiaozhi/modules/museum/controller/MuseumRagController.java`
- `main/manager-api/src/main/java/xiaozhi/modules/museum/service/MuseumRagService.java`
- `main/manager-api/src/main/resources/application-local.template.yml`
- `main/manager-api/src/main/resources/application-prod.yml`
- `main/manager-api/src/main/resources/db/changelog/202606282050.sql`
- `main/manager-api/src/main/resources/db/changelog/202607011955.sql`
- `main/manager-api/src/main/resources/db/changelog/202607012030.sql`
- `main/manager-web/src/apis/module/museumRag.js`
- `main/manager-web/src/views/MuseumKnowledge.vue`
- `main/xiaozhi-server/data/.config.yaml.example`
- `main/xiaozhi-server/plugins_func/functions/search_museum_knowledge.py`

### 需要谨慎保留的共享文件

当前与旧 ZIP 不同的共享文件包括：

- `main/manager-api/src/main/resources/application.yml`
- `main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml`
- `main/manager-web/src/apis/api.js`
- `main/manager-web/src/apis/httpRequest.js`
- `main/manager-web/src/components/HeaderBar.vue`
- `main/manager-web/src/router/index.js`
- `main/manager-web/vue.config.js`
- 根目录 `.gitignore`

这些文件可能同时包含原项目升级和本地品牌改造，不能直接从官方版本覆盖。

## 当前阻塞

本阶段尝试从 GitHub Clone 两个官方仓库时，网络连接被远端重置。为避免误判，当前没有用失败的 Clone 结果覆盖任何项目文件，也没有把 ZIP 当成最新上游。

阶段 1 因此分为两部分：

1. 本地快照、文件边界和风险已经审计完成；
2. 正式建立两个独立 Git 上游工作副本，待网络或 GitHub Desktop 可用后补齐。

## 下一步

阶段 2 只升级 SuperMew，顺序固定为：

1. 获取官方 Git 工作副本；
2. 先验证官方原始上传和问答；
3. 建立博物馆扩展补丁清单；
4. 逐项迁移 `/api/museum/query`、元数据和桥接鉴权；
5. 运行 docx、pdf、Excel、结构化筛选和回归问题集；
6. 通过后才进入小智升级。

在阶段 2 之前，不覆盖当前 `rag/SuperMew-main`，不修改小智核心，不修改硬件。
