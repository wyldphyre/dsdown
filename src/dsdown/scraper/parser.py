"""Parser for the dynasty-scans.com releases page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from bs4 import BeautifulSoup, Tag


@dataclass
class ParsedChapter:
    """A chapter parsed from the releases page."""

    url: str
    title: str
    authors: list[str]
    tags: list[str]
    release_date: date | None


class ReleasesParser:
    """Parser for the chapter releases page."""

    def __init__(self, html: str) -> None:
        self.soup = BeautifulSoup(html, "lxml")

    def validate_structure(self) -> list[str]:
        """Check that expected page landmarks exist.

        Returns:
            List of warning messages for missing elements.
        """
        warnings = []
        if not self.soup.select_one("#main, .chapters, main"):
            warnings.append("Missing main content container (#main)")
        if not self.soup.find("dt"):
            warnings.append("No <dt> date headers found on releases page")
        if not self.soup.find("dd"):
            warnings.append("No <dd> chapter entries found on releases page")
        return warnings

    def parse(self) -> list[ParsedChapter]:
        """Parse all chapters from the releases page.

        Returns:
            List of parsed chapters, grouped by date.
        """
        chapters: list[ParsedChapter] = []
        current_date: date | None = None

        # Find the main content area
        # The chapters are typically in a list structure with date headers
        content = self.soup.select_one("#main, .chapters, main")
        if not content:
            content = self.soup.body

        if not content:
            return chapters

        # Look for chapter list items and date headers
        # Date headers are in dt elements, chapters are in dd elements
        for element in content.find_all(["dt", "dd"]):
            # Check if this is a date header
            if self._is_date_header(element):
                current_date = self._parse_date_header(element)
            # Check if this is a chapter entry
            elif self._is_chapter_entry(element):
                chapter = self._parse_chapter_entry(element, current_date)
                if chapter:
                    chapters.append(chapter)

        return chapters

    def _is_date_header(self, element: Tag) -> bool:
        """Check if an element is a date header."""
        # Date headers are dt elements with a date-like text
        if element.name == "dt":
            text = element.get_text(strip=True)
            # Check for date patterns like "January 23, 2026"
            if re.search(r"\w+\s+\d{1,2},?\s+\d{4}", text):
                return True
        return False

    def _parse_date_header(self, element: Tag) -> date | None:
        """Parse a date from a header element."""
        text = element.get_text(strip=True)

        # Try to parse various date formats
        formats = [
            "%B %d, %Y",  # January 23, 2026
            "%B %d %Y",  # January 23 2026
            "%b %d, %Y",  # Jan 23, 2026
            "%b %d %Y",  # Jan 23 2026
        ]

        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        return None

    def _is_chapter_entry(self, element: Tag) -> bool:
        """Check if an element is a chapter entry."""
        # Chapter entries are dd elements with links to /chapters/
        if element.name != "dd":
            return False
        chapter_link = element.select_one('a[href*="/chapters/"]')
        if chapter_link:
            href = chapter_link.get("href", "")
            # Exclude pagination links
            if "/chapters/added" not in href:
                return True
        return False

    def _parse_chapter_entry(self, element: Tag, release_date: date | None) -> ParsedChapter | None:
        """Parse a chapter entry element."""
        # Find the chapter link
        chapter_link = element.select_one('a[href*="/chapters/"]')
        if not chapter_link:
            return None

        href = chapter_link.get("href", "")
        if "/chapters/added" in href:
            return None

        url = href
        title = chapter_link.get_text(strip=True)

        # Find authors (links with /authors/)
        authors = []
        for author_link in element.select('a[href*="/authors/"]'):
            author_name = author_link.get_text(strip=True)
            if author_name:
                authors.append(author_name)

        # Find tags (links with /tags/)
        tags = []
        for tag_link in element.select('a[href*="/tags/"]'):
            tag_name = tag_link.get_text(strip=True)
            # Remove brackets if present
            tag_name = tag_name.strip("[]")
            if tag_name:
                tags.append(tag_name)

        return ParsedChapter(
            url=url,
            title=title,
            authors=authors,
            tags=tags,
            release_date=release_date,
        )

    def get_next_page_url(self) -> str | None:
        """Get the URL for the next page of releases, if any."""
        # Look for pagination links
        next_link = self.soup.select_one('a[rel="next"], a.next_page, a:-soup-contains("Next")')
        if next_link:
            return next_link.get("href")

        # Alternative: look for numbered pagination
        pagination = self.soup.select_one(".pagination")
        if pagination:
            current = pagination.select_one(".current, .active")
            if current:
                next_sibling = current.find_next_sibling("a")
                if next_sibling:
                    return next_sibling.get("href")

        return None

    def has_next_page(self) -> bool:
        """Check if there is a next page."""
        return self.get_next_page_url() is not None


def parse_releases(html: str) -> list[ParsedChapter]:
    """Convenience function to parse releases from HTML."""
    parser = ReleasesParser(html)
    return parser.parse()
