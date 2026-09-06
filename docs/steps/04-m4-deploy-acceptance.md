# M4：部署与一期验收

> 前置：[M1](01-m1-foundation.md) · [M2](02-m2-pipeline-rag.md) · [M3](03-m3-agent-review.md) · 约定：[00-shared](00-shared.md) · 总览：[PRD](../PRD.md)

---

## 目标

用 Docker Compose 在内网拉起 db + api + web，按一期验收清单走通主路径，并固化运维 env 与风险缓解说明。

## 范围 / 不做

**做**

- Compose 容器化 api / web（在 M1 已有 db 基础上）
- 汇总并执行一期验收清单
- README / `.env.example` 与部署步骤对齐

**不做**

- 公网 SaaS、计费、公开注册
- 二期能力实现（见附录）
- 细粒度运维后台（运维参数仍只走 `.env`）

---

## 数据与 API

本步不新增业务 API。部署依赖的 env 见 [00-shared](00-shared.md)：

```text
JOB_TIMEOUT_SEC=600
JOB_MAX_CONCURRENCY=2
DIFY_BASE_URL=...
DIFY_API_KEY=...
DIFY_WF_*=...
EMBEDDING_DIM=1536
DATABASE_URL=...
JWT_SECRET=...
```

仓库交付形态：

```text
banana-agents/
  backend/
  frontend/
  docs/
  docker-compose.yml   # db + api + web
  .env.example
  README.md
```

---

## 实现要点

### 部署

- 内网 Docker Compose：至少 PostgreSQL（pgvector）、FastAPI、Vue 静态或前端服务。
- 本地 Dify 可外挂（同一内网）；前端永不直连 Dify。
- 种子 `admin` / `123456`：验收用；部署后应改密（一期不强制改密流程）。

### 非功能复核

- 项目隔离与密码哈希
- Dify Key 仅服务端
- Job 可取消；SSE 中断可保留文本
- RAG top_k 默认 4；Job / Agent / RAG 有日志

### 前端信息架构（完整）

1. 登录页  
2. 项目列表 / 创建项目  
3. 设置页  
4. 项目工作台：参数 | 设定 | 目录 | 章节（SSE+编辑）| 角色/摘要 | 审校 | Job 进度 | Agent 侧栏  

---

## 验收清单（一期总表）

- [ ] `admin` / `123456` 可登录  
- [ ] 创建项目 → 设定 → 目录 → SSE 草稿 → 改稿 → 定稿 → 审校  
- [ ] 项目互不可见  
- [ ] Agent 白名单外拒绝；草稿意图返回 SSE 端点而非混流  
- [ ] 定稿后向量可检索；下一章含 RAG 上下文  
- [ ] 设置页可保存预设；Job 可查询/取消  
- [ ] 伪造他人 project_id → 403/404；前端无 Dify Key；密码非明文  
- [ ] `docker compose up` 可启动并完成上述主路径（Dify 按环境可达）

分里程碑细项仍以 [M1](01-m1-foundation.md) / [M2](02-m2-pipeline-rag.md) / [M3](03-m3-agent-review.md) 为准。

---

## 附录 A：二期 Backlog

知识库导入、批量生成、角色库、协作权限、伏笔实体、导出增强（EPUB/DOCX 等）、管理后台、审校后改写等。扩展 Agent 工具须评审注册。

## 附录 B：风险

| 风险 | 缓解 |
|------|------|
| Dify↔SSE 桥接不稳定 | 超时配置；降级 LangChain 直连 LLM |
| Embedding 维度变更 | 一期锁 1536；变更须重建 `chapter_chunks` |
| 长任务超时 | `JOB_TIMEOUT_SEC`、可取消、进度字段 |
| Prompt 质量 | Dify 工作流侧迭代；不阻塞协议层验收 |

---

## 本步验收清单（部署）

- [ ] Compose 含 db、api、web；文档写明启动顺序与必要 env
- [ ] `.env.example` 覆盖 [00-shared](00-shared.md) 所列键（无真实密钥）
- [ ] 一期总表全部勾选或明确环境阻塞项
- [ ] README 里程碑状态与文档链接一致
