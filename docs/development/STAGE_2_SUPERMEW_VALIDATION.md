# 阶段 2：SuperMew 升级验证门禁

更新时间：2026-08-22

## 本阶段决定

本阶段没有直接用官方快照覆盖当前 SuperMew。代码审计显示，两者不是简单的小版本差异：

- 官方 `backend/rag/pipeline.py` 约 1032 行，当前集成版本约 688 行；
- 官方 `backend/chat/service.py` 约 705 行，当前集成版本约 282 行；
- 官方版本已经加入 HITL、证据评分、恢复检索和新的重写协议；
- 当前版本保留了博物馆结构化过滤、桥接接口、请求级上下文和兼容 trace；
- `backend/api/routes/documents.py` 还包含本地博物馆文档画像和批量编辑逻辑，不能被官方文件直接覆盖。

因此，SuperMew 核心升级必须以 `pipeline + utils + chat service + schema` 为一个兼容批次迁移，不能逐文件复制。

## 已完成的升级保护层

在 `museum-rag/tests/test_museum_bridge_contract.py` 增加了不依赖 Milvus、Redis、PostgreSQL 或模型服务的回归测试，覆盖：

- docx、pdf、Excel 以及现有 HTML 文档扩展名校验；
- 博物馆检索请求默认值和 `top_k` 边界；
- 博物馆、展览、展品、时代、类别到检索查询的转换；
- Milvus 文件名过滤表达式的引号和反斜杠转义；
- 桥接接口返回检索证据和结构化过滤 trace；
- 结构化过滤无结果时回退到语义检索；
- 空结果返回，不伪造上下文。

测试目录已经从 SuperMew 的忽略规则中明确放行，但仍排除 `__pycache__` 和 `.pyc`。

## 验证结果

使用项目虚拟环境运行：

```text
python -m unittest discover -s tests -p "test_*.py" -v
Ran 7 tests ... OK
```

同时完成：

```text
python -m compileall -q backend tests
git diff --check
```

没有修改小智服务端、管理端和硬件代码，也没有把 HITL 草稿纳入本阶段提交。

## 下一批实现边界

下一批仍属于 SuperMew 阶段，名称建议为 `stage-2b-supermew-core-upgrade`，必须在独立升级分支完成：

1. 迁移官方 `backend/rag/utils.py` 的重写协议，同时保留博物馆 `filter_expr` 和 `trace_context`；
2. 迁移官方 `backend/rag/pipeline.py` 的证据评分和 HITL 状态，同时保留请求级 `ChatRequestContext`；
3. 迁移 `backend/chat/service.py` 的同步/流式 HITL 事件；
4. 将 `/api/museum/query` 的响应字段映射到新 trace，不改变管理端和小智插件的基础响应结构；
5. 运行本阶段 7 个桥接测试，再增加上游 RAG 测试和真实上传回归；
6. 只有通过后才提交并进入小智服务端升级阶段。

在 `stage-2b` 完成前，当前稳定演示链路继续使用现有 SuperMew 版本，不进行生产切换。
