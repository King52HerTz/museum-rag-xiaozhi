# 阶段 16：隔离环境真实 RAG 评测

更新时间：2026-08-30

## 本阶段目标

阶段 15 已完成马王堆 200 条离线评测集和兼容性门禁。本阶段不再扩展分支，而是在现有
SuperMew Fork 的 `codex/museum-upgrade` 上准备一次可复现的真实评测，确认“资料上传 →
Document Version/IndexManifest → 检索 → Evidence → 评测报告”的链路确实使用了隔离知识库。

## 分支边界

- 稳定演示：根项目 `main` 和 `museum-rag`，本阶段不修改。
- 集成文档：根项目当前 `codex/sync-supermew-upstream-20260830`，只记录阶段状态。
- SuperMew 升级验证：`rag/SuperMew-upstream` 的 `codex/museum-upgrade`，推送目标是个人 Fork
  `King52HerTz/SuperMew-museum`。
- 原作者 `icey1287/SuperMew` 只作为 `upstream` 拉取源，当前推送地址已禁用。
- 本阶段不创建新的 `codex/stage16-*` 分支，不修改硬件工程，不接触真实密钥和本地上传资料。

## 已完成的开发准备

在隔离 SuperMew 分支新增：

- `scripts/check_museum_live_readiness.py`：只读检查私有配置是否指向隔离 PostgreSQL/Redis/Milvus、
  模型必需变量、隔离 Compose、200 条评测集、资料清单和 IndexManifest 身份；不会启动服务、
  调用模型或打印密钥。
- `tests/test_museum_live_readiness.py`：覆盖完整就绪、稳定端口/默认 collection 拒绝以及未发布
  index 身份阻断。
- `docs/runbooks/museum-live-evaluation.md`：从私有配置、隔离容器、资料发布、live 评测到清理
  的可执行手册。

本阶段代码验证：

```text
tests/test_museum_live_readiness.py
tests/test_museum_eval_compat.py
tests/test_museum_eval_v3.py
共 9 项通过
```

## 待用户在本机完成的前置条件

1. 创建不提交的 `.env.museum-live`，填写隔离数据库、MinIO、Milvus、模型和 Embedding 配置；
2. 准备 manifest 中列出的 26 份官方优先 Markdown 资料；
3. 启动隔离 Compose，并在升级管理端上传资料，等待全部 Index Job 为 `READY`；
4. 记录本次发布的 IndexManifest/collection 身份。

配置完成后，先执行：

```powershell
cd rag/SuperMew-upstream
uv run --no-sync python scripts/check_museum_live_readiness.py `
  --env-file .env.museum-live `
  --corpus-dir <资料目录> `
  --profile-id local-mawangdui-v3 `
  --index-id <隔离索引身份>
```

所有检查必须为“通过”后，再按隔离副本中的
`rag/SuperMew-upstream/docs/runbooks/museum-live-evaluation.md` 执行 200 条 live 评测和人工抽检。

## 通过标准和下一步

报告必须使用 `live_rag` provenance，且满足 `evals/rag/live_gates_v1.json`；人工抽检要能确认
关键文物问题的 Evidence 来自本次隔离索引。没有满足这些条件时，不把升级分支合并到根项目
`main`，也不替换当前稳定服务。

通过后，阶段 17 才评估从上游新版运行时中挑选必要改动，逐批迁移到稳定副本并运行小智桥接和
设备回归。未通过时只修复资料、索引或配置问题，不通过降低门禁阈值“变绿”。
