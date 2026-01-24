"""HTTP client for dynasty-scans.com."""

from __future__ import annotations

import asyncio
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

    async def download_chapter(
        self,
        chapter_url: str,
        destination: Path,
        progress_callback: callable | None = None,
    ) -> Path:
        """Download a chapter archive.

        Args:
            chapter_url: The chapter URL path (e.g., '/chapters/some_chapter').
            destination: Directory to save the downloaded file.
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

            # Try to get filename from Content-Disposition header
            content_disposition = response.headers.get("content-disposition", "")
            filename = None
            if "filename=" in content_disposition:
                # Parse filename from header
                for part in content_disposition.split(";"):
                    part = part.strip()
                    if part.startswith("filename="):
                        filename = part[9:].strip('"\'')
                        break

            if not filename:
                # Fallback: use chapter slug from URL
                slug = chapter_url.rstrip("/").split("/")[-1]
                filename = f"{slug}.zip"

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
