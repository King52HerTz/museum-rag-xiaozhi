# 阶段 14：马王堆评测集扩展与 Windows 兼容性门禁

更新时间：2026-08-30

## 目标

在隔离的 SuperMew 上游升级分支先建立可重复的资料和运行时门禁，再决定是否迁移上游运行时模块。
本阶段不改变当前正在承担设备演示的 `rag/SuperMew-main`。

## 已完成改动

- 隔离仓库 `rag/SuperMew-upstream` 的 `codex/museum-upgrade` 分支新增
  `evals/rag/mawangdui_annotated_v2.json`，保留 v1 并将人工标注扩展到 32 条：
  - 24 条 `ANSWERABLE`；
  - 6 条 `INSUFFICIENT_EVIDENCE`；
  - 2 条 `NO_KNOWLEDGE`。
  新样本覆盖展览空间、家庭叙事、漆器和丝织工艺、简帛、乐器、身份线索、名称混淆及动态信息。
- 新增 `evals/rag/mawangdui_corpus_manifest_v1.json`，只记录 26 个官方优先资料文件名和来源元数据，
  不包含文档正文、上传路径或本地运行数据。
- 新增 `scripts/check_museum_eval_compat.py`，默认检查：
  - 样本数不少于 32，三种结果语义达到最低比例；
  - 关键标签覆盖复杂问题、证据缺口、无知识、安全和近实体场景；
  - 金标准文档必须出现在 corpus manifest 中；
  - 关键拒答样本必须允许保守回答；
  - 离线评测模块导入不能启动 Provider、RAG pipeline 或 Milvus。
- 新增 `tests/test_museum_eval_compat.py`，覆盖通过、缺失文档引用、运行时边界和 CLI 输出脱敏。

## 验证结果

- `check_museum_eval_compat.py`：通过，平台为 Windows，运行时边界无违规导入。
- `evaluate_rag.py validate --dataset evals/rag/mawangdui_annotated_v2.json`：通过，32 条样本。
- 评测/适配器/CLI/门禁定向测试：46 passed。
- `ruff check`、`ruff format --check`、评测模块 `compileall`：通过。
- 本阶段暂存内容敏感值样式扫描：0 条匹配。

## 使用方式

在隔离仓库目录执行：

```powershell
uv run --no-sync python scripts/check_museum_eval_compat.py
```

输出只包含样本统计、标签统计、平台和错误码，不打印 API Key、模型地址或文档正文。

## 安全与边界

- 本阶段没有运行 live 模型评测，不消耗模型额度，也没有修改本地 `.env`。
- v2 评测集暂不替换发布门禁；真实质量仍须把同一批资料上传到独立索引后，用 `run` 生成
  `live_rag` Observation，再审查答案、证据、路由和 Provider failure rate。
- 本阶段没有把隔离上游代码复制到 `rag/SuperMew-main`，没有修改小智插件、硬件或 `main` 分支。

## 提交

隔离分支提交：`4163f1e feat(evaluation): add mawangdui compatibility gate`。

该提交只存在于本地 `rag/SuperMew-upstream`，没有推送到 `icey1287/SuperMew` 上游仓库。

## 下一步

继续按同一标注规范扩展到至少 200 条，再在独立索引和受控模型配额下运行 live 评测；只有质量门禁
通过后，才评估把新版运行时模块分批迁移到当前集成分支。
