<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/3c190622-80c8-4101-8e7e-5c64ea5af2b3

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## 本地联调说明

- 登录、注册、学号查询、课表、时间规划、论坛和 AI 问询已改为调用后端真实接口，默认通过 `/api` 走 Vite 代理到后端。
- 若后端不是 `http://127.0.0.1:8000`，可设置 `VITE_API_PROXY_TARGET` 调整代理目标；也可设置 `VITE_API_BASE=http://127.0.0.1:8000/api` 直接请求后端。
- 个人主页支持点击头像上传图片，调用 `/api/auth/avatar` 后更新本地 `userInfo.avatarUrl`；也支持在“学业档案”页打开修改密码弹窗，调用 `/api/auth/change-password` 完成原密码校验和弱口令拦截。论坛话题列表、详情页和评论区会优先展示该头像。
- 教务工作台已接入 `/admin` 独立路由与布局，管理员登录后默认进入工作台；普通学生访问 `/admin` 会回到学生首页。当前包含概览页、用户与账号列表、指定学生毕业进度只读页、论坛治理页和学业预警发送，接口统一来自 `src/api/modules/admin.ts`。学业预警会在目标学生下次登录时通过 `pendingAcademicWarnings` 弹窗展示一次，不进入时间规划；论坛治理支持隐藏（`DELETE /api/admin/forum/topics/{id}`）与取消隐藏（`PATCH /api/admin/forum/topics/{id}`，`status: normal`）。管理员进入普通学生端后，侧栏和用户下拉会显示“返回教务工作台”入口。
- AI 问询需要先登录获得后端 JWT；前端通过 `POST /api/ai/chat/stream` 消费 SSE 流式响应，并展示后端 `status` 事件形成的处理过程。助手消息必须通过 `messages.value[index]` 中的响应式对象逐字追加，避免修改原始对象引用导致页面等到结束后才一次性渲染。历史会话下拉会读取 `/api/ai/conversations`，点击后再读取 `/api/ai/conversations/{conversation_id}` 回显本地落库消息。
- AI 历史会话下拉右侧提供减号删除入口，会调用 `DELETE /api/ai/conversations/{conversation_id}` 删除当前用户本地会话。
- AI 输入框附件选择后只会先挂载在输入框上方，不会立即发送；需要继续输入文字后点击发送或按 Enter 才会随问题一起提交。发送时前端先调用 `/api/ai/files/upload`，由后端代理上传到 Dify `/files/upload`，再把 `upload_file_id` 放入流式聊天请求的 `files` 参数。
- 知识卡片入口位于学生端侧栏“知识卡片”，默认展示画廊；点击“新建卡片”打开 Drawer，可输入知识文本、上传单张参考图片和补充要求。前端通过 `POST /api/knowledge-cards/stream` 消费 SSE 进度事件，生成完成后重新加载历史并通过授权 fetch 获取图片 blob 进行预览和下载；用户不能手动选择风格或模板。
- AI 助手回复使用 `markdown-it` 渲染 Markdown，支持标题、列表、加粗、引用、代码块、表格和链接等常见格式，样式定义在 `src/components/ChatWindow/index.vue`。
- 首页“毕业学分进度”与学号查询页共用 `/api/student/{student_id}/academic-info`，读取当前登录学生真实已修/毕业要求学分；“近期待办”读取时间规划事件并可直接勾选完成，状态会同步回 `/api/time-plan/events/{event_id}`；“消息通知”读取 `/api/dashboard/notifications`，聚合论坛回复、点赞和 AI 问询记录，默认折叠展示前 4 条，标记已读后会按当前账号写入本地已读集合并隐藏。
- 时间规划列表和日历共用 `/api/time-plan/events` 数据；日历会自动定位到第一条事件所在月份，并以按类型区分颜色的简洁卡片展示课程、考试、作业和个人事件。
- 论坛话题附件与评论附件下载均通过前端 `fetch` 携带 JWT 获取 blob 后触发浏览器下载，避免直接打开下载地址时缺少 `Authorization` 导致失败；论坛列表展开评论后也会显示历史评论、评论附件和“上传评论附件”回形针按钮，详情页评论卡片同样支持上传。
- 论坛专业筛选和发布页专业下拉会读取 `/api/forum/majors`；搜索支持标题、正文和标签；发布新话题已接入真实后端，支持创建后上传话题附件，话题作者或管理员可在列表/详情页编辑、删除话题。
