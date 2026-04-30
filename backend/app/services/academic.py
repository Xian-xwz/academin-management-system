from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GraduationRequirement, StudentCourse, User
from app.schemas.academic import (
    AcademicInfoResponse,
    BaseInfo,
    CategoryStatistic,
    CourseInfo,
    GraduationProgressResponse,
    GraduationRequirementInfo,
    Suggestion,
)


def _to_float(value: Decimal | int | float | None) -> float:
    return float(value or 0)


class GraduationProgressService:
    async def calculate(self, db: AsyncSession, student_id: str) -> GraduationProgressResponse:
        user, requirement, courses = await self._load_student_context(db, student_id)

        passed_courses = [course for course in courses if course.is_passed and course.status == "passed"]
        earned_by_category: dict[str, float] = defaultdict(float)
        for course in passed_courses:
            category = course.course_category or "未分类"
            earned_by_category[category] += _to_float(course.credits)

        total_required = _to_float(requirement.total_credits)
        total_earned = sum(earned_by_category.values())

        required_by_category = self._required_categories(requirement)
        category_breakdown = [
            CategoryStatistic(
                category=category,
                earned=round(earned_by_category.get(category, 0), 1),
                total=round(total, 1),
            )
            for category, total in required_by_category.items()
        ]

        suggestions = [
            Suggestion(category=item.category, gap=round(max(item.total - item.earned, 0), 1), desc=f"{item.category}还差 {round(max(item.total - item.earned, 0), 1)} 学分")
            for item in category_breakdown
            if item.total > 0 and item.earned < item.total
        ]

        return GraduationProgressResponse(
            studentId=student_id,
            majorCode=user.major.major_code if user.major else None,
            majorName=user.major.major_name if user.major else None,
            totalRequired=round(total_required, 1),
            totalEarned=round(total_earned, 1),
            totalGap=round(max(total_required - total_earned, 0), 1),
            categoryBreakdown=category_breakdown,
            missingItems=suggestions,
        )

    async def get_academic_info(self, db: AsyncSession, student_id: str) -> AcademicInfoResponse:
        user, requirement, courses = await self._load_student_context(db, student_id)
        progress = await self.calculate(db, student_id)
        passed_courses = [course for course in courses if course.is_passed and course.status == "passed"]

        return AcademicInfoResponse(
            baseInfo=BaseInfo(
                name=user.real_name or user.username,
                studentId=user.student_id,
                major=user.major.major_name if user.major else None,
                grade=user.grade,
            ),
            graduationReq=GraduationRequirementInfo(
                total=_to_float(requirement.total_credits),
                earned=progress.totalEarned,
                compulsory=round(_to_float(requirement.general_required_credits) + _to_float(requirement.major_basic_credits) + _to_float(requirement.major_required_credits), 1),
                elective=round(_to_float(requirement.general_elective_credits) + _to_float(requirement.major_limited_elective_credits) + _to_float(requirement.major_optional_credits), 1),
                practice=_to_float(requirement.practice_credits),
            ),
            courses=[
                CourseInfo(
                    name=course.course_name,
                    category=course.course_category,
                    credit=_to_float(course.credits),
                    score=_to_float(course.score) if course.score is not None else None,
                    term=course.semester,
                )
                for course in passed_courses
            ],
            statistics=progress.categoryBreakdown,
            suggestions=progress.missingItems,
        )

    async def _load_student_context(self, db: AsyncSession, student_id: str) -> tuple[User, GraduationRequirement, list[StudentCourse]]:
        user_result = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(User.student_id == student_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该学号对应的用户")
        if user.major is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该用户尚未绑定专业")

        requirement = await self._get_requirement(db, user)
        course_result = await db.execute(select(StudentCourse).where(StudentCourse.student_id == student_id))
        return user, requirement, list(course_result.scalars().all())

    async def _get_requirement(self, db: AsyncSession, user: User) -> GraduationRequirement:
        grades = [user.grade, "通用", None]
        for grade in grades:
            if not grade:
                continue
            result = await db.execute(
                select(GraduationRequirement)
                .where(
                    GraduationRequirement.major_id == user.major_id,
                    GraduationRequirement.grade == grade,
                )
                .order_by(GraduationRequirement.version.desc())
            )
            requirement = result.scalars().first()
            if requirement is not None:
                return requirement

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该专业对应的毕业要求")

    def _required_categories(self, requirement: GraduationRequirement) -> dict[str, float]:
        return {
            "通识必修": _to_float(requirement.general_required_credits),
            "通识选修": _to_float(requirement.general_elective_credits),
            "专业基础": _to_float(requirement.major_basic_credits),
            "专业必修": _to_float(requirement.major_required_credits),
            "专业限选": _to_float(requirement.major_limited_elective_credits),
            "专业任选": _to_float(requirement.major_optional_credits),
            "实践教学": _to_float(requirement.practice_credits),
        }


graduation_progress_service = GraduationProgressService()
