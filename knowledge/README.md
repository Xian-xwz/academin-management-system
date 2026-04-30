# knowledge

知识库与向量数据目录。

| 子目录/路径 | 用途 |
|-------------|------|
| `raw` | 原始培养方案 PDF 等（体积大，建议不提交大文件或改用 Git LFS） |
| `markdown` | PDF 转 Markdown 后的中间结果 |
| `wiki/majors` 等 | LLM Wiki 风格编译后的结构化知识页 |
| `dify_upload` | 按 Dify 单文件限制切分后的 Markdown 上传文件 |
| `chroma_db` | Chroma 嵌入式向量库持久化目录，可由 `09_ingest_chroma_optional.py` 生成（**建议加入 .gitignore**） |

构建脚本可放在 `scripts/`，与知识目录分离，便于复现论文中的知识构建流程。
