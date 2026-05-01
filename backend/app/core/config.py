from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def _load_env_file() -> dict[str, str]:
    """读取项目根目录 .env，兼容 KEY=value 和当前注释形式的 MySQL 配置。"""

    env_path = PROJECT_ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
            continue

        if line.startswith("#"):
            uncommented = line[1:].strip()
            if ":" in uncommented:
                key, value = uncommented.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key in {"host", "port", "user", "password", "database", "charset"}:
                    values[f"MYSQL_{key.upper()}"] = value

    return values


def _get_config_value(file_values: dict[str, str], key: str, default: str | None = None) -> str | None:
    return os.getenv(key) or file_values.get(key) or default


def _build_mysql_url(file_values: dict[str, str], driver: str) -> URL:
    host = _get_config_value(file_values, "MYSQL_HOST", "127.0.0.1")
    port = int(_get_config_value(file_values, "MYSQL_PORT", "3306") or "3306")
    username = _get_config_value(file_values, "MYSQL_USER", "root")
    password = _get_config_value(file_values, "MYSQL_PASSWORD", "")
    database = _get_config_value(file_values, "MYSQL_DATABASE", "")
    charset = _get_config_value(file_values, "MYSQL_CHARSET", "utf8mb4")

    if not database:
        raise RuntimeError("缺少数据库名，请设置 DATABASE_URL 或 MYSQL_DATABASE")

    return URL.create(
        drivername=driver,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"charset": charset or "utf8mb4"},
    )


def _coerce_driver(url: str, driver: str) -> URL:
    parsed = make_url(url)
    return parsed.set(drivername=driver)


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_prefix: str
    cors_origins: list[str]
    async_database_url: URL
    sync_database_url: URL
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    dify_app_api_base: str
    dify_app_api_key: str | None
    dify_app_api_id: str | None
    dify_timeout_seconds: float
    upload_dir: Path
    max_upload_size_mb: int
    openclaw_tool_token: str | None
    openclaw_allowed_student_ids: set[str]


def load_settings() -> Settings:
    file_values = _load_env_file()
    database_url = _get_config_value(file_values, "DATABASE_URL")

    async_url = _coerce_driver(database_url, "mysql+aiomysql") if database_url else _build_mysql_url(file_values, "mysql+aiomysql")
    sync_url = _coerce_driver(database_url, "mysql+pymysql") if database_url else _build_mysql_url(file_values, "mysql+pymysql")

    origins_raw = _get_config_value(file_values, "BACKEND_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = [origin.strip() for origin in (origins_raw or "").split(",") if origin.strip()]
    openclaw_students_raw = _get_config_value(file_values, "OPENCLAW_ALLOWED_STUDENT_IDS", "")
    openclaw_allowed_student_ids = {
        student_id.strip()
        for student_id in (openclaw_students_raw or "").split(",")
        if student_id.strip()
    }

    return Settings(
        app_name=_get_config_value(file_values, "APP_NAME", "AI 学业管理系统后端") or "AI 学业管理系统后端",
        api_prefix=_get_config_value(file_values, "API_PREFIX", "/api") or "/api",
        cors_origins=cors_origins,
        async_database_url=async_url,
        sync_database_url=sync_url,
        jwt_secret_key=_get_config_value(file_values, "JWT_SECRET_KEY", "dev-secret-key-change-me") or "dev-secret-key-change-me",
        jwt_algorithm=_get_config_value(file_values, "JWT_ALGORITHM", "HS256") or "HS256",
        access_token_expire_minutes=int(_get_config_value(file_values, "ACCESS_TOKEN_EXPIRE_MINUTES", "1440") or "1440"),
        dify_app_api_base=(_get_config_value(file_values, "DIFY_APP_API_BASE", "https://api.dify.ai/v1") or "https://api.dify.ai/v1").rstrip("/"),
        dify_app_api_key=_get_config_value(file_values, "DIFY_APP_API_KEY"),
        dify_app_api_id=_get_config_value(file_values, "DIFY_APP_API_ID"),
        dify_timeout_seconds=float(_get_config_value(file_values, "DIFY_TIMEOUT_SECONDS", "60") or "60"),
        upload_dir=Path(_get_config_value(file_values, "UPLOAD_DIR", str(BACKEND_ROOT / "storage")) or str(BACKEND_ROOT / "storage")),
        max_upload_size_mb=int(_get_config_value(file_values, "MAX_UPLOAD_SIZE_MB", "50") or "50"),
        openclaw_tool_token=_get_config_value(file_values, "OPENCLAW_TOOL_TOKEN"),
        openclaw_allowed_student_ids=openclaw_allowed_student_ids,
    )


settings = load_settings()
