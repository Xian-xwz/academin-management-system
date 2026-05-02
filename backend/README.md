# backend

FastAPI 后端目录。当前已根据前端页面与业务逻辑落地第一版 SQLAlchemy 表模型，并开始实现异步接口骨架、数据库 Session 和 harness 脚本。

## 子目录说明

| 目录 | 用途 |
|------|------|
| `app/api` | 路由层，REST 接口 |
| `app/core` | 配置、安全、统一响应等 |
| `app/db` | 数据库连接与 Session |
| `app/models` | SQLAlchemy 模型 |
| `app/schemas` | Pydantic 入参/出参 |
| `app/services` | 业务逻辑（学号、毕业进度、Dify 调用等） |
| `app/utils` | 工具函数 |
| `scripts` | 本地建表、数据库检查和后续数据导入 harness |
| `tests` | 单测/接口测试（可选） |

## 运行方式

依赖安装：

```bash
pip install -r requirements.txt
```

本地启动：

```bash
uvicorn app.main:app --reload
```

常用 harness：

```bash
python scripts/check_db.py
python scripts/init_schema.py
python scripts/import_knowledge_json.py
python scripts/seed_demo_data.py
python scripts/seed_scenario_data.py
python scripts/seed_dashboard_notifications.py
python scripts/harness_api_smoke.py
python scripts/harness_admin_api.py
```

当前后端配置优先读取项目根目录 `.env` 中的 `DATABASE_URL`；若未配置，会兼容读取现有注释形式的 MySQL 配置。正式联调时建议使用：

```env
DATABASE_URL=mysql+aiomysql://root:你的密码@127.0.0.1:3306/Academic%20Management%20System?charset=utf8mb4
```

Dify Chatflow 使用项目根目录 `.env` 中的 `DIFY_APP_API_BASE`、`DIFY_APP_API_KEY`、`DIFY_APP_API_ID`。后端只读取这些值，不会在响应或日志中输出密钥。

Mock 动态器默认在学生登录后触发，为对应专业论坛生成新帖或评论。配置项：

```env
MOCK_DYNAMIC_ENABLED=true
MOCK_DYNAMIC_USE_LLM=true
DASHSCOPE_API_KEY=请填写 DashScope Key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen3.6-flash
GEMINI_API_KEY=请填写 Gemini Key
GEMINI_MODEL=gemini-2.5-flash
```

动态器会先尝试 DashScope，再尝试 Gemini；若两者未配置或请求失败，后端会使用内置模板兜底，不影响登录成功。

OpenClaw 受控工具接口使用服务令牌和学生白名单，不复用学生 JWT 或管理员账号：

```env
OPENCLAW_TOOL_TOKEN=请填写高强度随机令牌
OPENCLAW_ALLOWED_STUDENT_IDS=202211911001,202211921001
```

`OPENCLAW_ALLOWED_STUDENT_IDS=*` 只适合本地演示。生产环境应只写允许被 OpenClaw 查询的学号。

附件上传默认保存在 `backend/storage/` 下，可通过 `UPLOAD_DIR` 覆盖；单文件大小默认限制为 50MB，可通过 `MAX_UPLOAD_SIZE_MB` 覆盖。头像上传保存在 `backend/storage/avatars/`，单张头像限制为 5MB，并通过 `/api/auth/avatars/{file_name}` 访问。

## 当前已定义的表模型

模型统一放在 `app/models/`，通过 `app/models/__init__.py` 汇总导出，后续可在建表脚本中导入所有模型后执行 `Base.metadata.create_all()`。

**表结构、外键与字段说明**见同目录文档：[app/models/README.md](app/models/README.md)。

| 文件 | 模型 | 用途 |
|------|------|------|
| `app/models/user.py` | `User` | 统一登录用户，当前以学生为主，通过 `role` 预留管理员 |
| `app/models/academic.py` | `Major`、`GraduationRequirement`、`Course`、`PracticeCourse`、`StudentCourse` | 专业、毕业要求、课程、实践环节、学生已修课程，用于学号查询和毕业进度计算 |
| `app/models/ai.py` | `AIConversation`、`AIMessage` | 保存前端会话 ID、Dify 会话 ID、消息、意图和知识来源 |
| `app/models/schedule.py` | `Schedule` | 学生课表、周次、节次和课程备注 |
| `app/models/time_plan.py` | `TimePlanEvent` | 时间规划事件，支持课程/考试/作业/个人类型及课表同步来源 |
| `app/models/academic_warning.py` | `AcademicWarning` | 管理员发送给学生的一次性登录弹窗预警，展示后记录 `shown_at` |
| `app/models/forum.py` | `ForumTopic`、`ForumComment`、`ForumFile`、`ForumTopicLike` | 论坛话题、一级/二级评论、附件和点赞去重 |
| `app/models/error_case.py` | `ErrorCase` | AI 问答错误案例与人工纠错记录，后置扩展 |
| `app/models/openclaw.py` | `OpenClawToolAudit` | OpenClaw 受控工具调用审计记录 |

