"""Chapter model for tracking chapters from dynasty-scans.com."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dsdown.models.database import Base

if TYPE_CHECKING:
    from dsdown.models.download import DownloadQueue
    from dsdown.models.series import Series


class Chapter(Base):
    """A chapter from dynasty-scans.com."""

    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    series_id: Mapped[Optional[int]] = mapped_column(ForeignKey("series.id"), nullable=True)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    authors_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    downloaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    download_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship to series
    series: Mapped[Optional["Series"]] = relationship(
        "Series", back_populates="chapters"
    )

    # Relationship to download queue
    download_queue_entry: Mapped[Optional["DownloadQueue"]] = relationship(
        "DownloadQueue", back_populates="chapter", uselist=False
    )

    @property
    def authors(self) -> list[str]:
        """Get the list of authors."""
        return json.loads(self.authors_json)

    @authors.setter
    def authors(self, value: list[str]) -> None:
        """Set the list of authors."""
        self.authors_json = json.dumps(value)

    @property
    def tags(self) -> list[str]:
        """Get the list of tags."""
        return json.loads(self.tags_json)

    @tags.setter
    def tags(self, value: list[str]) -> None:
        """Set the list of tags."""
        self.tags_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Chapter(title={self.title!r}, processed={self.processed})>"
