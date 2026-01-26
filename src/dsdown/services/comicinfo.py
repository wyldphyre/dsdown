"""ComicInfo.xml generation for CBZ files."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from dsdown.models.chapter import Chapter


def extract_chapter_number(title: str) -> str | None:
    """Extract chapter number from a chapter title.

    Args:
        title: The chapter title (e.g., 'Series Name ch001' or 'Chapter 15').

    Returns:
        The chapter number as a string, or None if not found.
    """
    patterns = [
        r"\bch\.?\s*(\d+(?:\.\d+)?)",  # ch1, ch.1, ch 1, ch01
        r"\bchapter\s*(\d+(?:\.\d+)?)",  # chapter 1, chapter01
        r"\bc(\d+(?:\.\d+)?)\b",  # c1, c01 (standalone)
        r"#(\d+(?:\.\d+)?)",  # #1, #01
        r"\b(\d+(?:\.\d+)?)\s*$",  # trailing number
    ]

    title_lower = title.lower()
    for pattern in patterns:
        match = re.search(pattern, title_lower, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_title_without_chapter(title: str, series_name: str | None) -> str | None:
    """Extract the title portion after removing series name and chapter number.

    Args:
        title: The full chapter title.
        series_name: The series name to remove.

    Returns:
        The remaining title text, or None if nothing meaningful remains.
    """
    result = title

    # Remove series name if present
    if series_name:
        if result.lower().startswith(series_name.lower()):
            result = result[len(series_name) :].strip()

    # Remove chapter number patterns
    patterns = [
        r"^\s*ch\.?\s*\d+(?:\.\d+)?\s*:?\s*",  # ch1:, ch.1:, ch 1:
        r"^\s*chapter\s*\d+(?:\.\d+)?\s*:?\s*",  # chapter 1:
        r"^\s*c\d+(?:\.\d+)?\s*:?\s*",  # c1:
        r"^\s*#\d+(?:\.\d+)?\s*:?\s*",  # #1:
        r"^\s*-\s*",  # leading dash
    ]

    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()

    # If nothing meaningful remains, return None
    if not result or result == title:
        return None

    return result


def generate_comicinfo_xml(chapter: Chapter, page_count: int | None = None) -> str:
    """Generate ComicInfo.xml content for a chapter.

    Args:
        chapter: The chapter to generate metadata for.
        page_count: Optional number of pages in the chapter.

    Returns:
        XML string for ComicInfo.xml.
    """
    root = ET.Element("ComicInfo")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    # Series
    if chapter.series:
        series_elem = ET.SubElement(root, "Series")
        series_elem.text = chapter.series.name

    # Number (chapter number)
    chapter_num = extract_chapter_number(chapter.title)
    if chapter_num:
        number_elem = ET.SubElement(root, "Number")
        number_elem.text = chapter_num

    # Volume
    if chapter.volume is not None:
        volume_elem = ET.SubElement(root, "Volume")
        volume_elem.text = str(chapter.volume)

    # Title (the subtitle/name portion after chapter number)
    series_name = chapter.series.name if chapter.series else None
    subtitle = extract_title_without_chapter(chapter.title, series_name)
    if subtitle:
        title_elem = ET.SubElement(root, "Title")
        title_elem.text = subtitle

    # Writer (authors)
    if chapter.authors:
        writer_elem = ET.SubElement(root, "Writer")
        writer_elem.text = ", ".join(chapter.authors)

    # Tags
    if chapter.tags:
        tags_elem = ET.SubElement(root, "Tags")
        tags_elem.text = ", ".join(chapter.tags)

    # Release date
    if chapter.release_date:
        year_elem = ET.SubElement(root, "Year")
        year_elem.text = str(chapter.release_date.year)
        month_elem = ET.SubElement(root, "Month")
        month_elem.text = str(chapter.release_date.month)
        day_elem = ET.SubElement(root, "Day")
        day_elem.text = str(chapter.release_date.day)

    # Page count
    if page_count is not None:
        page_count_elem = ET.SubElement(root, "PageCount")
        page_count_elem.text = str(page_count)

    # Manga indicator - default to right-to-left unless tagged otherwise
    manga_elem = ET.SubElement(root, "Manga")
    if any(tag.lower() == "read left to right" for tag in chapter.tags):
        manga_elem.text = "Yes"
    else:
        manga_elem.text = "YesAndRightToLeft"

    # Generate XML string with declaration
    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}


def add_comicinfo_to_cbz(cbz_path: Path, chapter: Chapter) -> None:
    """Add or update ComicInfo.xml in a CBZ file.

    Args:
        cbz_path: Path to the CBZ file.
        chapter: The chapter to generate metadata for.
    """
    # Read existing contents and count images
    with zipfile.ZipFile(cbz_path, "r") as zf:
        existing_files = {name: zf.read(name) for name in zf.namelist() if name != "ComicInfo.xml"}

    # Count image files
    page_count = sum(
        1 for name in existing_files if Path(name).suffix.lower() in IMAGE_EXTENSIONS
    )

    comicinfo_xml = generate_comicinfo_xml(chapter, page_count)

    # Write back with ComicInfo.xml (use STORED since images are already compressed)
    with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_STORED) as zf:
        # Write ComicInfo.xml first
        zf.writestr("ComicInfo.xml", comicinfo_xml)
        # Write all other files
        for name, data in existing_files.items():
            zf.writestr(name, data)
