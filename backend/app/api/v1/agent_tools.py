from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.responses import success
from app.core.security import (
    AgentToolClient,
    create_agent_session_token,
    decode_agent_session_token,
    get_current_user,
    require_agent_tool_client,
)
from app.db.session import get_db
from app.models import User
from app.schemas.forum import ForumCommentCreate, ForumTopicCreate, ForumTopicUpdate
from app.schemas.time_plan import TimePlanEventCreate, TimePlanEventUpdate
from app.services.academic import graduation_progress_service
from app.services.admin import admin_service
from app.services.forum import forum_service
from app.services.openclaw import openclaw_tool_service
from app.services.schedule import schedule_service
from app.services.time_plan import time_plan_service


router = APIRouter(prefix="/agent-tools", tags=["agent-tools"])


class AgentBoundPayload(BaseModel):
    agentSessionToken: str = Field(min_length=1, description="后端签发的短期 Agent 会话令牌")


class AgentForumTopicCreate(ForumTopicCreate, AgentBoundPayload):
    pass


class AgentForumTopicUpdate(ForumTopicUpdate, AgentBoundPayload):
    pass


class AgentForumCommentCreate(ForumCommentCreate, AgentBoundPayload):
    pass


class AgentTimePlanEventCreate(TimePlanEventCreate, AgentBoundPayload):
    pass


class AgentTimePlanEventUpdate(TimePlanEventUpdate, AgentBoundPayload):
    pass


class AgentForumModerateRequest(AgentBoundPayload):
    status: str = Field(description="帖子状态，仅支持 normal 或 deleted")
    reason: str | None = Field(default=None, max_length=200, description="治理原因，仅用于审计摘要")


def _user_summary(user: User) -> dict[str, Any]:
    return {
        "userId": user.id,
        "studentId": user.student_id,
        "username": user.username,
        "realName": user.real_name,
        "role": user.role,
        "majorCode": user.major.major_code if user.major else None,
        "majorName": user.major.major_name if user.major else None,
        "grade": user.grade,
        "avatarUrl": user.avatar_url,
        "canManageForum": user.role == "admin",
        "canTargetUsers": user.role == "admin",
    }


