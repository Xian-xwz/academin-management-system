# 基于 AI 的学业管理系统（毕设）

## 目录结构

```
.
├── backend/          # FastAPI 后端
├── frontend/         # Vue 3 前端
├── knowledge/        # 培养方案、wiki、Chroma 等知识资源
├── scripts/          # 构建/运维脚本（后补）
├── data/             # 演示/导入用数据
├── uploads/          # 用户上传文件
├── docs/             # 补充技术说明
├── plan/             # 阶段计划与备忘
├── logs/开发日志/     # 问题与修复记录（按月）
├── 开题报告.md
├── 需求文档.md
├── 技术文档.md
└── 中期报告.md
```

## 说明

- 具体代码与依赖初始化按 `技术文档.md` 与开发进度再补；当前为目录骨架 + 各目录 `README` 说明。

## Git 与 GitHub 备份

本仓库已在本地初始化 Git（默认分支 `main`），`.env`、前端 `node_modules`、`backend/storage/` 等已通过根目录 `.gitignore` 排除，请勿将密钥提交到远端。

**首次推送到 GitHub（在 GitHub 网页新建空仓库后执行）：**

```powershell
cd "d:\study\case\毕业设计"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

若远程已存在同名历史且需覆盖（慎用），需使用 `--force` 前请自行确认。后续日常备份：

```powershell
git add -A
git commit -m "chore: backup snapshot"
git push
```

建议使用英文提交信息，或在 Git Bash 下提交中文信息，以避免 PowerShell 编码导致的乱码。
