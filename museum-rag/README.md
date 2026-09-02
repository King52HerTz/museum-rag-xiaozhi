# 博物馆知识库服务

`museum-rag` 是「智博导览」项目中的知识库模块，负责博物馆资料的导入、解析、向量化、混合检索和检索证据返回。它被管理平台和小智服务端共同调用，当前稳定资料范围以湖南省博物馆、长沙马王堆汉墓陈列为主。

## 模块职责

- 接收并处理 `docx`、`pdf`、`xls/xlsx` 等博物馆资料；
- 使用向量检索与关键词检索组合召回，按需进行合并和重排；
- 保存文档的博物馆、展览、展品、时代和类别等业务元数据；
- 为管理平台提供问答测试与资料管理能力；
- 为小智服务端提供只返回证据片段的检索桥接接口。

## 主要接口

| 接口 | 作用 |
| --- | --- |
| `POST /api/museum/query` | 面向管理平台和小智插件的检索接口 |
| `/api/documents/*` | 文档上传、状态查询和删除 |
| `/api/sessions/*` | 知识库工作台的会话记录 |

`POST /api/museum/query` 使用桥接密钥鉴权。接口只负责检索，不直接生成最终导览话术；小智服务端收到证据后，再由配置的语言模型生成适合游客的回答。完整字段和错误语义见 `backend/api/routes/museum.py` 以及根目录的开发记录。

## 本地运行

在本仓库根目录使用一键脚本即可同时编排知识库和管理平台：

```powershell
.\start_museum_rag.ps1 -OpenBrowser
```

单独运行知识库服务时，需要先准备 Docker Compose 依赖和私有 `.env`：

```powershell
Copy-Item .env.example .env
uv sync
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

`.env` 只保存在本机，不要提交到 Git。示例文件只包含占位值，真实模型密钥、数据库密码和桥接密钥请按本机部署填写。

前端位于 `frontend/`，首次构建或修改前端后执行：

```powershell
cd frontend
npm install
npm run build
```

## 数据和资料边界

本仓库不包含本地上传资料、数据库、向量库、模型文件和运行日志。根目录 `.gitignore` 已忽略这些内容；资料应在本地管理端上传，并根据馆方公开资料进行来源登记。

## 开源来源

本模块基于 [icey1287/SuperMew](https://github.com/icey1287/SuperMew) 的代码快照进行博物馆场景适配。桥接接口、文档元数据、管理端联调、检索可观测性和项目文档属于本项目的集成工作。许可证和版权声明见根目录 [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)。
