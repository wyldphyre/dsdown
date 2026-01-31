"""Series model for tracking followed/ignored series."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dsdown.models.database import Base

if TYPE_CHECKING:
    from dsdown.models.chapter import Chapter


class SeriesStatus(str, Enum):
    """Status of a series."""

    FOLLOWED = "followed"
    IGNORED = "ignored"


class Series(Base):
    """A series from dynasty-scans.com."""

    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    download_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    include_series_in_filename: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="1"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship to chapters
    chapters: Mapped[List["Chapter"]] = relationship(
        "Chapter", back_populates="series"
    )

    @property
    def is_followed(self) -> bool:
        """Check if this series is followed."""
        return self.status == SeriesStatus.FOLLOWED.value

    @property
    def is_ignored(self) -> bool:
        """Check if this series is ignored."""
        return self.status == SeriesStatus.IGNORED.value

    @property
    def tags(self) -> list[str]:
        """Get the list of tags."""
        if self.tags_json:
            return json.loads(self.tags_json)
        return []

    @tags.setter
    def tags(self, value: list[str]) -> None:
        """Set the list of tags."""
        self.tags_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Series(name={self.name!r}, status={self.status!r})>"
