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
- 评测适配器已增加可选的用例间等待参数，并将文本文件换行规范化后再计算 corpus/source
  fingerprint，避免 Windows 的 CRLF 与 Linux 的 LF 造成虚假的基线不一致；该改动已提交为
  `4a447c9 feat(evaluation): pace live model probes`。
- 已按上游新版的 tenant/knowledge-base 目录模型准备方案 B 桥接接口
  `POST /api/museum/query`，只返回检索证据，不在 RAG 服务内生成导览话术；小智插件可以继续
  使用原有 `contexts/source/page_number/trace` 契约。该改动已提交为
  `81f616f feat(museum): prepare upstream retrieval bridge`，仍只存在于隔离升级分支。

## 验证结果

- 新增 Markdown/上传安全测试：3 项通过。
- 稳定兼容性测试：24 项通过，1 项按平台条件跳过。
- 新版后端 `compileall` 和变更文件 `ruff` 检查通过。
- 桥接接口契约测试 8 项通过，覆盖租户/知识库作用域传递、空结果、错误脱敏、Bearer 鉴权、
  参数校验和小智插件兼容响应结构。
- 升级分支新增模型配置预检脚本，只报告缺失、占位和地址格式问题，不打印密钥或发起模型请求；
  预检测试 3 项通过，提交为 `fbdce66 feat(evaluation): add model provider preflight`。
- 预检工具现在支持 `--env-file` 读取另一份本机配置，不需要把稳定副本的 `.env` 或密钥复制到
  升级副本；该改动提交为 `c7402c4 feat(evaluation): allow external env preflight`，新增测试后
  预检与桥接契约共 12 项通过。
- live 评测命令也支持同一个 `--env-file` 参数，并会在加载后端和模型前读取该文件；新增环境
  优先级与缺失文件测试后，升级分支提交为 `25a28af feat(evaluation): reuse external env for live runs`。
- 当前使用现有稳定配置文件做脱敏预检，必需模型配置为 5/5，桥接密钥已配置；`EVALUATION_MODEL`
  仍为可选缺省。该检查没有发起模型请求，也没有复制配置文件。
- 新版完整测试集在 Windows 收集阶段受 POSIX 专用依赖限制，涉及
  `O_DIRECTORY`、`O_NOFOLLOW` 和 `resource`；这不是资料或桥接代码失败，
 也没有因此修改稳定版代码。使用 WSL/Linux 运行完整上游测试后，结果为
 1176 passed、5 skipped、10 failed；失败项集中在未提供测试 JWT Secret、Windows
 换行导致的启动脚本 shebang、以及一项受本机负载影响的事件循环时序断言，均不在本轮
 评测适配器改动范围内；本轮涉及的 27 项评测测试全部通过。

### 本轮隔离运行对比（2026-08-29）

- 已临时停止稳定版 RAG 的 API 进程，使用独立的升级版 Compose 资源进行验证；验证完成后
  已恢复稳定版 API 和依赖，稳定版没有改动数据。
- 隔离 Milvus 首次启动因 MinIO 凭据未映射而以 134 退出；只在升级分支补齐
  `MINIO_ACCESS_KEY_ID` / `MINIO_SECRET_ACCESS_KEY` 映射后重启，未删除隔离卷。
- `scripts.smoke_milvus_compat` 已对真实隔离 Milvus 完成写入、版本精确校验、稠密检索、
  混合检索、租户过滤和按版本删除：写入 3 条、删除 2 条，稠密和混合检索首条均为
  `chunk-alpha`，跨租户记录保持隔离。
- 通过 WSL/Linux 运行升级版 API 和 indexing worker，26 篇 Markdown 均完成解析、向量化、
  发布和 `ready` 校验；升级版目录快照为 26 个当前文档，collection 为
  `embeddings_collection_upgrade_catalog_v1`，索引身份为
  `d495b23715032b06788e106eae5144134538b1f78bd1f896be5c022af0c5d2ac`。
