# 智博导览：博物馆 RAG 知识库与小智服务端桥接项目

本项目用于构建一个面向博物馆场景的智能导览原型系统，目标是把已经跑通的 RAG 知识库系统与小智 ESP32 服务端/管理平台连接起来，形成“资料上传、知识检索、管理端测试、设备端导览问答”的演示闭环。

当前演示主题以“湖南省博物馆 / 长沙马王堆汉墓陈列”为核心，适合用于大创项目阶段性展示、答辩原型和后续硬件导览设备集成。

## 项目目标

- 建设一个可上传博物馆资料的 RAG 知识库系统。
- 将小智管理端改造为“智博导览管理平台”。
- 在管理端提供“博物馆知识库”入口，完成资料管理和问答测试。
- 通过小智服务端插件 `search_museum_knowledge` 调用 RAG 检索接口。
- 后续接入导览设备，实现语音提问、知识检索、导览播报。

## 仓库结构

```text
.
├── rag/
│   └── SuperMew-main/              # RAG 知识库系统
│       ├── backend/                # FastAPI 后端、检索接口、文档处理逻辑
│       ├── frontend/               # RAG 工作台前端
│       └── docker-compose.yml      # RAG 依赖服务：PostgreSQL / Redis / Milvus 等
│
└── xiaozhi-esp32-server-main/
    └── main/
        ├── manager-api/            # 小智管理端后端，已增加 museum/rag 桥接模块
        ├── manager-web/            # 小智管理端前端，已增加博物馆知识库入口
        └── xiaozhi-server/         # 小智服务端，已增加 RAG 检索插件
```

## 当前已完成能力

### RAG 知识库系统

- 支持上传 `docx / pdf / excel` 等资料。
- 新增博物馆检索接口：

```text
POST /api/museum/query
```

- 支持桥接鉴权：

```text
Authorization: Bearer <BRIDGE_API_KEY>
```

- 管理端日常资料操作不需要再次登录；高级维护工作台提供可选的免登录跳转。

### 智博导览管理平台

- 管理端标题已改造为“智博导览管理平台”。
- 新增“博物馆知识库”页面入口。
- 后端新增 `museum/rag` 桥接 Controller / Service。
- 管理端可直接上传资料、查看异步处理进度、删除资料并进行检索测试。
- SuperMew 工作台仍保留为高级维护和故障排查入口；免登录失败时不会回退到第二个登录页面。
- 管理端已内置“导览问答测试”控制台，可直接调用 `manager-api /museum/rag/query`，由管理端后端桥接到 SuperMew `POST /api/museum/query`。

### 小智服务端插件

新增插件：

```text
xiaozhi-server/plugins_func/functions/search_museum_knowledge.py
```

该插件用于在用户询问湖南省博物馆、马王堆汉墓、辛追夫人、素纱单衣、T 形帛画等相关问题时，调用 RAG 检索接口，并把检索结果交给小智 LLM 生成自然语言导览回答。

本地已验证该插件可通过 `search_museum_knowledge` 调用 SuperMew RAG，并返回 `Action.REQLLM`，即把检索片段作为上下文交给小智 LLM 继续生成语音导览回答。

### 演示智能体初始化

管理端数据库迁移中已经加入演示智能体初始化逻辑：

```text
湖南省博物馆导览员
```

该智能体会自动绑定 `SYSTEM_PLUGIN_MUSEUM_KNOWLEDGE` 插件，并写入本地联调用的 RAG 桥接参数。这样新环境初始化数据库后，可以直接围绕“湖南省博物馆 / 长沙马王堆汉墓陈列”进行导览问答演示。

## 本地运行说明

本仓库不提交本地真实配置文件、模型文件和文档资料；启动脚本只负责编排本地服务，不包含敏感值。运行前需要根据自己的环境补充：

- RAG `.env`
- 小智管理端数据库 / Redis 配置
- 小智服务端运行配置
- 模型或第三方 API Key
- 本地上传的博物馆资料

建议本地联调端口规划（请使用源码管理端 `8001`，不要把官方 Docker 页面 `8002` 当作本项目入口）：

```text
8000  SuperMew RAG 工作台与后端
8001  智博导览管理平台前端
8003  智博导览管理平台后端
8011  小智语音 WebSocket 服务端（接硬件阶段建议）
8013  小智语音 HTTP/MCP 服务端（接硬件阶段建议）
15432 SuperMew PostgreSQL
6379  SuperMew Redis
19530 Milvus
```

如果本机仍运行官方 `xiaozhi-esp32-server-web` 容器（端口 `8002`），它是未包含本项目博物馆接口的旧版页面，访问 `/museum/rag/*` 会返回 404。启动脚本会让源码管理端 API 复用该官方容器的 MySQL/Redis 数据，因此 `8001` 登录后可以继续看到官方账号、智能体和设备；两套服务不会再使用两套登录数据库。

