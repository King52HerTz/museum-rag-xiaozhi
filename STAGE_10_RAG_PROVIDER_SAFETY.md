# 阶段 10：RAG 精排 Provider 安全与可观测性

更新时间：2026-08-30

## 目标

收口精排服务的错误边界，使 RAG 追踪、管理端和小智桥接只看到稳定错误码，
不把供应商原始响应或请求信息写入返回结果；精排不可用时继续使用已有召回结果。

## 已完成改动

- `backend/rag/utils.py`：精排 HTTP 错误、请求异常和空结果统一转换为安全错误码，
  不再保存响应正文；保留原有召回结果作为回退。
- `backend/infra/provider_errors.py`：补充 400/422 请求错误和 500 服务错误的统一分类。
- `backend/schemas/chat.py`：追踪新增 `rerank_error_code`、`rerank_retryable` 字段，
  兼容历史 `rerank_error` 字段。
- `frontend/src/components/Chat/RetrievalTraceDetails.vue`：在检索过程面板显示精排错误码
  和是否可重试，便于定位而不暴露供应商详情。
- 新增精排限流、空响应、追踪规范化回归用例；测试凭据只使用明显的虚假占位值。

## 验证结果

- 后端完整测试：37 passed、11 个子测试通过。
- `python -m compileall -q backend tests`：通过。
- 前端 `npm run build`：通过；仅有既有的 bundle 体积提示。
- 暂存内容敏感值样式扫描：0 条匹配。

## 提交

代码提交：`b08d53c feat(rag): redact rerank provider failures`。

## 边界与下一步

本阶段没有修改模型配置、API Key、密码、上传资料、设备固件或小智核心协议。
下一阶段继续在隔离的 SuperMew 上游分支扩展人工标注评测集，并在通过同一回归门禁后
再评估是否迁移上游运行时模块；稳定版仍作为当前设备演示版本。
