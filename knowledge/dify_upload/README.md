# dify_upload

Dify 知识库上传专用 Markdown 目录。

生成规则：

- 按“专业 + 主题模块”拆分文件。
- 单个文件目标控制在 200KB 以内。
- 超过 500KB 的文件需要继续拆分。
- 每个文件开头必须包含专业名称、专业代码、文档类型和来源。

生成命令：

```bash
python scripts/knowledge_pipeline/run_all.py
```
