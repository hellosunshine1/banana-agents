# Banana-Agents（香蕉小说生成器 Web 版）

多 Agent 协作的长篇小说生成系统：设定 → 目录 → SSE 草稿 → 定稿 → 一致性审校。

- 技术栈：FastAPI + LangChain | 本地 Dify（五工作流）| PostgreSQL + pgvector | Vue3 + SSE
- 形态：团队内网版（简单登录 + 项目按用户隔离）
- 规格总览：[docs/PRD.md](docs/PRD.md)
- 分步实现：[docs/steps/](docs/steps/)（[共享约定](docs/steps/00-shared.md) · [M1](docs/steps/01-m1-foundation.md) · [M2](docs/steps/02-m2-pipeline-rag.md) · [M3](docs/steps/03-m3-agent-review.md) · [M4](docs/steps/04-m4-deploy-acceptance.md)）

## 快速开始（M1）

```bash
cp .env.example .env
docker compose up -d

cd backend
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
- 种子账号：`admin` / `123456`

## 里程碑

- [x] [M1](docs/steps/01-m1-foundation.md) 仓库骨架 + 登录 + 项目 CRUD + 设置页
- [ ] [M2](docs/steps/02-m2-pipeline-rag.md) Dify 五流接通 + SSE 草稿 + pgvector RAG
- [ ] [M3](docs/steps/03-m3-agent-review.md) 受控 Agent + 审校面板
- [ ] [M4](docs/steps/04-m4-deploy-acceptance.md) docker-compose + 验收
