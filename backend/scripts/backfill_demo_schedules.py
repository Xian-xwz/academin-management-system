from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal, async_engine
from app.models import Course, Schedule, User


TERMS = ["2023-2024-2", "2024-2025-1", "2024-2025-2", "2025-2026-1"]

SLOTS = [
    (1, 1, 2),
    (1, 3, 4),
    (2, 1, 2),
    (2, 5, 6),
    (3, 3, 4),
    (3, 7, 8),
    (4, 1, 2),
    (4, 5, 6),
    (5, 3, 4),
    (5, 9, 10),
]

WEEK_PATTERNS = [
    ("1-16周", 1, 16, "all"),
    ("1-8周", 1, 8, "all"),
    ("9-16周", 9, 16, "all"),
    ("1-16周（单周）", 1, 16, "odd"),
    ("2-16周（双周）", 2, 16, "even"),
]

LOCATIONS = ["教学楼 A", "教学楼 B", "实验楼", "信息楼机房", "工程实训中心", "综合楼"]


@dataclass
class BackfillStats:
    students: int = 0
    terms: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


async def _students(session) -> list[User]:
    result = await session.execute(
        select(User)
        .where(User.role == "student", User.is_active.is_(True), User.major_id.is_not(None))
        .order_by(User.student_id)
    )
    return list(result.scalars().all())


async def _major_courses(session, user: User) -> list[Course]:
    if user.major_id is None:
        return []
    result = await session.execute(
        select(Course)
        .where(Course.major_id == user.major_id)
        .order_by(Course.id)
    )
    return list(result.scalars().all())


async def _upsert_schedule(session, *, user: User, course: Course, term: str, slot_index: int) -> str:
    day, start_section, end_section = SLOTS[slot_index % len(SLOTS)]
    weeks_text, start_week, end_week, week_pattern = WEEK_PATTERNS[slot_index % len(WEEK_PATTERNS)]
    location_prefix = LOCATIONS[slot_index % len(LOCATIONS)]

    result = await session.execute(
        select(Schedule).where(
            Schedule.student_id == user.student_id,
            Schedule.semester == term,
            Schedule.day_of_week == day,
            Schedule.start_section == start_section,
            Schedule.course_name == course.course_name,
        )
    )
    schedule = result.scalars().first()
    created = False
    if schedule is None:
        schedule = Schedule(
            user_id=user.id,
            student_id=user.student_id,
            course_id=course.id,
            course_name=course.course_name,
            semester=term,
            day_of_week=day,
            start_section=start_section,
            end_section=end_section,
        )
        session.add(schedule)
        created = True

    changed = created
    updates = {
        "user_id": user.id,
        "course_id": course.id,
        "teacher": f"{course.course_category or '专业'}教师{slot_index % 6 + 1}",
        "location": f"{location_prefix} {day}{start_section:02d}",
        "weeks_text": weeks_text,
        "start_week": start_week,
        "end_week": end_week,
        "week_pattern": week_pattern,
        "end_section": end_section,
    }
    for key, value in updates.items():
        if getattr(schedule, key) != value:
            setattr(schedule, key, value)
            changed = True
    if not schedule.note:
        schedule.note = ""

    if created:
        return "inserted"
    return "updated" if changed else "skipped"


async def backfill() -> BackfillStats:
    stats = BackfillStats()
    async with AsyncSessionLocal() as session:
        students = await _students(session)
        stats.students = len(students)
        for user in students:
            courses = await _major_courses(session, user)
            if not courses:
                stats.skipped += len(TERMS) * len(SLOTS)
                continue
            for term_index, term in enumerate(TERMS):
                stats.terms += 1
                for slot_index, _slot in enumerate(SLOTS):
                    course = courses[(slot_index + term_index * 3) % len(courses)]
                    result = await _upsert_schedule(
                        session,
                        user=user,
                        course=course,
                        term=term,
                        slot_index=slot_index,
                    )
                    setattr(stats, result, getattr(stats, result) + 1)
        await session.commit()
    return stats


async def main() -> None:
    try:
        stats = await backfill()
        print(
            "backfill_demo_schedules "
            f"students={stats.students} terms={stats.terms} "
            f"inserted={stats.inserted} updated={stats.updated} skipped={stats.skipped}"
        )
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
