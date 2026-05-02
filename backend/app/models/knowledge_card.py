from __future__ import annotations

from sqlalchemy import BigInteger, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class KnowledgeCard(TimestampMixin, Base):
    """知识卡片生成记录，保存输入、prompt、Dify 响应和输出图片。"""

    __tablename__ = "knowledge_cards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False, comment="创建用户 ID")
    title: Mapped[str | None] = mapped_column(String(150), index=True, comment="卡片标题")
    input_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text", comment="text/image/mixed")
    input_text: Mapped[str | None] = mapped_column(Text, comment="用户输入文本")
    input_image_path: Mapped[str | None] = mapped_column(String(255), comment="输入图片相对路径")
    input_image_url: Mapped[str | None] = mapped_column(String(255), comment="输入图片访问 URL")
    input_image_mime: Mapped[str | None] = mapped_column(String(80), comment="输入图片 MIME")
    input_image_size: Mapped[int | None] = mapped_column(BigInteger, comment="输入图片大小")
    template_id: Mapped[str | None] = mapped_column(String(100), index=True, comment="Dify 自动选择的模板 ID")
    image_number: Mapped[str | None] = mapped_column(String(20), comment="Dify 自动选择的模板编号")
    route_reason: Mapped[str | None] = mapped_column(String(255), comment="Dify 自动路由原因")
    prompt: Mapped[str | None] = mapped_column(Text, comment="最终生图 prompt")
    extra_prompt: Mapped[str | None] = mapped_column(Text, comment="用户补充要求")
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False, default="processing", comment="生成状态")
    dify_workflow_run_id: Mapped[str | None] = mapped_column(String(100), comment="Dify workflow run id")
    dify_task_id: Mapped[str | None] = mapped_column(String(100), comment="Dify task id")
    output_image_path: Mapped[str | None] = mapped_column(String(255), comment="输出图片相对路径")
    output_image_url: Mapped[str | None] = mapped_column(String(255), comment="输出图片访问 URL")
    raw_response: Mapped[dict | None] = mapped_column(JSON, comment="过滤敏感信息后的 Dify 响应摘要")
    error_message: Mapped[str | None] = mapped_column(Text, comment="失败原因")
