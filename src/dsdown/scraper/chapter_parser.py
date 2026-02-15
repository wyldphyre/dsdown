"""Parser for individual chapter pages on dynasty-scans.com."""

from __future__ import annotations

from bs4 import BeautifulSoup


class ChapterPageParser:
    """Parser for an individual chapter page."""

    def __init__(self, html: str) -> None:
        self.soup = BeautifulSoup(html, "lxml")

    def validate_structure(self) -> list[str]:
        """Check that expected page landmarks exist.

        Returns:
            List of warning messages for missing elements.
        """
        warnings = []
        if not self.soup.select_one("h2#chapter-title, h2.chapter-title, h2"):
            warnings.append("No chapter title element (h2) found")
        return warnings

    def get_series_url(self) -> str | None:
        """Get the series URL for this chapter.

        Returns:
            The series URL path (e.g., '/series/some_series') or None if not found.
        """
        # Look for series link
        series_link = self.soup.select_one('a[href*="/series/"]')
        if series_link:
            return series_link.get("href")
        return None

    def get_series_name(self) -> str | None:
        """Get the series name for this chapter.

        Returns:
            The series name or None if not found.
        """
        series_link = self.soup.select_one('a[href*="/series/"]')
        if series_link:
            return series_link.get_text(strip=True)
        return None

    def get_download_url(self, chapter_url: str) -> str:
        """Get the download URL for this chapter.

        Args:
            chapter_url: The base chapter URL.

        Returns:
            The download URL.
        """
        # Download URL is typically chapter_url + /download
        return f"{chapter_url.rstrip('/')}/download"

    def get_title(self) -> str | None:
        """Get the chapter title.

        Returns:
            The chapter title or None if not found.
        """
        # Title is typically in h2#chapter-title or similar
        title_elem = self.soup.select_one("h2#chapter-title, h2.chapter-title, h2")
        if title_elem:
            return title_elem.get_text(strip=True)
        return None

    def get_tags(self) -> list[str]:
        """Get the tags for this chapter.

        Returns:
            List of tag names.
        """
        tags = []
        for tag_link in self.soup.select('a[href*="/tags/"]'):
            tag_name = tag_link.get_text(strip=True).strip("[]")
            if tag_name and tag_name not in tags:
                tags.append(tag_name)
        return tags

    def get_authors(self) -> list[str]:
        """Get the authors for this chapter.

        Returns:
            List of author names.
        """
        authors = []
        for author_link in self.soup.select('a[href*="/authors/"]'):
            author_name = author_link.get_text(strip=True)
            if author_name and author_name not in authors:
                authors.append(author_name)
        return authors


def get_series_url(html: str) -> str | None:
    """Convenience function to get series URL from chapter HTML."""
    parser = ChapterPageParser(html)
    return parser.get_series_url()


def get_series_name(html: str) -> str | None:
    """Convenience function to get series name from chapter HTML."""
    parser = ChapterPageParser(html)
    return parser.get_series_name()
