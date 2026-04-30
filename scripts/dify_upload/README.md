# dify_upload

将 `knowledge/dify_upload/` 中的 Markdown 批量导入 Dify 云端知识库。

## 配置

复制项目根目录 `.env.example` 为 `.env`，填写：

- `DIFY_KNOWLEDGE_API_BASE`
- `DIFY_DATASET_API_KEY`
- `DIFY_DATASET_ID`
- `DIFY_UPLOAD_CONCURRENCY`
- `DIFY_KNOWLEDGE_REQUESTS_PER_MINUTE`

如果知识库已经在 Dify 控制台配置了 Embedding 模型，脚本无需额外传模型参数。若需要通过 API 指定，可在 `.env` 中补充：

- `DIFY_EMBEDDING_MODEL`
- `DIFY_EMBEDDING_MODEL_PROVIDER`

## 试跑

只查看将要上传的文件：

```bash
python scripts/dify_upload/upload_markdown_to_dify.py --dry-run --limit 3
```

先上传计算机科学与技术相关文件：

```bash
python scripts/dify_upload/upload_markdown_to_dify.py --include 计算机科学与技术 --limit 3
```

脚本默认跳过 `广东海洋大学 2021 版本科` 这类总标题伪专业文件。若还需要排除其他文件，可追加 `--exclude 关键词`。

## 全量上传

```bash
python scripts/dify_upload/upload_markdown_to_dify.py
```

脚本会按文件输出实时日志，包括上传开始、请求节流等待、索引轮询状态和报告写入。报告中 `upload_status=success` 的文件会自动跳过，因此中断后可以直接用同一命令断点续传。

如果 Dify 返回 `The number of documents has reached the limit of your subscription`，说明知识库文档数量达到当前订阅上限。脚本会停止继续上传，此时需要删除旧文档、升级额度，或先把 Markdown 合并成更少的上传文件。

如果 Dify 云端提示知识库请求限流，改用单并发慢速续传。脚本会对所有知识库 API 请求统一节流，`10` 表示每 6 秒最多发起 1 次请求：

```bash
python scripts/dify_upload/upload_markdown_to_dify.py --concurrency 1 --knowledge-requests-per-minute 10 --max-retries 10 --rate-limit-cooldown 180
```

如果希望遇到限流就立即停止，等待之后再断点续传：

```bash
python scripts/dify_upload/upload_markdown_to_dify.py --concurrency 1 --knowledge-requests-per-minute 10 --stop-on-rate-limit
```

上传结果会写入 `reports/dify_upload_result.json`。脚本默认跳过报告中已成功上传的文件；如需重传，添加 `--force`。

## 分专业档案上传

正式问询知识库建议使用“一个专业一个 Markdown”的档案式上传，避免检索命中专业总览却漏掉学分结构：

```bash
python scripts/dify_upload/build_and_upload_major_markdown.py
```

该脚本会生成 `knowledge/dify_upload_major/`，每个专业 1 个 Markdown，开头固定包含“毕业条件速查卡”，覆盖总学分、模块学分、必修/选修、实践环节、毕业实习/毕业设计、毕业能力要求，以及必须依赖个人成绩数据判断的事项。上传报告写入 `reports/dify_upload_major_result_selfhosted.json`。
