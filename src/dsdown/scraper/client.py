"""HTTP client for dynasty-scans.com."""

from __future__ import annotations

import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx

from dsdown.config import DYNASTY_BASE_URL, DYNASTY_RELEASES_URL
from dsdown.utils import extract_chapter_number, sanitize_filename

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

    @staticmethod
    def _validate_html_response(response: httpx.Response) -> None:
        """Validate that an HTTP response looks like an HTML page.

        Raises:
            ValueError: If the response doesn't look like valid HTML.
        """
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            raise ValueError(f"Unexpected content type: {content_type}")
        if len(response.text) < 500:
            raise ValueError(
                f"Response suspiciously short ({len(response.text)} bytes) - "
                "may be an error page or CAPTCHA"
            )

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
        self._validate_html_response(response)
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
        self._validate_html_response(response)
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
        self._validate_html_response(response)
        return response.text

    async def download_image(self, image_url: str) -> bytes:
        """Download an image and return its bytes.

        Args:
            image_url: The image URL (absolute or relative to dynasty-scans.com).

        Returns:
            The image data as bytes.
        """
        if image_url.startswith("/"):
            url = f"{DYNASTY_BASE_URL}{image_url}"
        else:
            url = image_url

        response = await self.client.get(url)
        response.raise_for_status()
        return response.content

    def _ensure_zip_archive(self, file_path: Path) -> Path:
        """Ensure the file is a valid zip archive, converting if necessary.

        If the file is not a valid zip, attempts to extract it and recompress as zip.

        Args:
            file_path: Path to the downloaded file.

        Returns:
            Path to the (possibly converted) zip archive.
        """
        # Check if it's already a valid zip
        if zipfile.is_zipfile(file_path):
            return file_path

        # Not a zip - try to extract and recompress
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            extract_dir = temp_path / "extract"
            extract_dir.mkdir()

            # Try different extraction methods
            extracted = False

            # Try unrar for RAR files
            if not extracted:
                try:
                    result = subprocess.run(
                        ["unrar", "x", "-y", str(file_path), str(extract_dir) + "/"],
                        capture_output=True,
                        timeout=120,
                    )
                    if result.returncode == 0 and any(extract_dir.iterdir()):
                        extracted = True
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

            # Try 7z for various formats
            if not extracted:
                try:
                    result = subprocess.run(
                        ["7z", "x", f"-o{extract_dir}", "-y", str(file_path)],
                        capture_output=True,
                        timeout=120,
                    )
                    if result.returncode == 0 and any(extract_dir.iterdir()):
                        extracted = True
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

            if not extracted:
                # Could not extract - return as-is
                return file_path

            # Collect all extracted files
            files_to_zip: list[tuple[Path, str]] = []
            for item in extract_dir.rglob("*"):
                if item.is_file():
                    # Use relative path from extract_dir
                    rel_path = item.relative_to(extract_dir)
                    files_to_zip.append((item, str(rel_path)))

            if not files_to_zip:
                return file_path

            # Sort files for consistent ordering
            files_to_zip.sort(key=lambda x: x[1])

            # Create new zip archive
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_STORED) as zf:
                for src_path, arc_name in files_to_zip:
                    zf.write(src_path, arc_name)

        return file_path

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
            if chapter_title:
                # Extract chapter number from title
                chapter_num = extract_chapter_number(chapter_title)
                if chapter_num:
                    # Build filename with available parts
                    parts = []
                    if series_name:
                        parts.append(sanitize_filename(series_name))
                    if volume is not None:
                        parts.append(f"v{volume}")
                    parts.append(f"ch{chapter_num}")
                    filename = " ".join(parts)
                    if subtitle:
                        filename += f" - {sanitize_filename(subtitle)}"
                    filename += ".cbz"
                elif series_name:
                    # No chapter number found, use slug from URL
                    slug = chapter_url.rstrip("/").split("/")[-1]
                    filename = f"{sanitize_filename(series_name)} - {slug}.cbz"
                else:
                    # No series name or chapter number, use sanitized title
                    filename = f"{sanitize_filename(chapter_title)}.cbz"
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

            # Ensure the file is a valid zip archive
            file_path = self._ensure_zip_archive(file_path)

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


async def download_image(image_url: str) -> bytes:
    """Convenience function to download an image."""
    async with DynastyClient() as client:
        return await client.download_image(image_url)
