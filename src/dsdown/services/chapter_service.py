"""Service for managing chapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from dsdown.config import get_config
from dsdown.models.chapter import Chapter
from dsdown.models.database import get_session
from dsdown.models.series import Series, SeriesStatus
from dsdown.scraper.chapter_parser import ChapterPageParser
from dsdown.scraper.client import DynastyClient
from dsdown.scraper.parser import ParsedChapter, ReleasesParser


@dataclass
class FetchResult:
    """Result of fetching new chapters."""

    total: int
    queued: int
    ignored: int
    new: int  # Unprocessed (not followed or ignored)


class ChapterService:
    """Service for managing chapters."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        """Get the database session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def get_unprocessed_chapters(self) -> Sequence[Chapter]:
        """Get all unprocessed chapters, ordered by release date descending."""
        stmt = (
            select(Chapter)
            .options(joinedload(Chapter.series))  # Eager load series to avoid lazy loading issues
            .where(Chapter.processed == False)  # noqa: E712
            .order_by(Chapter.release_date.desc(), Chapter.id.desc())
        )
        return self.session.execute(stmt).scalars().unique().all()

    def get_chapters_by_date(self) -> dict[date | None, list[Chapter]]:
        """Get unprocessed chapters grouped by release date."""
        chapters = self.get_unprocessed_chapters()
        grouped: dict[date | None, list[Chapter]] = {}
        for chapter in chapters:
            if chapter.release_date not in grouped:
                grouped[chapter.release_date] = []
            grouped[chapter.release_date].append(chapter)
        return grouped

    def get_chapter_by_url(self, url: str) -> Chapter | None:
        """Get a chapter by its URL."""
        stmt = (
            select(Chapter)
            .options(joinedload(Chapter.series))
            .where(Chapter.url == url)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_chapter_by_id(self, chapter_id: int) -> Chapter | None:
        """Get a chapter by its ID, with series eager-loaded."""
        stmt = (
            select(Chapter)
            .options(joinedload(Chapter.series))
            .where(Chapter.id == chapter_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_chapter(
        self,
        url: str,
        title: str,
        authors: list[str],
        tags: list[str],
        release_date: date | None = None,
        series_id: int | None = None,
    ) -> Chapter:
        """Create a new chapter."""
        chapter = Chapter(
            url=url,
            title=title,
            release_date=release_date,
            series_id=series_id,
        )
        chapter.authors = authors
        chapter.tags = tags
        self.session.add(chapter)
        self.session.commit()
        return chapter

    def mark_processed(self, chapter: Chapter) -> None:
        """Mark a chapter as processed."""
        chapter.processed = True
        self.session.commit()

    def mark_downloaded(self, chapter: Chapter) -> None:
        """Mark a chapter as downloaded."""
        chapter.downloaded = True
        chapter.download_timestamp = datetime.now()
        self.session.commit()

    async def fetch_new_chapters(
        self,
        progress_callback: callable | None = None,
    ) -> FetchResult:
        """Fetch new chapters from the releases page.

        Args:
            progress_callback: Optional callback for progress updates.
                Called with (message: str, current: int, total: int | None)

        Returns:
            FetchResult with counts of total, queued, ignored, and new chapters.
        """
        config = get_config()
        last_url = config.last_fetched_chapter_url
        new_chapters: list[Chapter] = []
        first_chapter_url: str | None = None
        page = 1
        found_last = False

        async with DynastyClient() as client:
            while not found_last:
                if progress_callback:
                    progress_callback(f"Fetching page {page}...", page, None)

                html = await client.get_releases_page(page)
                parser = ReleasesParser(html)
                parsed_chapters = parser.parse()

                if not parsed_chapters:
                    break

                for parsed in parsed_chapters:
                    # Track the first chapter URL
                    if first_chapter_url is None:
                        first_chapter_url = parsed.url

                    # Check if we've reached the last fetched chapter
                    if last_url and parsed.url == last_url:
                        found_last = True
                        break

                    # Skip if chapter already exists
                    existing = self.get_chapter_by_url(parsed.url)
                    if existing:
                        continue

                    # Create the chapter
                    chapter = await self._create_chapter_from_parsed(client, parsed)
                    new_chapters.append(chapter)

                # If this is the first fetch (no last_url), only process first page
                if last_url is None:
                    break

                # Check if there's a next page
                if not parser.has_next_page():
                    break

                page += 1

        # Update the last fetched chapter URL
        if first_chapter_url:
            config.last_fetched_chapter_url = first_chapter_url

        # Process chapters based on series status and get counts
        queued, ignored = await self._process_chapters_by_series(new_chapters)

        return FetchResult(
            total=len(new_chapters),
            queued=queued,
            ignored=ignored,
            new=len(new_chapters) - queued - ignored,
        )

    async def _create_chapter_from_parsed(
        self,
        client: DynastyClient,
        parsed: ParsedChapter,
    ) -> Chapter:
        """Create a chapter from parsed data, fetching series info if needed."""
        # Try to get series info
        series_id = None
        try:
            chapter_html = await client.get_chapter_page(parsed.url)
            chapter_parser = ChapterPageParser(chapter_html)
            series_url = chapter_parser.get_series_url()
            series_name = chapter_parser.get_series_name()

            if series_url:
                # Get or create series
                from dsdown.services.series_service import SeriesService

                series_service = SeriesService(self.session)
                series = series_service.get_or_create_series(series_url, series_name or "Unknown")
                series_id = series.id
        except Exception:
            # If we can't fetch series info, continue without it
            pass

        return self.create_chapter(
            url=parsed.url,
            title=parsed.title,
            authors=parsed.authors,
            tags=parsed.tags,
            release_date=parsed.release_date,
            series_id=series_id,
        )

    async def _process_chapters_by_series(self, chapters: list[Chapter]) -> tuple[int, int]:
        """Process chapters based on their series status.

        Returns:
            Tuple of (queued_count, ignored_count).
        """
        from dsdown.services.download_service import DownloadService

        download_service = DownloadService(self.session)
        queued = 0
        ignored = 0

        for chapter in chapters:
            if chapter.series:
                if chapter.series.is_followed:
                    # Auto-queue followed series chapters
                    download_service.add_to_queue(chapter)
                    self.mark_processed(chapter)
                    queued += 1
                elif chapter.series.is_ignored:
                    # Auto-process ignored series chapters
                    self.mark_processed(chapter)
                    ignored += 1

        return queued, ignored
