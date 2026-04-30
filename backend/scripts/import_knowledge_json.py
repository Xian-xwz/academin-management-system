from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal, async_engine
from app.models import Course, GraduationRequirement, Major, PracticeCourse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def _load_json(name: str) -> list[dict]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _text(value: object) -> str:
    return str(value or "").strip()


def _limit(value: object, max_length: int) -> str:
    return _text(value)[:max_length]


async def import_majors(session) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for item in _load_json("majors.json"):
        result = await session.execute(select(Major).where(Major.major_code == item["major_code"]))
        major = result.scalar_one_or_none()
        if major is None:
            major = Major(major_code=_limit(item["major_code"], 30), major_name=_limit(item["major_name"], 100))
            session.add(major)
            inserted += 1
        else:
            updated += 1

        major.major_name = _limit(item["major_name"], 100)
        major.major_category = _limit(item.get("major_category"), 100) or None
        major.degree = _limit(item.get("degree"), 100) or None
        major.school_system = _limit(item.get("school_system"), 50) or None
        major.source_file = _limit(item.get("source_file"), 255) or None
        major.needs_review = bool(item.get("needs_review", False))
        major.raw_json = item
    await session.flush()
    return inserted, updated


async def _major_map(session) -> dict[str, Major]:
    result = await session.execute(select(Major))
    return {major.major_code: major for major in result.scalars().all()}


async def import_graduation_requirements(session, majors: dict[str, Major]) -> tuple[int, int, int]:
    inserted = 0
    updated = 0
    skipped = 0
    for item in _load_json("graduation_requirements.json"):
        major = majors.get(item["major_code"])
        if major is None:
            skipped += 1
            continue

        grade = _text(item.get("grade")) or "通用"
        version = _text(item.get("version")) or "default"
        result = await session.execute(
            select(GraduationRequirement).where(
                GraduationRequirement.major_id == major.id,
                GraduationRequirement.grade == grade,
                GraduationRequirement.version == version,
            )
        )
        requirement = result.scalar_one_or_none()
        if requirement is None:
            requirement = GraduationRequirement(major_id=major.id, grade=grade, version=version)
            session.add(requirement)
            inserted += 1
        else:
            updated += 1

        for field in [
            "total_credits",
            "theory_credits",
            "practice_credits",
            "general_required_credits",
            "general_elective_credits",
            "major_basic_credits",
            "major_required_credits",
            "major_limited_elective_credits",
            "major_optional_credits",
        ]:
            setattr(requirement, field, item.get(field))
        requirement.other_requirements = item.get("other_requirements")
        requirement.source_file = _limit(item.get("source_file"), 255) or None
        requirement.needs_review = bool(item.get("needs_review", False))
        requirement.raw_json = item
    await session.flush()
    return inserted, updated, skipped


async def import_courses(session, majors: dict[str, Major]) -> tuple[int, int, int]:
    processed = 0
    updated = 0
    skipped = 0
    for item in _load_json("courses.json"):
        major = majors.get(item["major_code"])
        if major is None:
            skipped += 1
            continue

        values = {
            "major_id": major.id,
            "course_code": _limit(item.get("course_code"), 50),
            "course_name": _limit(item.get("course_name"), 150),
            "module": _limit(item.get("module"), 100),
            "course_category": _limit(item.get("course_type"), 50) or None,
            "course_nature": _limit(item.get("course_type"), 50) or None,
            "credits": item.get("credits") or 0,
            "theory_hours": item.get("lecture_hours") or item.get("hours"),
            "practice_hours": item.get("practice_hours"),
            "suggested_semester": _limit(item.get("semester"), 50) or None,
            "assessment_type": _limit(item.get("assessment"), 50) or None,
            "source_file": _limit(item.get("source_file"), 255) or None,
            "raw_json": item,
        }
        stmt = mysql_insert(Course).values(**values)
        await session.execute(
            stmt.on_duplicate_key_update(
                course_category=stmt.inserted.course_category,
                course_nature=stmt.inserted.course_nature,
                credits=stmt.inserted.credits,
                theory_hours=stmt.inserted.theory_hours,
                practice_hours=stmt.inserted.practice_hours,
                suggested_semester=stmt.inserted.suggested_semester,
                assessment_type=stmt.inserted.assessment_type,
                source_file=stmt.inserted.source_file,
                raw_json=stmt.inserted.raw_json,
            )
        )
        processed += 1
    await session.flush()
    return processed, updated, skipped


async def import_practice_courses(session, majors: dict[str, Major]) -> tuple[int, int, int]:
    processed = 0
    updated = 0
    skipped = 0
    for item in _load_json("practice_courses.json"):
        major = majors.get(item["major_code"])
        if major is None:
            skipped += 1
            continue

        values = {
            "major_id": major.id,
            "item_name": _limit(item.get("practice_name"), 150),
            "module": _limit(item.get("module"), 100),
            "suggested_semester": _limit(item.get("semester"), 50),
            "credits": item.get("credits") or 0,
            "weeks": item.get("weeks"),
            "requirement_note": item.get("organization"),
            "source_file": _limit(item.get("source_file"), 255) or None,
            "raw_json": item,
        }
        stmt = mysql_insert(PracticeCourse).values(**values)
        await session.execute(
            stmt.on_duplicate_key_update(
                credits=stmt.inserted.credits,
                weeks=stmt.inserted.weeks,
                requirement_note=stmt.inserted.requirement_note,
                source_file=stmt.inserted.source_file,
                raw_json=stmt.inserted.raw_json,
            )
        )
        processed += 1
    await session.flush()
    return processed, updated, skipped


async def main() -> None:
    async with AsyncSessionLocal() as session:
        try:
            major_stats = await import_majors(session)
            majors = await _major_map(session)
            requirement_stats = await import_graduation_requirements(session, majors)
            course_stats = await import_courses(session, majors)
            practice_stats = await import_practice_courses(session, majors)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await async_engine.dispose()

    print(f"majors inserted={major_stats[0]} updated={major_stats[1]}")
    print(f"graduation_requirements inserted={requirement_stats[0]} updated={requirement_stats[1]} skipped={requirement_stats[2]}")
    print(f"courses inserted={course_stats[0]} updated={course_stats[1]} skipped={course_stats[2]}")
    print(f"practice_courses inserted={practice_stats[0]} updated={practice_stats[1]} skipped={practice_stats[2]}")


if __name__ == "__main__":
    asyncio.run(main())
