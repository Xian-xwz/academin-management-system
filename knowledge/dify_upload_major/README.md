# dify_upload_major

Dify 分专业知识库上传目录。

生成规则：

- 每个专业生成 1 个 Markdown 文档。
- 文档开头固定包含“毕业条件速查卡”，覆盖总学分、模块学分、必修/选修、实践环节、毕业实习/设计和需个人数据判断的事项。
- 后续依次拼接专业总览、课程设置、实践教学和课程体系矩阵，避免检索命中总览却漏掉学分结构。
- 当前目录由 `scripts/dify_upload/build_and_upload_major_markdown.py` 生成。

当前生成专业文档数：48
