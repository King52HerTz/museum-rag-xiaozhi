# 阶段 15：马王堆 200 条评测集与真实质量门禁

更新时间：2026-08-30

## 目标

在不影响稳定演示链路的前提下，把马王堆 RAG 的质量验证从 32 条兼容性样本推进到至少 200 条，并为后续真实 live 评测准备可审计的输入。这个阶段先验证“资料、标签和评测程序”是否完整，再决定是否迁移新版 SuperMew 运行时。

## 分支边界

- 稳定运行副本：`rag/SuperMew-main`，本阶段不修改。
- 上游隔离副本：`rag/SuperMew-upstream` 的 `codex/museum-upgrade`，只在这里新增评测资产。
- 个人 Fork：`https://github.com/King52HerTz/SuperMew-museum`，升级分支已推送到该仓库；原作者仓库只用于拉取更新。
- 主项目集成分支：只记录阶段文档和桥接状态，不把上游仓库整体覆盖到 `main`。
- 不修改硬件工程、账号密码、API Key 或本地上传资料。

## 本阶段已完成

### 1. 新增 200 条版本化评测集

文件位于隔离仓库：

```text
evals/rag/mawangdui_annotated_v3.json
```

它保留 v2 的 32 条样本，并新增 21 个问题族、每族 8 个问题，共 200 条：

| 结果语义 | 数量 | 用途 |
| --- | ---: | --- |
| `ANSWERABLE` | 144 | 验证官方资料能否召回并支撑回答 |
| `INSUFFICIENT_EVIDENCE` | 30 | 验证资料不完整时是否明确披露边界 |
| `NO_KNOWLEDGE` | 26 | 验证资料未覆盖时是否拒绝臆测 |

问题覆盖展览结构、发掘与墓主人、漆器、丝织品、帛画、彩棺、简帛、乐器、博戏、身份线索、数字人、名称消歧、保护边界和动态信息等主题。所有 `gold_documents` 均来自 26 个官方优先资料文件名。

### 2. 新增可重复构建脚本和测试

```text
scripts/generate_mawangdui_eval_v3.py
tests/test_museum_eval_v3.py
```

v3 不覆盖 v2。运行构建脚本可以从 v2 重新生成同一份 JSON，测试会检查 200 条数量、三种结果语义比例、26 个资料名覆盖以及构建结果可复现。

## 验证结果

已通过：

```text
evaluate_rag.py validate：200 条样本通过
check_museum_eval_compat.py --min-cases 200：通过
定向评测测试：6 passed
ruff check / ruff format --check：通过
Python 编译检查：通过
```

完整测试套件在 Windows 上仍有上游已有的平台限制：技能注册器需要 `O_DIRECTORY/O_NOFOLLOW`，沙箱测试需要 Unix `resource` 模块。这些错误与本阶段评测资产无关，因此没有修改上游安全实现来绕过它们。

## 真实 live 评测前置条件

当前只完成了离线资产和兼容性门禁，尚未宣称生产 RAG 质量已经通过。运行 live 评测前还需要：

1. 将 26 份官方优先 Markdown 上传到独立测试知识库和独立索引，不使用稳定演示索引。
2. 准备本机私有环境文件，配置可用模型、Embedding、Rerank、PostgreSQL、Milvus 和桥接地址；密钥只放在本机，不进入仓库。
3. 先运行模型配置预检，再以 5—15 秒用例间隔运行 v3 live Adapter，避免把供应商限流误判为检索质量问题。
4. 审查报告中的召回、证据、结果语义、路由和 Provider failure rate，并人工抽检关键文物问题。

建议命令：

```powershell
uv run --no-sync python scripts/check_model_provider_config.py --env-file <本机私有配置文件>
uv run --no-sync python scripts/evaluate_rag.py run `
  --dataset evals/rag/mawangdui_annotated_v3.json `
  --gates evals/rag/live_gates_v1.json `
  --observations .artifacts/rag-eval/mawangdui-v3-live-observations.json `
  --report .artifacts/rag-eval/mawangdui-v3-live-report.json `
  --markdown .artifacts/rag-eval/mawangdui-v3-live-report.md `
  --profile-id local-mawangdui-v3 `
  --index-id <独立索引版本标识> `
  --timeout-seconds 60 `
  --inter-case-delay-seconds 10
```

`<本机私有配置文件>` 和 `<独立索引版本标识>` 仅是占位符，不能直接提交或写入公开文档中的真实值。

## 当前结论

阶段 15 的离线部分已完成：200 条评测集可加载、可复现、资料引用完整，且没有启动模型或向量库。真实 live 评测依赖独立索引和本机模型额度，暂不在没有前置配置时强行运行。

本轮前置检查还确认：本机模型配置预检已经通过，但隔离 Compose 所需的 `MUSEUM_SUPERMEW_UPGRADE_*` 变量尚未填入私有 `.env`，因此没有启动或写入新的数据库、Milvus 和 MinIO 数据。`.env.example` 只提供占位符，不包含真实密码或 API Key。

只有 live 报告和人工抽检达到门禁要求后，才进入下一阶段：从 `SuperMew-upstream` 分批挑选运行时改动，做兼容性迁移和稳定版回归。
