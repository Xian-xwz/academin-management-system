from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, async_engine
from app.main import app
from app.models import User


ADMIN_USERNAME = "admin001"
ADMIN_PASSWORD = "123456"
STUDENT_PASSWORD = "123456"
PREFERRED_STUDENT_ID = "202211911001"


async def ensure_admin_and_pick_student() -> str:
    async with AsyncSessionLocal() as session:
        admin_result = await session.execute(select(User).where(User.student_id == ADMIN_USERNAME))
        admin = admin_result.scalar_one_or_none()
        if admin is None:
            admin = User(username=ADMIN_USERNAME, student_id=ADMIN_USERNAME)
            session.add(admin)
        admin.password_hash = hash_password(ADMIN_PASSWORD)
        admin.real_name = "教务管理员"
        admin.role = "admin"
        admin.is_active = True

        preferred_result = await session.execute(
            select(User)
            .options(selectinload(User.major))
            .where(User.student_id == PREFERRED_STUDENT_ID, User.role == "student")
        )
        target = preferred_result.scalar_one_or_none()
        if target is None:
            fallback_result = await session.execute(
                select(User)
                .options(selectinload(User.major))
                .where(User.role == "student", User.major_id.is_not(None), User.is_active.is_(True))
                .order_by(User.created_at.desc())
                .limit(1)
            )
            target = fallback_result.scalar_one_or_none()
        if target is None:
            raise RuntimeError("缺少可用于教务工作台 harness 的学生账号，请先运行 seed_scenario_data.py")

        await session.commit()
        return target.student_id


async def bootstrap() -> str:
    target_student_id = await ensure_admin_and_pick_student()
    # TestClient 会在自己的事件循环内运行应用，先释放初始化阶段的连接池，避免 Windows + aiomysql 跨 loop 复用连接。
    await async_engine.dispose()
    return target_student_id


def main() -> None:
    target_student_id = asyncio.run(bootstrap())
    client = TestClient(app)
    client.__enter__()
    try:
        admin_login = client.post("/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
        print(f"admin_login={admin_login.status_code}")
        admin_login.raise_for_status()
        admin_token = admin_login.json()["data"]["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        summary = client.get("/api/admin/dashboard/summary", headers=admin_headers)
        print(f"admin_summary={summary.status_code}")
        summary.raise_for_status()
        assert summary.json()["data"]["totalUsers"] >= 1

        users = client.get("/api/admin/users", params={"page": 1, "pageSize": 10, "q": target_student_id}, headers=admin_headers)
        print(f"admin_users={users.status_code}")
        users.raise_for_status()
        user_items = users.json()["data"]["items"]
        assert any(item["studentId"] == target_student_id for item in user_items)

        detail = client.get(f"/api/admin/users/{target_student_id}", headers=admin_headers)
        print(f"admin_user_detail={detail.status_code}")
        detail.raise_for_status()
        assert detail.json()["data"]["studentId"] == target_student_id

        academic = client.get(f"/api/admin/users/{target_student_id}/academic-info", headers=admin_headers)
        print(f"admin_academic={academic.status_code}")
        academic.raise_for_status()
        assert academic.json()["data"]["baseInfo"]["studentId"] == target_student_id

        progress = client.get(f"/api/admin/users/{target_student_id}/graduation-progress", headers=admin_headers)
        print(f"admin_progress={progress.status_code}")
        progress.raise_for_status()
        assert progress.json()["data"]["studentId"] == target_student_id

        warning = client.post(
            f"/api/admin/users/{target_student_id}/warnings",
            headers=admin_headers,
            json={"title": "harness 学业预警", "content": "这是一条管理员 harness 生成的学业预警。"},
        )
        print(f"admin_warning={warning.status_code}")
        warning.raise_for_status()
        assert warning.json()["data"]["studentId"] == target_student_id

        forum_topics = client.get("/api/admin/forum/topics", params={"page": 1, "pageSize": 5, "status": "normal"}, headers=admin_headers)
        print(f"admin_forum_topics={forum_topics.status_code}")
        forum_topics.raise_for_status()

        student_login = client.post("/api/auth/login", json={"username": target_student_id, "password": STUDENT_PASSWORD})
        print(f"student_login={student_login.status_code}")
        if student_login.status_code == 200:
            student_login_data = student_login.json()["data"]
            pending_warnings = student_login_data.get("pendingAcademicWarnings") or []
            assert any(item["title"] == "harness 学业预警" for item in pending_warnings)
            student_headers = {"Authorization": f"Bearer {student_login_data['token']}"}
            forbidden = client.get("/api/admin/dashboard/summary", headers=student_headers)
            print(f"student_admin_forbidden={forbidden.status_code}")
            assert forbidden.status_code == 403
            self_academic = client.get(f"/api/student/{target_student_id}/academic-info", headers=student_headers)
            print(f"student_self_academic={self_academic.status_code}")
            self_academic.raise_for_status()
            second_student_login = client.post("/api/auth/login", json={"username": target_student_id, "password": STUDENT_PASSWORD})
            print(f"student_warning_once={second_student_login.status_code}")
            second_student_login.raise_for_status()
            assert second_student_login.json()["data"].get("pendingAcademicWarnings") == []

            smoke_topic = client.post(
                "/api/forum/topics",
                headers=student_headers,
                json={"title": "harness 管理端隐藏测试帖", "content": "用于验证管理员论坛治理软删除。", "tags": ["harness"]},
            )
            print(f"student_create_forum_topic={smoke_topic.status_code}")
            smoke_topic.raise_for_status()
            smoke_topic_id = smoke_topic.json()["data"]["id"]
            hide_topic = client.delete(f"/api/admin/forum/topics/{smoke_topic_id}", headers=admin_headers)
            print(f"admin_hide_forum_topic={hide_topic.status_code}")
            hide_topic.raise_for_status()
            assert hide_topic.json()["data"]["status"] == "deleted"
            restore_topic = client.patch(
                f"/api/admin/forum/topics/{smoke_topic_id}",
                headers=admin_headers,
                json={"status": "normal"},
            )
            print(f"admin_restore_forum_topic={restore_topic.status_code}")
            restore_topic.raise_for_status()
            assert restore_topic.json()["data"]["status"] == "normal"
        else:
            print("student_forbidden_check=skipped, target student password is not the default 123456")
    finally:
        client.__exit__(None, None, None)
        asyncio.run(async_engine.dispose())


if __name__ == "__main__":
    main()