## 设计说明

- 当前不做教师端/学生端双登录，先使用统一 `users` 表，`role` 字段预留 `student/admin`。
- 学业主线以 `student_id` 查询，登录名与学号一致；模型内部关系尽量保留自增 `id` 外键。
- 毕业要求按 `专业 + 年级 + 版本` 预留多套培养方案，课表按结构化周次支持第 N 周精准过滤。
- 学分类字段使用 `Numeric`，避免整数丢失 0.5 学分。
- `source_file`、`raw_json`、`needs_review` 用于保留培养方案导入来源和人工复核信息。
- 前端 mock 中的字段会在 service/schema 层做映射，例如 `graduationReq.earned`、`statistics[]`、`suggestions[]` 都由后端计算后输出，不直接存宽字段。
- Web 接口统一使用 `async def`、SQLAlchemy `AsyncSession` 和 `mysql+aiomysql`，避免在事件循环中执行同步查库。
- API 响应统一为 `{ code, message, data }`；业务数据均放在 `data` 字段。

## 当前已实现接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 后端与数据库连通性检查 |
| `POST` | `/api/auth/register` | 注册学生账号，登录名固定等于学号 |
| `POST` | `/api/auth/login` | 学号密码登录，返回 JWT、`userInfo` 与一次性 `pendingAcademicWarnings`；登录成功后生成少量论坛/AI 模拟互动数据用于首页通知演示 |
| `GET` | `/api/auth/me` | 根据 Bearer Token 返回当前用户信息 |
| `POST` | `/api/auth/avatar` | 上传当前用户头像，更新 `userInfo.avatarUrl` |
| `GET` | `/api/auth/avatars/{file_name}` | 读取头像图片，用于个人主页和论坛头像展示 |
| `GET` | `/api/admin/dashboard/summary` | 管理员工作台摘要：用户数、活跃数、学生/管理员数、专业分布 |
| `GET` | `/api/admin/users` | 管理员分页查询用户，支持学号/姓名、专业、角色、启用状态筛选 |
| `GET` | `/api/admin/users/{student_id}` | 管理员查看用户详情 |
| `GET` | `/api/admin/users/{student_id}/academic-info` | 管理员查看指定学生完整学业信息，复用学生端学业结构 |
| `GET` | `/api/admin/users/{student_id}/graduation-progress` | 管理员查看指定学生毕业进度 |
| `POST` | `/api/admin/users/{student_id}/warnings` | 管理员向指定学生发送学业预警，学生下次登录时弹窗展示一次，不进入时间规划事件 |
| `GET` | `/api/admin/forum/topics` | 管理员分页查询论坛帖子，支持标题/正文与状态筛选 |
| `DELETE` | `/api/admin/forum/topics/{topic_id}` | 管理员隐藏/软删除论坛帖子，学生端列表不再展示 |
| `PATCH` | `/api/admin/forum/topics/{topic_id}` | 管理员调整帖子状态，`{"status":"normal"}` 取消隐藏恢复展示，`{"status":"deleted"}` 与 DELETE 等效 |
| `GET` | `/api/dashboard/notifications` | 聚合当前用户的论坛回复、点赞和 AI 问询通知 |
| `GET` | `/api/student/{student_id}/academic-info` | 返回前端学号查询页需要的基本信息、毕业要求、已修课程、分类统计和建议；普通学生只能查本人，管理员可查任意学生 |
| `GET` | `/api/student/{student_id}/graduation-progress` | 返回机器可读的毕业进度和缺口学分；普通学生只能查本人，管理员可查任意学生 |
| `POST` | `/api/ai/chat` | 调用 Dify Chatflow；异常时返回本地学业摘要 fallback |
| `POST` | `/api/ai/chat/stream` | 以 SSE 流式转发 Dify Chatflow，前端可逐段展示回答；额外输出 `status` 事件用于展示处理过程 |
| `POST` | `/api/ai/files/upload` | 代理上传 AI 附件到 Dify `/files/upload`，返回可用于聊天请求的文件 ID |
| `GET` | `/api/ai/conversations` | 查询当前用户本地 AI 历史会话列表 |
| `GET` | `/api/ai/conversations/{conversation_id}` | 读取当前用户的本地 AI 会话消息 |
| `DELETE` | `/api/ai/conversations/{conversation_id}` | 删除当前用户的本地 AI 历史会话 |
| `POST` | `/api/ai/error-cases` | 提交 AI 错误案例，默认状态 `pending` |
| `GET` | `/api/ai/error-cases` | 查询当前用户提交的 AI 错误案例，管理员可查全部 |
| `PATCH` | `/api/ai/error-cases/{case_id}/status` | 更新错误案例状态 |
| `GET` | `/api/schedule?term=&week=` | 按学期和第 N 周查询课表 |
| `PATCH` | `/api/schedule/{schedule_id}/note` | 更新课表备注 |
| `GET` | `/api/time-plan/events` | 查询时间规划事件 |
| `POST` | `/api/time-plan/events` | 新增时间规划事件 |
| `PUT` | `/api/time-plan/events/{event_id}` | 更新时间规划事件 |
| `DELETE` | `/api/time-plan/events/{event_id}` | 删除时间规划事件 |
| `POST` | `/api/time-plan/sync-from-schedule?term=` | 从课表同步时间规划事件 |
| `GET` | `/api/forum/majors` | 查询数据库中的专业列表，用于论坛筛选和发布页专业下拉 |
| `GET` | `/api/forum/topics` | 查询论坛话题列表，并返回历史评论与评论附件用于前端展开渲染 |
| `POST` | `/api/forum/topics` | 发布论坛话题 |
| `GET` | `/api/forum/topics/{topic_id}` | 查询论坛话题详情 |
| `PUT` | `/api/forum/topics/{topic_id}` | 编辑本人或管理员可管理的话题 |
| `DELETE` | `/api/forum/topics/{topic_id}` | 删除本人或管理员可管理的话题（软删除） |
| `POST` | `/api/forum/topics/{topic_id}/comments` | 发表评论 |
| `POST` | `/api/forum/topics/{topic_id}/like` | 点赞话题，幂等 |
| `DELETE` | `/api/forum/topics/{topic_id}/like` | 取消点赞 |
| `POST` | `/api/forum/topics/{topic_id}/files` | 上传论坛附件并写入元数据 |
| `POST` | `/api/forum/topics/{topic_id}/comments/{comment_id}/files` | 上传评论附件并写入元数据 |
| `GET` | `/api/forum/files/{file_id}/download` | 下载论坛附件并累加下载次数 |
| `GET` | `/api/openclaw/health` | OpenClaw 工具探活，返回后端、数据库和 Dify 配置摘要，不返回密钥 |
| `GET` | `/api/openclaw/students/me/academic-info` | OpenClaw 读取白名单学生本人学业信息 |
| `GET` | `/api/openclaw/students/me/graduation-progress` | OpenClaw 读取白名单学生本人毕业进度 |
| `GET` | `/api/openclaw/students/me/schedule` | OpenClaw 读取白名单学生本人课表 |
| `GET` | `/api/openclaw/students/me/time-plan/events` | OpenClaw 读取白名单学生本人时间规划事件 |
| `POST` | `/api/openclaw/ai/chat` | OpenClaw 调用非流式 AI 问询封装，不暴露 Dify Key 或原始内部链路 |

