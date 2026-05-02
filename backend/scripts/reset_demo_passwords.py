from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import User


DEFAULT_PASSWORD = "guangdong11"
TARGET_MAJORS = ["080702", "080901", "080902"]
MAJOR_STUDENT_CODE = {
    "080702": "1191",
    "080901": "1192",
    "080902": "1193",
}


def _legacy_student_ids() -> set[str]:
    return {
        f"2021{major_code[-4:]}{suffix:02d}"
        for major_code in TARGET_MAJORS
        for suffix in range(1, 7)
    }


def _scenario_student_ids() -> set[str]:
    sequence_by_suffix = {
        1: ("2022", "1001"),
        2: ("2022", "1002"),
        3: ("2023", "1001"),
        4: ("2024", "1001"),
        5: ("2023", "1002"),
        6: ("2022", "1003"),
    }
    return {
        f"{entry_year}{MAJOR_STUDENT_CODE[major_code]}{sequence}"
        for major_code in TARGET_MAJORS
        for entry_year, sequence in sequence_by_suffix.values()
    }


DEMO_USER_IDS = {"admin001", "2021000001", "2021000002", "2021000003"} | _legacy_student_ids() | _scenario_student_ids()


async def reset_demo_passwords() -> None:
    password_hash = hash_password(DEFAULT_PASSWORD)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.student_id.in_(DEMO_USER_IDS)))
        users = list(result.scalars().all())
        for user in users:
            user.password_hash = password_hash
        await session.commit()
        print(f"updated_users={len(users)}")
        print(f"demo_password={DEFAULT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(reset_demo_passwords())
