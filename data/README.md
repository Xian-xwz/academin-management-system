# data

测试与演示用结构化数据（JSON/CSV 等），例如专业、课程、学生选课样例。

业务正式数据以 MySQL 为准，本目录仅作导入模板或毕设演示。

## 与演示数据脚本的关系

- `backend/scripts/import_knowledge_json.py` 会将本目录的专业、毕业要求、课程和实践环节导入 MySQL。
- `backend/scripts/seed_scenario_data.py` 会复用这些结构化数据，按固定规则生成学生账号、已修课程、课表和时间规划，便于本地联调毕业进度与 AI 问询。
