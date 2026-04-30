# knowledge_pipeline

MinerU 知识库处理流水线。

## 功能

将 `docs/人才培养方案/` 中的 MinerU 输出整理为：

- `knowledge/markdown/`：合并文档、专业原始切分。
- `knowledge/wiki/`：标准 LLM Wiki 知识页。
- `knowledge/dify_upload/`：适配 Dify 文件大小限制的上传版 Markdown。
- `data/`：后端可导入的结构化 JSON。
- `reports/`：覆盖、校验、Dify 上传清单和问答回归测试清单。

## 执行

```bash
python scripts/knowledge_pipeline/run_all.py
```

如需单步执行，可按文件编号从 `01_inventory_sources.py` 到 `08_generate_reports.py` 依次运行。

可选 Chroma 兜底索引入口：

```bash
python scripts/knowledge_pipeline/09_ingest_chroma_optional.py
```

该步骤依赖 `chromadb`，当前主链路以 Dify 上传层为准，不强制执行。

## 保护约定

- 不修改 `docs/人才培养方案/` 原始 MinerU 输出。
- 不覆盖根目录正式文档。
- 生成物集中写入 `knowledge/`、`data/`、`reports/`、`schemas/`。
