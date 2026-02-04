"""Service for managing the download queue."""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from dsdown.config import MAX_DOWNLOADS_PER_24H
from dsdown.models.chapter import Chapter
from dsdown.models.database import get_session
from dsdown.models.download import DownloadHistory, DownloadQueue, DownloadStatus
from dsdown.scraper.client import DynastyClient
from dsdown.scraper.series_parser import get_chapter_volumes
from dsdown.services.comicinfo import add_comicinfo_to_cbz, extract_title_without_chapter


def _open_folder_in_file_manager(folder: Path) -> None:
    """Open a folder in the system's default file manager.

    Args:
        folder: The folder path to open.
    """
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(folder)], check=False)
        elif system == "Windows":
            subprocess.run(["explorer", str(folder)], check=False)
        else:  # Linux and others
            subprocess.run(["xdg-open", str(folder)], check=False)
    except Exception:
        pass  # Silently ignore errors opening folder


class DownloadService:
    """Service for managing downloads."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        """Get the database session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def get_queue(self) -> Sequence[DownloadQueue]:
        """Get all items in the download queue, ordered by priority and added time."""
        stmt = (
            select(DownloadQueue)
            .options(joinedload(DownloadQueue.chapter))  # Eager load chapter
            .where(DownloadQueue.status.in_([
                DownloadStatus.PENDING.value,
                DownloadStatus.DOWNLOADING.value,
                DownloadStatus.FAILED.value,
            ]))
            .order_by(DownloadQueue.priority.desc(), DownloadQueue.added_at)
        )
        return self.session.execute(stmt).scalars().unique().all()

    def get_pending_downloads(self) -> Sequence[DownloadQueue]:
        """Get all pending downloads."""
        stmt = (
            select(DownloadQueue)
            .options(joinedload(DownloadQueue.chapter).joinedload(Chapter.series))  # Eager load chapter and series
            .where(DownloadQueue.status == DownloadStatus.PENDING.value)
            .order_by(DownloadQueue.priority.desc(), DownloadQueue.added_at)
        )
        return self.session.execute(stmt).scalars().unique().all()

    def add_to_queue(self, chapter: Chapter, priority: int = 0) -> DownloadQueue:
        """Add a chapter to the download queue.

        Args:
            chapter: The chapter to queue.
            priority: Higher priority items are downloaded first.

        Returns:
            The created queue entry.
        """
        # Check if already in queue
        existing = self.session.execute(
            select(DownloadQueue).where(DownloadQueue.chapter_id == chapter.id)
        ).scalar_one_or_none()

        if existing:
            return existing

        entry = DownloadQueue(
            chapter_id=chapter.id,
            priority=priority,
            status=DownloadStatus.PENDING.value,
        )
        self.session.add(entry)
        self.session.commit()
        return entry

    def remove_from_queue(self, entry: DownloadQueue) -> None:
        """Remove an entry from the download queue."""
        self.session.delete(entry)
        self.session.commit()

    def get_available_slots(self) -> int:
        """Get the number of available download slots.

        Downloads are limited to MAX_DOWNLOADS_PER_24H per 24 hours.

        Returns:
            Number of available download slots.
        """
        cutoff = datetime.now() - timedelta(hours=24)
        count = self.session.execute(
            select(func.count(DownloadHistory.id)).where(
                DownloadHistory.started_at >= cutoff
            )
        ).scalar_one()
        return max(0, MAX_DOWNLOADS_PER_24H - count)

    def get_downloads_in_last_24h(self) -> int:
        """Get the number of downloads started in the last 24 hours."""
        cutoff = datetime.now() - timedelta(hours=24)
        return self.session.execute(
            select(func.count(DownloadHistory.id)).where(
                DownloadHistory.started_at >= cutoff
            )
        ).scalar_one()

    def get_next_slot_time(self) -> datetime | None:
        """Get when the next download slot will become available.

        Returns:
            Datetime when next slot opens, or None if slots are available now.
        """
        if self.get_available_slots() > 0:
            return None

        # Find the oldest download in the last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        oldest = self.session.execute(
            select(DownloadHistory)
            .where(DownloadHistory.started_at >= cutoff)
            .order_by(DownloadHistory.started_at)
            .limit(1)
        ).scalar_one_or_none()

        if oldest:
            return oldest.started_at + timedelta(hours=24)
        return None

    def record_download_start(self, chapter: Chapter) -> DownloadHistory:
        """Record that a download has started.

        This is used for rate limiting tracking.

        Args:
            chapter: The chapter being downloaded.

        Returns:
            The download history record.
        """
        history = DownloadHistory(chapter_id=chapter.id)
        self.session.add(history)
        self.session.commit()
        return history

    async def _fetch_volume_info(self, chapter: Chapter, client: DynastyClient) -> None:
        """Fetch and set volume information for a chapter from its series page.

        Args:
            chapter: The chapter to get volume info for.
            client: The HTTP client to use.
        """
        # Skip if already has volume info or no series
        if chapter.volume is not None or not chapter.series:
            return

        try:
            series_url = chapter.series.url
            if not series_url:
                return

            # Fetch and parse series page
            series_html = await client.get_series_page(series_url)
            chapter_volumes = get_chapter_volumes(series_html)

            # Look up this chapter's volume
            if chapter.url in chapter_volumes:
                chapter.volume = chapter_volumes[chapter.url]
                self.session.commit()
        except Exception:
            # Silently ignore errors fetching volume info
            pass

    async def process_queue(
        self,
        progress_callback: callable | None = None,
        download_progress_callback: callable | None = None,
    ) -> list[Chapter]:
        """Process the download queue.

        Downloads chapters up to the available rate limit.

        Args:
            progress_callback: Optional callback for progress updates.
                Called with (message: str, current: int, total: int)
            download_progress_callback: Optional callback for file download progress.
                Called with (title: str, downloaded: int, total: int)

        Returns:
            List of successfully downloaded chapters.
        """
        from dsdown.services.chapter_service import ChapterService

        chapter_service = ChapterService(self.session)
        downloaded: list[Chapter] = []
        pending = list(self.get_pending_downloads())

        if not pending:
            if progress_callback:
                progress_callback("No pending downloads.", 0, 0)
            return downloaded

        available = self.get_available_slots()
        if available == 0:
            next_time = self.get_next_slot_time()
            if progress_callback and next_time:
                progress_callback(
                    f"No download slots available. Next slot at {next_time.strftime('%H:%M')}.",
                    0,
                    len(pending),
                )
            return downloaded

        to_process = pending[:available]

        async with DynastyClient() as client:
            for i, entry in enumerate(to_process):
                chapter = entry.chapter

                if progress_callback:
                    progress_callback(
                        f"Downloading: {chapter.title}",
                        i + 1,
                        len(to_process),
                    )

                # Update status to downloading
                entry.status = DownloadStatus.DOWNLOADING.value
                self.session.commit()

                try:
                    # Fetch volume info from series page if not already set
                    await self._fetch_volume_info(chapter, client)

                    # Get download path from series or use default
                    if chapter.series and chapter.series.download_path:
                        destination = Path(chapter.series.download_path)
                    else:
                        destination = Path.home() / "Downloads" / "dsdown"

                    # Record download start for rate limiting
                    self.record_download_start(chapter)

                    # Download the chapter with series name and title for filename
                    # Only include series name if the setting is enabled
                    include_series = (
                        chapter.series.include_series_in_filename
                        if chapter.series else True
                    )
                    series_name = chapter.series.name if chapter.series and include_series else None

                    # Get subtitle for filename
                    subtitle = extract_title_without_chapter(chapter.title, series_name)

                    # Create file progress callback
                    def file_progress(downloaded: int, total: int) -> None:
                        if download_progress_callback:
                            download_progress_callback(chapter.title, downloaded, total)

                    cbz_path = await client.download_chapter(
                        chapter.url,
                        destination,
                        series_name=series_name,
                        chapter_title=chapter.title,
                        volume=chapter.volume,
                        subtitle=subtitle,
                        progress_callback=file_progress,
                    )

                    # Add ComicInfo.xml metadata
                    add_comicinfo_to_cbz(cbz_path, chapter)

                    # Mark as completed
                    entry.status = DownloadStatus.COMPLETED.value
                    chapter_service.mark_downloaded(chapter)
                    downloaded.append(chapter)

                    # Open the folder in file manager
                    _open_folder_in_file_manager(destination)

                except Exception as e:
                    # Mark as failed
                    entry.status = DownloadStatus.FAILED.value
                    if progress_callback:
                        progress_callback(f"Failed: {chapter.title} - {e}", i + 1, len(to_process))

                self.session.commit()

        if progress_callback:
            progress_callback(
                f"Downloaded {len(downloaded)} of {len(to_process)} chapters.",
                len(to_process),
                len(to_process),
            )

        return downloaded