async def _bound_user(db: AsyncSession, agent_session_token: str) -> User:
    payload = decode_agent_session_token(agent_session_token)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent 会话令牌缺少用户身份") from None

    result = await db.execute(
        select(User)
        .options(selectinload(User.major))
        .where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent 绑定用户不存在或已禁用")
    if payload.get("student_id") != user.student_id or payload.get("role") != user.role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent 会话令牌与当前用户状态不一致")
    return user


async def _run_agent_tool(
    *,
    db: AsyncSession,
    client: AgentToolClient,
    user: User,
    tool_name: str,
    request_summary: dict | None,
    operation,
    audit_student_id: str | None = None,
):
    return await openclaw_tool_service.run_with_audit(
        db=db,
        client=client,
        tool_name=tool_name,
        student_id=audit_student_id or user.student_id,
        request_summary=request_summary,
        operation=operation,
    )


async def _admin_bound_user(db: AsyncSession, agent_session_token: str) -> User:
    user = await _bound_user(db, agent_session_token)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员 Agent 可查询目标学生数据")
    return user


async def _target_student(db: AsyncSession, student_id: str) -> User:
    result = await db.execute(
        select(User)
        .options(selectinload(User.major))
        .where(User.student_id == student_id, User.role == "student", User.is_active.is_(True))
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到目标学生")
    return student


@router.post("/sessions")
async def create_agent_session(current_user: User = Depends(get_current_user)) -> dict:
    token, expires_at = create_agent_session_token(current_user)
    return success(
        {
            "agentSessionToken": token,
            "expiresAt": expires_at.isoformat(),
            "expiresInMinutes": settings.agent_session_expire_minutes,
            "user": _user_summary(current_user),
        }
    )


@router.get("/me")
async def get_bound_user(
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> dict:
        return _user_summary(user)

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me",
            request_summary={},
            operation=operation,
        )
    )


@router.get("/me/academic-info")
async def get_my_academic_info(
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> dict:
        return (await graduation_progress_service.get_academic_info(db, user.student_id)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me.academic_info",
            request_summary={},
            operation=operation,
        )
    )


@router.get("/me/graduation-progress")
async def get_my_graduation_progress(
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> dict:
        return (await graduation_progress_service.calculate(db, user.student_id)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me.graduation_progress",
            request_summary={},
            operation=operation,
        )
    )


@router.get("/me/schedule")
async def get_my_schedule(
    agentSessionToken: str = Query(..., min_length=1),
    term: str = Query(..., min_length=1),
    week: int = Query(1, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> dict:
        return (await schedule_service.get_schedule(db, user, term, week)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me.schedule",
            request_summary={"term": term, "week": week},
            operation=operation,
        )
    )


@router.get("/me/time-plan/events")
async def list_my_time_plan_events(
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> list[dict]:
        return [item.model_dump() for item in await time_plan_service.list_events(db, user)]

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me.time_plan_events",
            request_summary={},
            operation=operation,
        )
    )


@router.get("/admin/students/{student_id}/academic-info")
async def admin_get_student_academic_info(
    student_id: str,
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    admin_user = await _admin_bound_user(db, agentSessionToken)
    target_student = await _target_student(db, student_id)

    async def operation() -> dict:
        return (await graduation_progress_service.get_academic_info(db, target_student.student_id)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=admin_user,
            tool_name="agent.admin.students.academic_info",
            request_summary={"targetStudentId": target_student.student_id},
            operation=operation,
            audit_student_id=target_student.student_id,
        )
    )


@router.get("/admin/students/{student_id}/graduation-progress")
async def admin_get_student_graduation_progress(
    student_id: str,
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    admin_user = await _admin_bound_user(db, agentSessionToken)
    target_student = await _target_student(db, student_id)

    async def operation() -> dict:
        return (await graduation_progress_service.calculate(db, target_student.student_id)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=admin_user,
            tool_name="agent.admin.students.graduation_progress",
            request_summary={"targetStudentId": target_student.student_id},
            operation=operation,
            audit_student_id=target_student.student_id,
        )
    )


@router.get("/admin/students/{student_id}/schedule")
async def admin_get_student_schedule(
    student_id: str,
    agentSessionToken: str = Query(..., min_length=1),
    term: str = Query(..., min_length=1),
    week: int = Query(1, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    admin_user = await _admin_bound_user(db, agentSessionToken)
    target_student = await _target_student(db, student_id)

    async def operation() -> dict:
        return (await schedule_service.get_schedule(db, target_student, term, week)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=admin_user,
            tool_name="agent.admin.students.schedule",
            request_summary={"targetStudentId": target_student.student_id, "term": term, "week": week},
            operation=operation,
            audit_student_id=target_student.student_id,
        )
    )


@router.get("/admin/students/{student_id}/time-plan/events")
async def admin_list_student_time_plan_events(
    student_id: str,
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    admin_user = await _admin_bound_user(db, agentSessionToken)
    target_student = await _target_student(db, student_id)

    async def operation() -> list[dict]:
        return [item.model_dump() for item in await time_plan_service.list_events(db, target_student)]

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=admin_user,
            tool_name="agent.admin.students.time_plan_events",
            request_summary={"targetStudentId": target_student.student_id},
            operation=operation,
            audit_student_id=target_student.student_id,
        )
    )


@router.post("/me/time-plan/events")
async def create_my_time_plan_event(
    payload: AgentTimePlanEventCreate,
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, payload.agentSessionToken)

    async def operation() -> dict:
        request = TimePlanEventCreate(**payload.model_dump(exclude={"agentSessionToken"}))
        return (await time_plan_service.create_event(db, user, request)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me.time_plan_events.create",
            request_summary={"title": payload.title, "type": payload.type, "startTime": payload.startTime.isoformat()},
            operation=operation,
        )
    )


