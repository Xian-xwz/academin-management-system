# scripts

一次性/运维脚本目录。

## 子目录

| 目录 | 用途 |
|------|------|
| `knowledge_pipeline/` | MinerU 输出到 LLM Wiki / Dify 上传层 / 结构化 JSON 的处理流水线 |
| `dify_upload/` | 调用 Dify 知识库 API，批量上传 `knowledge/dify_upload/` Markdown |

## 推荐执行

```bash
python scripts/knowledge_pipeline/run_all.py
```

脚本只写入 `knowledge/`、`data/`、`reports/`、`schemas/` 等生成目录，不修改 `docs/人才培养方案/` 原始 MinerU 输出。

## Dify API 配置

批量上传等脚本从项目根目录读取环境变量：复制根目录 `.env.example` 为 `.env`，填写 `DIFY_DATASET_API_KEY`、`DIFY_DATASET_ID` 等（详见 `.env.example` 内注释）。

试跑 Dify 批量上传：

```bash
python scripts/dify_upload/upload_markdown_to_dify.py --dry-run --limit 3
```
