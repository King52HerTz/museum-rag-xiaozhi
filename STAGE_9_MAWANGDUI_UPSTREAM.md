# 阶段 9：马王堆官方资料库与 SuperMew 上游隔离升级

更新时间：2026-08-30

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
- 当前使用现有稳定配置文件做脱敏预检，必需模型配置为 5/5；`EVALUATION_MODEL` 仍为可选
  缺省。`BRIDGE_API_KEY` 仍是占位配置，因此只允许进入应用层评测，不能进行真实的小智到
  SuperMew 服务端桥接。该检查没有发起模型请求，也没有复制配置文件。
- 已针对 DeepSeek OpenAI 兼容接口补充结构化输出适配：证据评分、复杂度规划、查询重写和
  评测裁判在 DeepSeek endpoint 上统一使用 LangChain `function_calling`，其它模型仍保留默认
  策略；适配代码提交为 `bfdd26a fix(provider): use function calling for DeepSeek schemas`，
  新增兼容测试后定向测试 36 项全部通过，`ruff` 与 `compileall` 均通过。
- 因 RAG 源码指纹按设计发生变化，已按仓库既定命令重建离线 `baseline_v1.json`；模型预检、
  桥接契约、CLI 评测与适配器回归共 39 项通过（仅保留上游依赖弃用提示），新基线提交为
  `5ad9216 chore(evaluation): refresh offline rag baseline`。
- 针对复杂问题子问题的路由又补了一层保护：子问题只要拿到 `partial` 或 `sufficient` 证据，
  就交给最终 synthesis 合并，不会把局部缺口升级成整条主问题的澄清；完全没有答案线索时
  仍保留 `clarify`、`scope_select` 和 `no_knowledge`。新增回归用例后，相关测试共 82 项通过，
  修复提交为 `5e9a3cc fix(rag): keep partial sub-agent evidence for synthesis`，离线基线随之
  更新为 `31060fa chore(evaluation): refresh baseline after routing fix`。
- 针对“同一件文物的多个属性”增加了保守的本地快速判定：只有出现单一所属关系、一个连接词、
  一个疑问词且没有比较/多步骤表达时才跳过复杂度模型；跨对象、跨文档或多步骤问题仍交给
  复杂度规划器。新增边界测试后，相关回归共 83 项通过，提交为
  `744176d perf(rag): fast-path single-entity attribute queries`，离线基线更新为
  `2a557d6 chore(evaluation): refresh baseline after fast path`。
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
- 在启动 Docker 隔离依赖并用 WSL 启动升级 API 后，重新执行了同一套 10 题应用层回归；10/10
  均在生成前以 `MODEL_RATE_LIMITED` 失败，检索结果为 0，报告仍未通过。单独调用方案 B
  `/api/museum/query` 则真实返回 5 个 contexts，`retrieval_empty=false` 且索引身份为目标隔离
  index，证明当前阻断位于模型供应商调用而不是 Milvus 召回或桥接响应。
- 为排除“连续请求过快”这一因素，随后使用同一隔离索引运行了 2 条应用层探针，并设置
  `--inter-case-delay-seconds 10`；两条仍均返回 `MODEL_RATE_LIMITED`，说明当前阻断更可能是
  模型供应商配置、部署或配额问题，而不是评测用例间隔。脱敏 Observation、Report 和 Markdown
  报告保存在本机 `runtime-logs/corpus-build` 忽略目录，未写入回答原文、密钥或原始异常。
- Windows 直接启动新版 API 仍会在上游 Skill Registry 的
  `O_DIRECTORY` / `O_NOFOLLOW` POSIX 安全文件要求处阻断，因此采用 WSL/Linux 完成了本轮
  导入和检索验证，没有为了本机试跑而绕过安全校验。稳定版恢复后 `/docs` 返回 200，原有
  10 条验收问题再次全部命中预期来源。
- 使用本机专用 `.env` 中的 DeepSeek 配置和上述兼容层重跑了同一套 10 题应用层评测：此前的
  `PROVIDER_REQUEST_INVALID` 已消失；开启 CPU 嵌入模型预热并将嵌入超时设为 60 秒后，10/10
  个用例都完成了实际召回和模型流程，生成、裁判、检索三类 provider failure rate 均为 0，
  `route_accuracy=1.0`、`complexity_accuracy=0.9`、`document_recall_at_10=1.0`，
  `case_pass_rate=0.6`、`outcome_accuracy=0.7`，平均耗时约 4.54 秒、P95 约 7.50 秒。
  三个未通过用例是 `t_shape_worlds`、`lacquer_silk_counts` 和 `half_box_qin`：当前官方资料
  能支撑带限定条件的部分回答，但没有覆盖问题要求的全部细节，因此保留
  `INSUFFICIENT_EVIDENCE`，不能为了过门禁把它们改判为完整可回答。另有一个黑地彩绘棺问题
  被模型随机判为复杂，已用上述保守快速判定降低此类波动，但尚未重新消耗外部配额进行全量
  live 验证。评测报告仍未达到发布门槛；脱敏 Observation、Report 和 Markdown 报告保存在
  本机 `runtime-logs/corpus-build` 忽略目录。

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

1. 保持 DeepSeek 配置只存在本机专用 `.env`；继续定位复杂问题的超时、素纱单衣的证据评分
   误判和辛追数字人问题的澄清策略。每次调整后重跑同一 10 题，先达到 provider failure rate
   为 0，再评估路由、答案可回答性、来源证据和错误率；不能把仅有向量召回的结果当成答案质量。
2. 修订并扩充人工标注集：为每个问题补充 reference answer、required claims 和允许的
   证据边界，区分“知识库没有答案”和“召回到了但评分器过于保守”，再扩充到至少 200 条
   覆盖单事实、多跳、歧义/HITL、无知识与来源冲突的用例。
3. 在通过回归前，只在升级分支用正确的 `BRIDGE_API_KEY` 做接口级检索冒烟，确认 trace 和
   来源契约；不要把升级 API 接入设备。
4. 只有新版通过答案/证据回归后，才把该桥接接口迁移到稳定部署并切换小智插件的 `base_url`；
   在此之前继续使用已恢复的稳定版。

本机已准备好仅用于隔离验证的 Markdown 导入脚本，账号密码通过环境变量读取；它只上传和检查
资料，不提供删除旧资料的操作。

## 来源

- [湖南博物院官网](https://www.hnmuseum.com/)
- [SuperMew 官方仓库](https://github.com/icey1287/SuperMew)
