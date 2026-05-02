from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, async_engine
from app.models import Course, ForumComment, ForumTopic, Major, Schedule, StudentCourse, TimePlanEvent, User


DEMO_USERS = [
    ("2021000001", "电科演示学生", "080702", "2021级"),
    ("2021000002", "计科演示学生", "080901", "2021级"),
    ("2021000003", "软工演示学生", "080902", "2021级"),
]
DEFAULT_PASSWORD = "guangdong11"


async def _get_major(session, major_code: str) -> Major:
    result = await session.execute(select(Major).where(Major.major_code == major_code))
    major = result.scalar_one_or_none()
    if major is None:
        raise RuntimeError(f"缺少专业数据：{major_code}，请先运行 import_knowledge_json.py")
    return major


async def seed_users(session) -> list[User]:
    users: list[User] = []
    password_hash = hash_password(DEFAULT_PASSWORD)
    for student_id, real_name, major_code, grade in DEMO_USERS:
        major = await _get_major(session, major_code)
        result = await session.execute(select(User).where(User.student_id == student_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username=student_id,
                student_id=student_id,
                password_hash=password_hash,
            )
            session.add(user)
        user.real_name = real_name
        user.major_id = major.id
        user.grade = grade
        user.is_active = True
        users.append(user)
    await session.flush()
    return users


async def seed_student_courses(session, users: list[User]) -> int:
    count = 0
    for user in users:
        result = await session.execute(
            select(Course)
            .where(Course.major_id == user.major_id)
            .order_by(Course.id)
            .limit(8)
        )
        courses = list(result.scalars().all())
        for index, course in enumerate(courses):
            semester = "2021-2022-1" if index < 4 else "2021-2022-2"
            existing = await session.execute(
                select(StudentCourse).where(
                    StudentCourse.student_id == user.student_id,
                    StudentCourse.course_name == course.course_name,
                    StudentCourse.semester == semester,
                )
            )
            student_course = existing.scalar_one_or_none()
            if student_course is None:
                student_course = StudentCourse(
                    user_id=user.id,
                    student_id=user.student_id,
                    course_id=course.id,
                    course_name=course.course_name,
                    semester=semester,
                )
                session.add(student_course)
                count += 1

            student_course.user_id = user.id
            student_course.course_id = course.id
            student_course.course_category = course.course_category or course.module or "未分类"
            student_course.credits = course.credits
            student_course.score = 85
            student_course.grade_point = 3.5
            student_course.status = "passed"
            student_course.is_passed = True
    await session.flush()
    return count


async def seed_schedules(session, users: list[User]) -> int:
    count = 0
    for user in users:
        result = await session.execute(
            select(Course)
            .where(Course.major_id == user.major_id)
            .order_by(Course.id)
            .limit(3)
        )
        for index, course in enumerate(result.scalars().all(), start=1):
            existing = await session.execute(
                select(Schedule).where(
                    Schedule.student_id == user.student_id,
                    Schedule.semester == "2025-2026-1",
                    Schedule.course_name == course.course_name,
                    Schedule.day_of_week == index,
                )
            )
            schedule = existing.scalar_one_or_none()
            if schedule is None:
                schedule = Schedule(
                    user_id=user.id,
                    student_id=user.student_id,
                    course_id=course.id,
                    course_name=course.course_name,
                    semester="2025-2026-1",
                    day_of_week=index,
                    start_section=1,
                    end_section=2,
                )
                session.add(schedule)
                count += 1
            schedule.teacher = "演示教师"
            schedule.location = f"教学楼 {index}01"
            schedule.weeks_text = "1-16周"
            schedule.start_week = 1
            schedule.end_week = 16
            schedule.week_pattern = "all"
    await session.flush()
    return count


async def seed_time_plan(session, users: list[User]) -> int:
    count = 0
    for user in users:
        existing = await session.execute(
            select(TimePlanEvent).where(
                TimePlanEvent.student_id == user.student_id,
                TimePlanEvent.title == "完成毕业设计阶段检查",
            )
        )
        event = existing.scalar_one_or_none()
        if event is None:
            event = TimePlanEvent(
                user_id=user.id,
                student_id=user.student_id,
                title="完成毕业设计阶段检查",
                event_type="作业",
                start_time=datetime(2026, 4, 30, 14, 0),
                end_time=datetime(2026, 4, 30, 16, 0),
            )
            session.add(event)
            count += 1
        event.location = "线上"
        event.description = "演示时间规划数据"
        event.status = "待开始"
        event.source_type = "manual"
    await session.flush()
    return count


async def seed_forum(session, users: list[User]) -> int:
    count = 0
    user = users[0]
    existing = await session.execute(select(ForumTopic).where(ForumTopic.title == "毕业要求资料分享"))
    topic = existing.scalar_one_or_none()
    if topic is None:
        topic = ForumTopic(
            user_id=user.id,
            major_id=user.major_id,
            title="毕业要求资料分享",
            summary="演示论坛话题",
            content="这里整理了培养方案、毕业学分和课程建议，供同学们参考。",
            tags_json=["毕业要求", "培养方案"],
        )
        session.add(topic)
        await session.flush()
        count += 1
    existing_comment = await session.execute(select(ForumComment).where(ForumComment.topic_id == topic.id, ForumComment.content == "感谢分享"))
    if existing_comment.scalar_one_or_none() is None:
        session.add(ForumComment(topic_id=topic.id, user_id=user.id, content="感谢分享"))
        topic.comment_count += 1
    await session.flush()
    return count


async def main() -> None:
    async with AsyncSessionLocal() as session:
        try:
            users = await seed_users(session)
            course_count = await seed_student_courses(session, users)
            schedule_count = await seed_schedules(session, users)
            time_plan_count = await seed_time_plan(session, users)
            forum_count = await seed_forum(session, users)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await async_engine.dispose()

    print(f"demo_users={len(users)}")
    print(f"student_courses_inserted={course_count}")
    print(f"schedules_inserted={schedule_count}")
    print(f"time_plan_events_inserted={time_plan_count}")
    print(f"forum_topics_inserted={forum_count}")
    print(f"demo_password={DEFAULT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
