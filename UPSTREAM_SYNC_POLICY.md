# 上游同步策略

本项目同时依赖小智服务端和 SuperMew。两者更新频率不同，因此采用“按版本同步、按阶段验证”的策略，而不是追踪每日最新提交。

## 版本选择原则

- 稳定演示优先于最新提交；
- 安全修复和影响当前运行环境的修复可以优先评估；
- 与博物馆功能无关的新功能不主动同步；
- 每次只升级一个上游项目；
- 每次升级必须保留可回退的稳定版本。

## 分支规则

建议在后续正规化完成后使用以下分支：

```text
main                  可复现的稳定版本
upstream/xiaozhi-main 小智官方跟踪分支
upstream/supermew-main SuperMew 官方跟踪分支
upgrade/xiaozhi-*     小智某次升级验证
upgrade/supermew-*    SuperMew 某次升级验证
museum/*              博物馆适配层开发
```

如果继续使用当前单仓库，也必须在提交信息中标明：

```text
upstream: xiaozhi @ <commit>
upstream: supermew @ <commit>
museum: <feature>
```

## 当前分支清单（2026-08-30）

根项目 `museum-rag-xiaozhi` 目前保留一个稳定分支和若干历史检查点：

- `main`：稳定演示基线；
- `codex/stage2b-*` 到 `codex/stage8-*`：已完成阶段的回滚检查点；
- `codex/sync-supermew-upstream-20260830`：当前集成文档和升级候选分支。

这些分支不会同时部署，也不代表多套运行环境。后续开发不再创建新的阶段分支；阶段 16 和后续
评测继续使用当前集成分支，SuperMew 代码继续使用个人 Fork 的 `codex/museum-upgrade`。
待真实 live 门禁通过后，再把确认无误的提交合并到 `main`，并为已合并的历史分支打标签后统一
归档或删除。没有明确确认前不执行远程分支删除。

## SuperMew Fork 推送保护

SuperMew 的原始仓库不是本项目所有者的仓库。当前升级副本采用以下远程边界：

```text
origin   https://github.com/King52HerTz/SuperMew-museum.git
upstream https://github.com/icey1287/SuperMew.git（仅用于 fetch）
```

升级分支 `codex/museum-upgrade` 已推送到个人 Fork。隔离仓库的 `upstream` push URL 已设置为禁用值，普通 `git push` 默认只允许推送到 `origin`；任何需要向原作者仓库提交的操作都不在本项目流程内。

## 升级检查表

### SuperMew

- [ ] 原始服务可以启动；
- [ ] docx 上传和解析正常；
- [ ] pdf 上传和解析正常；
- [ ] Excel 上传和解析正常；
- [ ] 原始问答正常；
- [ ] 博物馆元数据仍可保存；
- [ ] `/api/museum/query` 返回正确证据；
- [ ] 错误码、鉴权和 trace 不回归。

### 小智

- [ ] 管理端可以登录；
- [ ] Agent 配置可以读取；
- [ ] 原有设备相关接口不回归；
- [ ] 博物馆管理端代理正常；
- [ ] `search_museum_knowledge` 可以调用桥接接口；
- [ ] RAG 不可用时有明确降级提示；
- [ ] 不把真实密钥提交到仓库。

## 回退规则

出现以下任一情况，停止本次升级并回退到上一个稳定版本：

- 原有 RAG 上传或问答失败；
- 管理端无法登录或无法加载；
- 桥接鉴权失败且无法在配置层解释；
- 小智核心设备链路异常；
- 回归问题集的准确性或响应时间明显下降。

回退只允许切换到已记录的 commit 或标签，不允许用未记录的本地 ZIP 覆盖。
