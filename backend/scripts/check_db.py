from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import async_engine
import app.models  # noqa: F401 确保所有模型注册进 metadata


async def main() -> None:
    expected = set(Base.metadata.tables.keys())

    try:
        async with async_engine.connect() as conn:
            version = (await conn.execute(text("SELECT VERSION()"))).scalar_one()
            database = (await conn.execute(text("SELECT DATABASE()"))).scalar_one()
            current_user = (await conn.execute(text("SELECT CURRENT_USER()"))).scalar_one()
            tables = set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
    finally:
        await async_engine.dispose()

    missing = sorted(expected - tables)
    extra = sorted(tables - expected)

    print("db=ok")
    print(f"database={database}")
    print(f"mysql_version={version}")
    print(f"current_user={current_user}")
    print(f"expected_tables={len(expected)}")
    print(f"db_tables={len(tables)}")
    print(f"missing={','.join(missing)}")
    print(f"extra={','.join(extra)}")

    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
