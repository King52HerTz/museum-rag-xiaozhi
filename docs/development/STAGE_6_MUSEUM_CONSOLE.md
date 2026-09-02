# 阶段 6：智博导览管理端统一知识库资料管理

更新时间：2026-08-23

## 目标

把“博物馆知识库”资料管理从单独打开 SuperMew 工作台，收敛到智博导览管理平台页面内，完成资料上传、处理进度查看、资料列表、删除和检索测试。

## 本阶段改动

- `manager-web` 的 `MuseumKnowledge.vue` 增加资料列表、上传入口、异步处理进度和删除操作。
- 上传时将“湖南省博物馆”和“长沙马王堆汉墓陈列”画像字段传给 RAG，保证结构化过滤可以命中新资料。
- `manager-api` 的博物馆上传接口转发画像字段，并拒绝空文件。
- 保留 SuperMew 工作台免登录入口，用于高级维护和排查，不再作为日常上传的必经路径；免登录失败时留在管理端，不跳转到第二个登录页。
- API Key、SuperMew 账号、数据库密码和上传资料继续保留在本地配置，不进入 Git。

## 管理端接口

```text
GET    /xiaozhi/museum/rag/documents
POST   /xiaozhi/museum/rag/documents/upload
GET    /xiaozhi/museum/rag/documents/upload/jobs
GET    /xiaozhi/museum/rag/documents/upload/jobs/{jobId}
DELETE /xiaozhi/museum/rag/documents/{filename}
GET    /xiaozhi/museum/rag/documents/delete/jobs/{jobId}
POST   /xiaozhi/museum/rag/query
```

所有接口继续使用智博导览管理平台登录态；RAG 的内部登录凭据和桥接密钥只由 `manager-api` 使用。

## 验证结果

- 前端 `npm run build`：通过；仅有既有资源体积和 Browserslist 提示。
- 后端 `mvn -DskipTests compile`：通过。
- 管理端前端可正常访问，未登录访问管理接口仍返回未授权。
- SuperMew 文档接口可正常返回现有资料列表；当前本地知识库已有资料记录。

## 运行时一致性修复（2026-08-30）

- 官方 Docker 管理端仍占用 `8002`，只保留作为原版页面；本项目源码管理端统一从 `http://127.0.0.1:8001/` 进入。
- `manager-web` 的开发代理固定指向源码 `manager-api:8003`，避免把博物馆接口请求误发到旧版 `8002`。
- 一键启动脚本会把源码 `manager-api` 运行在官方 XiaoZhi Docker 网络中，复用官方 MySQL/Redis 登录数据；因此 `8001` 可以使用同一账号看到原有智能体和设备。
- `GET /museum/rag/workbench-login-url` 的桥接票据已实测可跳转到 SuperMew 工作台；管理端检索烟测返回 3 个知识库上下文并包含追踪信息。

## 人工验收

登录 `http://127.0.0.1:8001` 后打开“博物馆知识库”页面，依次验证：

1. 页面显示已有资料列表和分块数；
2. 上传一份 PDF、DOCX 或 XLSX，看到上传任务进度；
3. 任务完成后刷新，文件出现在列表中；
4. 使用“辛追夫人为什么能够千年不腐？”进行检索测试，返回检索片段；
5. 删除测试文件，确认异步删除完成后从列表消失。

## 下一阶段

阶段 7 已补充 SmartRing 本地 WebSocket 切换入口；下一阶段进行真实设备上线、智能体绑定和语音问答闭环回归。
