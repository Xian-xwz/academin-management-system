from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import async_engine
import app.models  # noqa: F401 确保所有模型注册进 metadata


async def main() -> None:
    expected = set(Base.metadata.tables.keys())

    try:
        async with async_engine.begin() as conn:
            before = set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
            await conn.run_sync(Base.metadata.create_all)
            after = set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
    finally:
        await async_engine.dispose()

    created = sorted(after - before)
    missing = sorted(expected - after)
    extra = sorted(after - expected)

    print(f"expected_tables={len(expected)}")
    print(f"db_tables={len(after)}")
    print(f"created_tables={len(created)}")
    print(f"created={','.join(created)}")
    print(f"missing={','.join(missing)}")
    print(f"extra={','.join(extra)}")

    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
