"""Download queue and history models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dsdown.models.database import Base

if TYPE_CHECKING:
    from dsdown.models.chapter import Chapter


class DownloadStatus(str, Enum):
    """Status of a download queue entry."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadQueue(Base):
    """A chapter in the download queue."""

    __tablename__ = "download_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=DownloadStatus.PENDING.value, nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship to chapter
    chapter: Mapped["Chapter"] = relationship(
        "Chapter", back_populates="download_queue_entry"
    )

    def __repr__(self) -> str:
        return f"<DownloadQueue(chapter_id={self.chapter_id}, status={self.status!r})>"


class DownloadHistory(Base):
    """Record of download starts for rate limiting."""

    __tablename__ = "download_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DownloadHistory(chapter_id={self.chapter_id}, started_at={self.started_at})>"
