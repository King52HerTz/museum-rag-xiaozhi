# 阶段 12：RAG 结果可核验面板

更新时间：2026-08-30

## 目标

让管理端聊天记录直接展示本轮是否真正使用了知识库、检索结果是否足够、
是否发生检索降级，以及复杂问题有哪些证据覆盖缺口，减少只看最终回答造成的误判。

## 已完成改动

- `frontend/src/types/chat.ts`：补齐 `retrieval_outcome`、`retrieval_status`、`route`、
  `retrieval_degraded_code`、`provider_error_code` 和 coverage gap 字段。
- `frontend/src/components/Chat/RetrievalTraceDetails.vue`：在“检索过程”中显示 RAG 结果
  的中文说明、检索状态、最终路由、降级/Provider 错误码和未覆盖子问题。
- 仅消费后端已有 `rag_trace` 字段，不改变问答、检索、桥接和设备协议。

## 验证结果

- 前端 `npm run build`：通过；仅有既有 bundle 体积提示。
- 本批暂存内容敏感值样式扫描：0 条匹配。

## 提交

代码提交：`59b8364 feat(frontend): surface rag outcomes`。

## 下一步

在隔离的 SuperMew 上游分支扩展马王堆人工标注集和评测门禁，先验证答案/证据质量，
再决定是否迁移上游运行时模块；稳定版继续承担当前小智设备演示。
