"""Parser for series pages on dynasty-scans.com."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag


class SeriesPageParser:
    """Parser for a series page to extract metadata.

    Extracts:
    - Volume information (chapters organized under volume headers)
    - Series name
    - Description/summary
    - Cover image URL
    - Tags
    """

    def __init__(self, html: str) -> None:
        self.soup = BeautifulSoup(html, "lxml")

    def get_chapter_volumes(self) -> dict[str, int]:
        """Get a mapping of chapter URLs to their volume numbers.

        Returns:
            Dictionary mapping chapter URL paths to volume numbers.
            Only chapters that belong to a volume are included.
        """
        chapter_volumes: dict[str, int] = {}
        current_volume: int | None = None

        # Find the chapters list container
        # Dynasty-scans uses a dl (definition list) structure for chapters
        chapters_list = self.soup.select_one(".chapter-list, #chapters, dl.chapter-list")
        if not chapters_list:
            # Try to find any dl element that contains chapter links
            for dl in self.soup.find_all("dl"):
                if dl.select_one('a[href*="/chapters/"]'):
                    chapters_list = dl
                    break

        if not chapters_list:
            # Fallback: scan the whole document
            chapters_list = self.soup.body

        if not chapters_list:
            return chapter_volumes

        # Iterate through elements to find volume headers and chapter links
        # Volume headers are often in dt elements or h3/h4 elements
        for element in chapters_list.find_all(["dt", "dd", "h3", "h4", "div", "li"]):
            # Check if this is a volume header
            volume_num = self._extract_volume_number(element)
            if volume_num is not None:
                current_volume = volume_num
                continue

            # Check if this element contains chapter links
            if current_volume is not None:
                for chapter_link in element.select('a[href*="/chapters/"]'):
                    href = chapter_link.get("href", "")
                    if href and "/chapters/" in href:
                        # Normalize the URL path
                        if not href.startswith("/"):
                            href = "/" + href.split("/chapters/", 1)[1]
                            href = "/chapters/" + href
                        chapter_volumes[href] = current_volume

        return chapter_volumes

    def _extract_volume_number(self, element: Tag) -> int | None:
        """Extract volume number from an element if it's a volume header.

        Args:
            element: The element to check.

        Returns:
            The volume number if this is a volume header, None otherwise.
        """
        text = element.get_text(strip=True)

        # Don't match chapter links as volumes
        if element.name == "a" and "/chapters/" in element.get("href", ""):
            return None

        # Pattern to match "Volume X" or "Vol. X" or "Vol X"
        patterns = [
            r"^Volume\s+(\d+)",
            r"^Vol\.?\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def get_series_name(self) -> str | None:
        """Get the series name from the page.

        Returns:
            The series name or None if not found.
        """
        # Series name is typically in an h2 tag or title
        name_elem = self.soup.select_one("h2.tag-title, h2#tag-title, h2")
        if name_elem:
            # Get the text, excluding any child "b" tags that might contain "Series"
            for b_tag in name_elem.find_all("b"):
                b_tag.decompose()
            return name_elem.get_text(strip=True)
        return None

    def get_description(self) -> str | None:
        """Get the series description/summary from the page.

        Returns:
            The description text or None if not found.
        """
        # Description is in a paragraph element within the tag-content-summary div
        summary_div = self.soup.select_one(".tag-content-summary, .description, #description")
        if summary_div:
            # Get the text content
            text = summary_div.get_text(strip=True)
            if text:
                return text

        # Fallback: Look for paragraphs that appear to be descriptions
        # (longer text blocks near the top of the page)
        for p in self.soup.select("p"):
            text = p.get_text(strip=True)
            # Skip very short paragraphs or those that look like metadata
            if len(text) > 100 and not text.startswith(("Tags:", "Author:", "Status:")):
                return text

        return None

    def get_cover_image_url(self) -> str | None:
        """Get the cover image URL from the page.

        Returns:
            The cover image URL or None if not found.
        """
        # Cover images are stored in /system/tag_contents_covers/
        cover_img = self.soup.select_one('img[src*="tag_contents_covers"]')
        if cover_img:
            src = cover_img.get("src", "")
            if src:
                # Return the full URL if it's relative
                if src.startswith("/"):
                    return f"https://dynasty-scans.com{src}"
                return src
        return None

    def get_tags(self) -> list[str]:
        """Get the tags associated with this series.

        Returns:
            List of tag names.
        """
        tags: list[str] = []

        # Tags are typically in a section with links to /tags/
        # Look for the tags container (usually has class "tags" or similar)
        tags_container = self.soup.select_one(".tag-tags, .tags")
        if tags_container:
            for tag_link in tags_container.select('a[href*="/tags/"]'):
                tag_text = tag_link.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
            if tags:
                return tags

        # Fallback: find all tag links on the page
        for tag_link in self.soup.select('a[href*="/tags/"]'):
            tag_text = tag_link.get_text(strip=True)
            # Skip if it looks like the series name or navigation
            if tag_text and len(tag_text) < 50:
                tags.append(tag_text)

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags


def get_chapter_volumes(html: str) -> dict[str, int]:
    """Convenience function to get chapter volume mapping from series HTML.

    Args:
        html: The series page HTML.

    Returns:
        Dictionary mapping chapter URL paths to volume numbers.
    """
    parser = SeriesPageParser(html)
    return parser.get_chapter_volumes()
