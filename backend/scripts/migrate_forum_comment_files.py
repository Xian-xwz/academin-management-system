from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


def main() -> None:
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        db_name = conn.execute(text("select database()")).scalar()
        has_comment_id = conn.execute(
            text(
                """
                select count(*)
                from information_schema.columns
                where table_schema = :db_name
                  and table_name = 'forum_files'
                  and column_name = 'comment_id'
                """
            ),
            {"db_name": db_name},
        ).scalar()
        if not has_comment_id:
            conn.execute(text("alter table forum_files add column comment_id bigint null comment '评论 ID；为空表示话题附件' after topic_id"))
            print("added forum_files.comment_id")
        else:
            print("forum_files.comment_id already exists")

        has_index = conn.execute(
            text(
                """
                select count(*)
                from information_schema.statistics
                where table_schema = :db_name
                  and table_name = 'forum_files'
                  and index_name = 'idx_forum_files_comment_id'
                """
            ),
            {"db_name": db_name},
        ).scalar()
        if not has_index:
            conn.execute(text("create index idx_forum_files_comment_id on forum_files(comment_id)"))
            print("added idx_forum_files_comment_id")
        else:
            print("idx_forum_files_comment_id already exists")
    engine.dispose()


if __name__ == "__main__":
    main()
