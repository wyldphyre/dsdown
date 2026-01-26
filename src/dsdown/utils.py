"""Shared utility functions."""

from __future__ import annotations

import re


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Args:
        name: The string to sanitize.

    Returns:
        A filename-safe string.
    """
    invalid_chars = '<>:"/\\|?*'
    result = name
    for char in invalid_chars:
        result = result.replace(char, "_")
    return result.strip()


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