### Windows 一键启动

在项目根目录双击 `start_museum_rag.cmd`，脚本会启动 Docker 依赖、RAG API、智博导览管理端前后端和小智服务端，并自动打开管理端入口。启动完成后 CMD 窗口会保留结果，按任意键关闭窗口不会停止已经启动的服务：

```text
http://127.0.0.1:8001/
```

首次运行如果没有 `manager-api/target/xiaozhi-esp32-api.jar` 或 SuperMew 前端构建产物，脚本会自动执行构建；Java 源码比现有 JAR 更新时也会自动重新打包，避免继续运行旧接口。因此首次启动或代码更新后的启动可能需要更长时间。脚本只读取已运行官方容器的连接配置，不把账号密码、API Key 写入仓库；运行日志保存在 `runtime-logs/museum-startup/logs`。

需要手动启动或跳过某个组件时，也可以在 PowerShell 中执行：

```powershell
.\start_museum_rag.ps1 -OpenBrowser
```

如果端口被上一次异常退出的进程占用，可以使用：

```powershell
.\start_museum_rag.ps1 -ForceRestart -OpenBrowser
```

如果需要在 Windows 上启动本地小智语音服务端，还需要确保 Python 能加载 Opus 动态库，否则会出现：

```text
Could not find Opus library. Make sure it is installed.
```

本地联调可将 `opus.dll` 所在目录加入启动进程的 `PATH`。本机验证时使用的是 conda-forge `libopus` 包解出的 `Library/bin/opus.dll`，放在小智服务端 `tmp/opus-lib` 目录下供本地运行使用；该目录不应提交到仓库。

可参考以下模板补充本地配置：

```text
xiaozhi-esp32-server-main/main/manager-api/src/main/resources/application-local.template.yml
xiaozhi-esp32-server-main/main/xiaozhi-server/data/.config.yaml.example
rag/SuperMew-main/.env.example
```

其中 `application-local.template.yml` 与 `.config.yaml.example` 已预留博物馆 RAG 桥接配置项，但真实密码、真实 API Key 不应提交到仓库。

## 已忽略内容

为避免仓库过大、泄露密钥或误提交本地资料，以下内容未上传到 GitHub：

- 本地 `.env` 和私有配置文件
- 数据库密码、API Key 等敏感信息
- `node_modules`
- Python 虚拟环境
- Java / 前端构建产物，例如 `target`、`dist`
- 下载的模型文件
- 上传的测试资料
- 项目文档和申请书
- 硬件工程资料
- 运行日志和本地运行状态

## 后续开发方向

1. 将硬件设备从小智官方服务切换到本地小智服务端：`ws://<本机局域网 IP>:8011/xiaozhi/v1/`。
2. 在本地管理端为真实设备绑定“湖南省博物馆导览员”智能体，验证设备私有配置能下发 `search_museum_knowledge` 插件参数。
3. 持续整理湖南省博物馆示例数据，形成稳定演示脚本和答辩话术。

阶段开发记录：

- [阶段 4：本地小智服务端启动回归](STAGE_4_XIAOZHI_LOCAL_SERVICE.md)
- [阶段 6：管理端统一知识库资料管理](STAGE_6_MUSEUM_CONSOLE.md)
- [阶段 7：智博导览设备本地 WebSocket 切换](STAGE_7_SMARTRING_LOCAL_WS.md)
- [阶段 8：聊天记录中的博物馆知识库调用核验](STAGE_8_RAG_AUDIT.md)
- [阶段 9：马王堆官方资料库与 SuperMew 上游隔离升级](STAGE_9_MAWANGDUI_UPSTREAM.md)
- [阶段 10：RAG 精排 Provider 安全与可观测性](STAGE_10_RAG_PROVIDER_SAFETY.md)
- [阶段 11：博物馆桥接失败安全契约](STAGE_11_MUSEUM_BRIDGE_SAFETY.md)
- [阶段 12：RAG 结果可核验面板](STAGE_12_RAG_AUDIT_PANEL.md)
- [阶段 13：桥接层传递 RAG 结果语义](STAGE_13_BRIDGE_RAG_OUTCOME.md)
- [阶段 14：马王堆评测集扩展与 Windows 兼容性门禁](STAGE_14_MAWANGDUI_EVAL_GATE.md)

## 项目定位

本项目是一个教学/竞赛/原型验证性质的博物馆智能导览系统，重点验证：

- RAG 知识库在博物馆资料问答中的可行性；
- 智能导览管理平台与知识库系统的集成方式；
- 小智类硬件设备调用外部知识库进行导览问答的可行路径。
