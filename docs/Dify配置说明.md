# Dify 与知识库配置说明（索引）

> **定位**：集中说明「去哪里看完整配置、环境变量叫什么、测试与报告在哪」，避免与 `docs/mine/技术文档.md` 重复堆叠全文。  
> **注意**：本文档**不包含**任何真实 API Key、Dataset ID 或密码；密钥仅放在项目根目录 `.env`（勿提交到版本库）。

## 1. 详细设计入口

- **整体架构与 AI 问询链路**：`docs/mine/技术文档.md`（检索「Dify」「Chatflow」「知识库」等小节）。
- **MinerU → Wiki → Dify 上传 → JSON 流水线**：`plan/mineru知识库处理_812ac5d4.plan.md`。
- **控制台手工问答回归（表格模板）**：`plan/Dify问答测试清单.md`。

## 2. 后端与环境变量（名称级）

- **接口清单与路径**：`backend/README.md`（`/api/ai/chat`、`/api/ai/chat/stream`、附件上传等）。
- **Dify Agent 工具 Schema 公网地址**：`https://academin-management-system.maplexian.cn/dify-agent-tools.openapi.json`。该地址应返回 `application/json`，当前版本为 `2.1.0`，包含 `admin_get_student_*` 管理员/辅导员目标学生查询工具。若 Dify 控制台仍拒绝按学号查询，请重新导入该 schema 并同步 `docs/dify/agent_prompt.md`。
- **Dify Agent 系统提示词**：`docs/dify/agent_prompt.md`。管理员/辅导员按目标学号查询的规则必须与 OpenAPI schema 同步。
- **常见变量名**（以仓库 `.env` / `backend` 读取为准，具体说明见技术文档）：
  - `DIFY_APP_API_BASE`、`DIFY_APP_API_KEY`、`DIFY_APP_API_ID`：Chatflow / Agent 调用（流式/非流式）；若使用正式版 Agent，可配置 `DIFY_AGENT_TOKEN` / `dify_agent_token` 与 `DIFY_AGENT_ID` / `dify_agent_id`，后端优先读取 Agent 专用变量。
  - `DIFY_KNOWLEDGE_API_BASE`、`DIFY_DATASET_API_KEY`、`DIFY_DATASET_ID`：Knowledge API 批量上传（与控制台/自托管实例基址对齐方式见 mineru 计划「自托管 Dify」一节）。
  - 上传并发、轮询等：如 `DIFY_UPLOAD_CONCURRENCY`（见 `scripts/dify_upload/` 下脚本说明）。

## 3. 知识产物与脚本位置

- **分专业正式问询 Markdown**：`knowledge/dify_upload_major/`（同目录 `README.md` 有粒度说明）。
- **细粒度上传层归档**：`knowledge/dify_upload/`。
- **标准 Wiki**：`knowledge/wiki/`。
- **结构化 JSON（毕业进度等）**：`data/*.json`，字段约束见 `schemas/*.schema.json`。
- **流水线脚本**：`scripts/knowledge_pipeline/`（见该目录 `README.md`）。
- **Dify 批量上传脚本**：`scripts/dify_upload/`（见各脚本 `--help` / 目录内 README）。

## 4. 运行报告与清单（便于答辩展示「可追溯」）

目录：`reports/`

示例（以仓库实际文件为准）：

- `dify_upload_manifest.json`、`dify_upload_result*.json`：上传批次与索引状态。
- `dify_qa_regression_report.md`：问答回归记录。
- `knowledge_pipeline_report.md`、`field_validation_report.json`：流水线与字段校验摘要。

## 5. 与阶段规划文档的对应关系

`plan/毕设阶段规划_33b76acb.plan.md` 中「阶段一交付物」所指的 Dify/知识库说明，**以本文件为入口**，细节仍以 `docs/mine/技术文档.md` 与 `plan/mineru知识库处理_812ac5d4.plan.md` 为准。

---

*本文档为仓库内索引型说明，随部署环境变化时请同步更新路径与变量名，勿写入密钥。*
