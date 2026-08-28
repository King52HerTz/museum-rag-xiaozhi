# 阶段 9：马王堆官方资料库与 SuperMew 上游隔离升级

更新时间：2026-08-29

## 本阶段目标

围绕湖南博物院“长沙马王堆汉墓陈列”建立可审计的官方优先资料集，同时把最新
SuperMew 放到独立目录和独立分支中验证，避免直接覆盖当前可用的博物馆 RAG 和小智桥接。

## 已完成内容

### 1. 马王堆资料主库

- 已整理 26 篇 UTF-8 Markdown 资料，主题覆盖展览概览、三座墓葬、T 形帛画、
  黑地彩绘棺、素纱单衣、印花敷彩纱、乘云绣、帛书、漆器、乐器、辛追保护边界、
  展览路线和常见问法。
- 每篇资料都带有标题、展览、分类、别名、整理日期、来源级别和官方来源 URL。
- 新资料只使用湖南博物院官网及其官方子域名公开页面；正文明确标注事实边界，
  不把推测、营销文案或未核验的二手内容写成馆方事实。
- Markdown 主库保存在本机 `rag_test/mawangdui_markdown_2026-08-29`，该目录按仓库策略
  被忽略，不上传文档原件。

### 2. 当前稳定 RAG 的上传验证

- 为兼容当前稳定版只支持的上传格式，已将 26 篇 Markdown 转换为 DOCX，保存在本机
  `rag_test/mawangdui_docx_2026-08-29`。
- 26 个 DOCX 已通过结构检查和渲染检查，没有发现分页溢出、文字裁切或标题层级异常。
- 当前运行中的 RAG 已完成旧资料备份、上传新资料、等待索引、检索抽样和旧资料撤销。
- 目前知识库中是 26 篇马王堆官方资料；替换前的记录保存在本机
  `runtime-logs/corpus-build/before-mawangdui-replacement.json`，不提交到仓库。
- 10 个验收问题均命中预期来源，覆盖 T 形帛画、黑地彩绘棺、素纱单衣、玉、
  半箱式琴、帛书、辛追数字人、展品辨析和参观时长等场景。
- 已额外保存稳定版基线结果（10 题全部通过，平均检索耗时约 919 ms），只包含来源、
  trace 摘要和耗时，不包含 API Key 或回答原文；基线文件位于本机 `runtime-logs/corpus-build`。

### 3. 最新 SuperMew 独立升级副本

- 上游来源：[icey1287/SuperMew](https://github.com/icey1287/SuperMew)。
- 已在 `rag/SuperMew-upstream` 单独 clone，当前上游快照为
  `23f8f14970954d50ab5c3f7af97919935cccde4d`。
- 已创建独立工作分支 `codex/museum-upgrade`；上游 `main` 和当前稳定副本
  `rag/SuperMew-main` 均未被覆盖。
- 已增加 UTF-8 Markdown 的上传校验、解析、索引和文档类型显示，保持 PDF、DOCX、
  Excel 等已有格式兼容。
- 该改动已提交为 `3e90d6e feat(museum): support native markdown corpus uploads`。

## 验证结果

- 新增 Markdown/上传安全测试：3 项通过。
- 稳定兼容性测试：24 项通过，1 项按平台条件跳过。
- 新版后端 `compileall` 和变更文件 `ruff` 检查通过。
- 新版完整测试集在 Windows 收集阶段受 POSIX 专用依赖限制，涉及
  `O_DIRECTORY`、`O_NOFOLLOW` 和 `resource`；这不是资料或桥接代码失败，
  也没有因此修改稳定版代码。

### 本轮隔离运行对比（2026-08-29）

- 已临时停止稳定版 RAG 的 API 和 Docker 依赖，使用独立的升级版 Compose 资源进行验证；
  验证完成后已恢复稳定版依赖和 API，稳定版没有改动数据。
- 隔离 Milvus 首次启动因 MinIO 凭据未映射而以 134 退出；只在升级分支补齐
  `MINIO_ACCESS_KEY_ID` / `MINIO_SECRET_ACCESS_KEY` 映射后重启，未删除隔离卷。
- `scripts.smoke_milvus_compat` 已对真实隔离 Milvus 完成写入、版本精确校验、稠密检索、
  混合检索、租户过滤和按版本删除：写入 3 条、删除 2 条，稠密和混合检索首条均为
  `chunk-alpha`，跨租户记录保持隔离。
- 新版完整 API 在 Windows 导入阶段被上游 Skill Registry 对
  `O_DIRECTORY` / `O_NOFOLLOW` 的 POSIX 安全文件要求阻断，因此本轮没有向升级版导入
  26 篇资料，也没有宣称完成新版端到端 RAG 对比。稳定版恢复后 `/docs` 返回 200，原有
  10 条验收问题再次全部命中预期来源。

## 当前边界

- 新版 SuperMew 尚未接管现有小智设备链路；设备演示仍使用当前稳定 RAG 桥接。
- 新版隔离 Compose 使用独立容器名、端口、网络和 `volumes-upgrade/` 数据目录，不能与稳定版
  资源混用；隔离卷只保留在本机并被 Git 忽略。
- 新版隔离运行需要单独的 PostgreSQL、Redis、Milvus、上传目录和模型配置；在本机内存紧张
  时不启动第二套 Milvus，避免影响正在运行的演示环境。
- 不把 API Key、数据库密码、JWT Secret、上传资料或运行日志写入 Git。

## 下一阶段

隔离 Compose/环境模板已经在升级分支准备完成，并通过无敏感值的配置校验。后续按资源情况执行：

1. 优先在 WSL/Linux 或上游修复并验证 Windows 文件注册器兼容性后，再启动隔离版 API、索引
   worker 和评估 worker，导入同一套官方资料；不要为了本机试跑而绕过安全校验。
2. 用同一组问题对比稳定版与新版的召回来源、检索状态、耗时和错误行为；当前已完成底层
   Milvus 对比，应用层对比仍待平台条件满足。
3. 只有新版通过回归后，才迁移 `/api/museum/query` 兼容接口和小智桥接；在此之前继续使用
   已恢复的稳定版。

本机已准备好仅用于隔离验证的 Markdown 导入脚本，账号密码通过环境变量读取；它只上传和检查
资料，不提供删除旧资料的操作。

## 来源

- [湖南博物院官网](https://www.hnmuseum.com/)
- [SuperMew 官方仓库](https://github.com/icey1287/SuperMew)