`/api/ai/chat/stream` 当前会输出 `status`、`message`、`message_replace`、`message_end`、`error` 等 SSE 事件。`status` 只表示“读取学业数据 / 上传附件 / 检索知识库 / 生成回答 / 整理来源”等处理阶段，不暴露模型内部思维链。AI 附件遵循 Dify 官方流程：先调用 `/files/upload` 获得 `upload_file_id`，再在 `/chat-messages` 的 `files` 数组中以 `transfer_method=local_file` 引用。

评论附件依赖 `forum_files.comment_id` 字段，旧库需运行：

```bash
python scripts/migrate_forum_comment_files.py
```

## 演示账号

运行 `python scripts/seed_demo_data.py` 后会创建以下本地演示账号，密码均为 `123456`：

| 学号 | 专业 |
|------|------|
| `2021000001` | 电子科学与技术 |
| `2021000002` | 计算机科学与技术 |
| `2021000003` | 软件工程 |

若需要更完整的联调数据，运行 `python scripts/seed_scenario_data.py`。该脚本会先导入 `data/*.json` 中的专业、毕业要求、课程和实践环节，再按固定规则生成电子科学与技术、计算机科学与技术、软件工程三个专业的场景学生、已修课程、当前学期课表和时间规划事件。脚本会覆盖清理旧版演示账号与本脚本生成的论坛内容，再重建一批新数据。

| 账号 | 角色 | 说明 |
|------|------|------|
| `admin001` | 管理员 | 教务工作台预留管理员账号 |
| `202211911001`、`202211911002`、`202211911003` | 学生 | 电子科学与技术 2022 级临近毕业样例 |
| `202311911001`、`202311911002`、`202411911001` | 学生 | 电子科学与技术 2023/2024 级在读样例 |
| `202211921001`、`202211921002`、`202211921003` | 学生 | 计算机科学与技术 2022 级临近毕业样例 |
| `202311921001`、`202311921002`、`202411921001` | 学生 | 计算机科学与技术 2023/2024 级在读样例 |
| `202211931001`、`202211931002`、`202211931003` | 学生 | 软件工程 2022 级临近毕业样例 |
| `202311931001`、`202311931002`、`202411931001` | 学生 | 软件工程 2023/2024 级在读样例 |

电科场景数据还会生成 3 条论坛话题，内容采用学生真实讨论风格；若 `docs/参考资料/电科/传感器2023年试题/` 下存在文件，会象征性复制前 3 个文件到论坛附件存储并写入 `forum_files`。

> 注意：`seed_scenario_data.py` 的默认密码也是 `123456`。如果真实部署，请勿保留演示密码。
