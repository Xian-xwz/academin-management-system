from __future__ import annotations

import asyncio
import mimetypes
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import import_knowledge_json
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, async_engine
from app.models import (
    AIConversation,
    AIMessage,
    Course,
    ErrorCase,
    ForumComment,
    ForumFile,
    ForumTopic,
    ForumTopicLike,
    GraduationRequirement,
    Major,
    PracticeCourse,
    Schedule,
    StudentCourse,
    TimePlanEvent,
    User,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


TARGET_MAJORS = [
    ("080702", "电子科学与技术"),
    ("080901", "计算机科学与技术"),
    ("080902", "软件工程"),
]

MAJOR_STUDENT_CODE = {
    "080702": "1191",
    "080901": "1192",
    "080902": "1193",
}

SCENARIO_SEMESTER = "2025-2026-1"
DEFAULT_PASSWORD = "123456"
FORUM_ATTACHMENT_SOURCE = PROJECT_ROOT / "docs" / "参考资料" / "电科" / "传感器2023年试题"
FORUM_ATTACHMENT_LIMIT = 3
SCENARIO_FORUM_TITLES = [
    "【电科】传感器 2023 试题资料分享",
    "2022 级电科毕业学分自查交流",
    "专业限选课怎么搭配比较稳？",
]


@dataclass(frozen=True)
class StudentProfile:
    suffix: int
    name_prefix: str
    scenario: str
    grade: str
    ratio: float
    practice_ratio: float | None = None
    has_failed_course: bool = False


STUDENT_PROFILES = [
    StudentProfile(1, "接近毕业", "near_graduation", "2022级", 0.97),
    StudentProfile(2, "毕业预警", "near_with_gap", "2022级", 0.90, practice_ratio=0.72),
    StudentProfile(3, "正常推进", "normal", "2023级", 0.74),
    StudentProfile(4, "正常推进", "normal", "2024级", 0.68),
    StudentProfile(5, "学分风险", "risk", "2023级", 0.48),
    StudentProfile(6, "实践缺口", "practice_gap", "2022级", 0.78, practice_ratio=0.25, has_failed_course=True),
]


def _to_float(value: Decimal | int | float | None) -> float:
    return float(value or 0)


async def import_static_data(session) -> None:
    """确保培养方案结构化数据已经进入 MySQL。"""

    major_stats = await import_knowledge_json.import_majors(session)
    majors = await import_knowledge_json._major_map(session)
    requirement_stats = await import_knowledge_json.import_graduation_requirements(session, majors)
    course_stats = await import_knowledge_json.import_courses(session, majors)
    practice_stats = await import_knowledge_json.import_practice_courses(session, majors)
    print(
        "static_data "
        f"majors={major_stats} requirements={requirement_stats} "
        f"courses={course_stats} practice={practice_stats}"
    )


async def _get_major(session, major_code: str) -> Major:
    result = await session.execute(select(Major).where(Major.major_code == major_code))
    major = result.scalar_one_or_none()
    if major is None:
        raise RuntimeError(f"缺少专业数据：{major_code}")
    return major


async def _get_requirement(session, major: Major) -> GraduationRequirement:
    result = await session.execute(
        select(GraduationRequirement)
        .where(GraduationRequirement.major_id == major.id)
        .order_by(GraduationRequirement.grade.desc(), GraduationRequirement.version.desc())
    )
    requirement = result.scalars().first()
    if requirement is None:
        raise RuntimeError(f"缺少毕业要求：{major.major_code} {major.major_name}")
    return requirement


async def _get_courses(session, major: Major) -> list[Course]:
    result = await session.execute(select(Course).where(Course.major_id == major.id).order_by(Course.id))
    courses = list(result.scalars().all())
    if len(courses) < 12:
        raise RuntimeError(f"专业课程数量不足，无法生成演示数据：{major.major_code} {major.major_name}")
    return courses


async def _get_practice_courses(session, major: Major) -> list[PracticeCourse]:
    result = await session.execute(select(PracticeCourse).where(PracticeCourse.major_id == major.id).order_by(PracticeCourse.id))
    return list(result.scalars().all())


async def _upsert_user(
    session,
    *,
    student_id: str,
    real_name: str,
    password_hash: str,
    major_id: int | None,
    grade: str | None,
    role: str = "student",
) -> User:
    result = await session.execute(select(User).where(User.student_id == student_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=student_id, student_id=student_id, password_hash=password_hash)
        session.add(user)
    user.username = student_id
    user.password_hash = password_hash
    user.real_name = real_name
    user.major_id = major_id
    user.grade = grade
    user.role = role
    user.is_active = True
    await session.flush()
    return user


async def _upsert_student_course(
    session,
    *,
    user: User,
    course_name: str,
    semester: str,
    category: str,
    credits: float,
    score: float | None,
    status: str,
    is_passed: bool,
    course_id: int | None = None,
) -> None:
    result = await session.execute(
        select(StudentCourse).where(
            StudentCourse.student_id == user.student_id,
            StudentCourse.course_name == course_name,
            StudentCourse.semester == semester,
        )
    )
    item = result.scalars().first()
    if item is None:
        item = StudentCourse(student_id=user.student_id, course_name=course_name, semester=semester)
        session.add(item)

    item.user_id = user.id
    item.course_id = course_id
    item.course_category = category
    item.credits = credits
    item.score = score
    item.grade_point = _score_to_point(score) if score is not None and is_passed else None
    item.status = status
    item.is_passed = is_passed


def _score_to_point(score: float | None) -> float | None:
    if score is None:
        return None
    if score >= 90:
        return 4.0
    if score >= 85:
        return 3.7
    if score >= 80:
        return 3.3
    if score >= 75:
        return 3.0
    if score >= 70:
        return 2.7
    if score >= 60:
        return 2.0
    return 0.0


def _required_categories(requirement: GraduationRequirement) -> dict[str, float]:
    return {
        "通识必修": _to_float(requirement.general_required_credits),
        "通识选修": _to_float(requirement.general_elective_credits),
        "专业基础": _to_float(requirement.major_basic_credits),
        "专业必修": _to_float(requirement.major_required_credits),
        "专业限选": _to_float(requirement.major_limited_elective_credits),
        "专业任选": _to_float(requirement.major_optional_credits),
        "实践教学": _to_float(requirement.practice_credits),
    }


def _entry_year_from_grade(grade: str) -> str:
    return grade.replace("级", "").strip()


def _student_id_for(major_code: str, profile: StudentProfile) -> str:
    entry_year = _entry_year_from_grade(profile.grade)
    student_code = MAJOR_STUDENT_CODE[major_code]
    sequence_by_grade = {
        1: "1001",
        2: "1002",
        3: "1001",
        4: "1001",
        5: "1002",
        6: "1003",
    }
    return f"{entry_year}{student_code}{sequence_by_grade[profile.suffix]}"


def _legacy_student_ids() -> set[str]:
    return {
        f"2021{major_code[-4:]}{suffix:02d}"
        for major_code, _ in TARGET_MAJORS
        for suffix in range(1, 7)
    }


def _scenario_student_ids() -> set[str]:
    return {
        _student_id_for(major_code, profile)
        for major_code, _ in TARGET_MAJORS
        for profile in STUDENT_PROFILES
    }


async def _seed_student_courses(
    session,
    *,
    user: User,
    profile: StudentProfile,
    requirement: GraduationRequirement,
    courses: list[Course],
    practice_courses: list[PracticeCourse],
) -> int:
    inserted_or_updated = 0
    categories = _required_categories(requirement)
    used_course_names: set[str] = set()
    course_index = 0

    for category, required_credits in categories.items():
        if required_credits <= 0:
            continue
        ratio = profile.practice_ratio if category == "实践教学" and profile.practice_ratio is not None else profile.ratio
        target = required_credits * ratio
        earned = 0.0

        while earned < target:
            if category == "实践教学" and practice_courses:
                source = practice_courses[(len(used_course_names) + profile.suffix) % len(practice_courses)]
                course_name = source.item_name
                credits = _to_float(source.credits) or 1.0
                course_id = None
            else:
                source = courses[course_index % len(courses)]
                course_index += 1
                course_name = source.course_name
                credits = _to_float(source.credits) or 1.0
                course_id = source.id

            if course_name in used_course_names:
                course_name = f"{course_name}（演示{profile.suffix}-{len(used_course_names)}）"
            used_course_names.add(course_name)

            semester = "2021-2022-1" if len(used_course_names) % 2 else "2021-2022-2"
            score = 78 + ((len(used_course_names) + profile.suffix) % 18)
            await _upsert_student_course(
                session,
                user=user,
                course_name=course_name,
                semester=semester,
                category=category,
                credits=credits,
                score=float(score),
                status="passed",
                is_passed=True,
                course_id=course_id,
            )
            earned += credits
            inserted_or_updated += 1

    if profile.has_failed_course:
        failed = courses[(course_index + profile.suffix) % len(courses)]
        await _upsert_student_course(
            session,
            user=user,
            course_name=f"{failed.course_name}（挂科演示）",
            semester="2024-2025-2",
            category="专业必修",
            credits=_to_float(failed.credits) or 2.0,
            score=52.0,
            status="failed",
            is_passed=False,
            course_id=failed.id,
        )
        inserted_or_updated += 1

    return inserted_or_updated


async def _upsert_schedule(session, *, user: User, course: Course, day: int, start_section: int) -> None:
    result = await session.execute(
        select(Schedule).where(
            Schedule.student_id == user.student_id,
            Schedule.semester == SCENARIO_SEMESTER,
            Schedule.day_of_week == day,
            Schedule.start_section == start_section,
            Schedule.course_name == course.course_name,
        )
    )
    schedule = result.scalars().first()
    if schedule is None:
        schedule = Schedule(
            user_id=user.id,
            student_id=user.student_id,
            course_id=course.id,
            course_name=course.course_name,
            semester=SCENARIO_SEMESTER,
            day_of_week=day,
            start_section=start_section,
            end_section=start_section + 1,
        )
        session.add(schedule)

    schedule.user_id = user.id
    schedule.course_id = course.id
    schedule.teacher = f"演示教师{day}"
    schedule.location = f"教学楼 {day}{start_section:02d}"
    schedule.weeks_text = "1-16周"
    schedule.start_week = 1
    schedule.end_week = 16
    schedule.week_pattern = "all"
    schedule.note = schedule.note or ""


async def _seed_schedule(session, *, user: User, courses: list[Course]) -> int:
    count = 0
    slots = [(1, 1), (1, 3), (2, 5), (3, 1), (4, 7)]
    for index, (day, section) in enumerate(slots):
        await _upsert_schedule(session, user=user, course=courses[(index + 3) % len(courses)], day=day, start_section=section)
        count += 1
    return count


async def _upsert_time_event(
    session,
    *,
    user: User,
    title: str,
    event_type: str,
    start_time: datetime,
    end_time: datetime,
    location: str,
    description: str,
) -> None:
    result = await session.execute(select(TimePlanEvent).where(TimePlanEvent.student_id == user.student_id, TimePlanEvent.title == title))
    event = result.scalars().first()
    if event is None:
        event = TimePlanEvent(student_id=user.student_id, title=title, event_type=event_type, start_time=start_time)
        session.add(event)

    event.user_id = user.id
    event.event_type = event_type
    event.start_time = start_time
    event.end_time = end_time
    event.location = location
    event.description = description
    event.status = "待开始"
    event.source_type = "manual"


async def _seed_time_plan(session, *, user: User) -> int:
    base = datetime(2026, 5, 6, 9, 0)
    events = [
        ("毕业设计中期检查", "作业", base, base + timedelta(hours=2), "线上", "演示数据：提交中期检查材料"),
        ("专业课期末复习", "个人", base + timedelta(days=3), base + timedelta(days=3, hours=2), "图书馆", "演示数据：复习专业核心课程"),
        ("培养方案答疑", "考试", base + timedelta(days=7), base + timedelta(days=7, hours=1), "教学楼 301", "演示数据：模拟重要节点提醒"),
    ]
    for title, event_type, start, end, location, description in events:
        await _upsert_time_event(
            session,
            user=user,
            title=title,
            event_type=event_type,
            start_time=start,
            end_time=end,
            location=location,
            description=description,
        )
    return len(events)


async def cleanup_scenario_data(session) -> dict[str, int]:
    """清理旧版演示账号和本脚本生成的论坛内容，保证覆盖式重建。"""

    cleanup_student_ids = _legacy_student_ids() | _scenario_student_ids()
    user_result = await session.execute(select(User.id).where(User.student_id.in_(cleanup_student_ids)))
    user_ids = [row[0] for row in user_result.all()]

    topic_ids: set[int] = set()
    title_result = await session.execute(select(ForumTopic.id).where(ForumTopic.title.in_(SCENARIO_FORUM_TITLES)))
    topic_ids.update(row[0] for row in title_result.all())
    if user_ids:
        user_topic_result = await session.execute(select(ForumTopic.id).where(ForumTopic.user_id.in_(user_ids)))
        topic_ids.update(row[0] for row in user_topic_result.all())

    removed_files = 0
    if topic_ids:
        file_result = await session.execute(select(ForumFile).where(ForumFile.topic_id.in_(topic_ids)))
        for file_record in file_result.scalars().all():
            file_path = settings.upload_dir / file_record.storage_path
            if file_path.exists():
                file_path.unlink()
                removed_files += 1
        await session.execute(delete(ForumTopicLike).where(ForumTopicLike.topic_id.in_(topic_ids)))
        await session.execute(delete(ForumComment).where(ForumComment.topic_id.in_(topic_ids)))
        await session.execute(delete(ForumFile).where(ForumFile.topic_id.in_(topic_ids)))
        await session.execute(delete(ForumTopic).where(ForumTopic.id.in_(topic_ids)))

    if user_ids:
        conversation_result = await session.execute(select(AIConversation.id).where(AIConversation.user_id.in_(user_ids)))
        conversation_ids = [row[0] for row in conversation_result.all()]
        if conversation_ids:
            await session.execute(delete(AIMessage).where(AIMessage.conversation_id.in_(conversation_ids)))
            await session.execute(delete(AIConversation).where(AIConversation.id.in_(conversation_ids)))
        await session.execute(delete(ErrorCase).where(ErrorCase.user_id.in_(user_ids)))
        await session.execute(delete(ForumTopicLike).where(ForumTopicLike.user_id.in_(user_ids)))
        await session.execute(delete(ForumComment).where(ForumComment.user_id.in_(user_ids)))
        await session.execute(delete(ForumFile).where(ForumFile.uploader_id.in_(user_ids)))

    await session.execute(delete(Schedule).where(Schedule.student_id.in_(cleanup_student_ids)))
    await session.execute(delete(TimePlanEvent).where(TimePlanEvent.student_id.in_(cleanup_student_ids)))
    await session.execute(delete(StudentCourse).where(StudentCourse.student_id.in_(cleanup_student_ids)))
    if user_ids:
        await session.execute(delete(User).where(User.id.in_(user_ids)))

    await session.flush()
    return {"users": len(user_ids), "topics": len(topic_ids), "files": removed_files}


async def _upsert_forum_topic(
    session,
    *,
    user: User,
    major: Major,
    title: str,
    summary: str,
    content: str,
    tags: list[str],
) -> ForumTopic:
    result = await session.execute(select(ForumTopic).where(ForumTopic.title == title))
    topic = result.scalar_one_or_none()
    if topic is None:
        topic = ForumTopic(user_id=user.id, major_id=major.id, title=title, summary=summary, content=content, tags_json=tags)
        session.add(topic)
    topic.user_id = user.id
    topic.major_id = major.id
    topic.summary = summary
    topic.content = content
    topic.tags_json = tags
    topic.status = "normal"
    await session.flush()
    return topic


async def _add_comment_if_missing(session, *, topic: ForumTopic, user: User, content: str) -> None:
    result = await session.execute(select(ForumComment).where(ForumComment.topic_id == topic.id, ForumComment.user_id == user.id, ForumComment.content == content))
    if result.scalar_one_or_none() is None:
        session.add(ForumComment(topic_id=topic.id, user_id=user.id, content=content))
        topic.comment_count += 1


def _forum_attachment_sources() -> list[Path]:
    if not FORUM_ATTACHMENT_SOURCE.exists():
        return []
    return [path for path in FORUM_ATTACHMENT_SOURCE.rglob("*") if path.is_file()][:FORUM_ATTACHMENT_LIMIT]


async def _attach_file_if_missing(session, *, topic: ForumTopic, user: User, source: Path) -> bool:
    result = await session.execute(select(ForumFile).where(ForumFile.topic_id == topic.id, ForumFile.original_name == source.name))
    if result.scalar_one_or_none() is not None:
        return False

    topic_dir = settings.upload_dir / "forum" / str(topic.id)
    topic_dir.mkdir(parents=True, exist_ok=True)
    storage_path = topic_dir / source.name
    if storage_path.exists():
        storage_path = topic_dir / f"scenario_{source.name}"
    shutil.copy2(source, storage_path)
    relative_path = storage_path.relative_to(settings.upload_dir).as_posix()
    session.add(
        ForumFile(
            topic_id=topic.id,
            uploader_id=user.id,
            original_name=source.name,
            storage_path=relative_path,
            file_size=storage_path.stat().st_size,
            mime_type=mimetypes.guess_type(source.name)[0],
        )
    )
    return True


async def seed_electronic_forum(session, users_by_student_id: dict[str, User]) -> dict[str, int]:
    major = await _get_major(session, "080702")
    author = users_by_student_id[_student_id_for("080702", STUDENT_PROFILES[0])]
    commenter = users_by_student_id[_student_id_for("080702", STUDENT_PROFILES[1])]
    junior = users_by_student_id[_student_id_for("080702", STUDENT_PROFILES[2])]

    stats = {"topics": 0, "comments": 0, "attachments": 0}
    topics = [
        (
            SCENARIO_FORUM_TITLES[0],
            "整理了一份传感器课程复习资料，适合考前按题型查漏补缺。",
            "我把电科传感器课的 2023 年试题资料放上来了。建议先看选择和简答，再对照实验题梳理传感器静态特性、灵敏度、线性度这些概念。",
            ["电科", "传感器", "复习资料"],
        ),
        (
            SCENARIO_FORUM_TITLES[1],
            "2022 级临近毕业，大家可以把自己的学分缺口和实践环节进度贴出来互相核对。",
            "我用系统查了一下，通识和专业必修基本没问题，主要担心实践教学和专业任选。有没有同学已经把毕业实习、毕业设计、中期检查这些节点都确认好了？",
            ["毕业要求", "学分自查", "2022级"],
        ),
        (
            SCENARIO_FORUM_TITLES[2],
            "想听听学长学姐对专业限选课和任选课搭配的建议。",
            "如果后面想做嵌入式和传感器方向，是优先补硬件类课程，还是选一点数据处理/通信相关课程更稳？希望大家分享一下自己的选课组合。",
            ["选课建议", "专业限选", "经验交流"],
        ),
    ]

    created_topics: list[ForumTopic] = []
    for title, summary, content, tags in topics:
        topic = await _upsert_forum_topic(session, user=author, major=major, title=title, summary=summary, content=content, tags=tags)
        created_topics.append(topic)
        stats["topics"] += 1

    comments = [
        (created_topics[0], commenter, "感谢分享，我刚好在整理传感器动态特性那部分，试题可以用来对照复习。"),
        (created_topics[1], junior, "2023 级也可以提前看这个帖子，感觉实践学分最好不要拖到最后一个学期。"),
        (created_topics[2], commenter, "如果偏硬件方向，我建议限选课优先选和单片机、传感器接口相关的课，后面做毕设会顺一点。"),
    ]
    for topic, user, content in comments:
        await _add_comment_if_missing(session, topic=topic, user=user, content=content)
        stats["comments"] += 1

    for source in _forum_attachment_sources():
        attached = await _attach_file_if_missing(session, topic=created_topics[0], user=author, source=source)
        if attached:
            stats["attachments"] += 1

    await session.flush()
    return stats


async def seed_scenario_data(session) -> dict[str, int]:
    password_hash = hash_password(DEFAULT_PASSWORD)
    cleanup_stats = await cleanup_scenario_data(session)
    stats = {"admins": 0, "students": 0, "student_courses": 0, "schedules": 0, "time_events": 0, "forum_topics": 0, "forum_comments": 0, "forum_attachments": 0}
    users_by_student_id: dict[str, User] = {}

    first_major = await _get_major(session, TARGET_MAJORS[0][0])
    await _upsert_user(
        session,
        student_id="admin001",
        real_name="教务管理员",
        password_hash=password_hash,
        major_id=first_major.id,
        grade=None,
        role="admin",
    )
    stats["admins"] += 1

    for major_code, major_name in TARGET_MAJORS:
        major = await _get_major(session, major_code)
        requirement = await _get_requirement(session, major)
        courses = await _get_courses(session, major)
        practice_courses = await _get_practice_courses(session, major)

        for profile in STUDENT_PROFILES:
            student_id = _student_id_for(major_code, profile)
            user = await _upsert_user(
                session,
                student_id=student_id,
                real_name=f"{major_name}{profile.name_prefix}{profile.suffix}",
                password_hash=password_hash,
                major_id=major.id,
                grade=profile.grade,
            )
            users_by_student_id[student_id] = user
            stats["students"] += 1
            stats["student_courses"] += await _seed_student_courses(
                session,
                user=user,
                profile=profile,
                requirement=requirement,
                courses=courses,
                practice_courses=practice_courses,
            )
            stats["schedules"] += await _seed_schedule(session, user=user, courses=courses)
            stats["time_events"] += await _seed_time_plan(session, user=user)

    forum_stats = await seed_electronic_forum(session, users_by_student_id)
    stats["forum_topics"] = forum_stats["topics"]
    stats["forum_comments"] = forum_stats["comments"]
    stats["forum_attachments"] = forum_stats["attachments"]
    stats["cleanup_users"] = cleanup_stats["users"]
    stats["cleanup_topics"] = cleanup_stats["topics"]
    stats["cleanup_files"] = cleanup_stats["files"]
    return stats


async def main() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await import_static_data(session)
            stats = await seed_scenario_data(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await async_engine.dispose()

    print(f"scenario_stats={stats}")
    print(f"demo_password={DEFAULT_PASSWORD}")
    print("admin_account=admin001")


if __name__ == "__main__":
    asyncio.run(main())
