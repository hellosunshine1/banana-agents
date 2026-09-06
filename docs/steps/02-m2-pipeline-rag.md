# M2：流水线、SSE 与 pgvector RAG

> 前置：[M1](01-m1-foundation.md) · 约定：[00-shared](00-shared.md) · 下一步：[M3](03-m3-agent-review.md)

---

## 目标

接通本地 Dify 四流（设定 / 目录 / 草稿 / 定稿），跑通「设定 → 目录 → SSE 草稿 → 改稿 → 定稿」；定稿后切块 embedding 入 pgvector，后续草稿可注入 RAG 上下文。

## 范围 / 不做

**做**

- `wf_architecture` / `wf_blueprint` / `wf_chapter_draft` / `wf_finalize_summary`
- 设定、目录、定稿走 Job；草稿走 SSE
- 工作台：设定区、目录编辑器、章节编辑器（流式 + 人工改稿）、角色/摘要展示
- 定稿写 `chapter_chunks`；草稿检索注入（Embedding/RAG **不经 Dify**）

**不做**

- `wf_consistency_review` 与审校面板（M3）
- 受控 Agent（M3）
- 外部知识库导入、批量章节生成（二期）
- Compose 全量验收（M4）

---

## 数据与 API

### 实体（本步完善）

| 实体 | 说明 |
|------|------|
| `projects.architecture` | 设定正文；可人工编辑 |
| `projects.character_state` / `global_summary` | 角色状态与全局摘要 |
| `chapter_blueprints` | `(project_id, chapter_number)` 唯一；title / summary / raw_text |
| `chapters` | `content`；status = empty / drafting / draft / finalized |
| `chapter_chunks` | RAG 切块 + `embedding vector(1536)` |
| `generation_jobs` | 设定 / 目录 / 定稿任务 |

模型路由：项目可覆盖 `model_routing`，缺省用全局 `choose_configs`（见 [00-shared](00-shared.md)）。

### 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects/{id}/architecture/generate` | 202 + `job_id`；成功写 architecture、character_state |
| POST | `/api/projects/{id}/blueprint/generate` | 202 + `job_id`；写 chapter_blueprints |
| GET/PUT | `/api/projects/{id}/blueprint` | 读/改目录（可按章编辑） |
| POST | `/api/projects/{id}/chapters/{n}/draft` | **SSE**；注入架构/蓝图/摘要/角色/RAG/guidance |
| PUT | `/api/projects/{id}/chapters/{n}` | 保存/改稿；**不**更新向量 |
| POST | `/api/projects/{id}/chapters/{n}/finalize` | 202 + `job_id`；更新摘要与角色；切块入 pgvector |
| GET | `/api/jobs/{job_id}` | 轮询 |
| POST | `/api/jobs/{job_id}/cancel` | 取消 |
| POST | `/api/projects/{id}/rag/query` | 只读检索（联调/验收可用） |

### SSE 事件

`meta` / `token` / `usage` / `done` / `error`（JSON data）。中断：保留已生成文本，用户可重试。

### Dify 工作流（本步四流）

| 逻辑名 | 调用 | 输入 → 输出 |
|--------|------|-------------|
| `wf_architecture` | Job | 主题等 → architecture + character_state |
| `wf_blueprint` | Job | architecture 等 → 蓝图 |
| `wf_chapter_draft` | 流式→SSE | 上下文 → token 流 |
| `wf_finalize_summary` | Job | 正文+旧状态 → 新摘要/角色 |

env 键与降级策略见 [00-shared](00-shared.md)。定稿 embedding **不经 Dify**。

---

## 实现要点

### 四步行为

1. **设定**：创建 Job → 成功写 `architecture`、`character_state` → 前端可编辑保存。
2. **目录**：创建 Job → 写 `chapter_blueprints` → 可按章编辑。
3. **草稿**：组装上下文（设定 / 蓝图 / 近章或摘要 / 角色 / RAG / guidance）→ Dify 流式 → SSE 推送 → 可 `PUT` 改稿；保存草稿不更新向量。
4. **定稿**：Job 调 `wf_finalize_summary` → 更新 `global_summary`、`character_state` → 切块 embedding 写入 `chapter_chunks` → 章节 status = finalized。

### RAG

- 一期 `EMBEDDING_DIM=1536`；`retrieval_k` / top_k 默认 4。
- 仅定稿入库；下一章草稿生成时应能命中已定稿片段。

### 前端工作台（本步）

参数 | 设定 | 目录 | 章节（SSE+编辑）| 角色/摘要 | Job 进度

### 职责边界

- 前端不直连 Dify。
- LangChain（FastAPI）：Job 编排、Dify 调用、SSE 桥接、Embedding、RAG。

---

## 验收清单

- [ ] 创建项目后可完成：设定 → 目录 → SSE 草稿 → 改稿 → 定稿
- [ ] 设定/目录/定稿返回 `job_id`，可轮询状态与取消
- [ ] 草稿 SSE 事件齐全；中断后已生成文本可保留并重试
- [ ] 保存草稿不写向量；定稿后 `chapter_chunks` 有数据
- [ ] `rag/query` 或下一章草稿上下文能命中本章定稿片段
- [ ] 架构/蓝图/章节/摘要/角色均可人工编辑并持久化
- [ ] Dify 不可用时的降级路径有文档或开关（一期目标仍是接通四流）
