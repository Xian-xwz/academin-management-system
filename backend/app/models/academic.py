from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Major(TimestampMixin, Base):
    """专业基础信息，来源于培养方案结构化数据。"""

    __tablename__ = "majors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    major_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
        comment="专业代码",
    )
    major_name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="专业名称",
    )
    major_category: Mapped[str | None] = mapped_column(String(100), comment="专业类别")
    degree: Mapped[str | None] = mapped_column(String(100), comment="授予学位")
    school_system: Mapped[str | None] = mapped_column(String(50), comment="学制")
    source_file: Mapped[str | None] = mapped_column(String(255), comment="来源文件")
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否需要人工复核",
    )
    raw_json: Mapped[dict | None] = mapped_column(JSON, comment="原始结构化数据")

    users: Mapped[list["User"]] = relationship(back_populates="major")
    graduation_requirements: Mapped[list["GraduationRequirement"]] = relationship(
        back_populates="major",
    )
    courses: Mapped[list["Course"]] = relationship(back_populates="major")
    practice_courses: Mapped[list["PracticeCourse"]] = relationship(back_populates="major")


class GraduationRequirement(TimestampMixin, Base):
    """毕业要求宽表，供毕业进度计算直接读取。"""

    __tablename__ = "graduation_requirements"
    __table_args__ = (
        UniqueConstraint("major_id", "grade", "version", name="uk_major_grade_requirement_version"),
        Index("idx_graduation_major_grade", "major_id", "grade"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    major_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("majors.id"),
        nullable=False,
        comment="专业 ID",
    )
    grade: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="通用",
        server_default="通用",
        comment="适用年级，例如 2021级；通用表示未区分年级",
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="default",
        server_default="default",
        comment="培养方案版本标识",
    )
    total_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="毕业总学分")
    theory_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="理论教学学分")
    practice_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="实践教学学分")
    general_required_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="通识必修学分")
    general_elective_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="通识选修学分")
    major_basic_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="专业基础学分")
    major_required_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="专业必修学分")
    major_limited_elective_credits: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1),
        comment="专业限选学分",
    )
    major_optional_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="专业任选学分")
    other_requirements: Mapped[str | None] = mapped_column(Text, comment="其他毕业要求")
    source_file: Mapped[str | None] = mapped_column(String(255), comment="来源文件")
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否需要人工复核",
    )
    raw_json: Mapped[dict | None] = mapped_column(JSON, comment="原始结构化数据")

    major: Mapped[Major] = relationship(back_populates="graduation_requirements")


class Course(TimestampMixin, Base):
    """理论课程与课程分类，按专业保留课程归属。"""

    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("major_id", "course_code", "course_name", "module", name="uk_major_course_module"),
        Index("idx_courses_major_category", "major_id", "course_category"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    major_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("majors.id"),
        index=True,
        nullable=False,
        comment="专业 ID",
    )
    course_code: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        default="",
        server_default="",
        comment="课程代码；无代码时为空字符串以便唯一约束去重",
    )
    course_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False, comment="课程名称")
    course_category: Mapped[str | None] = mapped_column(String(50), comment="课程类别")
    module: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        server_default="",
        comment="课程模块；无模块时为空字符串以便唯一约束去重",
    )
    course_nature: Mapped[str | None] = mapped_column(String(50), comment="课程性质")
    credits: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False, default=0, comment="学分")
    theory_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), comment="理论学时")
    practice_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), comment="实践学时")
    suggested_semester: Mapped[str | None] = mapped_column(String(50), comment="建议修读学期")
    assessment_type: Mapped[str | None] = mapped_column(String(50), comment="考核方式")
    source_file: Mapped[str | None] = mapped_column(String(255), comment="来源文件")
    raw_json: Mapped[dict | None] = mapped_column(JSON, comment="原始结构化数据")

    major: Mapped[Major] = relationship(back_populates="courses")
    student_courses: Mapped[list["StudentCourse"]] = relationship(back_populates="course")


class PracticeCourse(TimestampMixin, Base):
    """实践教学环节，独立于理论课程保存。"""

    __tablename__ = "practice_courses"
    __table_args__ = (
        UniqueConstraint("major_id", "item_name", "module", "suggested_semester", name="uk_major_practice_item"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    major_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("majors.id"),
        index=True,
        nullable=False,
        comment="专业 ID",
    )
    item_name: Mapped[str] = mapped_column(String(150), nullable=False, comment="实践项目名称")
    module: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        server_default="",
        comment="实践模块；无模块时为空字符串以便唯一约束去重",
    )
    credits: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False, default=0, comment="学分")
    weeks: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), comment="周数")
    hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), comment="学时")
    suggested_semester: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
        server_default="",
        comment="建议修读学期；无数据时为空字符串以便唯一约束去重",
    )
    requirement_note: Mapped[str | None] = mapped_column(Text, comment="要求说明")
    source_file: Mapped[str | None] = mapped_column(String(255), comment="来源文件")
    raw_json: Mapped[dict | None] = mapped_column(JSON, comment="原始结构化数据")

    major: Mapped[Major] = relationship(back_populates="practice_courses")


class StudentCourse(TimestampMixin, Base):
    """学生已修/在修课程记录，是毕业进度计算的直接依据。"""

    __tablename__ = "student_courses"
    __table_args__ = (
        Index("idx_student_course_semester", "student_id", "course_name", "semester"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        comment="用户 ID",
    )
    student_id: Mapped[str] = mapped_column(String(30), index=True, nullable=False, comment="学号")
    course_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("courses.id"), comment="课程 ID")
    course_name: Mapped[str] = mapped_column(String(150), nullable=False, comment="课程名称快照")
    course_category: Mapped[str | None] = mapped_column(String(50), comment="课程类别快照")
    credits: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False, default=0, comment="学分快照")
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="成绩")
    grade_point: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), comment="绩点")
    semester: Mapped[str | None] = mapped_column(String(50), comment="修读学期")
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="passed",
        comment="状态：passed/failed/in_progress/withdrawn",
    )
    is_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否通过")

    course: Mapped[Course | None] = relationship(back_populates="student_courses")
