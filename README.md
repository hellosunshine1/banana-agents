# Banana-Agents（香蕉小说生成器 Web 版）

多 Agent 协作的长篇小说生成系统：设定 → 目录 → SSE 草稿 → 定稿 → 一致性审校。

- 技术栈：FastAPI + LangChain | 本地 Dify（五工作流）| PostgreSQL + pgvector | Vue3 + SSE
- 形态：团队内网版（简单登录 + 项目按用户隔离）
- 规格文档：[docs/PRD.md](docs/PRD.md)

## 快速开始
1. `cp .env.example .env` 并填写 Dify / DB 配置
2. `docker compose up -d`（M4 交付后可用）

## 里程碑
- [ ] M1 仓库骨架 + 登录 + 项目 CRUD + 设置页
- [ ] M2 Dify 五流接通 + SSE 草稿 + pgvector RAG
- [ ] M3 受控 Agent + 审校面板
- [ ] M4 docker-compose + 验收