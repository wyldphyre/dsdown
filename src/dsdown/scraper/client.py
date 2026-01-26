"""HTTP client for dynasty-scans.com."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx

from dsdown.config import DYNASTY_BASE_URL, DYNASTY_RELEASES_URL

# Default headers to mimic a browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class DynastyClient:
    """Async HTTP client for interacting with dynasty-scans.com."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "DynastyClient":
        self._client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return self._client

    async def get_releases_page(self, page: int = 1) -> str:
        """Fetch the chapter releases page.

        Args:
            page: Page number to fetch (1-indexed).

        Returns:
            HTML content of the page.
        """
        url = DYNASTY_RELEASES_URL
        if page > 1:
            url = f"{url}?page={page}"

        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    async def get_chapter_page(self, chapter_url: str) -> str:
        """Fetch an individual chapter page.

        Args:
            chapter_url: The chapter URL path (e.g., '/chapters/some_chapter').

        Returns:
            HTML content of the page.
        """
        if chapter_url.startswith("/"):
            url = f"{DYNASTY_BASE_URL}{chapter_url}"
        else:
            url = chapter_url

        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    async def get_series_page(self, series_url: str) -> str:
        """Fetch a series page.

        Args:
            series_url: The series URL path (e.g., '/series/some_series').

        Returns:
            HTML content of the page.
        """
        if series_url.startswith("/"):
            url = f"{DYNASTY_BASE_URL}{series_url}"
        else:
            url = series_url

        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    def _extract_chapter_number(self, title: str) -> str | None:
        """Extract chapter number from a chapter title.

        Args:
            title: The chapter title (e.g., 'Series Name ch001' or 'Chapter 15').

        Returns:
            The chapter number as a string, or None if not found.
        """
        # Common patterns for chapter numbers
        patterns = [
            r'\bch\.?\s*(\d+(?:\.\d+)?)',  # ch1, ch.1, ch 1, ch01
            r'\bchapter\s*(\d+(?:\.\d+)?)',  # chapter 1, chapter01
            r'\bc(\d+(?:\.\d+)?)\b',  # c1, c01 (standalone)
            r'#(\d+(?:\.\d+)?)',  # #1, #01
            r'\b(\d+(?:\.\d+)?)\s*$',  # trailing number
        ]

        title_lower = title.lower()
        for pattern in patterns:
            match = re.search(pattern, title_lower, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            name: The string to sanitize.

        Returns:
            A filename-safe string.
        """
        # Remove or replace characters that are problematic in filenames
        invalid_chars = '<>:"/\\|?*'
        result = name
        for char in invalid_chars:
            result = result.replace(char, '_')
        return result.strip()

    async def download_chapter(
        self,
        chapter_url: str,
        destination: Path,
        series_name: str | None = None,
        chapter_title: str | None = None,
        volume: int | None = None,
        subtitle: str | None = None,
        progress_callback: callable | None = None,
    ) -> Path:
        """Download a chapter archive.

        Args:
            chapter_url: The chapter URL path (e.g., '/chapters/some_chapter').
            destination: Directory to save the downloaded file.
            series_name: Optional series name for filename formatting.
            chapter_title: Optional chapter title for extracting chapter number.
            volume: Optional volume number.
            subtitle: Optional chapter subtitle/name.
            progress_callback: Optional callback for progress updates.

        Returns:
            Path to the downloaded file.
        """
        # Build download URL
        if chapter_url.startswith("/"):
            download_url = f"{DYNASTY_BASE_URL}{chapter_url}/download"
        else:
            download_url = f"{chapter_url}/download"

        # Stream the download
        async with self.client.stream("GET", download_url) as response:
            response.raise_for_status()

            # Determine the filename
            if series_name and chapter_title:
                # Extract chapter number from title
                chapter_num = self._extract_chapter_number(chapter_title)
                if chapter_num:
                    # Build filename: <SeriesName> v<Vol> ch<Num> - <Title>.cbz
                    parts = [self._sanitize_filename(series_name)]
                    if volume is not None:
                        parts.append(f"v{volume}")
                    parts.append(f"ch{chapter_num}")
                    filename = " ".join(parts)
                    if subtitle:
                        filename += f" - {self._sanitize_filename(subtitle)}"
                    filename += ".cbz"
                else:
                    # No chapter number found, use slug from URL
                    slug = chapter_url.rstrip("/").split("/")[-1]
                    filename = f"{self._sanitize_filename(series_name)} - {slug}.cbz"
            else:
                # Fallback: try Content-Disposition header
                content_disposition = response.headers.get("content-disposition", "")
                filename = None
                if "filename=" in content_disposition:
                    for part in content_disposition.split(";"):
                        part = part.strip()
                        if part.startswith("filename="):
                            filename = part[9:].strip('"\'')
                            # Change .zip to .cbz
                            if filename.lower().endswith('.zip'):
                                filename = filename[:-4] + '.cbz'
                            break

                if not filename:
                    # Use chapter slug from URL
                    slug = chapter_url.rstrip("/").split("/")[-1]
                    filename = f"{slug}.cbz"

            # Ensure destination directory exists
            destination.mkdir(parents=True, exist_ok=True)
            file_path = destination / filename

            # Get total size for progress
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            # Download with progress
            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size:
                        progress_callback(downloaded, total_size)

            return file_path


async def fetch_releases_page(page: int = 1) -> str:
    """Convenience function to fetch releases page."""
    async with DynastyClient() as client:
        return await client.get_releases_page(page)


async def fetch_chapter_page(chapter_url: str) -> str:
    """Convenience function to fetch a chapter page."""
    async with DynastyClient() as client:
        return await client.get_chapter_page(chapter_url)


async def fetch_series_page(series_url: str) -> str:
    """Convenience function to fetch a series page."""
    async with DynastyClient() as client:
        return await client.get_series_page(series_url)
