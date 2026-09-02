# 智博导览管理与语音服务

`zhibo-guide-platform/main` 是「智博导览」的管理端和语音服务端模块。它保留小智 ESP32 服务端的通用设备、模型、音色和 OTA 能力，并增加了面向博物馆场景的管理端桥接功能。

## 模块组成

| 目录 | 技术栈 | 职责 |
| --- | --- | --- |
| `manager-web/` | Vue 3、Vite | 智博导览管理平台前端 |
| `manager-api/` | Spring Boot、MyBatis | 用户、智能体、设备和博物馆桥接 API |
| `xiaozhi-server/` | Python、WebSocket | 语音会话、模型编排和设备通信 |

管理端的博物馆页面通过 `manager-api` 调用 `museum-rag` 的检索接口；语音服务端插件 `plugins_func/functions/search_museum_knowledge.py` 负责把检索证据传给语言模型，形成导览回答。资料上传和问答测试优先在管理平台完成，知识库维护工作台用于高级排查。

## 本地启动

推荐从仓库根目录运行：

```powershell
.\start_museum_rag.ps1 -OpenBrowser
```

默认端口：

- `8001`：智博导览管理平台前端；
- `8003`：管理端 API；
- `8011`：小智语音 WebSocket；
- `8013`：小智语音 HTTP/MCP；
- `8000`：配套博物馆知识库服务（位于仓库根目录 `museum-rag/`）。

各服务的数据库、Redis、模型和设备配置均为本地运行配置，不应把真实密码、API Key 或私有配置提交到 Git。可复制对应的 `*.example` 模板后按本机环境填写。

## 上游来源

本模块基于 [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 的代码快照进行博物馆场景集成。新增和调整的范围包括管理端品牌、博物馆知识库入口、桥接 API、检索插件及相关文档。许可证和版权声明见根目录 [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md)。
