# Banana-Agents（香蕉小说生成器 Web 版）

多 Agent 协作的长篇小说生成系统：设定 → 目录 → SSE 草稿 → 定稿 → 一致性审校。

- 技术栈：FastAPI + LangChain/OpenAI 兼容 | 本地 Dify（五工作流）| PostgreSQL + pgvector | Vue3 + SSE
- 形态：团队内网版（简单登录 + 项目按用户隔离）
- 规格总览：[docs/PRD.md](docs/PRD.md)
- 分步实现：[docs/steps/](docs/steps/)（[共享约定](docs/steps/00-shared.md) · [M1](docs/steps/01-m1-foundation.md) · [M2](docs/steps/02-m2-pipeline-rag.md) · [M3](docs/steps/03-m3-agent-review.md) · [M4](docs/steps/04-m4-deploy-acceptance.md)）

## 快速开始（Docker Compose）

仓库根目录：

```bash
cp .env.example .env
# 按需填写 JWT_SECRET、DIFY_*；LLM/embedding 也可在启动后于「设置」页填写

docker compose up --build -d
```

启动顺序：`db`（健康检查）→ `api`（migrate + seed + uvicorn）→ `web`（nginx 静态 + `/api` 反代）。

- 前端：http://127.0.0.1:8080
- API / OpenAPI：http://127.0.0.1:8000/docs
- 种子账号：`admin` / `123456`（部署后请改密）

本地 Dify 为内网外挂，不在本 Compose 内。容器内默认 `DIFY_BASE_URL=http://host.docker.internal/v1`（macOS/Windows Docker Desktop）；Linux 请改为可达的 Dify 地址。

### 必要 env

根目录 `.env`（Compose）覆盖 [共享约定](docs/steps/00-shared.md) 运维键：`DATABASE_URL`、`JWT_SECRET`、`EMBEDDING_DIM`、`JOB_*`、`DIFY_*`。本机开发用 [`backend/.env.example`](backend/.env.example) → `backend/.env`。

### 生成能力说明

1. 在「设置」填写 `llm_configs` / `embedding_configs` 的 `api_key`（降级直连必需）。
2. 本地 Dify：填写 `DIFY_API_KEY` 与各 `DIFY_WF_*`（含 `DIFY_WF_CONSISTENCY_REVIEW`）；`GENERATION_BACKEND=auto` 优先 Dify。
3. 工作台「Agent」只返回 JSON（可含 `job_id` / `sse_endpoint`）；草稿流式仍走章节 SSE。
4. 「审校」写入 `consistency_reviews`，不自动改章节正文；「审计」可查 `agent/audits`。

## 本机开发（可选）

仅起数据库，api / web 在宿主机运行：

```bash
docker compose up -d db

cd backend
cp .env.example .env   # DATABASE_URL 主机用 localhost
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8000
```

另开终端：

```bash
cd frontend
npm install
npm run dev
```

- 前端：http://127.0.0.1:5173
- API：http://127.0.0.1:8000/docs

## 里程碑

- [x] [M1](docs/steps/01-m1-foundation.md) 仓库骨架 + 登录 + 项目 CRUD + 设置页
- [x] [M2](docs/steps/02-m2-pipeline-rag.md) Dify/降级四流 + SSE 草稿 + pgvector RAG
- [x] [M3](docs/steps/03-m3-agent-review.md) 受控 Agent + 审校面板
- [x] [M4](docs/steps/04-m4-deploy-acceptance.md) docker-compose + 验收
