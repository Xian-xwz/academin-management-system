from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


def _table_exists(conn, db_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                """
                select count(*)
                from information_schema.tables
                where table_schema = :db_name
                  and table_name = 'knowledge_cards'
                """
            ),
            {"db_name": db_name},
        ).scalar()
    )


def _index_exists(conn, db_name: str, index_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                """
                select count(*)
                from information_schema.statistics
                where table_schema = :db_name
                  and table_name = 'knowledge_cards'
                  and index_name = :index_name
                """
            ),
            {"db_name": db_name, "index_name": index_name},
        ).scalar()
    )


def main() -> None:
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        db_name = conn.execute(text("select database()")).scalar()
        if not _table_exists(conn, db_name):
            conn.execute(
                text(
                    """
                    create table knowledge_cards (
                        id bigint primary key auto_increment,
                        user_id bigint not null comment '创建用户 ID',
                        title varchar(150) null comment '卡片标题',
                        input_type varchar(20) not null default 'text' comment 'text/image/mixed',
                        input_text text null comment '用户输入文本',
                        input_image_path varchar(255) null comment '输入图片相对路径',
                        input_image_url varchar(255) null comment '输入图片访问 URL',
                        input_image_mime varchar(80) null comment '输入图片 MIME',
                        input_image_size bigint null comment '输入图片大小',
                        template_id varchar(100) null comment 'Dify 自动选择的模板 ID',
                        image_number varchar(20) null comment 'Dify 自动选择的模板编号',
                        route_reason varchar(255) null comment 'Dify 自动路由原因',
                        prompt mediumtext null comment '最终生图 prompt',
                        extra_prompt text null comment '用户补充要求',
                        status varchar(30) not null default 'processing' comment '生成状态',
                        dify_workflow_run_id varchar(100) null comment 'Dify workflow run id',
                        dify_task_id varchar(100) null comment 'Dify task id',
                        output_image_path varchar(255) null comment '输出图片相对路径',
                        output_image_url varchar(255) null comment '输出图片访问 URL',
                        raw_response json null comment '过滤敏感信息后的 Dify 响应摘要',
                        error_message text null comment '失败原因',
                        created_at datetime not null default current_timestamp comment '创建时间',
                        updated_at datetime not null default current_timestamp on update current_timestamp comment '更新时间',
                        constraint fk_knowledge_cards_user_id foreign key (user_id) references users(id)
                    ) engine=InnoDB default charset=utf8mb4 collate=utf8mb4_unicode_ci
                    """
                )
            )
            print("created knowledge_cards")
        else:
            print("knowledge_cards already exists")

        indexes = {
            "idx_knowledge_cards_user_created": "create index idx_knowledge_cards_user_created on knowledge_cards(user_id, created_at)",
            "idx_knowledge_cards_status": "create index idx_knowledge_cards_status on knowledge_cards(status)",
            "idx_knowledge_cards_template": "create index idx_knowledge_cards_template on knowledge_cards(template_id)",
        }
        for index_name, ddl in indexes.items():
            if not _index_exists(conn, db_name, index_name):
                conn.execute(text(ddl))
                print(f"created {index_name}")
            else:
                print(f"{index_name} already exists")
    engine.dispose()


if __name__ == "__main__":
    main()
