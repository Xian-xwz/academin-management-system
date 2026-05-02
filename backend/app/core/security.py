from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import get_db
from app.models import User


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class OpenClawClient:
    """OpenClaw 受控工具调用方身份。"""

    name: str = "openclaw"


@dataclass(frozen=True)
class AgentToolClient:
    """Dify Agent 受控工具调用方身份。"""

    name: str = "dify-agent"


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_agent_session_token(user: User) -> tuple[str, datetime]:
    """签发短期 Agent 会话令牌，用于把公共 Bot 工具调用绑定到当前登录用户。"""

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.agent_session_expire_minutes)
    payload = {
        "typ": "agent_session",
        "sub": str(user.id),
        "student_id": user.student_id,
        "role": user.role,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires_at


def decode_agent_session_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent 会话令牌无效或已过期") from None
    if payload.get("typ") != "agent_session":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent 会话令牌类型无效")
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少认证 Token")

    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证 Token 无效") from None

    result = await db.execute(
        select(User)
        .options(selectinload(User.major))
        .where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问该接口")
    return current_user


async def require_openclaw_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> OpenClawClient:
    if not settings.openclaw_tool_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenClaw 工具令牌未配置")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 OpenClaw 工具令牌")
    if not compare_digest(credentials.credentials, settings.openclaw_tool_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OpenClaw 工具令牌无效")
    return OpenClawClient()


async def require_agent_tool_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AgentToolClient:
    if not settings.agent_tool_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent 工具令牌未配置")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Agent 工具令牌")
    if not compare_digest(credentials.credentials, settings.agent_tool_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent 工具令牌无效")
    return AgentToolClient()
