# M1：仓库骨架与基础能力

> 前置：[00-shared](00-shared.md) · 总览：[PRD](../PRD.md) · 下一步：[M2](02-m2-pipeline-rag.md)

---

## 目标

搭好可运行的工程骨架：admin 登录、项目 CRUD、全局设置读写、Job API 壳（可不接真实生成）。Docker Compose 至少拉起带 pgvector 的数据库。

## 范围 / 不做

**做**

- `backend/`（FastAPI：api / models / services / alembic / seed）+ `frontend/`（Vue3）骨架
- `docker-compose.yml` 至少 `db`（PostgreSQL + pgvector）
- 登录与种子用户；项目归属隔离；设置页读写 `app_settings`
- `generation_jobs` 表与 `GET` / `cancel` 壳

**不做**

- 接通 Dify / 真实生成流水线（M2）
- 受控 Agent、审校面板（M3）
- api/web 全量容器化与总验收（M4）
- 公开注册、细粒度 RBAC、项目共享

---

## 数据与 API

### 实体

**`users`**：`id`, `username`, `password_hash`, `is_active`, `is_admin`, `created_at`

**`app_settings`**：`id`, `llm_configs`, `embedding_configs`, `choose_configs`, `updated_at`  
（字段形状见 [00-shared](00-shared.md)）

**`projects`**：`id`, `owner_id`, `name`, `topic`, `genre`, `num_chapters`, `word_number`, `model_routing`（可选）, `architecture`, `character_state`, `global_summary`, `status`, 时间戳

**`generation_jobs`**：见 [00-shared](00-shared.md)（本步可只建表 + 查询/取消壳）

### 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户名+密码；返回 token |
| GET/POST | `/api/projects` | 列表 / 创建（强制归属当前用户） |
| GET/PATCH/DELETE | `/api/projects/{id}` | 读写删；校验 `owner_id` |
| GET/PUT | `/api/settings` | 全局模型预设（admin 维护） |
| GET | `/api/jobs/{job_id}` | Job 查询壳 |
| POST | `/api/jobs/{job_id}/cancel` | Job 取消壳 |

除登录外：`Authorization: Bearer <token>`。

### 种子

- 用户：`admin` / `123456`，`is_admin=true`（部署后应改密；一期不强制改密流程）
- `app_settings` 可写入空 `api_key` 的预设骨架，部署后在设置页填写

---

## 实现要点

### 仓库结构（本步交付）

```text
banana-agents/
  backend/           # FastAPI：api / models / services / alembic / seed
  frontend/          # Vue3：登录 / 项目列表 / 设置页骨架
  docs/PRD.md
  docs/steps/
  docker-compose.yml # 至少 db（pgvector）
  README.md
```

### 前端信息架构（本步）

1. 登录页  
2. 项目列表 / 创建项目  
3. 设置页（模型预设与任务路由）  
4. 工作台壳（参数区即可；生成按钮可占位）

### 业务规则

- 密码 bcrypt/argon2；不做公开注册
- 项目字段：名称、topic、genre、`num_chapters`、`word_number`、可选 `model_routing`
- API 强制 `owner_id == current_user.id`
- Dify / Job 超时等 **不进** 前端设置页（仅 `.env`）

### 角色

| 角色 | 权限 |
|------|------|
| 管理员 `admin` | 维护设置中的模型预设 |
| 普通账号（后续手工入库） | 仅本人项目 |

---

## 验收清单

- [ ] `admin` / `123456` 可登录并拿到 token
- [ ] 可创建/列表/更新/删除本人项目；他人项目不可见
- [ ] 伪造他人 `project_id` → 403/404
- [ ] 设置页可读写 `llm_configs` / `embedding_configs` / `choose_configs` 并持久化
- [ ] `GET /api/jobs/{id}`、`POST .../cancel` 可用（壳即可）
- [ ] `docker compose` 可启动 pgvector 数据库；迁移/种子可跑通
- [ ] 密码非明文；前端无 Dify Key