- 用与稳定版相同的 10 个问题执行真实向量检索对比（不把模型生成结果混入检索指标）：
  升级版和稳定版均为 Top-5 命中 10/10、Top-1 命中 7/10。去除首次加载模型的冷启动后，
  升级版平均检索耗时约 339 ms，稳定版约 301 ms；两者运行环境不同，这个差异只作为本机
  参考，不作为上线性能承诺。脱敏结果保存在本机 `runtime-logs/corpus-build` 忽略目录。
- 同批次的应用层 live RAG 评测生成了 10 条 Observation，但外部模型接口出现
  `MODEL_RATE_LIMITED` 和一次超时，导致报告被标记为未通过；该结果只能说明当前模型配额/
  限流条件不足，不能据此否定已经通过的向量召回对比，也不能作为发布质量结论。
- 为排除“连续请求过快”这一因素，随后使用同一隔离索引运行了 2 条应用层探针，并设置
  `--inter-case-delay-seconds 10`；两条仍均返回 `MODEL_RATE_LIMITED`，说明当前阻断更可能是
  模型供应商配置、部署或配额问题，而不是评测用例间隔。脱敏 Observation、Report 和 Markdown
  报告保存在本机 `runtime-logs/corpus-build` 忽略目录，未写入回答原文、密钥或原始异常。
- Windows 直接启动新版 API 仍会在上游 Skill Registry 的
  `O_DIRECTORY` / `O_NOFOLLOW` POSIX 安全文件要求处阻断，因此采用 WSL/Linux 完成了本轮
  导入和检索验证，没有为了本机试跑而绕过安全校验。稳定版恢复后 `/docs` 返回 200，原有
  10 条验收问题再次全部命中预期来源。

## 当前边界

- 新版 SuperMew 尚未接管现有小智设备链路；设备演示仍使用当前稳定 RAG 桥接。
- 新版已经在隔离库完成同批 26 篇资料的索引和 Top-5 召回验证，但应用层答案生成尚未通过
  限流条件下的回归评测，不能直接替换稳定版。
- 新版隔离 Compose 使用独立容器名、端口、网络和 `volumes-upgrade/` 数据目录，不能与稳定版
  资源混用；隔离卷只保留在本机并被 Git 忽略。
- 桥接接口虽然已经在升级分支注册并完成契约测试，但尚未指向真实小智设备，也没有把稳定版
  的 `/api/museum/query` 替换掉；展览、展品编号、时代和类别在新版中记录为语义上下文，不能
  误称为旧版文档画像的结构化过滤。
- 新版隔离运行需要单独的 PostgreSQL、Redis、Milvus、上传目录和模型配置；在本机内存紧张
  时不启动第二套 Milvus，避免影响正在运行的演示环境。
- 不把 API Key、数据库密码、JWT Secret、上传资料或运行日志写入 Git。

## 下一阶段

隔离 Compose/环境模板已经在升级分支准备完成，并通过无敏感值的配置校验。后续按资源情况执行：

1. 先固定一个可审计且确实可调用的模型配置，解决当前 `MODEL_RATE_LIMITED`（核对模型部署、
   账户配额和 API Key 归属；必要时再评估退避或已配置的其他供应商）。密钥只通过本地环境变量
   提供，不写入仓库；可先运行升级分支的
   `scripts/check_model_provider_config.py --env-file <已有本机 .env>`，live 评测再使用
   `scripts/evaluate_rag.py run --env-file <升级环境 .env>`；在预检通过
   前不把 live 评测标记为通过。
2. 在同一隔离索引上重跑 10 题应用层评测，至少确认路由、答案可回答性、来源证据和错误率，
   再扩充到更大的人工标注集；不能把仅有向量召回的结果当成答案质量。
3. 在通过回归前，只在升级分支用正确的 `BRIDGE_API_KEY` 做接口级检索冒烟，确认 trace 和
   来源契约；不要把升级 API 接入设备。
4. 只有新版通过答案/证据回归后，才把该桥接接口迁移到稳定部署并切换小智插件的 `base_url`；
   在此之前继续使用已恢复的稳定版。

本机已准备好仅用于隔离验证的 Markdown 导入脚本，账号密码通过环境变量读取；它只上传和检查
资料，不提供删除旧资料的操作。

## 来源

- [湖南博物院官网](https://www.hnmuseum.com/)
- [SuperMew 官方仓库](https://github.com/icey1287/SuperMew)
