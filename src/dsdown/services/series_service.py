"""Service for managing series."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from dsdown.models.database import get_session
from dsdown.models.series import Series, SeriesStatus


class SeriesService:
    """Service for managing series."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        """Get the database session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def get_series_by_url(self, url: str) -> Series | None:
        """Get a series by its URL."""
        stmt = select(Series).where(Series.url == url)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_series_by_id(self, series_id: int) -> Series | None:
        """Get a series by its ID."""
        return self.session.get(Series, series_id)

    def get_followed_series(self) -> Sequence[Series]:
        """Get all followed series."""
        stmt = (
            select(Series)
            .where(Series.status == SeriesStatus.FOLLOWED.value)
            .order_by(Series.name)
        )
        return self.session.execute(stmt).scalars().all()

    def get_ignored_series(self) -> Sequence[Series]:
        """Get all ignored series."""
        stmt = (
            select(Series)
            .where(Series.status == SeriesStatus.IGNORED.value)
            .order_by(Series.name)
        )
        return self.session.execute(stmt).scalars().all()

    def get_or_create_series(self, url: str, name: str) -> Series:
        """Get an existing series or create a new one."""
        series = self.get_series_by_url(url)
        if series:
            return series

        series = Series(url=url, name=name)
        self.session.add(series)
        self.session.commit()
        return series

    def follow_series(self, series: Series, download_path: Path) -> None:
        """Mark a series as followed.

        Args:
            series: The series to follow.
            download_path: The path to download chapters to.
        """
        series.status = SeriesStatus.FOLLOWED.value
        series.download_path = str(download_path)
        self.session.commit()

    def ignore_series(self, series: Series) -> None:
        """Mark a series as ignored."""
        series.status = SeriesStatus.IGNORED.value
        series.download_path = None
        self.session.commit()

    def unfollow_series(self, series: Series) -> None:
        """Remove follow/ignore status from a series."""
        series.status = None
        series.download_path = None
        self.session.commit()

    def is_followed(self, series_url: str) -> bool:
        """Check if a series is followed."""
        series = self.get_series_by_url(series_url)
        return series is not None and series.is_followed

    def is_ignored(self, series_url: str) -> bool:
        """Check if a series is ignored."""
        series = self.get_series_by_url(series_url)
        return series is not None and series.is_ignored