@router.put("/me/time-plan/events/{event_id}")
async def update_my_time_plan_event(
    event_id: int,
    payload: AgentTimePlanEventUpdate,
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, payload.agentSessionToken)

    async def operation() -> dict:
        request = TimePlanEventUpdate(**payload.model_dump(exclude={"agentSessionToken"}, exclude_unset=True))
        return (await time_plan_service.update_event(db, user, event_id, request)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.me.time_plan_events.update",
            request_summary={"eventId": event_id, "fields": sorted(payload.model_dump(exclude={"agentSessionToken"}, exclude_unset=True).keys())},
            operation=operation,
        )
    )


@router.get("/forum/majors")
async def list_forum_majors(
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> list[dict[str, str]]:
        return await forum_service.list_majors(db)

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.forum.majors",
            request_summary={},
            operation=operation,
        )
    )


@router.get("/forum/topics")
async def list_forum_topics(
    agentSessionToken: str = Query(..., min_length=1),
    q: str | None = None,
    major: str | None = None,
    sort: str = Query("latest", pattern="^(latest|hot)$"),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> list[dict]:
        return [item.model_dump() for item in await forum_service.list_topics(db, user, q, major, sort)]

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.forum.topics.list",
            request_summary={"q": q, "major": major, "sort": sort},
            operation=operation,
        )
    )


@router.get("/forum/topics/{topic_id}")
async def get_forum_topic(
    topic_id: int,
    agentSessionToken: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, agentSessionToken)

    async def operation() -> dict:
        return (await forum_service.get_topic(db, user, topic_id)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.forum.topics.get",
            request_summary={"topicId": topic_id},
            operation=operation,
        )
    )


@router.post("/forum/topics")
async def create_forum_topic(
    payload: AgentForumTopicCreate,
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, payload.agentSessionToken)

    async def operation() -> dict:
        request = ForumTopicCreate(**payload.model_dump(exclude={"agentSessionToken"}))
        return (await forum_service.create_topic(db, user, request)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.forum.topics.create",
            request_summary={"title": payload.title, "major": payload.major, "contentLength": len(payload.content)},
            operation=operation,
        )
    )


@router.put("/forum/topics/{topic_id}")
async def update_forum_topic(
    topic_id: int,
    payload: AgentForumTopicUpdate,
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, payload.agentSessionToken)

    async def operation() -> dict:
        request = ForumTopicUpdate(**payload.model_dump(exclude={"agentSessionToken"}, exclude_unset=True))
        return (await forum_service.update_topic(db, user, topic_id, request)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.forum.topics.update",
            request_summary={"topicId": topic_id, "fields": sorted(payload.model_dump(exclude={"agentSessionToken"}, exclude_unset=True).keys())},
            operation=operation,
        )
    )


@router.post("/forum/topics/{topic_id}/comments")
async def create_forum_comment(
    topic_id: int,
    payload: AgentForumCommentCreate,
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, payload.agentSessionToken)

    async def operation() -> dict:
        request = ForumCommentCreate(**payload.model_dump(exclude={"agentSessionToken"}))
        return (await forum_service.add_comment(db, user, topic_id, request)).model_dump()

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.forum.comments.create",
            request_summary={"topicId": topic_id, "contentLength": len(payload.content), "parentId": payload.parent_id},
            operation=operation,
        )
    )


@router.patch("/admin/forum/topics/{topic_id}")
async def moderate_forum_topic(
    topic_id: int,
    payload: AgentForumModerateRequest,
    db: AsyncSession = Depends(get_db),
    client: AgentToolClient = Depends(require_agent_tool_client),
) -> dict:
    user = await _bound_user(db, payload.agentSessionToken)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员 Agent 可治理论坛")

    status_value = payload.status.strip()
    if status_value not in {"normal", "deleted"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status 仅允许为 normal 或 deleted")

    async def operation() -> dict:
        return await admin_service.set_forum_topic_status(db, topic_id, status_value)

    return success(
        await _run_agent_tool(
            db=db,
            client=client,
            user=user,
            tool_name="agent.admin.forum.topics.moderate",
            request_summary={"topicId": topic_id, "status": status_value, "reason": payload.reason},
            operation=operation,
        )
    )
